"""
RAG 问答服务（生产级检索链路）

链路：
  Query → Router(分类) → Rewriter(改写+HyDE)
       → 多查询 Dense+Sparse 粗排 → 去重合并
       → CrossEncoder Rerank 一次精排
       → LLM 生成回答

优化要点：
- 检索只跑一次，不在 Chain 里重复触发
- Rerank 只在最后统一跑一次（而非每条改写都跑）
"""

import json
import logging
import asyncio
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, AsyncGenerator

from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.config import settings
from app.services.prompt import build_prompt_template, format_context
from app.services.hybrid_searcher import get_hybrid_searcher
from app.services.query_rewriter import get_query_rewriter
from app.services.router import get_router
from app.services.reranker import CrossEncoderReranker
from app.models.search import SearchResult

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


def _full_search_sync(query: str, top_k: int, event_q: queue.Queue, owner: str = "") -> list[dict]:
    """在后台线程中运行检索，owner 用于多用户数据隔离"""
    def _emit(step: str, msg: str):
        event_q.put({"step": step, "message": msg})
        logger.info(f"[Progress] {step}: {msg}")

    searcher = get_hybrid_searcher()
    router = get_router()
    rewriter = get_query_rewriter()

    # Step 1: Router + Rewriter 并行
    _emit("route", "正在分析问题类型并改写查询...")
    future_route = _executor.submit(router.get_config, query)
    future_rewrite = _executor.submit(rewriter.rewrite, query, True)

    route_config = future_route.result()
    rewritten_queries = future_rewrite.result()

    search_top_k = route_config.get("top_k", top_k)
    enable_sparse = route_config.get("enable_sparse", True)
    enable_rerank = route_config.get("enable_rerank", True)
    recall_k = max(search_top_k * 3, 10)

    _emit("rewrite", f"问题分类: {route_config.get('query_type','?')}，改写 {len(rewritten_queries)} 条查询，启动多路召回")

    # Step 2: 多路召回
    _emit("search", "正在执行语义检索 + 关键词检索...")
    seen: set[str] = set()
    all_results: list[dict] = []

    for q in rewritten_queries:
        results = searcher.search(q, top_k=recall_k, enable_sparse=enable_sparse, enable_rerank=False, owner=owner)
        for r in results:
            key = r.content[:80]
            if key not in seen:
                seen.add(key)
                all_results.append(r.to_dict())

    all_results.sort(key=lambda x: x["score"], reverse=True)
    _emit("search", f"多路召回完成，共 {len(all_results)} 条候选")

    # Step 3: Rerank
    if enable_rerank and all_results:
        _emit("rerank", f"正在 Cross-Encoder 精排 {min(len(all_results), 10)} 条候选...")
        _valid_fields = {f.name for f in SearchResult.__dataclass_fields__.values()}
        candidates = [
            SearchResult(**{k: v for k, v in r.items() if k in _valid_fields})
            for r in all_results[:6]
        ]
        reranker = CrossEncoderReranker()
        final = reranker.rerank(query, candidates, top_k=search_top_k)
        final_dicts = [r.to_dict() for r in final]
    else:
        final_dicts = all_results[:search_top_k]

    _emit("done", f"检索完成，精选 {len(final_dicts)} 条参考资料")
    return final_dicts


def ask(question: str, owner: str = "") -> Dict[str, Any]:
    """同步问答"""
    q: queue.Queue = queue.Queue()
    retrieved = _full_search_sync(question, 4, q, owner=owner)
    context = format_context(retrieved)
    llm = ChatOpenAI(
        model=settings.llm_model, openai_api_key=settings.llm_api_key.get_secret_value(),
        openai_api_base=settings.llm_api_base, temperature=0.1,
    )
    prompt = build_prompt_template()
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})
    return {"answer": answer, "sources": retrieved}


async def ask_stream(question: str, owner: str = "") -> AsyncGenerator[str, None]:
    """流式问答——SSE 实时进度 + 最终结果，owner 用于用户隔离"""
    event_q: queue.Queue = queue.Queue()
    loop = asyncio.get_event_loop()

    future = loop.run_in_executor(_executor, _full_search_sync, question, 4, event_q, owner)

    # 实时消费事件（每 100ms 检查一次队列）
    while not future.done() or not event_q.empty():
        try:
            evt = event_q.get_nowait()
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except queue.Empty:
            await asyncio.sleep(0.1)

    # 排空最后的事件
    while not event_q.empty():
        evt = event_q.get_nowait()
        yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    retrieved = future.result()

    # Phase 2: LLM 生成
    yield f"data: {json.dumps({'step': 'generate', 'message': '正在 LLM 生成回答...'}, ensure_ascii=False)}\n\n"

    context = format_context(retrieved)
    llm = ChatOpenAI(
        model=settings.llm_model, openai_api_key=settings.llm_api_key.get_secret_value(),
        openai_api_base=settings.llm_api_base, temperature=0.1,
    )
    prompt = build_prompt_template()
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    # Phase 3: 最终结果
    result = {"step": "result", "answer": answer, "sources": retrieved}
    yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"

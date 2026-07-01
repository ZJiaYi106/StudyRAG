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

并发设计（重要，防止服务级联冻结）：
- 本模块被 async 路由 await 调用。任何同步阻塞调用（检索、chain.invoke）
  都会阻塞事件循环，导致"一个用户提问、所有人无响应"。
  因此：检索链路在 _search_executor 线程池中执行；
  LLM 生成使用 chain.ainvoke / chain.astream 异步等待。
- 两个线程池严格分离：外层问答任务用 _search_executor，
  检索内部 Router/Rewriter 的 LLM 调用用 _llm_executor。
  若共用一个池，当并发请求数达到 max_workers 时，外层任务占满
  worker 又在同一池里等待内层任务，内层任务永远无法被调度，
  造成线程池饥饿死锁（所有请求挂起且不自愈）。
"""

import json
import logging
import asyncio
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, AsyncGenerator, List

from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.config import settings
from app.services.prompt import build_prompt_template, format_context
from app.services.hybrid_searcher import get_hybrid_searcher
from app.services.query_rewriter import get_query_rewriter
from app.services.router import get_router
from app.services.reranker import get_reranker_service
from app.models.search import SearchResult

logger = logging.getLogger(__name__)

# ================================================================
# 线程池（两层分离，防饥饿死锁）
# ================================================================
# 外层：每个问答请求的完整检索链路占一个 worker
_search_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="rag-search")
# 内层：检索链路中的 LLM 辅助调用（Router 分类 / Rewriter 改写）
_llm_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="rag-llm")

# 送入 Cross-Encoder 精排的候选数（进度提示与实际截取必须一致）
RERANK_CANDIDATE_K = 6


def _sse(obj: dict) -> str:
    """把事件对象序列化为一行 SSE 数据帧"""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _full_search_sync(query: str, top_k: int, event_q: queue.Queue, owner: str = "") -> list[dict]:
    """在后台线程中运行检索，owner 用于多用户数据隔离"""
    def _emit(step: str, msg: str):
        event_q.put({"step": step, "message": msg})
        logger.info(f"[Progress] {step}: {msg}")

    searcher = get_hybrid_searcher()
    router = get_router()
    rewriter = get_query_rewriter()

    # Step 1: Router + Rewriter 并行
    # 注意：提交到 _llm_executor（与外层任务分池，防死锁）
    _emit("route", "正在分析问题类型并改写查询...")
    future_route = _llm_executor.submit(router.get_config, query)
    future_rewrite = _llm_executor.submit(rewriter.rewrite, query, True)

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

    # Step 3: Rerank（模型未加载时自动跳过，降级为粗排结果，问答仍可用）
    reranker = get_reranker_service()
    if enable_rerank and all_results and reranker.is_ready():
        candidate_count = min(len(all_results), RERANK_CANDIDATE_K)
        _emit("rerank", f"正在 Cross-Encoder 精排 {candidate_count} 条候选...")
        _valid_fields = {f.name for f in SearchResult.__dataclass_fields__.values()}
        candidates = [
            SearchResult(**{k: v for k, v in r.items() if k in _valid_fields})
            for r in all_results[:RERANK_CANDIDATE_K]
        ]
        final = reranker.rerank(query, candidates, top_k=search_top_k)
        final_dicts = [r.to_dict() for r in final]
    else:
        if enable_rerank and all_results and not reranker.is_ready():
            _emit("rerank", "未加载重排模型，跳过精排（可在左侧“重排模型”面板加载）")
        final_dicts = all_results[:search_top_k]

    _emit("done", f"检索完成，精选 {len(final_dicts)} 条参考资料")
    return final_dicts


def _build_llm() -> ChatOpenAI:
    """构建生成用的 ChatOpenAI 实例"""
    return ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.llm_api_key.get_secret_value(),
        openai_api_base=settings.llm_api_base,
        temperature=0.1,
    )


async def ask(question: str, owner: str = "") -> Dict[str, Any]:
    """异步问答：检索在线程池执行，LLM 异步生成，全程不阻塞事件循环"""
    event_q: queue.Queue = queue.Queue()
    loop = asyncio.get_running_loop()
    retrieved = await loop.run_in_executor(
        _search_executor, _full_search_sync, question, 4, event_q, owner
    )

    context = format_context(retrieved)
    chain = build_prompt_template() | _build_llm() | StrOutputParser()
    answer = await chain.ainvoke({"context": context, "question": question})
    return {"answer": answer, "sources": retrieved}


async def ask_stream(question: str, owner: str = "") -> AsyncGenerator[str, None]:
    """流式问答——SSE 检索进度 + LLM token 级逐字输出，owner 用于用户隔离"""
    event_q: queue.Queue = queue.Queue()
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(_search_executor, _full_search_sync, question, 4, event_q, owner)

    # Phase 1: 实时转发检索进度事件（检索在后台线程，事件循环保持空闲）
    while not future.done() or not event_q.empty():
        try:
            evt = event_q.get_nowait()
            yield _sse(evt)
        except queue.Empty:
            await asyncio.sleep(0.1)

    # 排空最后的事件
    while not event_q.empty():
        yield _sse(event_q.get_nowait())

    # 检索线程若抛出异常，转为 SSE error 事件（响应已开始，无法再改 HTTP 状态码）
    try:
        retrieved = future.result()
    except Exception as e:
        logger.error(f"[问答SSE] 检索阶段失败: {e}")
        yield _sse({"step": "error", "message": f"检索失败: {e}"})
        return

    # Phase 2: LLM 逐 token 流式生成（astream，等待期间不占用事件循环）
    yield _sse({"step": "generate", "message": "正在 LLM 生成回答..."})

    context = format_context(retrieved)
    chain = build_prompt_template() | _build_llm() | StrOutputParser()

    answer_parts: List[str] = []
    try:
        async for token in chain.astream({"context": context, "question": question}):
            answer_parts.append(token)
            yield _sse({"step": "token", "content": token})
    except Exception as e:
        logger.error(f"[问答SSE] LLM 生成失败: {e}")
        yield _sse({"step": "error", "message": f"生成失败: {e}"})
        return

    # Phase 3: 最终结果（前端收到后收尾）
    result = {"step": "result", "answer": "".join(answer_parts), "sources": retrieved}
    yield _sse(result)

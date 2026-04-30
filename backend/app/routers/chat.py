"""
问答 API 路由
接收用户问题，基于 RAG 管道返回基于文档的回答

数据流：
  ChatRequest → retrieve() → format_context() → RAG Chain → ChatResponse
                    ↓
              sources（返回给前端展示引用卡片）
"""

import logging
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse, SourceInfo
from app.services.chain import ask
from app.utils.registry import list_records

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["问答"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    基于已上传文档的 RAG 问答。

    完整流程：
    1. 检查是否有已上传的文档（无文档时提示用户）
    2. 向量检索最相关的资料片段
    3. 构建带引用来源的 Prompt
    4. LLM 基于参考资料生成中文回答
    5. 返回答案 + 引用来源列表
    """
    logger.info(f"[问答] 收到提问: {request.question[:50]}...")

    # 检查知识库是否为空
    docs = list_records()
    if not docs:
        raise HTTPException(
            status_code=400,
            detail="知识库中没有文档。请先上传 PDF 或 Markdown 文件后再提问。"
        )

    # 执行 RAG 问答
    try:
        result = ask(request.question)
    except Exception as e:
        logger.error(f"[问答] RAG Chain 执行失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"问答处理失败: {e}"
        )

    # 构建来源信息列表
    sources = []
    for item in result["sources"]:
        sources.append(SourceInfo(
            filename=item["filename"],
            page=item.get("page"),
            chapter=item.get("chapter"),
            excerpt=item.get("excerpt", item.get("content", "")[:200]),
            score=item["score"],
        ))

    logger.info(
        f"[问答] 完成: 返回 {len(sources)} 个来源, "
        f"回答长度 {len(result['answer'])} 字"
    )

    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        question=request.question,
    )

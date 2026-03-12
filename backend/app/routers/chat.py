"""
问答 API 路由
接收用户问题，基于 RAG 管道返回基于文档的回答
"""

import logging
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["问答"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    基于已上传文档的 RAG 问答。
    检索相关片段 → 构建 Prompt → LLM 生成中文回答。
    """
    # TODO: 步骤 7 实现完整 RAG Chain
    logger.info(f"收到提问: {request.question[:50]}...")
    raise HTTPException(status_code=501, detail="问答功能将在步骤 7 实现")

"""
StudyRAG FastAPI 应用入口
启动: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import documents, chat

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# --- 应用生命周期管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的生命周期事件"""
    # 启动时
    logger.info("=" * 50)
    logger.info("StudyRAG 启动中...")
    logger.info(f"LLM 模型: {settings.llm_model}")
    logger.info(f"Embedding 模型: {settings.embedding_model}")
    logger.info(f"上传目录: {settings.upload_dir}")

    # 确保上传目录存在
    os.makedirs(settings.upload_dir, exist_ok=True)

    logger.info("=" * 50)
    yield
    # 关闭时
    logger.info("StudyRAG 正在关闭...")


# --- 创建 FastAPI 应用 ---
app = FastAPI(
    title="StudyRAG",
    description="面向课程资料、论文和个人笔记的 RAG 知识库问答系统",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS 中间件（允许前端跨域访问） ---
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 注册路由 ---
app.include_router(documents.router)
app.include_router(chat.router)


# --- 健康检查端点 ---
@app.get("/api/health", tags=["系统"])
async def health_check():
    """
    健康检查：验证 API、Chroma、文档数量。
    """
    try:
        from app.services.vectorstore import get_collection_stats
        stats = get_collection_stats()
        chroma_status = "ok"
        doc_count = stats.get("count", 0)
    except Exception as e:
        chroma_status = f"error: {e}"
        doc_count = 0

    return {
        "status": "ok",
        "service": "StudyRAG",
        "version": "0.1.0",
        "chroma": chroma_status,
        "document_count": doc_count,
    }



"""
重排模型管理 API
手动加载 / 卸载 / 查询状态 / 列出可选模型

模型加载是耗时操作（首次需下载 ~1.2GB），因此：
- POST /load 立即返回，加载在后台线程进行；
- 前端通过 GET /status 轮询，直到 loading=False。
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.services.reranker import get_reranker_service, RERANKER_CATALOG
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reranker", tags=["重排模型"])


def _default_model_path() -> str:
    """取推荐模型路径，回退到配置项"""
    for m in RERANKER_CATALOG:
        if m.get("recommended"):
            return m["path"]
    if RERANKER_CATALOG:
        return RERANKER_CATALOG[0]["path"]
    return settings.rerank_model_path


@router.get("/status")
async def status(user: str = Depends(get_current_user)):
    """查询重排模型当前状态（是否已加载 / 加载中 / 错误信息 / 可选模型列表）"""
    return get_reranker_service().status()


@router.post("/load")
async def load(body: dict | None = None, user: str = Depends(get_current_user)):
    """
    触发模型加载（异步，立即返回；前端轮询 /status 直到 loading=False）。

    body.model: 模型路径（HuggingFace 名称或本地目录），为空时取推荐模型。
    """
    body = body or {}
    model_path = body.get("model") or _default_model_path()
    if not model_path:
        raise HTTPException(status_code=400, detail="未指定模型，且无可选模型")

    started = get_reranker_service().start_load(model_path)
    if not started:
        raise HTTPException(status_code=409, detail="模型正在加载中，请勿重复触发")

    logger.info(f"[RerankerAPI] 用户 {user} 触发加载模型: {model_path}")
    return {"loading": True, "model": model_path}


@router.post("/unload")
async def unload(user: str = Depends(get_current_user)):
    """卸载已加载的重排模型，释放内存"""
    logger.info(f"[RerankerAPI] 用户 {user} 卸载重排模型")
    get_reranker_service().unload()
    return get_reranker_service().status()

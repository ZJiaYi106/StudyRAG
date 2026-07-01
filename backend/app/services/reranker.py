"""
Cross-Encoder 重排序服务

精排（Cross-Encoder）：把 query 与候选拼接送入模型做二分类，
判断"这段能否回答这个问题"，比粗排（向量/关键词）更精确但更慢。

模型加载策略（重要）：
- 模型文件较大（~1.2GB），首次需从 HuggingFace 下载，耗时较长，
  且可能因网络问题失败。
- 因此不随服务启动自动加载，而是由前端用户手动触发加载，
  并可选择重排模型。加载期间问答链路自动跳过精排
  （降级为粗排结果，问答仍可用）。
- 加载在独立单线程池中执行，不阻塞事件循环，也不与检索线程池争抢。
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from app.config import settings
from app.services.interfaces import BaseReranker
from app.models.search import SearchResult

logger = logging.getLogger(__name__)

# ================================================================
# 可选重排模型目录（前端选择器数据源）
# 新增模型只需在此追加一项，前端自动出现新选项
# ================================================================
RERANKER_CATALOG: list[dict] = [
    {
        "id": "bge-reranker-v2-m3",
        "path": "BAAI/bge-reranker-v2-m3",
        "name": "bge-reranker-v2-m3",
        "size": "~1.2GB",
        "desc": "多语言 + 中文友好，效果 SOTA",
        "recommended": True,
    },
]

# 加载专用单线程池（模型下载/装载耗时，独占线程，避免与检索池争用）
_load_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rerank-load")


class RerankerService:
    """重排模型管理单例：加载 / 卸载 / 状态查询 / 精排"""

    def __init__(self):
        self._model: Optional[object] = None
        self._loaded_path: Optional[str] = None
        self._loading: bool = False
        self._error: Optional[str] = None
        self._lock = threading.Lock()

    # ---------- 状态 ----------
    def status(self) -> dict:
        with self._lock:
            return {
                "loaded": self._model is not None,
                "loading": self._loading,
                "model": self._loaded_path,
                "error": self._error,
                "available": RERANKER_CATALOG,
            }

    def is_ready(self) -> bool:
        """模型是否已就绪，可用于精排"""
        return self._model is not None

    # ---------- 加载 / 卸载 ----------
    def _construct(self, model_path: str):
        """构造 CrossEncoder 实例（单独方法，便于测试 mock）"""
        from sentence_transformers import CrossEncoder
        return CrossEncoder(model_path, trust_remote_code=True)

    def load(self, model_path: str) -> None:
        """同步加载模型（由 _load_executor 在后台线程调度）"""
        with self._lock:
            if self._loading:
                return  # 已在加载，忽略重复请求
            self._loading = True
            self._error = None
        logger.info(f"[Reranker] 开始加载模型: {model_path} ...")
        try:
            model = self._construct(model_path)
            with self._lock:
                self._model = model
                self._loaded_path = model_path
            logger.info(f"[Reranker] 模型加载完成: {model_path}")
        except Exception as e:
            with self._lock:
                self._error = str(e)
            logger.error(f"[Reranker] 模型加载失败: {e}")
        finally:
            with self._lock:
                self._loading = False

    def start_load(self, model_path: str) -> bool:
        """异步触发加载（立即返回）；返回 False 表示当前已在加载"""
        with self._lock:
            if self._loading:
                return False
        _load_executor.submit(self.load, model_path)
        return True

    def unload(self) -> None:
        """卸载模型，释放内存"""
        with self._lock:
            self._model = None
            self._loaded_path = None
            self._error = None
        logger.info("[Reranker] 模型已卸载，释放内存")

    # ---------- 精排 ----------
    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 4,
    ) -> List[SearchResult]:
        """
        对候选结果精排。模型未加载时降级为直接截断返回（不报错）。
        """
        model = self._model  # 读指针；加载中可能为 None（此时降级跳过）
        if model is None or not candidates:
            return candidates[:top_k]

        pairs = [(query, c.content) for c in candidates]
        scores = model.predict(pairs, show_progress_bar=False)

        for i, score in enumerate(scores):
            candidates[i].score = round(float(score), 4)
            candidates[i].source = "rerank"

        candidates.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"[Reranker] 重排完成: {len(candidates)} 条 → 返回 top {top_k}")
        return candidates[:top_k]


# 全局单例
_reranker_service: Optional[RerankerService] = None


def get_reranker_service() -> RerankerService:
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service


class CrossEncoderReranker(BaseReranker):
    """兼容旧调用方：委托给 RerankerService 单例"""

    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 4,
    ) -> List[SearchResult]:
        return get_reranker_service().rerank(query, candidates, top_k=top_k)

"""
Cross-Encoder 重排序器
对粗排结果进行精细排序，大幅提升检索精度。

粗排 vs 精排：
- 粗排（Dense/BM25）：速度快，向量/关键词匹配，但不够精准
- 精排（Cross-Encoder）：将 query 和候选直接拼接送入模型做二分类，
  判断"这段能否回答这个问题"，更精确但更慢。

使用 BAAI/bge-reranker-v2-m3（中文友好，效果 SOTA）。
首次运行会自动下载模型（约 1.2GB），后续使用本地缓存。
"""

import logging
from typing import List, Optional

from app.config import settings
from app.services.interfaces import BaseReranker
from app.models.search import SearchResult

logger = logging.getLogger(__name__)

# 懒加载
_reranker_model: Optional[object] = None


def _get_model():
    """懒加载 Cross-Encoder 模型"""
    global _reranker_model
    if _reranker_model is None:
        model_source = settings.rerank_model_path
        logger.info(f"[Reranker] 正在加载模型: {model_source} ...")
        from sentence_transformers import CrossEncoder
        _reranker_model = CrossEncoder(
            model_source,
            trust_remote_code=True,
        )
        logger.info("[Reranker] 模型加载完成")
    return _reranker_model


class CrossEncoderReranker(BaseReranker):
    """
    Cross-Encoder 重排序器。

    对每条 query-candidate pair 打分，返回按新分数降序排列的结果。
    """

    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 4,
    ) -> List[SearchResult]:
        if not candidates:
            return []

        model = _get_model()

        # 构建 query-doc pairs
        pairs = [(query, c.content) for c in candidates]

        # 批量打分
        scores = model.predict(pairs, show_progress_bar=False)

        # 更新分数并排序
        for i, score in enumerate(scores):
            candidates[i].score = round(float(score), 4)
            candidates[i].source = "rerank"

        candidates.sort(key=lambda x: x.score, reverse=True)

        logger.info(
            f"[Reranker] 重排完成: {len(candidates)} 条 → 返回 top {top_k}"
        )
        return candidates[:top_k]

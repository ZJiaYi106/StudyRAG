"""
混合检索引擎——完整检索链路的编排器。

链路：
  Query → [DenseRetriever + SparseRetriever] 多路召回
       → RRF Fusion 融合
       → CrossEncoderReranker 精排
       → 返回 Top-K 结果

这是生产级 RAG 检索的核心，可以从配置控制每一步的开关。
"""

import logging
from typing import List, Optional

from app.config import settings
from app.models.search import SearchResult
from app.services.retrievers.dense_retriever import DenseRetriever
from app.services.retrievers.bm25_retriever import BM25Retriever, get_bm25_retriever
from app.services.fusion import reciprocal_rank_fusion
from app.services.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


class HybridSearcher:
    """
    混合检索编排器。

    配置项（通过 settings 控制）：
    - hybrid_enable_sparse: 是否启用 BM25 关键词检索
    - hybrid_enable_rerank: 是否启用 Cross-Encoder 重排
    - hybrid_recall_k: 各路召回的候选数
    - hybrid_final_k: 最终返回的结果数
    """

    def __init__(self):
        self.dense = DenseRetriever()
        self.bm25 = get_bm25_retriever()
        self.reranker = CrossEncoderReranker()

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        enable_sparse: bool = True,
        enable_rerank: bool = True,
        owner: str = "",
    ) -> List[SearchResult]:
        """
        执行完整的混合检索链路。

        Args:
            query: 用户问题
            top_k: 最终返回结果数（默认 4）
            enable_sparse: 是否启用 BM25 关键词召回
            enable_rerank: 是否启用 Cross-Encoder 重排
            owner: 多用户隔离——只检索该用户的文档
        """
        final_k = top_k or settings.top_k
        recall_k = final_k * 3  # 召回阶段多取一些候选

        # ================================================================
        # Step 1: 多路召回
        # ================================================================
        recall_sets = []

        # 语义检索（必选），owner 作为显式参数传递
        dense_results = self.dense.retrieve(query, top_k=recall_k, owner=owner)
        recall_sets.append(dense_results)
        logger.info(f"[HybridSearch] Dense 召回: {len(dense_results)} 条")

        # BM25 关键词检索（可选），同样按 owner 过滤
        if enable_sparse:
            sparse_results = self.bm25.retrieve(query, top_k=recall_k, owner=owner)
            recall_sets.append(sparse_results)
            logger.info(f"[HybridSearch] Sparse 召回: {len(sparse_results)} 条")

        # ================================================================
        # Step 2: RRF 融合
        # ================================================================
        if len(recall_sets) > 1:
            fused = reciprocal_rank_fusion(recall_sets, final_top_k=max(final_k * 2, 8))
            logger.info(f"[HybridSearch] RRF 融合后: {len(fused)} 条")
        else:
            fused = dense_results

        # ================================================================
        # Step 3: Cross-Encoder 重排（可选）
        # ================================================================
        if enable_rerank and fused:
            final = self.reranker.rerank(query, fused, top_k=final_k)
        else:
            final = fused[:final_k]

        logger.info(
            f"[HybridSearch] 检索完成: "
            f"召回 {sum(len(s) for s in recall_sets)} → "
            f"融合 {len(fused)} → "
            f"最终 {len(final)} 条"
        )
        return final


# 全局单例
_hybrid_searcher: Optional[HybridSearcher] = None


def get_hybrid_searcher() -> HybridSearcher:
    global _hybrid_searcher
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher()
    return _hybrid_searcher

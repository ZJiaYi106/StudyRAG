"""
多路召回结果融合
使用 Reciprocal Rank Fusion (RRF) 算法合并稠密和稀疏检索结果。

RRF 原理：
- 对每个结果，按它在各路检索中的排名计算得分：
  RRF_score(d) = Σ 1 / (k + rank_i(d))
- k 是平滑参数（默认 60），防止某一路中排名靠后的结果被过度惩罚
- 最终按 RRF 分数降序排列

为什么用 RRF 而非简单合并？
- 不同检索器的分数不可直接比较（BM25 分数范围 vs cosine 相似度 0-1）
- RRF 只依赖排名，不依赖绝对分数，融合更公平
"""

import logging
from typing import List
from app.models.search import SearchResult

logger = logging.getLogger(__name__)

RRF_K = 60  # 平滑参数


def reciprocal_rank_fusion(
    result_sets: List[List[SearchResult]],
    k: int = RRF_K,
    final_top_k: int = 8,
) -> List[SearchResult]:
    """
    对多路检索结果做 RRF 融合。

    Args:
        result_sets: 各路检索的结果列表（如 [dense_results, sparse_results]）
        k: RRF 平滑参数
        final_top_k: 最终返回的结果数

    Returns:
        融合并排序后的 SearchResult 列表
    """
    if not result_sets:
        return []

    # 用 (content, filename) 作为去重 key
    rrf_scores: dict[str, float] = {}
    result_map: dict[str, SearchResult] = {}

    for results in result_sets:
        for rank, result in enumerate(results, start=1):
            key = f"{result.content[:80]}|{result.filename}"
            rrf_score = 1.0 / (k + rank)
            rrf_scores[key] = rrf_scores.get(key, 0) + rrf_score
            # 保留分数最高的那个来源的结果
            if key not in result_map or result.score > result_map[key].score:
                result_map[key] = result

    # 按 RRF 分数降序排列
    sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    top_keys = sorted_keys[:final_top_k]

    fused = []
    for key in top_keys:
        result = result_map[key]
        result.score = round(rrf_scores[key], 4)
        result.source = "fusion"
        fused.append(result)

    logger.info(
        f"[Fusion] RRF 融合: {sum(len(s) for s in result_sets)} 条输入"
        f" → {len(fused)} 条输出"
    )
    return fused

"""
稠密检索器（语义检索）
基于 Chroma 向量数据库的语义相似度搜索。
"""

import logging
from typing import List

from app.services.interfaces import BaseRetriever
from app.services.vectorstore import similarity_search
from app.models.search import SearchResult

logger = logging.getLogger(__name__)


class DenseRetriever(BaseRetriever):
    """
    语义检索器——基于 Chroma 的 cosine similarity 搜索。

    与 BM25Retriever 的区别：
    - Dense: 语义理解 "苹果手机" ≈ "iPhone"，但对精确关键词不敏感
    - Sparse: 精确匹配 "TR-9012" 等编号，但不理解同义词
    """

    def retrieve(self, query: str, top_k: int = 4, owner: str = "") -> List[SearchResult]:
        results = similarity_search(query, k=top_k, owner=owner)
        search_results = []
        for doc, score in results:
            search_results.append(SearchResult(
                content=doc.page_content,
                score=round(score, 4),
                filename=doc.metadata.get("filename", ""),
                page=doc.metadata.get("page"),
                chapter=doc.metadata.get("chapter"),
                document_id=doc.metadata.get("document_id", ""),
                chunk_index=doc.metadata.get("chunk_index", 0),
                source="dense",
            ))
        logger.info(f"[Dense] 检索完成，返回 {len(search_results)} 条结果")
        return search_results

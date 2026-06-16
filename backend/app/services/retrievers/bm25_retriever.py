"""
BM25 稀疏检索器（关键词匹配）
基于 rank_bm25 库，在内存中构建 BM25 索引。

BM25 vs 语义检索：
- BM25 擅长精确关键词匹配（如术语、编号、代码）
- 语义检索擅长理解同义词和语义相似（如"苹果手机"→"iPhone"）
- 两者互补，融合后可提升召回率
"""

import logging
from typing import List, Optional
from threading import Lock

from rank_bm25 import BM25Okapi
from langchain_core.documents import Document

from app.services.interfaces import BaseRetriever
from app.models.search import SearchResult

logger = logging.getLogger(__name__)


class BM25Retriever(BaseRetriever):
    """
    BM25 关键词检索器。

    维护一份全量 chunk 的 BM25 索引，随文档增删而重建。
    """

    def __init__(self):
        self._corpus: List[str] = []          # 所有 chunk 的文本
        self._metadata: List[dict] = []       # 对应 metadata
        self._bm25: Optional[BM25Okapi] = None
        self._lock = Lock()

    def _tokenize(self, text: str) -> List[str]:
        """简单分词：按字符 + 空格混合"""
        import jieba
        return list(jieba.cut(text))

    def _rebuild_index(self):
        """重建 BM25 索引"""
        if self._corpus:
            tokenized = [self._tokenize(text) for text in self._corpus]
            self._bm25 = BM25Okapi(tokenized)
        else:
            self._bm25 = None

    def add_chunks(self, chunks: List[Document]):
        """批量添加 chunk 到 BM25 索引"""
        with self._lock:
            for chunk in chunks:
                self._corpus.append(chunk.page_content)
                self._metadata.append(chunk.metadata)
            self._rebuild_index()
        logger.info(f"[BM25] 已添加 {len(chunks)} 个 chunk，索引总数: {len(self._corpus)}")

    def remove_by_document_id(self, document_id: str):
        """按 document_id 删除对应的 chunk"""
        with self._lock:
            keep_indices = [
                i for i, m in enumerate(self._metadata)
                if m.get("document_id") != document_id
            ]
            removed = len(self._corpus) - len(keep_indices)
            if removed > 0:
                self._corpus = [self._corpus[i] for i in keep_indices]
                self._metadata = [self._metadata[i] for i in keep_indices]
                self._rebuild_index()
            logger.info(f"[BM25] 已删除 {removed} 个 chunk，索引剩余: {len(self._corpus)}")

    def retrieve(self, query: str, top_k: int = 4, owner: str = "") -> List[SearchResult]:
        """
        BM25 关键词检索，owner 用于多用户过滤
        """
        if self._bm25 is None or not self._corpus:
            logger.warning("[BM25] 索引为空，返回空结果")
            return []

        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        # 按分数排序，取 top_k，同时按 owner 过滤
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, raw_score in indexed_scores:
            meta = self._metadata[idx]
            # owner 过滤
            if owner and meta.get("owner", "") != owner:
                continue
            results.append((idx, raw_score))
            if len(results) >= top_k * 2:  # 多取一些以应对过滤
                break

        # 归一化分数到 0-1
        if not results:
            return []
        max_score = results[0][1]
        min_score = results[-1][1]
        score_range = max_score - min_score or 1

        final_results = []
        for idx, raw_score in results[:top_k]:
            meta = self._metadata[idx]
            final_results.append(SearchResult(
                content=self._corpus[idx],
                score=round((raw_score - min_score) / score_range, 4),
                filename=meta.get("filename", ""),
                page=meta.get("page"),
                chapter=meta.get("chapter"),
                document_id=meta.get("document_id", ""),
                chunk_index=meta.get("chunk_index", 0),
                source="sparse",
            ))

        logger.info(f"[BM25] 检索完成，返回 {len(final_results)} 条结果 (owner={owner})")
        return final_results


# 全局单例
_bm25_instance: Optional[BM25Retriever] = None


def get_bm25_retriever() -> BM25Retriever:
    global _bm25_instance
    if _bm25_instance is None:
        _bm25_instance = BM25Retriever()
    return _bm25_instance

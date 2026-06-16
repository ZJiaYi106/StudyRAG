"""
服务工厂
根据配置创建具体的服务实例，实现可插拔架构。

新增一个组件只需：
1. 实现对应的抽象基类
2. 在工厂中注册
3. 通过配置或环境变量切换
"""

import logging
from app.models.search import SearchResult
from app.services.interfaces import (
    BaseLoader, BaseSplitter, BaseEmbedder,
    BaseRetriever, BaseReranker, BaseIndexer, BaseCache,
)

logger = logging.getLogger(__name__)

_services: dict = {}


def get_loader() -> BaseLoader:
    """获取文档加载器"""
    if "loader" not in _services:
        from app.services.loader import LoaderService
        _services["loader"] = LoaderService()
    return _services["loader"]


def get_splitter() -> BaseSplitter:
    """获取文本切分器"""
    if "splitter" not in _services:
        from app.services.splitter import SplitterService
        _services["splitter"] = SplitterService()
    return _services["splitter"]


def get_embedder() -> BaseEmbedder:
    """获取 Embedding 服务"""
    if "embedder" not in _services:
        from app.services.embeddings import EmbeddingService
        _services["embedder"] = EmbeddingService()
    return _services["embedder"]


def get_indexer() -> BaseIndexer:
    """获取索引服务"""
    if "indexer" not in _services:
        from app.services.vectorstore import ChromaIndexer
        _services["indexer"] = ChromaIndexer()
    return _services["indexer"]


def get_dense_retriever() -> BaseRetriever:
    """获取稠密检索器（语义检索）"""
    if "dense_retriever" not in _services:
        from app.services.retrievers.dense_retriever import DenseRetriever
        _services["dense_retriever"] = DenseRetriever()
    return _services["dense_retriever"]


def get_sparse_retriever() -> BaseRetriever:
    """获取稀疏检索器（BM25 关键词）"""
    if "sparse_retriever" not in _services:
        from app.services.retrievers.bm25_retriever import BM25Retriever
        _services["sparse_retriever"] = BM25Retriever()
    return _services["sparse_retriever"]


def get_reranker() -> BaseReranker:
    """获取重排序器"""
    if "reranker" not in _services:
        from app.services.reranker import CrossEncoderReranker
        _services["reranker"] = CrossEncoderReranker()
    return _services["reranker"]


def get_cache(name: str = "default") -> BaseCache:
    """获取缓存服务"""
    key = f"cache_{name}"
    if key not in _services:
        from app.services.cache.memory_cache import MemoryCache
        _services[key] = MemoryCache()
    return _services[key]


def reset_services():
    """重置所有服务（测试用）"""
    _services.clear()

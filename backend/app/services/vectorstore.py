"""
Chroma 向量存储服务
使用 LangChain Chroma 封装实现文档的向量化存储与检索

LangChain 组件 #4：Chroma VectorStore（向量存储）
- 作用：存储文档的向量表示 + 原始文本 + 元数据，支持相似度检索
- 核心操作：
  - add_documents(List[Document]): 向量化文档并存入数据库
  - similarity_search_with_score(query, k): 按余弦相似度检索 Top-K
  - delete(where={...}): 按 metadata 条件批量删除

为什么需要 VectorStore？
  用户提问 → 向量化 → 在向量空间中找最近的 K 个文档向量 → 返回对应的原文
  这一步叫"语义检索"，比关键词匹配精准得多——
  比如用户搜"苹果手机"能找到"iPhone 15"相关文档，尽管字面上不同
"""

import os
import logging
from typing import List, Tuple

from langchain_core.documents import Document

# LangChain: Chroma 封装 —— 将 Chroma 的增删查操作包装为 LangChain 接口
from langchain_chroma import Chroma

from app.config import settings
from app.services.embeddings import get_embeddings

logger = logging.getLogger(__name__)

# 持久化目录
CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "chroma",
)

# 全局单例
_vectorstore: Chroma | None = None
_current_collection_doc_count: int | None = None


def get_vectorstore() -> Chroma:
    """
    获取或创建 Chroma VectorStore 实例（单例模式）。
    使用持久化客户端，数据存入本地文件系统。

    --- LangChain 教学 ---
    输入：无
    输出：Chroma 实例，调用 .add_documents() / .similarity_search_with_score() / .delete()

    两种部署模式：
    1. 持久化客户端（本方案）：Chroma 内嵌在 Python 进程中，数据存本地目录
       → 简单，无需额外服务，适合 MVP 和单机部署
    2. HTTP 客户端：连接独立的 Chroma 服务（如 Docker 容器）
       → 适合生产环境，支持多副本
    """
    global _vectorstore

    if _vectorstore is None:
        if settings.chroma_mode == "remote":
            # 远程模式：连接 Docker 中的独立 Chroma 服务
            import chromadb
            client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
            logger.info(
                f"[VectorStore] 初始化 Chroma（远程模式: {settings.chroma_host}:{settings.chroma_port}）"
            )
            _vectorstore = Chroma(
                client=client,
                embedding_function=get_embeddings(),
                collection_name=settings.chroma_collection,
                collection_metadata={"hnsw:space": "cosine"},
            )
        else:
            # 嵌入式模式：Chroma 内嵌在 Python 进程中
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            logger.info(f"[VectorStore] 初始化 Chroma（嵌入式: {CHROMA_PERSIST_DIR}）")
            _vectorstore = Chroma(
                embedding_function=get_embeddings(),
                persist_directory=CHROMA_PERSIST_DIR,
                collection_name=settings.chroma_collection,
                collection_metadata={"hnsw:space": "cosine"},
            )

    return _vectorstore


# ================================================================
# 入库操作
# ================================================================

def add_documents(docs: List[Document], owner: str = "") -> List[str]:
    """将文档列表向量化并存入 Chroma，owner 用于多用户隔离"""
    if not docs:
        logger.warning("[VectorStore] 空文档列表，跳过人库")
        return []

    # 注入 owner 到 metadata
    if owner:
        for doc in docs:
            doc.metadata["owner"] = owner

    store = get_vectorstore()
    BATCH_SIZE = 10
    all_ids = []

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        batch_ids = store.add_documents(batch)
        all_ids.extend(batch_ids)

    logger.info(f"[VectorStore] 入库完成: 共 {len(all_ids)} 个 ID（{len(docs)} 个 chunk, owner={owner}）")
    return all_ids


# ================================================================
# 检索操作
# ================================================================

def similarity_search(
    query: str,
    k: int | None = None,
    owner: str = "",
) -> List[Tuple[Document, float]]:
    """
    检索最相似的 K 个文档片段。
    owner 参数用于多用户数据隔离——只检索该用户上传的文档。
    """
    if k is None:
        k = settings.top_k

    store = get_vectorstore()

    # 直接用 Chroma raw API，绕过 langchain_chroma 可能不转换距离的问题
    # 使用 store 自身的 embedding_function 以确保维度匹配
    query_vec = store._embedding_function.embed_query(query)

    where_filter = {"owner": owner} if owner else None
    raw = store._collection.query(
        query_embeddings=[query_vec],
        n_results=k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    from langchain_core.documents import Document as LCDocument

    normalized: List[Tuple[LCDocument, float]] = []
    if raw["ids"] and raw["ids"][0]:
        for i in range(len(raw["ids"][0])):
            doc = LCDocument(
                page_content=raw["documents"][0][i],
                metadata=raw["metadatas"][0][i] or {},
            )
            # Chroma 返回 cos distance = 1 - cos_sim
            # 转换: similarity = 1 - distance → 0=无关, 1=完全相同
            distance = raw["distances"][0][i]
            similarity = 1.0 - distance
            similarity = max(0.0, min(1.0, similarity))
            normalized.append((doc, round(similarity, 4)))

    logger.info(
        f"[VectorStore] 检索完成: query='{query[:30]}...', "
        f"返回 {len(normalized)} 条结果"
    )
    return normalized


# ================================================================
# 删除操作
# ================================================================

def delete_by_document_id(document_id: str) -> int:
    """
    按 document_id 删除某个文档的所有 chunk。
    使用 Chroma 的 metadata 过滤删除功能。

    --- LangChain 教学 ---
    这是 Chroma 的 metadata 过滤能力：
    delete(where={"document_id": "xxx"}) 删除所有匹配的 chunk
    不需要手动遍历或记录每个 chunk ID

    Args:
        document_id: 要删除的文档 ID

    Returns:
        删除的 chunk 数量（估算）
    """
    store = get_vectorstore()

    # 先查出该文档有多少 chunk（用于日志）
    results = store.get(where={"document_id": document_id})
    count = len(results.get("ids", []))

    if count == 0:
        logger.warning(f"[VectorStore] 未找到文档 {document_id} 的 chunk，跳过删除")
        return 0

    # LangChain: delete() 按 metadata 条件批量删除
    store.delete(where={"document_id": document_id})

    logger.info(f"[VectorStore] 已删除文档 {document_id} 的 {count} 个 chunk")
    return count


def get_collection_stats() -> dict:
    """
    获取 Collection 的统计信息（用于健康检查和调试）。

    Returns:
        {"collection_name": str, "count": int}
    """
    store = get_vectorstore()
    collection = store._collection
    return {
        "collection_name": collection.name,
        "count": collection.count(),
    }


# ================================================================
# 适配器：实现 BaseIndexer 接口
# ================================================================

from app.services.interfaces import BaseIndexer as _BaseIndexer
from app.models.search import SearchResult


class ChromaIndexer(_BaseIndexer):
    """Chroma 索引服务（实现 BaseIndexer 接口）"""

    def add(self, docs: List[Document]) -> List[str]:
        return add_documents(docs)

    def delete(self, document_id: str) -> int:
        return delete_by_document_id(document_id)

    def search(self, query: str, top_k: int = 4, owner: str = "") -> List[SearchResult]:
        """向量相似度搜索，按 owner 过滤"""
        results = similarity_search(query, k=top_k, owner=owner)
        search_results = []
        for doc, score in results:
            search_results.append(SearchResult(
                content=doc.page_content,
                score=score,
                filename=doc.metadata.get("filename", ""),
                page=doc.metadata.get("page"),
                chapter=doc.metadata.get("chapter"),
                document_id=doc.metadata.get("document_id", ""),
                chunk_index=doc.metadata.get("chunk_index", 0),
                source="dense",
            ))
        return search_results

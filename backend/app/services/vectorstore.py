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
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

        logger.info(f"[VectorStore] 初始化 Chroma（持久化路径: {CHROMA_PERSIST_DIR}）")

        # LangChain: Chroma 构造函数
        # - embedding_function: 传入 Embeddings 实例，add_documents 时自动向量化
        # - persist_directory: 本地持久化目录
        # - collection_name: 集合名（相当于数据库中的"表"）
        _vectorstore = Chroma(
            embedding_function=get_embeddings(),
            persist_directory=CHROMA_PERSIST_DIR,
            collection_name=settings.chroma_collection,
        )

    return _vectorstore


# ================================================================
# 入库操作
# ================================================================

def add_documents(docs: List[Document]) -> List[str]:
    """
    将文档列表向量化并存入 Chroma。

    数据流：
    List[Document] → Embeddings.embed_documents() → 向量
                   → Chroma 存储（向量 + 文本 + metadata）

    --- LangChain 教学 ---
    输入: List[Document]（来自 Splitter，已切分好的 chunks）
    输出: List[str]（每个 chunk 在 Chroma 中的唯一 ID）

    Chroma 内部存储结构（每个 chunk 一行）：
    | id        | embedding (1536维) | document (原文)  | metadata            |
    |-----------|---------------------|------------------|---------------------|
    | uuid-001  | [0.01, -0.03, ...] | "Transformer是..." | {filename, page, ...} |
    | uuid-002  | [0.05, 0.02, ...]  | "自注意力机制..."  | {filename, page, ...} |

    Args:
        docs: 待入库的 Document 列表（chunks，已含 metadata）

    Returns:
        Chroma 分配的 ID 列表
    """
    if not docs:
        logger.warning("[VectorStore] 空文档列表，跳过人库")
        return []

    store = get_vectorstore()
    logger.info(f"[VectorStore] 存入 {len(docs)} 个 chunk")

    # LangChain: add_documents() 内部自动调用 embedding_function 向量化
    # 我们不需要手动调用 embed_documents() — LangChain 帮我们做了
    ids = store.add_documents(docs)

    logger.info(f"[VectorStore] 入库完成: {len(ids)} 个 ID")

    return ids


# ================================================================
# 检索操作
# ================================================================

def similarity_search(
    query: str,
    k: int | None = None,
) -> List[Tuple[Document, float]]:
    """
    根据查询文本检索最相似的 K 个文档片段。
    返回 (Document, 相似度分数) 元组列表，按分数降序排列。

    --- LangChain 教学 ---
    输入: str（用户问题）
    输出: List[Tuple[Document, float]]
          - Document: 检索到的 chunk（含 page_content 和 metadata）
          - float: 余弦相似度分数（0~1，越大越相关）

    内部流程：
    1. 将 query 向量化（embed_query）
    2. 与 Chroma 中所有向量计算余弦相似度
    3. 返回相似度最高的 K 个

    Args:
        query: 查询文本
        k: 返回结果数，默认从配置读取（TOP_K=4）

    Returns:
        [(Document, score), ...] 按相似度降序排列
    """
    if k is None:
        k = settings.top_k

    store = get_vectorstore()

    # LangChain: similarity_search_with_score()
    # 与 similarity_search() 的区别：这个返回分数，另一个只返回 Document
    results = store.similarity_search_with_score(query, k=k)

    logger.info(
        f"[VectorStore] 检索完成: query='{query[:30]}...', "
        f"返回 {len(results)} 条结果"
    )
    for doc, score in results:
        logger.debug(
            f"  [{score:.4f}] {doc.metadata.get('filename', '?')} "
            f"p{doc.metadata.get('page', '?')} — {doc.page_content[:50]}..."
        )

    return results


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

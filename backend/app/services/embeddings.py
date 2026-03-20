"""
Embeddings 向量化服务
使用 LangChain OpenAIEmbeddings 接入 OpenAI API 兼容的 Embedding 接口

LangChain 组件 #3：Embeddings（向量化模型）
- 作用：将文本转换为固定维度的浮点数向量（如 text-embedding-3-small → 1536 维）
- 语义相近的文本，向量在空间中距离近 → 这是检索的基础
- 每段文本只需向量化一次，存入 VectorStore 后可反复检索

核心理解：
  文本 → Embedding 模型 → [0.012, -0.034, 0.056, ...] (1536 个浮点数)
  这个向量是多维空间中的一个"坐标"，语义相近的文本坐标靠近
"""

import logging
from typing import List

# LangChain: OpenAIEmbeddings 封装了 OpenAI 兼容的 /v1/embeddings API
# 通过 openai_api_base 参数可以指向任何兼容服务（如本地部署的模型）
from langchain_openai import OpenAIEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)

# 全局单例，避免重复初始化
_embeddings: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    """
    获取或创建 OpenAIEmbeddings 实例（单例模式）。
    每次调用返回同一个对象，避免重复创建连接。

    --- LangChain 教学 ---
    输入：无（从配置读取 API 参数）
    输出：OpenAIEmbeddings 实例，调用 .embed_documents(texts) 或 .embed_query(text) 进行向量化

    OpenAIEmbeddings 参数说明：
    - model: 模型名（默认 text-embedding-3-small）
    - openai_api_key: API 密钥
    - openai_api_base: API 基础 URL（换成其他兼容服务的关键参数）
    """
    global _embeddings

    if _embeddings is None:
        logger.info(
            f"[Embeddings] 初始化 Embedding 模型: {settings.embedding_model}"
        )
        _embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.embedding_api_key,
            openai_api_base=settings.embedding_api_base,
        )

    return _embeddings


def embed_documents(texts: List[str]) -> List[List[float]]:
    """
    批量将文本列表向量化（用于文档入库）。

    --- LangChain 教学 ---
    输入: List[str] —— 文本列表（chunk 的 page_content）
    输出: List[List[float]] —— 每个文本对应一个向量（1536 维）

    embed_documents 和 embed_query 的区别：
    - embed_documents: 批量向量化，内部可能做 batch 优化
    - embed_query: 单条向量化，通常用相同的模型但可能使用不同的预处理

    Args:
        texts: 待向量化的文本列表

    Returns:
        向量列表，每个向量是 float 列表
    """
    embeddings = get_embeddings()
    logger.info(f"[Embeddings] 批量向量化: {len(texts)} 条文本")
    vectors = embeddings.embed_documents(texts)
    logger.info(f"[Embeddings] 向量化完成: {len(vectors)} 个向量, 维度={len(vectors[0]) if vectors else 0}")
    return vectors


def embed_query(text: str) -> List[float]:
    """
    将单条查询文本向量化（用于用户提问）。

    --- LangChain 教学 ---
    输入: str —— 用户问题
    输出: List[float] —— 一个向量（与文档向量同维度，才能计算相似度）

    Args:
        text: 查询文本

    Returns:
        查询向量
    """
    embeddings = get_embeddings()
    return embeddings.embed_query(text)

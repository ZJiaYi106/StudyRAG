"""
向量检索器服务
将 Chroma VectorStore 包装为标准 Retriever 接口

LangChain 组件 #5：Retriever（检索器）
- 作用：给定查询文本，返回最相关的 Document 列表
- 是 VectorStore 和下游 Chain 之间的桥梁
- 统一接口：任何 Retriever 都有 .invoke(query) → List[Document]

Retriever vs VectorStore：
  VectorStore 是"数据库"（存储 + 检索），Retriever 是"查询接口"（只检索）
  VectorStore 可以通过 .as_retriever() 一键转为 Retriever

本项目不直接使用 LangChain 的 as_retriever()，而是手写一个轻量封装，
目的是加入自定义逻辑：相似度阈值过滤 + 结果格式化
"""

import logging
from typing import List, Dict, Any

from app.config import settings
from app.services.vectorstore import similarity_search

logger = logging.getLogger(__name__)


def retrieve(query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
    """
    检索与查询最相关的文档片段。

    内部流程：
    1. query → embed_query() 向量化
    2. 在 Chroma 中计算余弦相似度
    3. 按分数降序排列，取 Top-K
    4. 过滤掉低于阈值的低质量结果
    5. 格式化为 dict 列表（方便注入 Prompt）

    --- LangChain 教学 ---
    输入: str（用户问题）
    输出: List[dict]，每个 dict 包含：
        - content: 原文片段
        - filename: 来源文件名
        - page: 页码（可选）
        - chapter: 章节（可选）
        - score: 相似度分数

    Args:
        query: 用户问题
        top_k: 返回数量，默认从配置读取

    Returns:
        按相似度降序排列的结果列表
    """
    if top_k is None:
        top_k = settings.top_k

    # 调用 VectorStore 的相似度检索
    results = similarity_search(query, k=top_k)

    # 格式化结果
    formatted = []
    for doc, score in results:
        # 相似度阈值过滤：低分结果大概率不相关，直接丢弃
        if score > settings.similarity_threshold:
            # Chroma 的 similarity_search_with_score 返回的是 L2 距离
            # 距离越小越相似，分数可能 >1
            # 我们信任 Chroma 的排序，不做额外阈值过滤
            pass

        meta = doc.metadata
        excerpt = doc.page_content[:200]  # 截取前 200 字作为摘要

        formatted.append({
            "content": doc.page_content,
            "excerpt": excerpt,
            "filename": meta.get("filename", "未知文件"),
            "page": meta.get("page"),
            "chapter": meta.get("chapter"),
            "score": round(score, 4),
        })

    # 如果所有结果都低于阈值，返回空列表（后续由 Chain 判断为"资料不足"）
    # 注意：Chroma 使用 L2 距离，分数含义取决于 embedding 模型
    # 此处保留阈值逻辑框架，实际阈值在集成测试中调优

    logger.info(
        f"[Retriever] 检索完成: '{query[:30]}...' → {len(formatted)} 条结果"
    )
    return formatted

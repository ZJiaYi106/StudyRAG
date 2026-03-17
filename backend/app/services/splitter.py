"""
文本切分器服务
使用 LangChain Text Splitter 将长文档切分为可检索的短片段

LangChain 组件 #2：Text Splitter（文本切分器）
- 作用：将长文档切分为固定大小的 chunk，同时保留语义完整性
- 核心参数：
  - chunk_size: 每个 chunk 的最大字符数
  - chunk_overlap: 相邻 chunk 之间的重叠字符数（防止关键信息被切断）
- metadata 自动从父 Document 继承到每个 chunk
"""

import logging
from typing import List

from langchain_core.documents import Document

# LangChain: RecursiveCharacterTextSplitter —— 递归按分隔符优先级切分
# 它会依次尝试用 ["\n\n", "\n", "。", ".", " ", ""] 等分隔符切分，
# 优先用段落边界，实在不行才在字符中间切断，最大限度保持语义完整
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings

logger = logging.getLogger(__name__)


# ================================================================
# PDF 专用分隔符：优先在段落和句号处切断
# ================================================================
PDF_SEPARATORS = [
    "\n\n",     # 段落间空行（最优先）
    "\n",       # 换行
    "。",       # 中文句号
    ". ",       # 英文句号+空格
    "；",       # 中文分号
    "，",       # 中文逗号
    " ",        # 空格
    "",         # 逐字符切分（最后手段）
]

# ================================================================
# Markdown 专用分隔符：优先在章节和代码块边界切断
# ================================================================
MARKDOWN_SEPARATORS = [
    "\n## ",    # H2 标题（最高的非 H1 层级）
    "\n### ",   # H3 标题
    "\n#### ",  # H4 标题
    "\n```\n",  # 代码块结束到下一段
    "\n\n",     # 段落间空行
    "\n",       # 换行
    "。",       # 中文句号
    ". ",       # 英文句号+空格
    " ",        # 空格
    "",         # 逐字符切分（最后手段）
]


def get_splitter(file_type: str = "pdf") -> RecursiveCharacterTextSplitter:
    """
    根据文件类型创建 Text Splitter。
    PDF 和 Markdown 使用不同的分隔符优先级，
    确保 Markdown 不会在标题行中间被切断。

    --- LangChain 教学 ---
    输入：无需输入，返回一个配置好的 Splitter 对象
    输出：RecursiveCharacterTextSplitter 实例，调用 .split_documents(docs) 进行切分

    Args:
        file_type: "pdf" 或 "markdown"

    Returns:
        配置好的 RecursiveCharacterTextSplitter 实例
    """
    separators = MARKDOWN_SEPARATORS if file_type == "markdown" else PDF_SEPARATORS

    return RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=settings.chunk_size,          # 从配置读取，默认 1000
        chunk_overlap=settings.chunk_overlap,    # 从配置读取，默认 200
        # 下面两个参数确保元数据正确传递
        add_start_index=True,       # 在 metadata 中加入 start_index（chunk 在原文中的起始位置）
        keep_separator=True,        # 保留分隔符在 chunk 中（不丢弃标题行）
    )


def split_documents(docs: List[Document], file_type: str = "pdf") -> List[Document]:
    """
    将 Document 列表切分为更小的 chunk 列表。
    每个 chunk 自动继承父 Document 的 metadata（LangChain 内置行为），
    并额外添加 chunk_index 标记。

    --- LangChain 教学 ---
    输入：List[Document]（来自 Loader）
    输出：List[Document]（每个 Document 是一个 chunk，metadata 继承自父文档）

    数据流：
    Loader → List[Document]（页/章节级）
         → Splitter.split_documents() → List[Document]（chunk 级，≤ chunk_size 字符）
         → 每个 chunk 保留原始 metadata + 新增 chunk_index

    Args:
        docs: Loader 返回的 Document 列表
        file_type: 文件类型，决定使用哪套分隔符

    Returns:
        切分后的 Document 列表（chunks）
    """
    if not docs:
        logger.warning("[Text Splitter] 传入空文档列表，跳过切分")
        return []

    splitter = get_splitter(file_type)

    # --- LangChain: split_documents() ---
    # 这是核心调用：接收 List[Document]，返回 List[Document]
    # LangChain 自动将父 Document 的 metadata 复制到每个 chunk
    chunks = splitter.split_documents(docs)

    # 给每个 chunk 添加序号，方便排序和引用
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

    logger.info(
        f"[Text Splitter] 切分完成: {len(docs)} 个源文档 "
        f"→ {len(chunks)} 个 chunk (file_type={file_type}, "
        f"chunk_size={settings.chunk_size}, overlap={settings.chunk_overlap})"
    )

    return chunks

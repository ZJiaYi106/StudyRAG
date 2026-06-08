"""
文本切分器服务
使用 LangChain Text Splitter 将长文档切分为可检索的短片段

LangChain 组件 #2：Text Splitter（文本切分器）
- 作用：将长文档切分为固定大小的 chunk，同时保留语义完整性
- 核心参数：
  - chunk_size: 每个 chunk 的最大字符数（token 策略下为 token 数）
  - chunk_overlap: 相邻 chunk 之间的重叠字符数（防止关键信息被切断）
- metadata 自动从父 Document 继承到每个 chunk

支持三种分块策略：
  - recursive:  递归按分隔符优先级切分（默认，兼顾语义和效率）
  - token:      按 token 数切分（tiktoken），精确控制 LLM 上下文窗口
  - character:  按固定字符数切分（最简单，不考虑语义边界）
"""

import logging
from typing import List, Optional

from langchain_core.documents import Document

# LangChain: RecursiveCharacterTextSplitter —— 递归按分隔符优先级切分
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
    CharacterTextSplitter,
)

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

# ================================================================
# TXT / DOCX / PPTX: 通用文本分隔符
# ================================================================
GENERAL_SEPARATORS = [
    "\n\n",     # 段落间空行
    "\n",       # 换行
    "。",       # 中文句号
    ". ",       # 英文句号+空格
    "！",       # 中文感叹号
    "？",       # 中文问号
    "；",       # 中文分号
    "，",       # 中文逗号
    " ",        # 空格
    "",         # 逐字符切分
]

# ================================================================
# Excel: 表格数据以换行为主
# ================================================================
EXCEL_SEPARATORS = [
    "\n\n",     # 工作表之间的空行
    "\n",       # 行分隔（最常用）
    " | ",      # 表格单元格分隔
    " ",        # 空格
    "",         # 逐字符切分
]


# ================================================================
# 文件类型 → 分隔符 映射
# ================================================================
SEPARATOR_MAP = {
    "pdf":      PDF_SEPARATORS,
    "markdown": MARKDOWN_SEPARATORS,
    "txt":      GENERAL_SEPARATORS,
    "docx":     GENERAL_SEPARATORS,
    "pptx":     GENERAL_SEPARATORS,
    "excel":    EXCEL_SEPARATORS,
}

# 有效的分块策略
VALID_STRATEGIES = {"recursive", "token", "character"}


def get_separators(file_type: str) -> List[str]:
    """根据文件类型获取对应的分隔符列表"""
    return SEPARATOR_MAP.get(file_type, PDF_SEPARATORS)


def get_splitter(
    file_type: str = "pdf",
    strategy: str = "recursive",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
):
    """
    根据文件类型和分块策略创建 Text Splitter。

    --- 三种策略对比 ---
    | 策略      | 类                         | 特点                              |
    | recursive | RecursiveCharacterTextSplitter | 按分隔符优先级递归切分，保持语义 |
    | token     | TokenTextSplitter           | 按 tiktoken 计数，精确控制上下文  |
    | character | CharacterTextSplitter       | 纯字符数切分，最快但不保留语义    |

    Args:
        file_type: 文件类型（"pdf", "markdown", "txt", "docx", "pptx", "excel"）
        strategy:  分块策略（"recursive", "token", "character"）
        chunk_size:    覆盖默认的 chunk_size（None 则使用 settings 值）
        chunk_overlap: 覆盖默认的 chunk_overlap（None 则使用 settings 值）

    Returns:
        配置好的 Text Splitter 实例

    Raises:
        ValueError: 无效的分块策略
    """
    if strategy not in VALID_STRATEGIES:
        raise ValueError(
            f"无效的分块策略「{strategy}」，可选: {', '.join(sorted(VALID_STRATEGIES))}"
        )

    size = chunk_size if chunk_size is not None else settings.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap
    separators = get_separators(file_type)

    if strategy == "token":
        # TokenTextSplitter: 用 tiktoken 按 token 数切分
        # 更适合精确控制 LLM 上下文窗口大小
        return TokenTextSplitter(
            chunk_size=size,        # token 数
            chunk_overlap=max(1, overlap // 10),  # token 重叠不宜太大
        )

    elif strategy == "character":
        # CharacterTextSplitter: 最简单的按字符数切分
        # 不递归尝试分隔符——在 chunk_size 处直接切断
        return CharacterTextSplitter(
            separator="\n\n",       # 尽量在段落边界切
            chunk_size=size,
            chunk_overlap=overlap,
            keep_separator=True,
            add_start_index=True,
        )

    else:
        # 默认 recursive: 当前策略，分隔符优先级递归切分
        return RecursiveCharacterTextSplitter(
            separators=separators,
            chunk_size=size,
            chunk_overlap=overlap,
            add_start_index=True,
            keep_separator=True,
        )


def split_documents(
    docs: List[Document],
    file_type: str = "pdf",
    strategy: str = "recursive",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """
    将 Document 列表切分为更小的 chunk 列表。
    每个 chunk 自动继承父 Document 的 metadata（LangChain 内置行为），
    并额外添加 chunk_index 标记。

    --- 新增：分块策略选择 ---
    通过 strategy 参数可以选择不同的切分算法：
    - "recursive": 默认，语义感知的递归切分
    - "token":     按 LLM token 数切分，精确控制上下文窗口
    - "character": 纯字符数切分，适合有特殊格式需求的数据

    数据流：
    Loader → List[Document]（页/章节/幻灯片级）
          → Splitter.split_documents() → List[Document]（chunk 级，≤ chunk_size）
          → 每个 chunk 保留原始 metadata + 新增 chunk_index

    Args:
        docs:          Loader 返回的 Document 列表
        file_type:     文件类型，决定分隔符
        strategy:      分块策略，决定 Splitter 类型
        chunk_size:    覆盖默认值
        chunk_overlap: 覆盖默认值

    Returns:
        切分后的 Document 列表（chunks）
    """
    if not docs:
        logger.warning("[Text Splitter] 传入空文档列表，跳过切分")
        return []

    splitter = get_splitter(file_type, strategy, chunk_size, chunk_overlap)

    # --- LangChain: split_documents() ---
    # 这是核心调用：接收 List[Document]，返回 List[Document]
    # LangChain 自动将父 Document 的 metadata 复制到每个 chunk
    chunks = splitter.split_documents(docs)

    # 给每个 chunk 添加序号，方便排序和引用
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
        chunk.metadata["chunk_strategy"] = strategy

    size = chunk_size if chunk_size is not None else settings.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    logger.info(
        f"[Text Splitter] 切分完成: {len(docs)} 个源文档 "
        f"→ {len(chunks)} 个 chunk "
        f"(file_type={file_type}, strategy={strategy}, "
        f"chunk_size={size}, overlap={overlap})"
    )

    return chunks

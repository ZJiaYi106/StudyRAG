"""
文档加载器服务
使用 LangChain Document Loader 加载 PDF 和 Markdown 文件，提取元数据

LangChain 组件 #1：Document Loader（文档加载器）
- 作用：将各种格式的原始文件转换为 LangChain 统一的 Document 对象
- Document 对象 = page_content（文本内容）+ metadata（元数据字典）
- 统一接口让下游的 Splitter、VectorStore 等组件无需关心原始文件格式
"""

import re
import logging
from pathlib import Path
from typing import List

# LangChain: Document 是 LangChain 的数据载体，所有组件都围绕它工作
from langchain_core.documents import Document

# LangChain: PyMuPDFLoader 封装了 PyMuPDF 库，自动逐页提取 PDF 文本
from langchain_community.document_loaders import PyMuPDFLoader

from app.config import settings

logger = logging.getLogger(__name__)


def load_pdf(file_path: str, document_id: str) -> List[Document]:
    """
    使用 LangChain PyMuPDFLoader 加载 PDF 文件。
    每页生成一个 Document 对象，自动提取页码到 metadata。

    Args:
        file_path: PDF 文件的绝对路径
        document_id: 关联的文档唯一 ID（用于后续删除向量）

    Returns:
        List[Document]: 每个元素代表 PDF 的一页，metadata 含 source、page、document_id 等
    """
    filename = Path(file_path).name

    logger.info(f"[Document Loader] 开始加载 PDF: {filename}")

    # --- LangChain: PyMuPDFLoader ---
    # 输入：PDF 文件路径
    # 输出：List[Document]，每个 Document 对应一页
    #   - page_content: 该页的纯文本
    #   - metadata: {"source": 文件路径, "page": 页码(0-indexed), "file_path": 文件路径}
    loader = PyMuPDFLoader(file_path)
    docs = loader.load()

    # 给每个 Document 注入自定义元数据
    for doc in docs:
        # PyMuPDFLoader 的 page 是 0-indexed，转为人类友好的 1-indexed
        page_number = doc.metadata.get("page", 0) + 1
        doc.metadata.update({
            "document_id": document_id,       # 关联文档 ID，删除时用
            "filename": filename,             # 原始文件名
            "file_type": "pdf",               # 文件类型标记
            "page": page_number,              # 页码（1-indexed）
            "chapter": None,                  # PDF 暂不提取章节（后续可加书签提取）
        })

    logger.info(f"[Document Loader] PDF 加载完成: {filename}, 共 {len(docs)} 页")
    return docs


def load_markdown(file_path: str, document_id: str) -> List[Document]:
    """
    加载 Markdown 文件，按标题层级（# ## ###）分节。
    每个章节生成一个 Document，章节标题存入 metadata。

    注意：LangChain 的 TextLoader 会将整个 MD 文件作为一个 Document，
    不适合按章节检索的场景。这里手写一个章节感知的分节逻辑——
    这是"不用 LangChain 需要手写什么"的典型例子。

    Args:
        file_path: Markdown 文件的绝对路径
        document_id: 关联的文档唯一 ID

    Returns:
        List[Document]: 每个元素代表一个章节
    """
    filename = Path(file_path).name

    logger.info(f"[Document Loader] 开始加载 Markdown: {filename}")

    # 读取整个文件
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 如果文件为空
    if not content.strip():
        logger.warning(f"[Document Loader] Markdown 文件为空: {filename}")
        return []

    # --- 按标题分节（手写逻辑，LangChain 没有内置的 Markdown 章节 Loader） ---
    # 用正则匹配行首的 # 标题（1-6 级）
    # 以标题为边界切分内容，标题本身归属到它引领的章节
    sections = split_by_headers(content)

    docs = []
    for i, (title, body) in enumerate(sections):
        # 合并标题和正文作为 page_content
        full_text = f"{title}\n{body}" if title else body

        # 标题为空时（文件开头没有 # 的内容），标记为"前言"
        chapter = title.replace("#", "").strip() if title else "前言"

        doc = Document(
            page_content=full_text.strip(),
            metadata={
                "document_id": document_id,
                "filename": filename,
                "file_type": "markdown",
                "page": None,                   # Markdown 没有页码概念
                "chapter": chapter,             # 章节名（从标题提取）
                "section_index": i,             # 章节序号
            }
        )
        docs.append(doc)

    logger.info(f"[Document Loader] Markdown 加载完成: {filename}, 共 {len(docs)} 节")
    return docs


def split_by_headers(content: str) -> List[tuple]:
    """
    按 Markdown 标题（# ~ ######）将内容拆分为 (标题, 正文) 元组列表。

    算法思路：
    1. 用正则找出每个标题的行号和标题文本
    2. 以标题为边界，将文件切为多个 section
    3. 每个 section 的标题是离它最近的、层级最高的标题

    Args:
        content: Markdown 原始文本

    Returns:
        List[tuple[str, str]]: [(标题, 正文), ...]，第一个元素的标题可能为空字符串
    """
    lines = content.split("\n")

    # 第一步：找出所有标题行的位置和文本
    header_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
    headers = []  # [(行号, "原始标题行"), ...]
    for i, line in enumerate(lines):
        if header_pattern.match(line):
            headers.append((i, line.strip()))

    if not headers:
        # 没有标题，整个文件作为一个 section
        return [("", content.strip())]

    # 第二步：以标题位置为边界切分
    sections = []

    # 处理第一个标题之前的内容（前言，没有标题的引言部分）
    first_header_line = headers[0][0]
    if first_header_line > 0:
        preamble = "\n".join(lines[:first_header_line]).strip()
        if preamble:
            sections.append(("", preamble))

    # 第三步：按标题边界切分
    for idx, (line_no, header_text) in enumerate(headers):
        # 正文从标题行的下一行开始
        start = line_no + 1
        # 正文到下一个标题行（或文件末尾）结束
        end = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        body = "\n".join(lines[start:end]).strip()

        sections.append((header_text, body))

    return sections


# ================================================================
# 统一入口：根据文件类型自动选择加载器
# ================================================================

def load_document(file_path: str, document_id: str) -> List[Document]:
    """
    根据文件扩展名自动选择对应的加载器。

    Args:
        file_path: 文件路径
        document_id: 文档唯一 ID

    Returns:
        List[Document]: 加载并注入元数据后的 Document 列表
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return load_pdf(file_path, document_id)
    elif ext in (".md", ".markdown"):
        return load_markdown(file_path, document_id)
    else:
        raise ValueError(f"不支持的文件类型: {ext}")

"""
文档加载器服务
使用 LangChain Document Loader 加载多种格式文件，提取元数据

LangChain 组件 #1：Document Loader（文档加载器）
- 作用：将各种格式的原始文件转换为 LangChain 统一的 Document 对象
- Document 对象 = page_content（文本内容）+ metadata（元数据字典）
- 统一接口让下游的 Splitter、VectorStore 等组件无需关心原始文件格式

支持格式：
- PDF (.pdf)       → PyMuPDFLoader（逐页提取）
- Markdown (.md)   → 自定义标题分节
- TXT (.txt)       → 原生读取
- DOCX (.docx)     → python-docx（按标题样式分节）
- PPTX (.pptx)     → python-pptx（逐幻灯片提取）
- Excel (.xlsx)    → openpyxl / xlrd（逐工作表提取，渲染为 Markdown 表格）
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

    # --- OCR + VLM 增强：对文本量少的页面做 OCR，提取图片用 VLM 描述 ---
    for doc in docs:
        page_num = doc.metadata.get("page", 0) + 1  # 1-indexed
        text_len = len(doc.page_content.strip())

        # OCR：文本少的页面可能是扫描件
        if text_len < settings.pdf_ocr_min_chars:
            try:
                from app.services.ocr import ocr_page
                logger.info(f"[Document Loader] 第{page_num}页文本仅{text_len}字符，启动 OCR...")
                ocr_text = ocr_page(file_path, page_num - 1)
                if ocr_text:
                    doc.page_content = ocr_text.strip()
                    logger.info(f"[Document Loader] 第{page_num}页 OCR 完成: {len(ocr_text)} 字符")
            except ImportError:
                logger.debug(f"[Document Loader] OCR 未安装，跳过第{page_num}页")
            except Exception as e:
                logger.warning(f"[Document Loader] 第{page_num}页 OCR 失败: {e}")

        # VLM：提取页面内嵌图片并生成文字描述，追加到 page_content
        try:
            from app.services.ocr import extract_images_from_pdf, describe_image_vlm
            images = extract_images_from_pdf(file_path, page_num - 1)
            if images:
                logger.info(f"[Document Loader] 第{page_num}页提取到 {len(images)} 张图片，启动 VLM...")
                for img_idx, img_bytes in enumerate(images):
                    desc = describe_image_vlm(img_bytes)
                    if desc:
                        doc.page_content += f"\n[图片{img_idx+1}描述] {desc}"
                        logger.info(f"[Document Loader] VLM 描述完成: {desc[:60]}...")
        except ImportError:
            logger.debug(f"[Document Loader] VLM 依赖缺失，跳过图片分析")
        except Exception as e:
            logger.warning(f"[Document Loader] 第{page_num}页 VLM 失败: {e}")

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


def load_txt(file_path: str, document_id: str) -> List[Document]:
    """
    加载纯文本文件。
    整个文件内容作为一个 Document，适合短文本（如笔记、日志、代码片段）。

    Args:
        file_path: TXT 文件的绝对路径
        document_id: 关联的文档唯一 ID

    Returns:
        List[Document]: 包含整个文件内容的单元素列表
    """
    filename = Path(file_path).name

    logger.info(f"[Document Loader] 开始加载 TXT: {filename}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        logger.warning(f"[Document Loader] TXT 文件为空: {filename}")
        return []

    doc = Document(
        page_content=content.strip(),
        metadata={
            "document_id": document_id,
            "filename": filename,
            "file_type": "txt",
            "page": None,
            "chapter": None,
        }
    )

    logger.info(f"[Document Loader] TXT 加载完成: {filename}, {len(content)} 字符")
    return [doc]


def load_docx(file_path: str, document_id: str) -> List[Document]:
    """
    加载 Word (.docx) 文档，按标题样式分节。

    解析逻辑：
    - 遍历所有段落，遇到 Word 内置标题样式（Heading 1-6）时作为章节边界
    - 标题之前的正文段落归入上一个章节（或"前言"）
    - 没有标题时整个文档作为一个 Document

    Args:
        file_path: DOCX 文件的绝对路径
        document_id: 关联的文档唯一 ID

    Returns:
        List[Document]: 每个元素代表文档的一个章节
    """
    try:
        from docx import Document as DocxDocument
    except ImportError:
        raise ImportError("需要安装 python-docx 库: pip install python-docx")

    filename = Path(file_path).name

    logger.info(f"[Document Loader] 开始加载 DOCX: {filename}")

    docx = DocxDocument(file_path)

    # 收集所有段落及其样式信息
    sections: List[tuple] = []  # [(title, body_lines), ...]
    current_title = ""
    current_lines: List[str] = []

    # Word 内置标题样式名称（中英文兼容）
    HEADING_STYLES = {
        "Heading 1", "Heading 2", "Heading 3",
        "Heading 4", "Heading 5", "Heading 6",
        "标题 1", "标题 2", "标题 3",
        "标题 4", "标题 5", "标题 6",
        "heading 1", "heading 2", "heading 3",
    }

    for para in docx.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_name = para.style.name if para.style else ""

        # 检查是否为标题样式
        is_heading = style_name in HEADING_STYLES or style_name.startswith("Heading") or style_name.startswith("标题")

        if is_heading:
            # 保存上一个章节
            if current_lines:
                sections.append((current_title, "\n".join(current_lines)))
            # 开始新章节
            current_title = text
            current_lines = []
        else:
            current_lines.append(text)

    # 保存最后一个章节
    if current_lines:
        sections.append((current_title, "\n".join(current_lines)))
    elif current_title and not current_lines:
        # 只有标题没有正文的情况
        sections.append((current_title, ""))

    # 如果没有识别到标题，整个文档作为一个段落组
    if not sections:
        all_text = "\n".join(p.text for p in docx.paragraphs if p.text.strip())
        if all_text:
            sections.append(("", all_text))

    docs = []
    for i, (title, body) in enumerate(sections):
        full_text = f"{title}\n{body}" if title else body
        chapter = title if title else ("前言" if i == 0 else f"第{i+1}节")

        doc = Document(
            page_content=full_text.strip(),
            metadata={
                "document_id": document_id,
                "filename": filename,
                "file_type": "docx",
                "page": None,
                "chapter": chapter,
                "section_index": i,
            }
        )
        docs.append(doc)

    if not docs:
        logger.warning(f"[Document Loader] DOCX 解析结果为空: {filename}")

    logger.info(f"[Document Loader] DOCX 加载完成: {filename}, 共 {len(docs)} 节")
    return docs


def load_pptx(file_path: str, document_id: str) -> List[Document]:
    """
    加载 PowerPoint (.pptx) 演示文稿，逐幻灯片提取文本。

    提取内容包括：
    - 幻灯片标题和副标题
    - 所有形状内的文本（文本框、占位符、表格等）
    - 备注页文本（如果有）

    Args:
        file_path: PPTX 文件的绝对路径
        document_id: 关联的文档唯一 ID

    Returns:
        List[Document]: 每个元素代表一张幻灯片
    """
    try:
        from pptx import Presentation
    except ImportError:
        raise ImportError("需要安装 python-pptx 库: pip install python-pptx")

    filename = Path(file_path).name

    logger.info(f"[Document Loader] 开始加载 PPTX: {filename}")

    prs = Presentation(file_path)
    docs = []

    for slide_num, slide in enumerate(prs.slides, start=1):
        texts: List[str] = []

        # 提取幻灯片中所有形状的文本
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    line = para.text.strip()
                    if line:
                        texts.append(line)

            # 提取表格内的文本
            if shape.has_table:
                table = shape.table
                for row in table.rows:
                    row_texts = [cell.text.strip() for cell in row.cells]
                    texts.append(" | ".join(row_texts))

        # 提取备注
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                texts.append(f"\n[备注] {notes}")

        content = "\n".join(texts)

        if not content.strip():
            continue  # 跳过空白幻灯片

        doc = Document(
            page_content=content,
            metadata={
                "document_id": document_id,
                "filename": filename,
                "file_type": "pptx",
                "page": slide_num,
                "chapter": None,
            }
        )
        docs.append(doc)

    if not docs:
        logger.warning(f"[Document Loader] PPTX 解析结果为空: {filename}")

    logger.info(f"[Document Loader] PPTX 加载完成: {filename}, 共 {len(docs)} 张幻灯片")
    return docs


def load_excel(file_path: str, document_id: str) -> List[Document]:
    """
    加载 Excel 表格文件（.xlsx / .xls），逐工作表提取。
    每个工作表渲染为可读的文本格式（包含列名和数据类型信息）。

    Args:
        file_path: Excel 文件的绝对路径
        document_id: 关联的文档唯一 ID

    Returns:
        List[Document]: 每个元素代表一个工作表
    """
    filename = Path(file_path).name
    ext = Path(file_path).suffix.lower()

    logger.info(f"[Document Loader] 开始加载 Excel: {filename}")

    # 根据扩展名选择读取引擎
    if ext == ".xls":
        try:
            import xlrd
            workbook = xlrd.open_workbook(file_path)
            sheet_names = workbook.sheet_names()

            docs = []
            for sheet_name in sheet_names:
                sheet = workbook.sheet_by_name(sheet_name)
                rows = []
                for row_idx in range(sheet.nrows):
                    row_values = [str(sheet.cell_value(row_idx, col_idx)) for col_idx in range(sheet.ncols)]
                    rows.append(" | ".join(row_values))

                if not rows:
                    continue

                content = f"[工作表: {sheet_name}]\n" + "\n".join(rows)

                doc = Document(
                    page_content=content,
                    metadata={
                        "document_id": document_id,
                        "filename": filename,
                        "file_type": "excel",
                        "page": None,
                        "chapter": sheet_name,
                    }
                )
                docs.append(doc)
        except ImportError:
            raise ImportError("需要安装 xlrd 库: pip install xlrd")
    else:
        # .xlsx 使用 openpyxl
        try:
            import openpyxl
        except ImportError:
            raise ImportError("需要安装 openpyxl 库: pip install openpyxl")

        workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        docs = []

        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            rows = []
            max_col = sheet.max_column or 1

            for row in sheet.iter_rows(values_only=True):
                row_values = [str(cell) if cell is not None else "" for cell in row]
                # 补齐到最大列数
                row_values += [""] * (max_col - len(row_values))
                rows.append(" | ".join(row_values))

            if not rows:
                continue

            content = f"[工作表: {sheet_name}]\n" + "\n".join(rows)

            doc = Document(
                page_content=content,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "file_type": "excel",
                    "page": None,
                    "chapter": sheet_name,
                }
            )
            docs.append(doc)

        workbook.close()

    if not docs:
        logger.warning(f"[Document Loader] Excel 解析结果为空: {filename}")

    logger.info(f"[Document Loader] Excel 加载完成: {filename}, 共 {len(docs)} 个工作表")
    return docs


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
    elif ext == ".txt":
        return load_txt(file_path, document_id)
    elif ext == ".docx":
        return load_docx(file_path, document_id)
    elif ext == ".pptx":
        return load_pptx(file_path, document_id)
    elif ext in (".xlsx", ".xls"):
        return load_excel(file_path, document_id)
    else:
        raise ValueError(f"不支持的文件类型: {ext}")


# ================================================================
# 适配器：实现 BaseLoader 接口
# ================================================================

from app.services.interfaces import BaseLoader as _BaseLoader


class LoaderService(_BaseLoader):
    """文档加载器服务（实现 BaseLoader 接口）"""
    def load(self, file_path: str, document_id: str) -> List[Document]:
        return load_document(file_path, document_id)

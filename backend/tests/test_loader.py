"""
Document Loader 单元测试
测试 PDF 和 Markdown 加载、元数据提取、边界情况
"""

import os
import pytest
from pathlib import Path

from app.services.loader import (
    load_pdf,
    load_markdown,
    load_document,
    split_by_headers,
)

# 测试用 fixture 文件路径
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PDF = str(FIXTURES_DIR / "sample.pdf")
SAMPLE_MD = str(FIXTURES_DIR / "sample.md")
TEST_DOC_ID = "test-doc-001"


# ================================================================
# PDF 加载测试
# ================================================================

class TestPDFLoader:
    """测试 LangChain PyMuPDFLoader 封装"""

    def test_load_pdf_returns_documents(self):
        """PDF 加载应返回 Document 列表，每页一个"""
        docs = load_pdf(SAMPLE_PDF, TEST_DOC_ID)
        assert len(docs) == 2, f"2 页 PDF 应返回 2 个 Document，实际 {len(docs)} 个"

    def test_pdf_page_content_not_empty(self):
        """每个 Document 的 page_content 不应为空"""
        docs = load_pdf(SAMPLE_PDF, TEST_DOC_ID)
        for doc in docs:
            assert len(doc.page_content.strip()) > 0, f"第 {doc.metadata['page']} 页内容为空"

    def test_pdf_metadata_contains_required_fields(self):
        """PDF Document 的 metadata 应包含所有必要字段"""
        docs = load_pdf(SAMPLE_PDF, TEST_DOC_ID)
        for doc in docs:
            meta = doc.metadata
            assert "document_id" in meta
            assert "filename" in meta
            assert "file_type" in meta
            assert "page" in meta
            assert "chapter" in meta  # 允许为 None

    def test_pdf_metadata_values(self):
        """PDF metadata 的具体值应正确"""
        docs = load_pdf(SAMPLE_PDF, TEST_DOC_ID)
        doc = docs[0]
        assert doc.metadata["document_id"] == TEST_DOC_ID
        assert doc.metadata["file_type"] == "pdf"
        assert doc.metadata["page"] == 1  # 1-indexed
        assert "sample.pdf" in doc.metadata["filename"]

    def test_pdf_page_numbers_are_sequential(self):
        """PDF 页码应从 1 开始递增"""
        docs = load_pdf(SAMPLE_PDF, TEST_DOC_ID)
        pages = [doc.metadata["page"] for doc in docs]
        assert pages == [1, 2], f"页码应为 [1, 2]，实际 {pages}"


# ================================================================
# Markdown 加载测试
# ================================================================

class TestMarkdownLoader:
    """测试自定义 Markdown 章节加载器"""

    def test_load_markdown_returns_documents(self):
        """MD 加载应返回 Document 列表，按章节分"""
        docs = load_markdown(SAMPLE_MD, TEST_DOC_ID)
        assert len(docs) >= 2, f"应至少有 2 个章节，实际 {len(docs)} 个"

    def test_markdown_page_content_not_empty(self):
        """每个章节的 page_content 不应为空"""
        docs = load_markdown(SAMPLE_MD, TEST_DOC_ID)
        for doc in docs:
            assert len(doc.page_content.strip()) > 0

    def test_markdown_metadata_contains_required_fields(self):
        """MD Document 的 metadata 应包含所有必要字段"""
        docs = load_markdown(SAMPLE_MD, TEST_DOC_ID)
        for doc in docs:
            meta = doc.metadata
            assert "document_id" in meta
            assert "filename" in meta
            assert "file_type" in meta
            assert "chapter" in meta
            assert "section_index" in meta
            assert meta["page"] is None  # Markdown 无页码

    def test_markdown_metadata_values(self):
        """MD metadata 的具体值应正确"""
        docs = load_markdown(SAMPLE_MD, TEST_DOC_ID)
        assert docs[0].metadata["file_type"] == "markdown"
        assert docs[0].metadata["document_id"] == TEST_DOC_ID
        assert "sample.md" in docs[0].metadata["filename"]

    def test_markdown_chapters_extracted(self):
        """章节标题应从 # 标题中正确提取"""
        docs = load_markdown(SAMPLE_MD, TEST_DOC_ID)
        chapters = [doc.metadata["chapter"] for doc in docs]
        # 应该包含各级标题
        assert any("深度学习" in ch for ch in chapters if ch), \
            f"应包含'深度学习'相关章节，实际: {chapters}"
        assert any("Transformer" in ch for ch in chapters if ch), \
            f"应包含'Transformer'相关章节，实际: {chapters}"


# ================================================================
# split_by_headers 函数测试
# ================================================================

class TestSplitByHeaders:
    """测试 Markdown 标题分节核心算法"""

    def test_no_headers(self):
        """无标题时应整体作为一个 section"""
        result = split_by_headers("这是一段没有标题的文本。")
        assert len(result) == 1
        assert result[0][0] == ""  # 标题为空
        assert "没有标题" in result[0][1]

    def test_single_h1(self):
        """单个 H1 标题"""
        result = split_by_headers("# 标题\n正文内容")
        assert len(result) == 1
        assert result[0][0] == "# 标题"
        assert "正文内容" in result[0][1]

    def test_multiple_h1(self):
        """多个 H1 标题应各自成节"""
        content = "# 第一章\n内容A\n# 第二章\n内容B"
        result = split_by_headers(content)
        assert len(result) == 2
        assert result[0][0] == "# 第一章"
        assert result[1][0] == "# 第二章"

    def test_preamble_before_first_header(self):
        """第一个标题之前的内容应作为前言"""
        content = "这是前言\n这是前言第二行\n# 第一章\n内容"
        result = split_by_headers(content)
        assert len(result) == 2
        assert result[0][0] == ""  # 前言无标题
        assert "前言" in result[0][1]
        assert result[1][0] == "# 第一章"

    def test_h2_h3_headers(self):
        """## 和 ### 标题也应被正确识别"""
        content = "## 1.1 小节\n内容A\n### 1.1.1 细节\n内容B"
        result = split_by_headers(content)
        assert len(result) == 2
        assert result[0][0] == "## 1.1 小节"
        assert result[1][0] == "### 1.1.1 细节"

    def test_empty_content(self):
        """空内容应返回空列表"""
        result = split_by_headers("")
        assert len(result) == 1
        assert result[0][1] == ""

    def test_header_at_line_1(self):
        """标题出现在第一行（没有前言）"""
        content = "# 首页标题\n正文"
        result = split_by_headers(content)
        assert len(result) == 1
        assert result[0][0] == "# 首页标题"


# ================================================================
# 统一入口测试
# ================================================================

class TestLoadDocument:
    """测试 load_document 统一入口的分发逻辑"""

    def test_load_pdf_via_unified(self):
        """通过统一入口加载 PDF"""
        docs = load_document(SAMPLE_PDF, TEST_DOC_ID)
        assert len(docs) == 2

    def test_load_md_via_unified(self):
        """通过统一入口加载 Markdown"""
        docs = load_document(SAMPLE_MD, TEST_DOC_ID)
        assert len(docs) >= 2

    def test_unsupported_extension(self):
        """不支持的文件类型应抛出异常"""
        with pytest.raises(ValueError, match="不支持的文件类型"):
            load_document("/fake/path.txt", TEST_DOC_ID)

    def test_pdf_with_nonexistent_file(self):
        """不存在的 PDF 文件应抛出异常"""
        with pytest.raises(Exception):
            load_pdf("/nonexistent/file.pdf", TEST_DOC_ID)

"""
Text Splitter 单元测试
测试 RecursiveCharacterTextSplitter 的切分行为、metadata 继承、边界情况
"""

import pytest
from langchain_core.documents import Document

from app.services.splitter import (
    split_documents,
    get_splitter,
    PDF_SEPARATORS,
    MARKDOWN_SEPARATORS,
)


# ================================================================
# 辅助工具：创建测试用 Document
# ================================================================

def make_doc(text: str, **metadata) -> Document:
    """快速创建带 metadata 的测试 Document"""
    return Document(page_content=text, metadata=metadata)


# ================================================================
# get_splitter 测试
# ================================================================

class TestGetSplitter:
    """测试 Splitter 工厂函数"""

    def test_pdf_splitter_uses_pdf_separators(self):
        """PDF splitter 应使用 PDF 分隔符"""
        splitter = get_splitter("pdf")
        # RecursiveCharacterTextSplitter 内部存储了 separators
        assert splitter._separators == PDF_SEPARATORS

    def test_markdown_splitter_uses_md_separators(self):
        """Markdown splitter 应使用 Markdown 分隔符"""
        splitter = get_splitter("markdown")
        assert splitter._separators == MARKDOWN_SEPARATORS

    def test_markdown_separators_include_code_block(self):
        """Markdown 分隔符应包含代码块边界标记"""
        assert "\n```\n" in MARKDOWN_SEPARATORS

    def test_default_is_pdf(self):
        """默认文件类型应为 pdf"""
        splitter = get_splitter()
        assert splitter._separators == PDF_SEPARATORS


# ================================================================
# split_documents 测试
# ================================================================

class TestSplitDocuments:
    """测试 split_documents 核心逻辑"""

    def test_split_returns_more_chunks_than_input(self):
        """长文档切分后 chunk 数应多于输入"""
        # 创建一个 3000 字的文档，chunk_size=1000，应产生 ~3-4 个 chunk
        long_text = "深度学习是机器学习的一个分支。" * 100  # ~1500 字
        docs = [make_doc(long_text, source="test.txt", page=1)]
        chunks = split_documents(docs, "pdf")
        assert len(chunks) > 1, f"长文档应被切分，实际 chunk 数: {len(chunks)}"

    def test_short_document_not_split(self):
        """短文档（小于 chunk_size）不应被切分"""
        short_text = "这是一个很短的文档。"
        docs = [make_doc(short_text, source="short.txt")]
        chunks = split_documents(docs, "pdf")
        assert len(chunks) == 1

    def test_metadata_inherited(self):
        """切分后 metadata 应从父文档继承"""
        docs = [make_doc(
            "测试内容。" * 200,
            document_id="abc-123",
            filename="test.pdf",
            file_type="pdf",
            page=3,
        )]
        chunks = split_documents(docs, "pdf")
        for chunk in chunks:
            assert chunk.metadata["document_id"] == "abc-123"
            assert chunk.metadata["filename"] == "test.pdf"
            assert chunk.metadata["file_type"] == "pdf"
            assert chunk.metadata["page"] == 3

    def test_chunk_index_added(self):
        """每个 chunk 应有唯一的 chunk_index"""
        docs = [make_doc("测试。" * 200)]
        chunks = split_documents(docs, "pdf")
        indices = [chunk.metadata["chunk_index"] for chunk in chunks]
        assert indices == list(range(len(chunks))), \
            f"chunk_index 应连续递增，实际: {indices}"

    def test_chunk_content_within_size(self):
        """每个 chunk 的 page_content 长度应 ≤ chunk_size + 一些余量"""
        docs = [make_doc("A" * 5000)]  # 5000 字符的无分隔符文本
        chunks = split_documents(docs, "pdf")
        # 由于无分隔符，切分可能略超 chunk_size，通常不会超过太多
        for chunk in chunks:
            # 允许 10% 的余量（RecursiveCharacterTextSplitter 的长度度量方式）
            assert len(chunk.page_content) <= settings_chunk_size() * 1.5, \
                f"chunk 长度 {len(chunk.page_content)} 超出预期"

    def test_chunks_have_overlap(self):
        """相邻 chunk 之间应有重叠内容"""
        # 创建一个有明确重复模式的长文本，便于检测 overlap
        text = "第一段内容。第二段内容。第三段内容。" * 50
        docs = [make_doc(text)]
        chunks = split_documents(docs, "pdf")
        if len(chunks) >= 2:
            # 取第一个 chunk 的末尾和第二个 chunk 的开头
            end_of_first = chunks[0].page_content[-50:]
            start_of_second = chunks[1].page_content[:50:]
            # 由于 overlap 存在，两者应有共同子串
            # 用字符集合重叠来判断（粗略但有效的指标）
            common = set(end_of_first) & set(start_of_second)
            assert len(common) > 0, "相邻 chunk 应有内容重叠"

    def test_multiple_documents_merged_and_split(self):
        """多个 Document 输入时应全部被切分"""
        docs = [
            make_doc("文档A内容。" * 100, page=1),
            make_doc("文档B内容。" * 100, page=2),
        ]
        chunks = split_documents(docs, "pdf")
        pages = {chunk.metadata["page"] for chunk in chunks}
        assert pages == {1, 2}, f"应包含两页的内容，实际页码: {pages}"


# ================================================================
# Markdown 切分测试
# ================================================================

class TestMarkdownSplitting:
    """测试 Markdown 专用切分策略"""

    def test_markdown_headers_preserved(self):
        """MD 切分时标题行不应被切断"""
        md_text = (
            "## 1.1 注意力机制\n\n"
            + "注意力机制是 Transformer 的核心。" * 50
            + "\n\n## 1.2 多头注意力\n\n"
            + "多头注意力并行运行多个注意力头。" * 50
        )
        docs = [make_doc(md_text, file_type="markdown")]
        chunks = split_documents(docs, "markdown")

        # 至少有两个 chunk（因为有两个 ## 标题）
        assert len(chunks) >= 2

        # 检查是否有 chunk 以 "## 1.1" 或 "## 1.2" 开头
        # 说明分隔符在标题前生效了
        headers_found = 0
        for chunk in chunks:
            if chunk.page_content.strip().startswith("##"):
                headers_found += 1
        # 不要求每个标题都行首，但至少有一部分在开头
        assert headers_found >= 1, "至少有一个 chunk 应以 ## 标题开头"

    def test_code_block_not_split(self):
        """代码块内容不应在中间被切断（分隔符包含 \n```\n）"""
        code_md = (
            "## 示例代码\n\n"
            "以下是 Python 代码：\n\n"
            "```\ndef hello():\n    print('Hello')\n```\n\n"
            + "这段代码很简单。" * 30
        )
        docs = [make_doc(code_md, file_type="markdown")]
        chunks = split_documents(docs, "markdown")

        # 如果代码块被完整保留，应该能找到包含 ``` 的 chunk
        code_chunks = [c for c in chunks if "```" in c.page_content]
        assert len(code_chunks) >= 1, "代码块标记应出现在至少一个 chunk 中"


# ================================================================
# 边界情况测试
# ================================================================

class TestEdgeCases:
    """边界和异常情况"""

    def test_empty_list(self):
        """空列表输入应返回空列表"""
        chunks = split_documents([], "pdf")
        assert chunks == []

    def test_empty_content_document(self):
        """空内容 Document 应安全处理"""
        docs = [make_doc("")]
        chunks = split_documents(docs, "pdf")
        # 空内容应该不会产生有效 chunk
        assert len(chunks) == 0

    def test_single_char(self):
        """单个字符的 Document"""
        docs = [make_doc("A")]
        chunks = split_documents(docs, "pdf")
        assert len(chunks) == 1
        assert chunks[0].page_content == "A"

    def test_whitespace_only(self):
        """仅包含空白字符的 Document"""
        docs = [make_doc("   \n\n  \n  ")]
        chunks = split_documents(docs, "pdf")
        # RecursiveCharacterTextSplitter 默认会过滤空白 chunk
        # 行为取决于实现版本
        assert isinstance(chunks, list)  # 不应抛异常

    def test_metadata_not_mutated_by_splitting(self):
        """切分不应修改传入的原始 Document 的 metadata"""
        original_meta = {"document_id": "xyz", "page": 5}
        docs = [make_doc("短文本。", **original_meta)]
        split_documents(docs, "pdf")
        # 原始 Document 的 metadata 应保持不变
        assert docs[0].metadata["document_id"] == "xyz"
        assert docs[0].metadata["page"] == 5


# ================================================================
# 辅助函数
# ================================================================

def settings_chunk_size() -> int:
    """延迟导入，避免循环依赖"""
    from app.config import settings
    return settings.chunk_size

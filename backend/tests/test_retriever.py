"""
Retriever 服务单元测试
测试检索结果的格式化、字段完整性
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

from app.services.retriever import retrieve


def make_mock_result(content: str, filename: str, page: int, score: float) -> tuple:
    """快速创建 mock 检索结果"""
    doc = Document(
        page_content=content,
        metadata={
            "filename": filename,
            "page": page,
            "chapter": "测试章节",
            "document_id": "test-001",
        }
    )
    return (doc, score)


class TestRetrieve:
    """测试 retrieve 函数"""

    @patch("app.services.retriever.similarity_search")
    def test_retrieve_returns_formatted_list(self, mock_search):
        """检索应返回格式化后的 dict 列表"""
        mock_search.return_value = [
            make_mock_result("深度学习是机器学习的一个分支", "AI讲义.pdf", 3, 0.95),
            make_mock_result("Transformer 使用自注意力机制", "AI讲义.pdf", 5, 0.88),
        ]

        results = retrieve("什么是深度学习？", top_k=2)

        assert len(results) == 2
        assert isinstance(results[0], dict)

    @patch("app.services.retriever.similarity_search")
    def test_retrieve_result_has_required_fields(self, mock_search):
        """每个结果应包含 content, excerpt, filename, page, chapter, score"""
        mock_search.return_value = [
            make_mock_result("测试内容", "test.pdf", 1, 0.9),
        ]

        results = retrieve("测试", top_k=1)
        item = results[0]

        assert "content" in item
        assert "excerpt" in item
        assert "filename" in item
        assert "page" in item
        assert "chapter" in item
        assert "score" in item

    @patch("app.services.retriever.similarity_search")
    def test_retrieve_result_excerpt_is_truncated(self, mock_search):
        """excerpt 应截取前 200 字"""
        long_text = "A" * 300
        mock_search.return_value = [
            make_mock_result(long_text, "long.pdf", 1, 0.9),
        ]

        results = retrieve("测试")
        assert len(results[0]["excerpt"]) <= 200

    @patch("app.services.retriever.similarity_search")
    def test_retrieve_empty_results(self, mock_search):
        """向量库无结果时应返回空列表"""
        mock_search.return_value = []

        results = retrieve("无匹配内容")
        assert results == []

    @patch("app.services.retriever.similarity_search")
    def test_retrieve_score_is_float(self, mock_search):
        """score 应为数值类型"""
        mock_search.return_value = [
            make_mock_result("内容", "f.pdf", 1, 0.92),
        ]

        results = retrieve("测试")
        assert isinstance(results[0]["score"], (int, float))

    @patch("app.services.retriever.similarity_search")
    def test_retrieve_page_can_be_none(self, mock_search):
        """Markdown 文档 page 可能为 None"""
        doc = Document(
            page_content="MD 内容",
            metadata={
                "filename": "notes.md",
                "page": None,
                "chapter": "第一章",
            }
        )
        mock_search.return_value = [(doc, 0.85)]

        results = retrieve("测试")
        assert results[0]["page"] is None
        assert results[0]["chapter"] == "第一章"

    @patch("app.services.retriever.similarity_search")
    def test_retrieve_uses_default_top_k_from_config(self, mock_search):
        """未指定 top_k 时应使用配置默认值"""
        mock_search.return_value = []

        retrieve("测试")
        # 验证 similarity_search 被调用时使用了配置的 top_k
        call_kwargs = mock_search.call_args
        assert call_kwargs[1]["k"] == 4  # 默认 TOP_K=4

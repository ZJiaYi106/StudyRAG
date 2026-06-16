"""
LCEL Chain 服务单元测试
测试 Chain 构建、Runnable 组件、ask() 函数
"""

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.output_parsers import StrOutputParser

from app.services.chain import ask


class TestAsk:
    """测试 ask() 便捷问答函数"""

    @patch("app.services.chain._full_search_sync")
    def test_ask_returns_dict_with_answer_and_sources(self, mock_search):
        """ask() 应返回包含 answer 和 sources 的字典"""
        mock_search.return_value = [{
            "content": "测试内容",
            "filename": "test.pdf",
            "page": 1,
            "chapter": None,
            "score": 0.9,
        }]

        # Mock ChatOpenAI 避免真实 API 调用
        with patch("app.services.chain.ChatOpenAI"), \
             patch.object(StrOutputParser, "invoke", return_value="测试回答"):
            result = ask("测试问题")

        assert "answer" in result
        assert "sources" in result
        assert isinstance(result["answer"], str)
        assert isinstance(result["sources"], list)

    @patch("app.services.chain._full_search_sync")
    def test_ask_passes_sources_to_response(self, mock_search):
        """sources 应包含检索结果"""
        mock_search.return_value = [
            {"content": "A", "filename": "a.pdf", "page": 1, "chapter": None, "score": 0.9},
            {"content": "B", "filename": "b.pdf", "page": 2, "chapter": "Ch1", "score": 0.8},
        ]

        with patch("app.services.chain.ChatOpenAI"), \
             patch.object(StrOutputParser, "invoke", return_value="回答"):
            result = ask("问题")

        assert len(result["sources"]) == 2
        assert result["sources"][0]["filename"] == "a.pdf"

    @patch("app.services.chain._full_search_sync")
    def test_ask_handles_no_sources(self, mock_search):
        """无检索结果时也应正常返回"""
        mock_search.return_value = []

        with patch("app.services.chain.ChatOpenAI"), \
             patch.object(StrOutputParser, "invoke", return_value="资料不足"):
            result = ask("不知道的问题")

        assert result["sources"] == []
        assert isinstance(result["answer"], str)

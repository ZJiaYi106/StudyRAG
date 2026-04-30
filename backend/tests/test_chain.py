"""
LCEL Chain 服务单元测试
测试 Chain 构建、Runnable 组件、ask() 函数
"""

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.messages import AIMessage

from app.services.chain import build_rag_chain, ask, _retrieve_and_format


class TestRetrieveAndFormat:
    """测试 _retrieve_and_format 内部函数"""

    @patch("app.services.chain.retrieve")
    def test_returns_formatted_context_string(self, mock_retrieve):
        """应返回格式化后的字符串"""
        mock_retrieve.return_value = [{
            "content": "深度学习是机器学习的一个分支。",
            "filename": "test.pdf",
            "page": 3,
            "chapter": "第一章",
            "score": 0.95,
        }]

        result = _retrieve_and_format("什么是深度学习？")
        assert isinstance(result, str)
        assert "test.pdf" in result
        assert "第3页" in result

    @patch("app.services.chain.retrieve")
    def test_empty_results_returns_placeholder(self, mock_retrieve):
        """无检索结果时应返回占位文本"""
        mock_retrieve.return_value = []
        result = _retrieve_and_format("随机问题")
        assert "暂无" in result


class TestBuildRagChain:
    """测试 build_rag_chain()"""

    @patch("app.services.chain.ChatOpenAI")
    def test_chain_is_buildable(self, mock_llm_class):
        """Chain 应能成功构建"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        chain = build_rag_chain()
        assert chain is not None

    @patch("app.services.chain.ChatOpenAI")
    def test_chain_has_invoke_method(self, mock_llm_class):
        """构建的 Chain 应有 invoke 方法（Runnable 接口）"""
        mock_llm_class.return_value = MagicMock()
        chain = build_rag_chain()
        assert hasattr(chain, "invoke")
        assert callable(chain.invoke)


class TestAsk:
    """测试 ask() 便捷问答函数"""

    @patch("app.services.chain.build_rag_chain")
    @patch("app.services.chain.retrieve")
    def test_ask_returns_dict_with_answer_and_sources(self, mock_retrieve, mock_build_chain):
        """ask() 应返回包含 answer 和 sources 的字典"""
        mock_retrieve.return_value = [{
            "content": "测试内容",
            "filename": "test.pdf",
            "page": 1,
            "chapter": None,
            "score": 0.9,
        }]

        # Mock 整个 Chain：invoke 直接返回字符串
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "这是一个测试回答。"
        mock_build_chain.return_value = mock_chain

        result = ask("测试问题")

        assert "answer" in result
        assert "sources" in result
        assert isinstance(result["answer"], str)
        assert isinstance(result["sources"], list)

    @patch("app.services.chain.build_rag_chain")
    @patch("app.services.chain.retrieve")
    def test_ask_passes_sources_to_response(self, mock_retrieve, mock_build_chain):
        """sources 应包含检索结果"""
        mock_sources = [
            {"content": "A", "filename": "a.pdf", "page": 1, "chapter": None, "score": 0.9},
            {"content": "B", "filename": "b.pdf", "page": 2, "chapter": "Ch1", "score": 0.8},
        ]
        mock_retrieve.return_value = mock_sources

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "回答"
        mock_build_chain.return_value = mock_chain

        result = ask("问题")
        assert len(result["sources"]) == 2
        assert result["sources"][0]["filename"] == "a.pdf"

    @patch("app.services.chain.build_rag_chain")
    @patch("app.services.chain.retrieve")
    def test_ask_handles_no_sources(self, mock_retrieve, mock_build_chain):
        """无检索结果时也应正常返回"""
        mock_retrieve.return_value = []

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "资料中未找到足够依据"
        mock_build_chain.return_value = mock_chain

        result = ask("不知道的问题")
        assert result["sources"] == []
        assert isinstance(result["answer"], str)

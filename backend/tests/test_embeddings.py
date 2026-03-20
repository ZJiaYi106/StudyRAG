"""
Embeddings 服务单元测试
测试配置加载、单例模式、接口契约（不实际调用 API）
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.embeddings import get_embeddings, embed_documents, embed_query


class TestEmbeddingsConfig:
    """测试 Embeddings 配置和初始化"""

    def test_get_embeddings_returns_singleton(self):
        """多次调用应返回同一个实例"""
        # 重置单例
        import app.services.embeddings as mod
        mod._embeddings = None

        e1 = get_embeddings()
        e2 = get_embeddings()
        assert e1 is e2, "get_embeddings 应返回单例"

    def test_embeddings_model_from_config(self):
        """Embedding 模型名应从配置读取"""
        embeddings = get_embeddings()
        from app.config import settings
        assert embeddings.model == settings.embedding_model

    def test_embeddings_api_base_from_config(self):
        """API base 应从配置读取"""
        embeddings = get_embeddings()
        from app.config import settings
        assert str(embeddings.openai_api_base) == settings.embedding_api_base.rstrip("/")


class TestEmbedDocuments:
    """测试批量向量化"""

    @patch("app.services.embeddings.get_embeddings")
    def test_embed_documents_calls_underlying_method(self, mock_get_emb):
        """embed_documents 应正确委托给 LangChain"""
        mock_instance = MagicMock()
        mock_instance.embed_documents.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]
        mock_get_emb.return_value = mock_instance

        texts = ["文本A", "文本B"]
        vectors = embed_documents(texts)

        assert len(vectors) == 2
        assert len(vectors[0]) == 3
        mock_instance.embed_documents.assert_called_once_with(texts)

    @patch("app.services.embeddings.get_embeddings")
    def test_embed_documents_empty_list(self, mock_get_emb):
        """空列表应安全处理"""
        mock_instance = MagicMock()
        mock_instance.embed_documents.return_value = []
        mock_get_emb.return_value = mock_instance

        vectors = embed_documents([])
        assert vectors == []


class TestEmbedQuery:
    """测试单条查询向量化"""

    @patch("app.services.embeddings.get_embeddings")
    def test_embed_query_calls_underlying_method(self, mock_get_emb):
        """embed_query 应正确委托给 LangChain"""
        mock_instance = MagicMock()
        mock_instance.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_get_emb.return_value = mock_instance

        vector = embed_query("什么是 RAG？")

        assert len(vector) == 3
        mock_instance.embed_query.assert_called_once_with("什么是 RAG？")

    @patch("app.services.embeddings.get_embeddings")
    def test_embed_query_returns_float_list(self, mock_get_emb):
        """返回的向量元素应为 float 类型"""
        mock_instance = MagicMock()
        mock_instance.embed_query.return_value = [0.12, -0.034, 0.0]
        mock_get_emb.return_value = mock_instance

        vector = embed_query("测试")
        for v in vector:
            assert isinstance(v, float)

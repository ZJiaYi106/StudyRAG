"""
问答 API 集成测试
测试 POST /api/chat 端点的行为
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestChatEndpoint:
    """测试 POST /api/chat"""

    @patch("app.routers.chat.ask")
    @patch("app.routers.chat.list_records")
    def test_chat_returns_answer_and_sources(self, mock_list, mock_ask):
        """正常问答应返回 200 + answer + sources"""
        mock_list.return_value = [{"id": "abc", "filename": "test.pdf"}]
        mock_ask.return_value = {
            "answer": "Transformer 是一种基于自注意力机制的深度学习架构。",
            "sources": [
                {
                    "content": "Transformer 是一种基于自注意力机制的深度学习架构，由 Vaswani 等人于 2017 年提出。",
                    "excerpt": "Transformer 是一种基于自注意力机制的深度学习架构...",
                    "filename": "NLP讲义.pdf",
                    "page": 5,
                    "chapter": "第二章 Transformer",
                    "score": 0.95,
                }
            ],
        }

        response = client.post("/api/chat", json={
            "question": "什么是 Transformer？",
            "top_k": 4,
        })

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "question" in data
        assert data["question"] == "什么是 Transformer？"
        assert len(data["sources"]) == 1

    @patch("app.routers.chat.ask")
    @patch("app.routers.chat.list_records")
    def test_chat_source_has_required_fields(self, mock_list, mock_ask):
        """来源信息应包含所有必要字段"""
        mock_list.return_value = [{"id": "abc"}]
        mock_ask.return_value = {
            "answer": "回答",
            "sources": [
                {
                    "content": "完整内容",
                    "excerpt": "摘要",
                    "filename": "test.md",
                    "page": None,
                    "chapter": "第一章",
                    "score": 0.88,
                }
            ],
        }

        response = client.post("/api/chat", json={"question": "测试"})
        data = response.json()
        source = data["sources"][0]
        assert "filename" in source
        assert "page" in source  # 可以为 null
        assert "chapter" in source
        assert "excerpt" in source
        assert "score" in source

    @patch("app.routers.chat.list_records", return_value=[])
    def test_chat_with_empty_knowledge_base(self, mock_list):
        """知识库为空时应返回 400"""
        response = client.post("/api/chat", json={"question": "测试"})
        assert response.status_code == 400
        assert "没有文档" in response.json()["detail"]

    @patch("app.routers.chat.ask")
    @patch("app.routers.chat.list_records")
    def test_chat_with_custom_top_k(self, mock_list, mock_ask):
        """应接受 top_k 参数"""
        mock_list.return_value = [{"id": "abc"}]
        mock_ask.return_value = {"answer": "回答", "sources": []}

        response = client.post("/api/chat", json={
            "question": "测试",
            "top_k": 6,
        })
        assert response.status_code == 200

    def test_chat_empty_question(self):
        """空问题应返回 422（Pydantic 校验）"""
        response = client.post("/api/chat", json={"question": ""})
        assert response.status_code == 422

    def test_chat_missing_question(self):
        """缺少 question 字段应返回 422"""
        response = client.post("/api/chat", json={})
        assert response.status_code == 422

    @patch("app.routers.chat.ask")
    @patch("app.routers.chat.list_records")
    def test_chat_handles_chain_error(self, mock_list, mock_ask):
        """Chain 执行失败时应返回 500"""
        mock_list.return_value = [{"id": "abc"}]
        mock_ask.side_effect = RuntimeError("LLM 超时")

        response = client.post("/api/chat", json={"question": "测试"})
        assert response.status_code == 500

    @patch("app.routers.chat.ask")
    @patch("app.routers.chat.list_records")
    def test_chat_handles_insufficient_data(self, mock_list, mock_ask):
        """资料不足时 LLM 应返回明确的拒绝回答"""
        mock_list.return_value = [{"id": "abc"}]
        mock_ask.return_value = {
            "answer": "资料中未找到足够依据来回答这个问题。建议上传相关课程资料后再提问。",
            "sources": [],
        }

        response = client.post("/api/chat", json={"question": "火星上有没有水？"})
        assert response.status_code == 200
        data = response.json()
        assert "未找到足够依据" in data["answer"]
        assert data["sources"] == []

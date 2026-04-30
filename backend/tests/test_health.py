"""
健康检查端点测试
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """测试健康检查返回正常状态"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "StudyRAG"
        assert data["version"] == "0.1.0"


@pytest.mark.asyncio
@patch("app.routers.chat.list_records", return_value=[])
async def test_chat_endpoint_requires_documents(mock_list):
    """测试问答 API：知识库为空时应返回 400"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"question": "测试问题"})
        assert response.status_code == 400
        assert "没有文档" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_not_implemented():
    """测试上传 API 端点已存在（无文件时 FastAPI 参数校验返回 422）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/documents")
        assert response.status_code in [422, 501]

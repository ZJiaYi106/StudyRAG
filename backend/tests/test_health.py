"""
健康检查端点测试
"""

import pytest
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
async def test_chat_not_implemented():
    """测试问答 API 返回 501（尚未实现）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"question": "测试问题"})
        assert response.status_code == 501


@pytest.mark.asyncio
async def test_upload_not_implemented():
    """测试上传 API 返回 501（尚未实现）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/documents")
        # 没有文件时 FastAPI 返回 422（参数校验错误），这是预期行为
        # 有文件时返回 501
        assert response.status_code in [422, 501]

"""
认证 API 测试
测试注册、登录、JWT 验证
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestRegister:
    """测试 POST /api/auth/register"""

    def test_register_success(self):
        """注册成功应返回 token"""
        # 先清理可能存在的用户数据
        with patch("app.routers.auth.find_user", return_value=None), \
             patch("app.routers.auth.hash_password", return_value="hashed_mock"), \
             patch("app.routers.auth.create_user") as mock_create:
            mock_create.return_value = {
                "id": "1",
                "username": "testuser",
                "created_at": "2025-01-01T00:00:00",
            }
            response = client.post("/api/auth/register", json={
                "username": "testuser",
                "password": "123456",
            })
            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    def test_register_duplicate_username(self):
        """重复用户名应返回 409"""
        with patch("app.routers.auth.find_user") as mock_find:
            mock_find.return_value = {"username": "existing"}
            response = client.post("/api/auth/register", json={
                "username": "existing",
                "password": "123456",
            })
            assert response.status_code == 409
            assert "已被注册" in response.json()["detail"]

    def test_register_short_username(self):
        """用户名太短应返回 422"""
        response = client.post("/api/auth/register", json={
            "username": "a",
            "password": "12345678",
        })
        assert response.status_code == 422

    def test_register_short_password(self):
        """密码太短应返回 422"""
        response = client.post("/api/auth/register", json={
            "username": "validuser",
            "password": "12",
        })
        assert response.status_code == 422

    def test_register_invalid_username_chars(self):
        """包含特殊字符的用户名应返回 422"""
        response = client.post("/api/auth/register", json={
            "username": "user@name",
            "password": "123456",
        })
        assert response.status_code == 422


class TestLogin:
    """测试 POST /api/auth/login"""

    def test_login_success(self):
        """登录成功应返回 token"""
        with patch("app.routers.auth.find_user") as mock_find, \
             patch("app.routers.auth.verify_password") as mock_verify:
            mock_find.return_value = {
                "username": "testuser",
                "hashed_password": "$2b$12$...",
            }
            mock_verify.return_value = True

            response = client.post("/api/auth/login", json={
                "username": "testuser",
                "password": "correct_password",
            })
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data

    def test_login_wrong_password(self):
        """错误密码应返回 401"""
        with patch("app.routers.auth.find_user") as mock_find, \
             patch("app.routers.auth.verify_password") as mock_verify:
            mock_find.return_value = {"username": "testuser", "hashed_password": "x"}
            mock_verify.return_value = False

            response = client.post("/api/auth/login", json={
                "username": "testuser",
                "password": "wrong_password",
            })
            assert response.status_code == 401
            assert "错误" in response.json()["detail"]

    def test_login_nonexistent_user(self):
        """不存在的用户应返回 401"""
        with patch("app.routers.auth.find_user", return_value=None):
            response = client.post("/api/auth/login", json={
                "username": "nobody",
                "password": "anything",
            })
            assert response.status_code == 401


class TestAuthDependency:
    """测试认证依赖（get_current_user）"""

    def test_protected_route_without_token(self):
        """不带 token 访问受保护路由应返回 401"""
        # 临时取消 dependency override
        app.dependency_overrides.clear()

        response = client.get("/api/documents")
        assert response.status_code == 401
        assert "登录" in response.json()["detail"] or "token" in response.json()["detail"]

        # 恢复 override（conftest.py 在下一个测试的 fixture 中会重新设置）
        from app.utils.auth import get_current_user
        from tests.conftest import _mock_get_current_user
        app.dependency_overrides[get_current_user] = _mock_get_current_user

    def test_protected_route_with_invalid_token(self):
        """带无效 token 应返回 401"""
        app.dependency_overrides.clear()

        response = client.get(
            "/api/documents",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401

        # 恢复 override
        from app.utils.auth import get_current_user
        from tests.conftest import _mock_get_current_user
        app.dependency_overrides[get_current_user] = _mock_get_current_user

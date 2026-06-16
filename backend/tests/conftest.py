"""
测试全局配置
使用 FastAPI dependency_overrides 绕过认证依赖
"""

import pytest
from app.main import app
from app.utils.auth import get_current_user


async def _mock_get_current_user() -> str:
    """测试用：返回一个固定的测试用户名，跳过 JWT 验证"""
    return "test_user"


@pytest.fixture(autouse=True)
def override_auth():
    """自动在每个测试中覆盖 get_current_user 依赖"""
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    yield
    # 恢复原始依赖
    if original is not None:
        app.dependency_overrides[get_current_user] = original
    else:
        app.dependency_overrides.pop(get_current_user, None)

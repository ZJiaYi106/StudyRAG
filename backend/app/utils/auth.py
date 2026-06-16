"""
认证工具：密码哈希 + JWT 令牌生成与验证

密码：使用 bcrypt 直接哈希
JWT：使用 python-jose 库，HS256 算法签名
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import settings

# --- JWT ---
# HTTPBearer: FastAPI 提供的依赖，自动从请求头提取 Bearer token
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希是否匹配"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(username: str) -> str:
    """生成 JWT 访问令牌

    Args:
        username: 用户名，会被编码到 token 的 payload 中

    Returns:
        JWT 字符串，有效期由 settings.jwt_expire_days 控制
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    payload = {
        "sub": username,                    # subject：令牌所属用户
        "exp": expire,                      # expiration：过期时间
        "iat": datetime.now(timezone.utc),  # issued at：签发时间
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    """解码并验证 JWT token，返回 payload 或 None"""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    FastAPI 依赖：从请求的 Authorization header 中提取并验证 JWT。

    用法：在路由函数参数中添加 `user: str = Depends(get_current_user)`

    Args:
        credentials: HTTPBearer 自动从请求头提取的 Bearer token

    Returns:
        用户名（token 中的 sub 字段）

    Raises:
        HTTPException 401: token 缺失、无效或已过期
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录。在请求头中添加 Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username

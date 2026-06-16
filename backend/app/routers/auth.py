"""
认证 API 路由
提供注册、登录、获取当前用户信息
"""

import logging
from fastapi import APIRouter, HTTPException, Depends

from app.models.user import UserRegister, UserLogin, TokenResponse, UserInfo
from app.utils.user_store import find_user, create_user
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: UserRegister):
    """
    注册新用户。成功后直接返回 JWT token，无需再次登录。

    - 用户名 2-30 位，支持中英文、数字、下划线
    - 密码至少 4 位
    - 用户名已存在时返回 409
    """
    # 检查用户名是否已存在
    if find_user(body.username) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"用户名「{body.username}」已被注册，请换一个。",
        )

    # 创建用户
    hashed = hash_password(body.password)
    user = create_user(body.username, hashed)

    if user is None:
        raise HTTPException(
            status_code=500,
            detail="注册失败，请稍后重试。",
        )

    # 注册成功，直接生成 token（无需再次登录）
    token = create_access_token(body.username)

    logger.info(f"[认证] 注册成功: {body.username}")
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    """
    登录，验证用户名密码后返回 JWT token。

    - token 有效期 {settings.jwt_expire_days} 天
    - 在需要认证的请求中带上 Authorization: Bearer <token>
    """
    user = find_user(body.username)

    if user is None or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误。",
        )

    token = create_access_token(body.username)

    logger.info(f"[认证] 登录成功: {body.username}")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserInfo)
async def get_me(username: str = Depends(get_current_user)):
    """
    获取当前登录用户的信息。需要认证。

    Returns:
        当前用户名和注册时间
    """
    user = find_user(username)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    return UserInfo(
        username=user["username"],
        created_at=user["created_at"],
    )

"""
用户认证相关的 Pydantic 数据模型
"""

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    """注册请求"""
    username: str = Field(
        ...,
        min_length=2,
        max_length=30,
        pattern=r"^[a-zA-Z0-9_一-鿿]+$",
        description="用户名（2-30位，支持中英文、数字、下划线）",
    )
    password: str = Field(
        ...,
        min_length=4,
        max_length=100,
        description="密码（至少4位）",
    )


class UserLogin(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT Token 响应"""
    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")


class UserInfo(BaseModel):
    """当前用户信息"""
    username: str
    created_at: str

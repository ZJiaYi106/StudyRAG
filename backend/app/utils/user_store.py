"""
用户数据存储
用 JSON 文件存储用户信息（用户名 + 哈希密码）。

设计选择：与 registry.py 风格一致，使用简单的 JSON 文件，
不引入数据库依赖。适合单用户或少量用户场景。
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)

_lock = Lock()


def get_user_store_path() -> str:
    """获取用户数据文件路径"""
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "users.json")


def load_users() -> list[dict]:
    """加载所有用户"""
    path = get_user_store_path()
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"读取用户数据失败: {e}")
        return []


def save_users(users: list[dict]) -> None:
    """保存所有用户"""
    path = get_user_store_path()
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)


def find_user(username: str) -> Optional[dict]:
    """查找用户，返回用户字典或 None"""
    for user in load_users():
        if user["username"] == username:
            return user
    return None


def create_user(username: str, hashed_password: str) -> dict:
    """创建新用户，用户名已存在时返回 None"""
    users = load_users()

    # 检查用户名是否已存在
    for u in users:
        if u["username"] == username:
            return None

    user = {
        "id": str(len(users) + 1),
        "username": username,
        "hashed_password": hashed_password,
        "created_at": datetime.now().isoformat(),
    }

    users.append(user)
    save_users(users)

    logger.info(f"[用户] 新用户注册: {username}")
    return user

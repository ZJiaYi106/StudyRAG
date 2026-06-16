"""
分层缓存——内存 LRU + TTL
用于缓存 Embedding 结果和常见查询的检索结果。

缓存策略：
- Embedding Cache: 按文本 Hash 缓存向量（永不失效，文本不变向量就不变）
- Retrieval Cache: 按查询 Hash 缓存检索结果（TTL 5分钟）
"""

import hashlib
import logging
import time
from typing import Optional

from app.services.interfaces import BaseCache

logger = logging.getLogger(__name__)


class MemoryCache(BaseCache):
    """
    内存缓存，支持 TTL 过期。
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._store: dict = {}
        self._expires: dict = {}  # key → expire_timestamp

    def _hash_key(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, key: str) -> Optional[object]:
        hashed = self._hash_key(key)
        if hashed not in self._store:
            return None
        # 检查是否过期
        if hashed in self._expires:
            if time.time() > self._expires[hashed]:
                del self._store[hashed]
                del self._expires[hashed]
                return None
        return self._store[hashed]

    def set(self, key: str, value: object, ttl: int = 300) -> None:
        hashed = self._hash_key(key)
        self._store[hashed] = value
        if ttl > 0:
            self._expires[hashed] = time.time() + ttl

    def clear(self) -> None:
        self._store.clear()
        self._expires.clear()
        logger.info(f"[Cache:{self.name}] 缓存已清空")

    def stats(self) -> dict:
        """获取缓存统计"""
        active = sum(1 for k in self._store
                     if k not in self._expires or time.time() <= self._expires[k])
        return {
            "name": self.name,
            "total_entries": len(self._store),
            "active_entries": active,
        }

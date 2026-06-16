"""
增量索引：文件 Hash 去重
基于 SHA256 判断文件是否已入库，避免重复处理。
"""

import hashlib
import json
import os
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)
_lock = Lock()


def _get_store_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "file_hashes.json")


def _load_hashes() -> dict:
    path = _get_store_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_hashes(data: dict) -> None:
    path = _get_store_path()
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def compute_file_hash(file_path: str) -> str:
    """计算文件的 SHA256 哈希"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def _hash_key(file_path: str, owner: str = "") -> str:
    """生成复合 key：file_hash + owner，多用户同文件不冲突"""
    h = compute_file_hash(file_path)
    return f"{h}:{owner}" if owner else h


def is_duplicate(file_path: str, owner: str = "") -> Optional[str]:
    """检查同一用户是否已上传过相同文件"""
    key = _hash_key(file_path, owner)
    hashes = _load_hashes()
    if key in hashes:
        existing = hashes[key]
        logger.info(f"[HashStore] 文件已存在(同用户): {existing['filename']} (id={existing['document_id']})")
        return existing["document_id"]
    return None


def remove_by_document_id(document_id: str) -> None:
    """根据 document_id 删除 Hash 记录"""
    hashes = _load_hashes()
    to_delete = [k for k, v in hashes.items() if v.get("document_id") == document_id]
    for k in to_delete:
        del hashes[k]
    if to_delete:
        _save_hashes(hashes)
        logger.info(f"[HashStore] 已删除 {len(to_delete)} 条 Hash 记录 (id={document_id})")


def mark_indexed(file_path: str, filename: str, document_id: str, owner: str = "") -> None:
    """标记文件已入库（复合 key：hash+owner，多用户不冲突）"""
    key = _hash_key(file_path, owner)
    hashes = _load_hashes()
    hashes[key] = {
        "filename": filename,
        "document_id": document_id,
        "owner": owner,
    }
    _save_hashes(hashes)
    logger.info(f"[HashStore] 已记录: {filename} (key={key[:32]}...)")

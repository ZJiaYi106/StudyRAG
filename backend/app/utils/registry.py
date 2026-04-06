"""
文档注册表
用 JSON 文件追踪已上传文档的元数据（用于列表和删除）。

设计选择：使用简单的 JSON 文件而非数据库——
- MVP 阶段不需要复杂的查询
- 文档数量通常不会很大（几十到几百个）
- JSON 文件可以直接用文本编辑器查看，方便调试
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)

# 写锁，防止并发写入时数据损坏
_lock = Lock()


def get_registry_path() -> str:
    """获取注册表文件路径（与 Chroma 数据同目录）"""
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "documents.json")


def load_registry() -> list[dict]:
    """加载注册表，文件不存在时返回空列表"""
    path = get_registry_path()
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"读取注册表失败: {e}")
        return []


def save_registry(data: list[dict]) -> None:
    """保存注册表"""
    path = get_registry_path()
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def add_record(
    document_id: str,
    filename: str,
    file_type: str,
    page_count: int,
    chunk_count: int,
) -> dict:
    """添加一条文档记录"""
    record = {
        "id": document_id,
        "filename": filename,
        "file_type": file_type,
        "page_count": page_count,
        "chunk_count": chunk_count,
        "created_at": datetime.now().isoformat(),
    }

    all_records = load_registry()
    all_records.append(record)
    save_registry(all_records)

    logger.info(f"[Registry] 已记录文档: {filename} (id={document_id})")
    return record


def get_record(document_id: str) -> Optional[dict]:
    """查询单条记录"""
    for record in load_registry():
        if record["id"] == document_id:
            return record
    return None


def list_records() -> list[dict]:
    """列出所有记录，按创建时间降序"""
    records = load_registry()
    records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return records


def delete_record(document_id: str) -> Optional[dict]:
    """删除一条记录，返回被删除的记录或 None"""
    records = load_registry()
    for i, record in enumerate(records):
        if record["id"] == document_id:
            deleted = records.pop(i)
            save_registry(records)
            logger.info(f"[Registry] 已删除记录: {document_id}")
            return deleted
    return None

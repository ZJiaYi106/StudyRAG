"""
文件工具函数
处理文件保存、格式校验
"""

import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".md", ".markdown"}

# 最大文件大小 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


def validate_file(file: UploadFile) -> str:
    """
    校验上传文件的类型和大小。

    Args:
        file: FastAPI UploadFile 对象

    Returns:
        文件扩展名（小写，如 ".pdf"）

    Raises:
        ValueError: 文件类型不支持或文件过大
    """
    # 检查文件名
    if not file.filename:
        raise ValueError("文件名为空")

    # 检查扩展名
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"不支持的文件类型「{ext}」。"
            f"请上传以下格式：{', '.join(ALLOWED_EXTENSIONS)}"
        )

    return ext


async def save_upload_file(file: UploadFile, upload_dir: str) -> str:
    """
    将上传文件保存到指定目录，用 UUID 作为文件名以避免冲突。

    Args:
        file: FastAPI UploadFile 对象
        upload_dir: 上传文件保存目录

    Returns:
        保存后的完整文件路径

    Raises:
        IOError: 文件保存失败
    """
    # 确保目录存在
    os.makedirs(upload_dir, exist_ok=True)

    # 用 UUID 重命名，保留原始扩展名
    ext = Path(file.filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, safe_name)

    try:
        # 流式写入，防止大文件撑爆内存
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 每次读 1MB
                buffer.write(chunk)
    except Exception as e:
        # 写入失败时清理半成品文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise IOError(f"文件保存失败: {e}")

    return file_path


def remove_file(file_path: str) -> None:
    """安全删除文件，不存在的文件静默忽略"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        pass  # 删除失败不阻塞主流程

"""
文档相关的 Pydantic 数据模型
定义 API 请求/响应的数据结构，确保类型安全
"""

from datetime import datetime
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """上传文档成功后的响应"""
    id: str = Field(..., description="文档唯一标识（UUID）")
    filename: str = Field(..., description="原始文件名")
    file_type: str = Field(..., description="文件类型：pdf 或 markdown")
    page_count: int = Field(..., description="文档总页数（Markdown 为 1）")
    chunk_count: int = Field(..., description="切分后的文本片段数")
    created_at: datetime = Field(..., description="上传时间")


class DocumentListItem(BaseModel):
    """文档列表中的单个文档信息"""
    id: str
    filename: str
    file_type: str
    chunk_count: int
    created_at: datetime


class DeleteResponse(BaseModel):
    """删除操作的响应"""
    message: str = Field(..., description="操作结果描述")

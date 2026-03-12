"""
文档管理 API 路由
处理文件上传、文档列表查询、文档删除
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.document import DocumentUploadResponse, DocumentListItem, DeleteResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["文档管理"])


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    """
    上传 PDF 或 Markdown 文档。
    文件将被解析、切分、向量化后存入 Chroma。
    """
    # TODO: 步骤 5 实现完整上传管道
    logger.info(f"收到上传请求: {file.filename}")
    raise HTTPException(status_code=501, detail="上传功能将在步骤 5 实现")


@router.get("", response_model=list[DocumentListItem])
async def list_documents():
    """列出所有已上传的文档及其状态"""
    # TODO: 步骤 5 实现
    logger.info("查询文档列表")
    return []


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    """删除指定文档及其对应的向量数据"""
    # TODO: 步骤 5 实现
    logger.info(f"删除文档: {document_id}")
    raise HTTPException(status_code=501, detail="删除功能将在步骤 5 实现")

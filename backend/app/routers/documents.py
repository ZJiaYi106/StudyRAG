"""
文档管理 API 路由
处理文件上传、文档列表查询、文档删除

数据流（上传管道）：
  UploadFile → save_upload_file → load_document → split_documents
  → add_documents (embed + store) → add_record → 返回响应
"""

import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings
from app.models.document import DocumentUploadResponse, DocumentListItem, DeleteResponse
from app.utils.file_utils import validate_file, save_upload_file, remove_file
from app.utils.registry import add_record, list_records, delete_record, get_record
from app.services.loader import load_document
from app.services.splitter import split_documents
from app.services.vectorstore import add_documents, delete_by_document_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["文档管理"])


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    """
    上传 PDF 或 Markdown 文档。

    完整管道：
    1. 校验文件类型和大小
    2. 保存到本地磁盘
    3. Document Loader 解析文件 → List[Document]
    4. Text Splitter 切分 → List[Document] (chunks)
    5. Chroma VectorStore 向量化并持久化
    6. 写入文档注册表
    7. 返回上传统计信息
    """
    # --- 步骤 1: 校验 ---
    try:
        ext = validate_file(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    file_type = "markdown" if ext in (".md", ".markdown") else "pdf"
    document_id = uuid.uuid4().hex
    original_filename = file.filename

    logger.info(f"[上传] 开始处理: {original_filename} (id={document_id})")

    # --- 步骤 2: 保存文件 ---
    try:
        file_path = await save_upload_file(file, settings.upload_dir)
    except IOError as e:
        logger.error(f"[上传] 文件保存失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}")

    # --- 步骤 3-5: Loader → Splitter → VectorStore ---
    try:
        # 3. 加载文档（LangChain Document Loader）
        docs = load_document(file_path, document_id)
        if not docs:
            raise ValueError("文档解析结果为空，请检查文件内容")

        page_count = len(docs)

        # 4. 切分文档（LangChain Text Splitter）
        chunks = split_documents(docs, file_type)
        if not chunks:
            raise ValueError("文档切分结果为空")

        # 5. 向量化并存入 Chroma（LangChain Chroma VectorStore）
        chunk_ids = add_documents(chunks)

    except ValueError as e:
        # 解析或切分失败时清理已保存的文件
        remove_file(file_path)
        logger.error(f"[上传] 处理失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 向量存储失败也清理文件
        remove_file(file_path)
        logger.error(f"[上传] VectorStore 入库失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档入库失败: {e}")

    # --- 步骤 6: 登记到注册表 ---
    record = add_record(
        document_id=document_id,
        filename=original_filename,
        file_type=file_type,
        page_count=page_count,
        chunk_count=len(chunks),
    )

    logger.info(
        f"[上传] 完成: {original_filename} "
        f"({page_count} 页/节 → {len(chunks)} chunks → {len(chunk_ids)} 向量)"
    )

    # --- 步骤 7: 返回 ---
    return DocumentUploadResponse(
        id=record["id"],
        filename=record["filename"],
        file_type=record["file_type"],
        page_count=record["page_count"],
        chunk_count=record["chunk_count"],
        created_at=datetime.fromisoformat(record["created_at"]),
    )


@router.get("", response_model=list[DocumentListItem])
async def list_documents():
    """列出所有已上传的文档，按上传时间降序"""
    records = list_records()
    logger.info(f"[列表] 返回 {len(records)} 个文档")
    return [
        DocumentListItem(
            id=r["id"],
            filename=r["filename"],
            file_type=r["file_type"],
            chunk_count=r["chunk_count"],
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in records
    ]


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    """
    删除指定文档及其关联数据：
    1. 从 Chroma 删除所有 chunk 向量
    2. 从注册表删除记录
    3. 清理上传文件（如果还存在）
    """
    # 先查注册表确认文档存在
    record = get_record(document_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"文档不存在: {document_id}")

    filename = record["filename"]

    # 1. 从 Chroma 删除向量
    try:
        deleted_count = delete_by_document_id(document_id)
        logger.info(f"[删除] Chroma 中删除 {deleted_count} 个 chunk")
    except Exception as e:
        logger.error(f"[删除] Chroma 删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"向量删除失败: {e}")

    # 2. 从注册表删除
    delete_record(document_id)

    # 3. 清理文件（静默失败，文件可能已被移除）
    # 遍历 upload_dir 下文件查找包含 document_id 的文件
    import os
    try:
        for f in os.listdir(settings.upload_dir):
            if f.startswith(document_id):
                remove_file(os.path.join(settings.upload_dir, f))
                break
    except Exception:
        pass  # 文件清理不是关键路径

    logger.info(f"[删除] 完成: {filename} (id={document_id})")
    return DeleteResponse(message=f"已删除文档「{filename}」及其 {deleted_count} 个资料片段")

"""
文档管理 API 集成测试
测试上传管道的端点行为（mock 底层服务，专注于 HTTP 层的正确性）
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ================================================================
# 上传端点测试
# ================================================================

class TestUploadDocument:
    """测试 POST /api/documents"""

    @patch("app.routers.documents.add_documents")
    @patch("app.routers.documents.split_documents")
    @patch("app.routers.documents.load_document")
    def test_upload_pdf_success(self, mock_load, mock_split, mock_add):
        """上传 PDF 应返回 201 和正确的响应结构"""
        # Mock 管道各环节
        from langchain_core.documents import Document

        mock_load.return_value = [
            Document(page_content="第1页内容", metadata={"page": 1}),
            Document(page_content="第2页内容", metadata={"page": 2}),
        ]
        mock_split.return_value = [
            Document(page_content="chunk 1", metadata={"page": 1, "chunk_index": 0}),
            Document(page_content="chunk 2", metadata={"page": 1, "chunk_index": 1}),
            Document(page_content="chunk 3", metadata={"page": 2, "chunk_index": 2}),
        ]
        mock_add.return_value = ["id1", "id2", "id3"]

        pdf_content = b"%PDF-1.4 fake pdf content"
        response = client.post(
            "/api/documents",
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["file_type"] == "pdf"
        assert data["page_count"] == 2
        assert data["chunk_count"] == 3
        assert "id" in data
        assert "created_at" in data

    @patch("app.routers.documents.add_documents")
    @patch("app.routers.documents.split_documents")
    @patch("app.routers.documents.load_document")
    def test_upload_markdown_success(self, mock_load, mock_split, mock_add):
        """上传 Markdown 应返回 201 和正确的 file_type"""
        from langchain_core.documents import Document

        mock_load.return_value = [
            Document(page_content="# 章节1\n内容", metadata={"chapter": "章节1"}),
        ]
        mock_split.return_value = [
            Document(page_content="chunk", metadata={"chapter": "章节1", "chunk_index": 0}),
        ]
        mock_add.return_value = ["id1"]

        md_content = b"# Test\n\nSome content"
        response = client.post(
            "/api/documents",
            files={"file": ("notes.md", BytesIO(md_content), "text/markdown")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_type"] == "markdown"
        assert data["filename"] == "notes.md"

    def test_upload_unsupported_format(self):
        """上传不支持的文件格式应返回 400"""
        response = client.post(
            "/api/documents",
            files={"file": ("image.png", BytesIO(b"fake-png"), "image/png")},
        )
        assert response.status_code == 400
        assert "不支持" in response.json()["detail"]

    def test_upload_no_file(self):
        """不传文件应返回 422（FastAPI 自动校验）"""
        response = client.post("/api/documents")
        assert response.status_code == 422

    @patch("app.routers.documents.load_document")
    def test_upload_empty_document(self, mock_load):
        """文档解析为空时应返回 400"""
        mock_load.return_value = []

        response = client.post(
            "/api/documents",
            files={"file": ("empty.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert response.status_code == 400
        assert "空" in response.json()["detail"]

    @patch("app.routers.documents.save_upload_file")
    def test_upload_save_failure(self, mock_save):
        """文件保存失败时应返回 500"""
        mock_save.side_effect = IOError("磁盘空间不足")

        response = client.post(
            "/api/documents",
            files={"file": ("test.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert response.status_code == 500

    @patch("app.routers.documents.add_documents")
    @patch("app.routers.documents.split_documents")
    @patch("app.routers.documents.load_document")
    def test_upload_vectordb_failure(self, mock_load, mock_split, mock_add):
        """向量存储失败时应返回 500"""
        from langchain_core.documents import Document

        mock_load.return_value = [
            Document(page_content="内容", metadata={"page": 1}),
        ]
        mock_split.return_value = [
            Document(page_content="chunk", metadata={"page": 1}),
        ]
        mock_add.side_effect = RuntimeError("Chroma 连接失败")

        response = client.post(
            "/api/documents",
            files={"file": ("test.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert response.status_code == 500


# ================================================================
# 列表端点测试
# ================================================================

class TestListDocuments:
    """测试 GET /api/documents"""

    def test_list_empty(self):
        """无文档时应返回空列表"""
        # 确保注册表为空
        with patch("app.routers.documents.list_records", return_value=[]):
            response = client.get("/api/documents")
            assert response.status_code == 200
            assert response.json() == []

    def test_list_with_documents(self):
        """有文档时应返回文档列表"""
        # list_records 已按时间降序排列
        mock_records = [
            {
                "id": "def456",
                "filename": "notes.md",
                "file_type": "markdown",
                "chunk_count": 3,
                "page_count": 1,
                "created_at": "2026-03-12T11:00:00",
            },
            {
                "id": "abc123",
                "filename": "lecture.pdf",
                "file_type": "pdf",
                "chunk_count": 15,
                "page_count": 5,
                "created_at": "2026-03-12T10:00:00",
            },
        ]
        with patch("app.routers.documents.list_records", return_value=mock_records):
            response = client.get("/api/documents")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["filename"] == "notes.md"     # 较新的在前
            assert data[1]["filename"] == "lecture.pdf"   # 较旧的在后


# ================================================================
# 删除端点测试
# ================================================================

class TestDeleteDocument:
    """测试 DELETE /api/documents/{id}"""

    @patch("app.routers.documents.delete_by_document_id")
    @patch("app.routers.documents.delete_record")
    @patch("app.routers.documents.get_record")
    def test_delete_success(self, mock_get, mock_delete_rec, mock_delete_vec):
        """删除存在的文档应返回成功消息"""
        mock_get.return_value = {
            "id": "abc123",
            "filename": "lecture.pdf",
            "file_type": "pdf",
            "chunk_count": 15,
            "page_count": 5,
            "created_at": "2026-03-12T10:00:00",
        }
        mock_delete_vec.return_value = 15
        mock_delete_rec.return_value = mock_get.return_value

        response = client.delete("/api/documents/abc123")
        assert response.status_code == 200
        data = response.json()
        assert "已删除" in data["message"]
        assert "lecture.pdf" in data["message"]

    @patch("app.routers.documents.get_record", return_value=None)
    def test_delete_nonexistent(self, mock_get):
        """删除不存在的文档应返回 404"""
        response = client.delete("/api/documents/nonexistent")
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]


# ================================================================
# 健康检查测试（更新后）
# ================================================================

class TestHealthCheck:
    """测试健康检查（含 Chroma 状态）"""

    def test_health_includes_chroma_and_doc_count(self):
        """健康检查应包含 chroma 状态和文档数"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "chroma" in data
        assert "document_count" in data

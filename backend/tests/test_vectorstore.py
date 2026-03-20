"""
Chroma VectorStore 单元测试
测试文档入库、相似度检索、按 ID 删除、统计信息

注意：这些测试使用 FakeEmbeddings（生成假向量）来避免调用实际 API，
同时验证 Chroma 的存储、检索、删除逻辑是否正确。
"""

import os
import uuid
import pytest
import tempfile
import shutil

from langchain_core.documents import Document

# 使用 FakeEmbeddings 产生固定维度向量，不依赖外部 API
from langchain_chroma import Chroma
from langchain_core.embeddings import FakeEmbeddings

from app.services.vectorstore import (
    add_documents,
    similarity_search,
    delete_by_document_id,
    get_collection_stats,
    CHROMA_PERSIST_DIR,
)


# ================================================================
# 测试环境准备
# ================================================================

@pytest.fixture(autouse=True)
def setup_vectorstore():
    """
    每个测试用例前后：
    - 使用临时目录作为 Chroma 持久化路径
    - 使用 FakeEmbeddings（每维都是 1.0 的假向量）
    - 测试后清理
    """
    # 准备临时目录
    tmpdir = tempfile.mkdtemp()

    # 覆盖全局变量（通过 patch）
    import app.services.vectorstore as vs
    old_persist = vs.CHROMA_PERSIST_DIR
    old_store = vs._vectorstore

    vs.CHROMA_PERSIST_DIR = tmpdir
    vs._vectorstore = None

    # 用 FakeEmbeddings 替代真实 Embeddings
    fake_embeddings = FakeEmbeddings(size=128)  # 128 维假向量

    vs._vectorstore = Chroma(
        embedding_function=fake_embeddings,
        persist_directory=tmpdir,
        collection_name="test_collection",
    )

    yield

    # 清理
    vs._vectorstore = old_store
    vs.CHROMA_PERSIST_DIR = old_persist
    shutil.rmtree(tmpdir, ignore_errors=True)


# ================================================================
# 测试数据
# ================================================================

def make_chunks(n: int = 3, doc_id: str = "test-doc-001") -> list[Document]:
    """快速创建测试用 chunk 列表"""
    return [
        Document(
            page_content=f"这是第 {i+1} 个测试片段。内容为深度学习相关。",
            metadata={
                "document_id": doc_id,
                "filename": "test.pdf",
                "file_type": "pdf",
                "page": i + 1,
                "chunk_index": i,
                "chapter": f"第 {i+1} 章",
            }
        )
        for i in range(n)
    ]


# ================================================================
# add_documents 测试
# ================================================================

class TestAddDocuments:
    """测试文档入库"""

    def test_add_returns_ids(self):
        """入库应返回 Chroma 分配的 ID 列表"""
        docs = make_chunks(3)
        ids = add_documents(docs)
        assert len(ids) == 3
        # 每个 ID 应该是非空字符串
        for id_ in ids:
            assert isinstance(id_, str)
            assert len(id_) > 0

    def test_add_empty_list(self):
        """空列表应返回空列表"""
        ids = add_documents([])
        assert ids == []

    def test_collection_count_after_add(self):
        """入库后 Collection 的文档数应增加"""
        docs = make_chunks(5)
        add_documents(docs)
        stats = get_collection_stats()
        assert stats["count"] == 5

    def test_metadata_preserved_in_storage(self):
        """入库后的 metadata 应完整保留"""
        docs = make_chunks(1, doc_id="meta-test-001")
        docs[0].metadata["custom_field"] = "custom_value"
        add_documents(docs)

        # 从 Chroma 中取回验证
        results = similarity_search("深度学习", k=1)
        assert len(results) == 1
        retrieved_doc, _ = results[0]
        assert retrieved_doc.metadata["document_id"] == "meta-test-001"
        assert retrieved_doc.metadata["custom_field"] == "custom_value"
        assert retrieved_doc.metadata["page"] == 1


# ================================================================
# similarity_search 测试
# ================================================================

class TestSimilaritySearch:
    """测试相似度检索"""

    def test_search_returns_results(self):
        """检索应返回非空结果"""
        docs = make_chunks(5)
        add_documents(docs)

        results = similarity_search("深度学习", k=3)
        assert 1 <= len(results) <= 3

    def test_search_result_format(self):
        """检索结果格式应为 (Document, float)"""
        docs = make_chunks(2)
        add_documents(docs)

        results = similarity_search("测试", k=2)
        for item in results:
            doc, score = item
            assert isinstance(doc, Document)
            assert isinstance(score, float)

    def test_search_scores_are_valid_numbers(self):
        """相似度分数应为有效数值（注意 FakeEmbeddings 使用 L2 距离，分数可较大）"""
        docs = make_chunks(3)
        add_documents(docs)

        results = similarity_search("片段", k=3)
        for _, score in results:
            assert isinstance(score, float), f"分数应为 float，实际 {type(score)}"
            # FakeEmbeddings 使用 L2 欧氏距离，分数 = 距离²，可以很大
            # 真实 Embeddings 用余弦相似度时分数在 [0,1]

    def test_search_with_empty_collection(self):
        """空 Collection 检索应返回空列表"""
        # 清理：使用新 collection
        import app.services.vectorstore as vs
        old_store = vs._vectorstore
        vs._vectorstore = None

        # 创建一个全新的空 Collection
        vs._vectorstore = Chroma(
            embedding_function=FakeEmbeddings(size=128),
            persist_directory=vs.CHROMA_PERSIST_DIR,
            collection_name=f"empty_test_{uuid.uuid4().hex[:8]}",
        )

        try:
            results = similarity_search("任意查询", k=3)
            assert results == []
        finally:
            vs._vectorstore = old_store

    def test_search_k_limits_results(self):
        """k 参数应限制返回数量"""
        docs = make_chunks(10)
        add_documents(docs)

        results = similarity_search("测试", k=3)
        assert len(results) <= 3


# ================================================================
# delete_by_document_id 测试
# ================================================================

class TestDeleteByDocumentId:
    """测试按文档 ID 删除"""

    def test_delete_removes_all_chunks(self):
        """删除应移除该文档的所有 chunk"""
        docs = make_chunks(5, doc_id="to-delete-001")
        add_documents(docs)

        # 再添加另一个文档（不应被删除）
        other_docs = make_chunks(3, doc_id="keep-001")
        add_documents(other_docs)

        stats_before = get_collection_stats()
        assert stats_before["count"] == 8

        deleted_count = delete_by_document_id("to-delete-001")
        assert deleted_count == 5

        stats_after = get_collection_stats()
        assert stats_after["count"] == 3  # 只剩 keep-001 的 3 个

    def test_delete_nonexistent_document(self):
        """删除不存在的文档应返回 0"""
        deleted = delete_by_document_id("nonexistent-id")
        assert deleted == 0

    def test_search_after_delete_returns_empty(self):
        """删除后检索不应再返回该文档的内容"""
        # 添加一个独特内容的文档
        unique_doc = [
            Document(
                page_content="XYZ特殊标记内容用于验证删除",
                metadata={"document_id": "unique-del-test", "filename": "test.pdf"}
            )
        ]
        add_documents(unique_doc)

        # 确认能检索到
        results_before = similarity_search("XYZ特殊标记", k=1)
        assert len(results_before) > 0

        # 删除
        delete_by_document_id("unique-del-test")

        # 确认检索不到（因为 FakeEmbeddings 的相似度行为，这里主要验证不抛异常）
        results_after = similarity_search("XYZ特殊标记", k=1)
        # 删除后，该文档不应出现在结果中
        for doc, _ in results_after:
            assert doc.metadata.get("document_id") != "unique-del-test"


# ================================================================
# 统计信息测试
# ================================================================

class TestCollectionStats:
    """测试统计信息"""

    def test_stats_returns_collection_info(self):
        """统计信息应包含 collection 名称和文档数"""
        stats = get_collection_stats()
        assert "collection_name" in stats
        assert "count" in stats
        assert isinstance(stats["count"], int)

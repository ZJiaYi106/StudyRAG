"""
重排模型管理 API 测试
测试 GET /api/reranker/status、POST /load、POST /unload

模型真实加载耗时且需联网，因此测试中 mock RerankerService._construct，
只验证状态机与 API 行为，不触发真实下载。
"""

import time
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app
from app.services.reranker import get_reranker_service

client = TestClient(app)


def _reset_service():
    """每个测试前重置单例状态，避免互相影响"""
    svc = get_reranker_service()
    with svc._lock:
        svc._model = None
        svc._loaded_path = None
        svc._loading = False
        svc._error = None


def _wait_loaded(timeout=3.0) -> bool:
    """轮询直到模型就绪或超时"""
    svc = get_reranker_service()
    end = time.time() + timeout
    while time.time() < end:
        if svc.is_ready():
            return True
        time.sleep(0.02)
    return False


class TestRerankerAPI:
    """测试重排模型管理接口"""

    def setup_method(self):
        _reset_service()

    def test_status_initial_not_loaded(self):
        """初始状态应为未加载，且返回可选模型列表"""
        r = client.get("/api/reranker/status")
        assert r.status_code == 200
        data = r.json()
        assert data["loaded"] is False
        assert data["loading"] is False
        assert isinstance(data["available"], list)
        assert len(data["available"]) >= 1
        assert data["available"][0]["path"] == "BAAI/bge-reranker-v2-m3"

    def test_load_then_loaded(self):
        """触发加载后，后台线程完成，状态变为已加载"""
        svc = get_reranker_service()
        with patch.object(svc, "_construct", return_value=MagicMock()):
            r = client.post("/api/reranker/load", json={"model": "BAAI/bge-reranker-v2-m3"})
            assert r.status_code == 200
            assert r.json()["loading"] is True
            assert _wait_loaded(), "模型应在后台线程加载完成"

        st = client.get("/api/reranker/status").json()
        assert st["loaded"] is True
        assert st["model"] == "BAAI/bge-reranker-v2-m3"

    def test_load_default_recommended_model(self):
        """未指定 model 时应加载推荐模型"""
        svc = get_reranker_service()
        with patch.object(svc, "_construct", return_value=MagicMock()) as mock_ctor:
            r = client.post("/api/reranker/load", json={})
            assert r.status_code == 200
            assert _wait_loaded()
            mock_ctor.assert_called_once_with("BAAI/bge-reranker-v2-m3")

    def test_load_while_loading_returns_409(self):
        """加载中再次触发应返回 409"""
        svc = get_reranker_service()
        with svc._lock:
            svc._loading = True
        try:
            r = client.post("/api/reranker/load", json={})
            assert r.status_code == 409
            assert "加载中" in r.json()["detail"]
        finally:
            with svc._lock:
                svc._loading = False

    def test_unload(self):
        """已加载模型可卸载，状态回到未加载"""
        svc = get_reranker_service()
        with patch.object(svc, "_construct", return_value=MagicMock()):
            client.post("/api/reranker/load", json={})
            assert _wait_loaded()

        r = client.post("/api/reranker/unload")
        assert r.status_code == 200
        assert r.json()["loaded"] is False

    def test_load_failure_records_error(self):
        """加载失败时应记录错误信息，loaded 仍为 False"""
        svc = get_reranker_service()
        with patch.object(svc, "_construct", side_effect=RuntimeError("网络超时")):
            client.post("/api/reranker/load", json={"model": "BAAI/bge-reranker-v2-m3"})
            # 等待后台线程结束（_loading 变 False）
            end = time.time() + 3.0
            while time.time() < end:
                with svc._lock:
                    if not svc._loading:
                        break
                time.sleep(0.02)

        st = client.get("/api/reranker/status").json()
        assert st["loaded"] is False
        assert st["loading"] is False
        assert "网络超时" in st["error"]

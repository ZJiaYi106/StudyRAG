"""
LCEL Chain 服务单元测试
测试 Chain 构建、Runnable 组件、ask() / ask_stream() 异步问答函数
"""

import json
import pytest
from unittest.mock import patch

from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage

from app.services.chain import ask, ask_stream


def _fake_llm(answer: str):
    """构造一个返回固定 AIMessage 的假 LLM。

    同步 invoke 与默认 astream 都可用，避免 MagicMock 在异步链路里
    无法被 RunnableLambda / StrOutputParser 正确解析的问题。
    """
    return RunnableLambda(lambda _input: AIMessage(content=answer))


class TestAsk:
    """测试 ask() 异步问答函数（检索在线程池执行，LLM 走 ainvoke）"""

    @patch("app.services.chain._full_search_sync")
    async def test_ask_returns_dict_with_answer_and_sources(self, mock_search):
        """ask() 应返回包含 answer 和 sources 的字典"""
        mock_search.return_value = [{
            "content": "测试内容",
            "filename": "test.pdf",
            "page": 1,
            "chapter": None,
            "score": 0.9,
        }]

        with patch("app.services.chain._build_llm", return_value=_fake_llm("测试回答")):
            result = await ask("测试问题")

        assert "answer" in result
        assert "sources" in result
        assert isinstance(result["answer"], str)
        assert isinstance(result["sources"], list)

    @patch("app.services.chain._full_search_sync")
    async def test_ask_passes_sources_to_response(self, mock_search):
        """sources 应包含检索结果"""
        mock_search.return_value = [
            {"content": "A", "filename": "a.pdf", "page": 1, "chapter": None, "score": 0.9},
            {"content": "B", "filename": "b.pdf", "page": 2, "chapter": "Ch1", "score": 0.8},
        ]

        with patch("app.services.chain._build_llm", return_value=_fake_llm("回答")):
            result = await ask("问题")

        assert len(result["sources"]) == 2
        assert result["sources"][0]["filename"] == "a.pdf"

    @patch("app.services.chain._full_search_sync")
    async def test_ask_handles_no_sources(self, mock_search):
        """无检索结果时也应正常返回"""
        mock_search.return_value = []

        with patch("app.services.chain._build_llm", return_value=_fake_llm("资料不足")):
            result = await ask("不知道的问题")

        assert result["sources"] == []
        assert isinstance(result["answer"], str)


class TestAskStream:
    """测试 ask_stream() 流式问答（SSE 事件序列）"""

    @staticmethod
    def _parse(evt: str) -> dict:
        """解析 SSE 数据帧为 dict"""
        return json.loads(evt.removeprefix("data: ").strip())

    @patch("app.services.chain._full_search_sync")
    async def test_stream_emits_token_then_result(self, mock_search):
        """LLM 生成应先推送 token 事件，最后推送 result 事件（含完整回答）"""
        mock_search.return_value = [
            {"content": "A", "filename": "a.pdf", "page": 1, "chapter": None, "score": 0.9},
        ]

        events = []
        with patch("app.services.chain._build_llm", return_value=_fake_llm("流式回答")):
            async for evt in ask_stream("测试问题"):
                events.append(self._parse(evt))

        steps = [e["step"] for e in events]
        assert "token" in steps, "应有 token 级流式事件"
        assert steps[-1] == "result", "最后一个事件应为 result"

        result_event = events[-1]
        assert result_event["answer"] == "流式回答"
        assert result_event["sources"][0]["filename"] == "a.pdf"

    @patch("app.services.chain._full_search_sync")
    async def test_stream_emits_error_event_on_search_failure(self, mock_search):
        """检索线程抛异常时应推送 error 事件，而不是让 SSE 流崩溃"""
        mock_search.side_effect = RuntimeError("rerank 模型加载失败")

        events = []
        with patch("app.services.chain._build_llm", return_value=_fake_llm("不会用到")):
            async for evt in ask_stream("测试问题"):
                events.append(self._parse(evt))

        error_events = [e for e in events if e["step"] == "error"]
        assert len(error_events) == 1
        assert "rerank" in error_events[0]["message"]

"""
Prompt 模板服务单元测试
测试 Prompt 渲染、来源格式化、模板构建
"""

import pytest
from app.services.prompt import (
    format_context,
    build_prompt_messages,
    build_prompt_template,
    SYSTEM_TEMPLATE,
    HUMAN_TEMPLATE,
)


class TestFormatContext:
    """测试检索结果 → 参考资料来源文本格式化"""

    def test_empty_list_returns_placeholder(self):
        """空检索结果应返回占位文本"""
        result = format_context([])
        assert "暂无" in result

    def test_single_result_formatting(self):
        """单个检索结果应正确格式化"""
        retrieved = [{
            "content": "深度学习是机器学习的一个分支。",
            "filename": "AI讲义.pdf",
            "page": 3,
            "chapter": "第一章",
            "score": 0.95,
        }]

        result = format_context(retrieved)
        assert "[1]" in result
        assert "AI讲义.pdf" in result
        assert "第3页" in result
        assert "第一章" in result
        assert "深度学习是机器学习的一个分支" in result

    def test_multiple_results_numbered(self):
        """多个结果应有递增编号"""
        retrieved = [
            {"content": "内容A", "filename": "a.pdf", "page": 1, "chapter": None, "score": 0.9},
            {"content": "内容B", "filename": "b.pdf", "page": 2, "chapter": "Ch2", "score": 0.8},
            {"content": "内容C", "filename": "c.pdf", "page": 5, "chapter": None, "score": 0.7},
        ]

        result = format_context(retrieved)
        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" in result

    def test_no_page_shows_only_filename(self):
        """无页码的结果不显示页码"""
        retrieved = [{
            "content": "Markdown 内容",
            "filename": "notes.md",
            "page": None,
            "chapter": None,
            "score": 0.85,
        }]

        result = format_context(retrieved)
        assert "notes.md" in result
        assert "第" not in result or "页" not in result  # 无页码标记

    def test_chapter_included_when_present(self):
        """有章节时应显示章节名"""
        retrieved = [{
            "content": "自注意力机制...",
            "filename": "transformer.md",
            "page": None,
            "chapter": "2.1 注意力机制",
            "score": 0.92,
        }]

        result = format_context(retrieved)
        assert "2.1 注意力机制" in result


class TestBuildPromptMessages:
    """测试消息列表构建"""

    def test_returns_list_of_two_messages(self):
        """应返回 system + user 两条消息"""
        messages = build_prompt_messages("参考资料内容", "什么是 RAG？")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_system_message_contains_rules(self):
        """System 消息应包含行为约束"""
        messages = build_prompt_messages("test context", "test question")
        system_msg = messages[0]["content"]
        assert "只能依据参考资料" in system_msg
        assert "资料中未找到足够依据" in system_msg
        assert "使用中文" in system_msg

    def test_user_message_contains_context(self):
        """User 消息应包含注入的参考资料"""
        messages = build_prompt_messages("---参考资料---", "问题")
        user_msg = messages[1]["content"]
        assert "---参考资料---" in user_msg

    def test_user_message_contains_question(self):
        """User 消息应包含用户问题"""
        messages = build_prompt_messages("context", "Transformer 是什么？")
        user_msg = messages[1]["content"]
        assert "Transformer 是什么？" in user_msg


class TestBuildPromptTemplate:
    """测试 LangChain ChatPromptTemplate"""

    def test_template_has_two_messages(self):
        """模板应包含 system 和 human 两条消息"""
        template = build_prompt_template()
        messages = template.messages
        assert len(messages) == 2

    def test_template_has_context_and_question_variables(self):
        """模板的 Human 消息应包含 {context} 和 {question} 变量"""
        template = build_prompt_template()
        # 通过 invoke 验证变量替换
        prompt_value = template.invoke({
            "context": "参考资料内容",
            "question": "用户问题",
        })
        messages = prompt_value.to_messages()
        human_content = messages[1].content
        assert "参考资料内容" in human_content
        assert "用户问题" in human_content

    def test_template_invoke_returns_prompt_value(self):
        """invoke 应返回 ChatPromptValue"""
        template = build_prompt_template()
        result = template.invoke({
            "context": "C",
            "question": "Q",
        })
        # ChatPromptValue 有 to_messages() 和 to_string() 方法
        assert hasattr(result, "to_messages")
        assert hasattr(result, "to_string")

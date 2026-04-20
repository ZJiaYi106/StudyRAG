"""
Prompt 模板服务
使用 LangChain ChatPromptTemplate 构建 RAG 问答 Prompt

LangChain 组件 #6：PromptTemplate（Prompt 模板）
- 作用：将动态变量（检索结果、用户问题）填入预设的 Prompt 结构中
- ChatPromptTemplate = SystemMessage（角色设定）+ HumanMessage（用户输入）
- 模板变量用 {变量名} 标记，调用 .format() 或 .invoke() 时替换

Prompt 设计是 RAG 系统最关键的一环：
1. 角色设定 → 约束 LLM 的行为边界
2. 参考资料注入 → 让 LLM 只能基于给定资料回答
3. 引用标记 → 要求 LLM 在回答中标注来源编号
4. 兜底规则 → 资料不足时明确拒绝，防止幻觉
"""

import logging
from typing import List, Dict, Any

# LangChain: ChatPromptTemplate —— 构建 Chat 模型的 Prompt
# 支持 SystemMessage + HumanMessage 等多角色消息结构
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


# ================================================================
# System Prompt（系统角色设定）
# ================================================================

SYSTEM_TEMPLATE = """你是一个严谨的课程资料问答助手。你的回答必须基于用户提供的参考资料。

## 回答规则

1. **只能依据参考资料**：你的所有回答必须来自下方「参考资料」中的内容，不得使用你自己的知识。
2. **引用来源**：每个观点后标注来源编号，例如 [1]、[2]。
3. **资料不足时诚实说明**：如果参考资料中没有足够信息回答用户问题，请明确说：
   "资料中未找到足够依据来回答这个问题。"
   然后可以建议用户补充相关资料。
4. **使用中文**：所有回答使用简体中文。

## 回答格式

对于可回答的问题，按以下结构组织：
- 先给出简洁的结论
- 再分点详细说明（每点标注来源编号）
- 末尾列出引用的来源清单

格式示例：
```
[结论段落]

1. 要点一 [1]
2. 要点二 [2]

---
**参考来源：**
[1] NLP讲义.pdf 第3页
[2] 深度学习笔记.md - "2.1 注意力机制"
```
"""

# ================================================================
# Human Prompt（用户消息模板，注入检索结果）
# ================================================================

HUMAN_TEMPLATE = """## 参考资料

{context}

## 用户问题

{question}"""


# ================================================================
# 构建 ChatPromptTemplate
# ================================================================

def build_prompt_template() -> ChatPromptTemplate:
    """
    创建 RAG 问答的 ChatPromptTemplate。

    --- LangChain 教学 ---
    输入：无
    输出：ChatPromptTemplate 实例

    ChatPromptTemplate 内部结构：
    [
        SystemMessage(content=SYSTEM_TEMPLATE),
        HumanMessage(content=HUMAN_TEMPLATE),  ← 包含 {context} 和 {question} 变量
    ]

    .invoke({"context": "...", "question": "..."}) 返回 ChatPromptValue
    然后传给 LLM 生成回答
    """
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_TEMPLATE),
        ("human", HUMAN_TEMPLATE),
    ])


# ================================================================
# 检索结果 → Prompt 上下文格式化
# ================================================================

def format_context(retrieved: List[Dict[str, Any]]) -> str:
    """
    将检索结果格式化为 Prompt 中的「参考资料」文本块。

    --- LangChain 教学 ---
    输入: List[dict]（来自 Retriever）
    输出: str（注入 {context} 变量的文本）

    这是 LangChain 不提供的自定义逻辑——
    如何把检索结果以最优格式写入 Prompt，取决于你的产品设计。

    格式：
    [1] (来源: NLP讲义.pdf, 第3页)
    Transformer 是一种基于自注意力机制的深度学习架构...

    [2] (来源: 深度学习笔记.md, 2.1 注意力机制)
    自注意力机制允许模型在处理每个词时关注输入序列中的所有其他词...

    Args:
        retrieved: Retriever 返回的格式化结果列表

    Returns:
        格式化的参考资料来源文本
    """
    if not retrieved:
        return "（暂无参考资料）"

    parts = []
    for i, item in enumerate(retrieved, start=1):
        # 构建来源头
        source_parts = [f"来源: {item['filename']}"]
        if item.get("page") is not None:
            source_parts.append(f"第{item['page']}页")
        if item.get("chapter"):
            source_parts.append(f"「{item['chapter']}」")
        source_str = "，".join(source_parts)

        # 组合来源 + 内容
        parts.append(
            f"[{i}] ({source_str})\n{item['content']}"
        )

    return "\n\n".join(parts)


# ================================================================
# 生成 Prompt（便捷方法，供 Chain 使用）
# ================================================================

def build_prompt_messages(context: str, question: str) -> List[Dict[str, str]]:
    """
    构建发送给 LLM 的完整消息列表。

    这是一个不依赖 LangChain PromptTemplate 的备选方案——
    方便你在面试中解释"如果不使用 LangChain 我会怎么组织 Prompt"。

    Args:
        context: 格式化后的参考资料来源文本
        question: 用户问题

    Returns:
        消息列表（可直接传给 OpenAI API 的 messages 参数）
    """
    return [
        {"role": "system", "content": SYSTEM_TEMPLATE},
        {"role": "user", "content": HUMAN_TEMPLATE.format(
            context=context,
            question=question,
        )},
    ]

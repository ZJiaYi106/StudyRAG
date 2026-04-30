"""
RAG Chain 服务
使用 LangChain LCEL（LangChain Expression Language）构建完整问答链

LangChain 组件 #7：Runnable / LCEL（LangChain Expression Language）
- 作用：用管道符 | 将多个组件串联成一个可执行的 Chain
- 核心理念：每个组件都是 Runnable，输入输出统一 → 可以像搭积木一样组合
- 管道操作：data | step1 | step2 | step3，数据从左到右流经每个步骤

Chain 结构（本项目的 RAG 问答链）：

  用户问题 "什么是 Transformer？"
      │
      ▼
  ┌─────────────────────────────────────┐
  │  {                                  │
  │    "context":  RunnableLambda(...),  │  ← 检索 + 格式化
  │    "question": RunnablePassthrough() │  ← 原样传递问题
  │  }                                  │
  └──────────────┬──────────────────────┘
                 │ {"context": "...", "question": "..."}
                 ▼
  ┌─────────────────────────────────────┐
  │  ChatPromptTemplate                 │  ← 填入 System + Human 模板
  └──────────────┬──────────────────────┘
                 │ ChatPromptValue (messages)
                 ▼
  ┌─────────────────────────────────────┐
  │  ChatOpenAI (LLM)                   │  ← 生成回答
  └──────────────┬──────────────────────┘
                 │ AIMessage
                 ▼
  ┌─────────────────────────────────────┐
  │  StrOutputParser()                  │  ← 提取纯文本
  └──────────────┬──────────────────────┘
                 │ "Transformer 是一种基于自注意力机制的..."
                 ▼
           最终回答（纯文本）
"""

import logging
from typing import Dict, Any

# LangChain: RunnablePassthrough —— 原样传递输入，不做任何转换
# LangChain: RunnableLambda —— 将普通函数包装为 Runnable
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# LangChain: StrOutputParser —— 从 AIMessage 中提取纯文本字符串
from langchain_core.output_parsers import StrOutputParser

# LangChain: ChatOpenAI —— OpenAI API 兼容的大语言模型
from langchain_openai import ChatOpenAI

from app.config import settings
from app.services.retriever import retrieve
from app.services.prompt import build_prompt_template, format_context

logger = logging.getLogger(__name__)


# ================================================================
# 检索函数（包装为 RunnableLambda）
# ================================================================

def _retrieve_and_format(question: str) -> str:
    """
    检索并格式化参考资料来源文本。
    这个函数会被包装为 RunnableLambda，嵌入到 LCEL Chain 中。

    --- LangChain 教学 ---
    输入: str（用户问题）
    输出: str（格式化的参考资料来源文本 → 注入 {context} 变量）
    """
    retrieved = retrieve(question)
    if not retrieved:
        logger.info("[Chain] 未检索到相关参考资料")
    return format_context(retrieved)


# ================================================================
# 构建 RAG Chain
# ================================================================

def build_rag_chain():
    """
    使用 LCEL 构建完整的 RAG 问答链。

    --- LangChain 教学：详解每一步 ---

    Step 1: 并行准备变量
    {
        "context": RunnableLambda(_retrieve_and_format),  ← 检索资料
        "question": RunnablePassthrough(),                ← 问题原样传递
    }
    输入: "什么是 Transformer？"
    输出: {"context": "[1] (来源: ...) ...", "question": "什么是 Transformer？"}

    Step 2: PromptTemplate
    输入: {"context": str, "question": str}
    输出: ChatPromptValue（SystemMessage + HumanMessage）

    Step 3: ChatOpenAI (LLM)
    输入: ChatPromptValue
    输出: AIMessage(content="Transformer 是...")

    Step 4: StrOutputParser
    输入: AIMessage
    输出: "Transformer 是..."（纯文本字符串）

    Returns:
        一个可调用的 LCEL Chain，.invoke("问题") → "回答"
    """
    # 初始化 LLM
    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.llm_api_key,
        openai_api_base=settings.llm_api_base,
        temperature=0.1,  # 低温度减少幻觉，让回答更忠实于参考资料
    )

    # 获取 Prompt 模板
    prompt = build_prompt_template()

    # --- LCEL: 用管道符 | 串联所有步骤 ---
    # 这是 LangChain 最核心的语法，每个 | 将前一步的输出传给下一步的输入
    rag_chain = (
        {
            "context": RunnableLambda(_retrieve_and_format),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    logger.info("[Chain] RAG Chain 构建完成")
    return rag_chain


# ================================================================
# 便捷问答函数
# ================================================================

def ask(question: str) -> Dict[str, Any]:
    """
    执行 RAG 问答：检索 → 生成 → 返回答案 + 来源。

    这是一个高层封装，供 API 路由直接调用。
    它将 Chain 的执行和来源追踪分开处理：
    1. 先执行检索（拿到格式化前的 sources，用于返回给前端）
    2. 再执行 Chain（拿到 LLM 回答）

    --- LangChain 教学 ---
    输入: str（用户问题）
    输出: dict {"answer": str, "sources": List[dict]}

    Args:
        question: 用户问题

    Returns:
        {"answer": LLM 生成的回答, "sources": 引用来源列表}
    """
    # Step 1: 检索（拿到原始结果，用于前端展示来源卡片）
    retrieved = retrieve(question)

    # Step 2: 格式化参考资料来源
    context = format_context(retrieved)

    # Step 3: 构建并执行 Chain
    chain = build_rag_chain()
    answer = chain.invoke(question)

    # Step 4: 组装响应
    return {
        "answer": answer,
        "sources": retrieved,  # 原始检索结果（含 excerpt, filename, page 等）
    }

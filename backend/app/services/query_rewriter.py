"""
查询改写器
使用 LLM 对用户原始查询进行多角度改写，提升检索召回率。

改写策略：
1. 基础改写：扩展缩写、补充上下文、规范表述
2. HyDE（Hypothetical Document Embeddings）：生成假设性回答，用回答去检索
   原理：回答文本与文档的语义空间更接近，检索效果更好
3. 多角度：从不同视角生成多个查询，覆盖更广

示例：
  用户问："Transformer 是啥？"
  → 改写1："Transformer 架构的定义和基本原理"
  → 改写2："深度学习中的 Transformer 模型，包括自注意力机制和位置编码"
  → HyDE："Transformer 是一种基于自注意力机制的神经网络架构..."
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings

logger = logging.getLogger(__name__)

# HyDE 改写 Prompt
HYDE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个知识库检索助手。用户会提出一个问题，请你写一段假设性的回答。
这段回答不需要完全正确，目的是用它去知识库中检索真正相关的文档。

要求：
- 用学术化、正式的语言
- 包含该领域的关键术语
- 2-4 句话即可
- 不要用"根据资料"、"参考资料显示"等措辞，直接陈述内容"""),
    ("human", "{question}"),
])

# 查询改写 Prompt
REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是一个查询改写助手。将用户的口语化问题改写为更适合检索的表述。

改写规则：
1. 展开缩写和简称（如"BERT"→"Bidirectional Encoder Representations from Transformers"）
2. 补充领域上下文
3. 保持原意不变
4. 用陈述句而非疑问句
5. 输出改写后的问题，每行一个，最多3个"""),
    ("human", "{question}"),
])


class QueryRewriter:
    """
    查询改写器——LLM 改写 + HyDE 并行执行。
    """

    def __init__(self):
        self._llm = None
        self._executor = ThreadPoolExecutor(max_workers=2)

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=settings.llm_model,
                openai_api_key=settings.llm_api_key.get_secret_value(),
                openai_api_base=settings.llm_api_base,
                temperature=0.3,
            )
        return self._llm

    def _do_rewrite(self, question: str) -> List[str]:
        """LLM 改写查询"""
        try:
            chain = REWRITE_PROMPT | self.llm | StrOutputParser()
            rewritten = chain.invoke({"question": question})
            results = []
            for line in rewritten.strip().split("\n"):
                line = line.strip()
                if line and line != question:
                    results.append(line)
            logger.info(f"[Rewriter] LLM 改写生成 {len(results)} 条")
            return results[:2]
        except Exception as e:
            logger.warning(f"[Rewriter] LLM 改写失败: {e}")
            return []

    def _do_hyde(self, question: str) -> str:
        """生成 HyDE 假设文档"""
        try:
            chain = HYDE_PROMPT | self.llm | StrOutputParser()
            hyde_answer = chain.invoke({"question": question})
            logger.info(f"[Rewriter] HyDE 生成: {hyde_answer[:80]}...")
            return hyde_answer.strip()
        except Exception as e:
            logger.warning(f"[Rewriter] HyDE 生成失败: {e}")
            return ""

    def rewrite(self, question: str, enable_hyde: bool = True) -> List[str]:
        """
        生成改写查询列表（LLM 改写 + HyDE 并行）。
        """
        queries = [question]

        if enable_hyde:
            # 并行：LLM 改写 + HyDE
            future_rewrite = self._executor.submit(self._do_rewrite, question)
            future_hyde = self._executor.submit(self._do_hyde, question)

            rewritten = future_rewrite.result()
            hyde_text = future_hyde.result()

            for q in rewritten:
                if q not in queries:
                    queries.append(q)
            if hyde_text and hyde_text not in queries:
                queries.append(hyde_text)
        else:
            queries.extend(self._do_rewrite(question))

        return queries[:3]  # 最多 3 条（原始+改写+HyDE）


# 全局单例
_rewriter: QueryRewriter | None = None


def get_query_rewriter() -> QueryRewriter:
    global _rewriter
    if _rewriter is None:
        _rewriter = QueryRewriter()
    return _rewriter

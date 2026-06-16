"""
问题路由器
根据问题类型将查询路由到不同的检索策略。

分类维度：
- fact: 事实查询 → 高 top_k，精确匹配优先
- concept: 概念解释 → 中等 top_k，语义优先
- compare: 对比分析 → 高 top_k，多路召回
- summary: 总结概括 → 低 top_k，长 chunk 优先
"""

import logging
from enum import Enum
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    FACT = "fact"           # 事实查询："Transformer 是哪年提出的？"
    CONCEPT = "concept"     # 概念解释："什么是注意力机制？"
    COMPARE = "compare"     # 对比分析："BERT 和 GPT 有什么区别？"
    SUMMARY = "summary"     # 总结概括："总结 Transformer 的主要贡献"

    @classmethod
    def default(cls) -> "QueryType":
        return cls.CONCEPT


# 路由配置：不同问题类型的检索参数
ROUTE_CONFIG = {
    QueryType.FACT: {
        "top_k": 6,
        "enable_sparse": True,   # 事实查询需要关键词精确匹配
        "enable_rerank": True,
        "description": "事实查询——启用关键词检索 + 重排，高召回",
    },
    QueryType.CONCEPT: {
        "top_k": 4,
        "enable_sparse": True,
        "enable_rerank": True,
        "description": "概念解释——标准检索链路",
    },
    QueryType.COMPARE: {
        "top_k": 8,
        "enable_sparse": True,
        "enable_rerank": True,
        "description": "对比分析——高召回，多路融合",
    },
    QueryType.SUMMARY: {
        "top_k": 3,
        "enable_sparse": False,  # 总结不需要关键词匹配
        "enable_rerank": True,
        "description": "总结概括——低召回，语义优先",
    },
}

ROUTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "将问题分类，只输出一个词：fact(事实查询) concept(概念解释) compare(对比分析) summary(总结概括)"),
    ("human", "{question}"),
])


class QueryRouter:
    """
    问题路由器——用 LLM 分类问题类型，返回对应的检索配置。
    """

    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=settings.llm_model,
                openai_api_key=settings.llm_api_key.get_secret_value(),
                openai_api_base=settings.llm_api_base,
                temperature=0,
                max_tokens=10,
            )
        return self._llm

    def classify(self, question: str) -> QueryType:
        """分类问题类型"""
        try:
            chain = ROUTER_PROMPT | self.llm | StrOutputParser()
            result = chain.invoke({"question": question}).strip().lower()
            for qt in QueryType:
                if qt.value in result:
                    logger.info(f"[Router] 问题分类: {question[:30]}... → {qt.value}")
                    return qt
        except Exception as e:
            logger.warning(f"[Router] 分类失败，使用默认类型: {e}")

        return QueryType.default()

    def get_config(self, question: str) -> dict:
        """
        根据问题类型返回检索配置。

        Returns:
            {"top_k": 4, "enable_sparse": True, "enable_rerank": True, ...}
        """
        qtype = self.classify(question)
        config = ROUTE_CONFIG.get(qtype, ROUTE_CONFIG[QueryType.default()]).copy()
        config["query_type"] = qtype.value
        return config


# 全局单例
_router: QueryRouter | None = None


def get_router() -> QueryRouter:
    global _router
    if _router is None:
        _router = QueryRouter()
    return _router

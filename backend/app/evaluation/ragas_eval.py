"""
RAGAS 评测框架
量化评估 RAG 系统的检索和生成质量。

指标说明：
- Faithfulness（忠实度）：回答是否有事实依据，是否可以从检索的上下文中推导出来
- Context Recall（上下文召回率）：检索到的上下文是否包含了参考答案中的关键信息
- Context Precision（上下文精确度）：检索结果中相关文档的排名是否靠前
- Answer Relevancy（回答相关性）：回答是否与问题相关

使用方式：
  evaluator = RAGASEvaluator()
  result = evaluator.evaluate(question, answer, contexts, ground_truth)
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """
    RAGAS 评测器封装。
    需要 ragas 库（pip install ragas）。
    """

    def __init__(self):
        self._available = self._check_ragas()

    def _check_ragas(self) -> bool:
        try:
            import ragas
            return True
        except ImportError:
            logger.warning("[RAGAS] ragas 库未安装，评测功能不可用。pip install ragas")
            return False

    def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: str = "",
    ) -> Dict[str, Any]:
        """
        对单条问答进行评测。

        Args:
            question: 用户问题
            answer: LLM 生成的回答
            contexts: 检索到的上下文文本列表
            ground_truth: 参考答案（可选，用于 Context Recall）

        Returns:
            {"faithfulness": float, "context_recall": float, ...}
        """
        if not self._available:
            return {"error": "ragas 未安装"}

        try:
            from ragas.metrics import faithfulness, context_recall, context_precision, answer_relevancy
            from ragas.llms import LangchainLLMWrapper
            from langchain_openai import ChatOpenAI

            # 使用项目的 LLM 配置
            from app.config import settings
            eval_llm = LangchainLLMWrapper(ChatOpenAI(
                model=settings.llm_model,
                openai_api_key=settings.llm_api_key.get_secret_value(),
                openai_api_base=settings.llm_api_base,
                temperature=0,
            ))

            # 构建评测数据集
            from datasets import Dataset
            dataset = Dataset.from_dict({
                "question": [question],
                "answer": [answer],
                "contexts": [contexts],
                "ground_truth": [ground_truth] if ground_truth else [""],
            })

            result = {}
            # 逐项评测
            try:
                score = faithfulness.Faithfulness(llm=eval_llm).score(dataset)
                result["faithfulness"] = round(float(score), 4)
            except Exception as e:
                result["faithfulness"] = f"error: {e}"

            try:
                score = context_precision.ContextPrecision(llm=eval_llm).score(dataset)
                result["context_precision"] = round(float(score), 4)
            except Exception as e:
                result["context_precision"] = f"error: {e}"

            if ground_truth:
                try:
                    score = context_recall.ContextRecall(llm=eval_llm).score(dataset)
                    result["context_recall"] = round(float(score), 4)
                except Exception as e:
                    result["context_recall"] = f"error: {e}"

            try:
                score = answer_relevancy.AnswerRelevancy(llm=eval_llm).score(dataset)
                result["answer_relevancy"] = round(float(score), 4)
            except Exception as e:
                result["answer_relevancy"] = f"error: {e}"

            return result
        except Exception as e:
            logger.error(f"[RAGAS] 评测失败: {e}")
            return {"error": str(e)}

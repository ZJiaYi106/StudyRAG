"""
评测 API——基于 RAGAS 的量化评估
"""

import json
import logging
import os
from fastapi import APIRouter, Depends
from app.evaluation.ragas_eval import RAGASEvaluator
from app.services.chain import ask
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/eval", tags=["评测"])


def _load_dataset() -> list[dict]:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "eval_dataset.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/run")
async def run_evaluation(user: str = Depends(get_current_user)):
    """
    对 eval_dataset.json 中的所有 QA 逐条评测，
    返回各项指标的平均值。
    """
    dataset = _load_dataset()
    if not dataset:
        return {"error": "评测数据集为空，请在 data/eval_dataset.json 中添加 QA 对"}

    evaluator = RAGASEvaluator()
    results = []

    for item in dataset:
        question = item["question"]
        ground_truth = item.get("ground_truth", "")

        # 执行 RAG 问答（限定当前用户知识库）
        rag_result = ask(question, owner=user)
        answer = rag_result["answer"]
        contexts = [s["content"] for s in rag_result["sources"]]

        # RAGAS 单样本评测
        scores = evaluator.evaluate_single(question, answer, contexts, ground_truth)
        results.append({
            "question": question[:50],
            "answer_length": len(answer),
            "contexts_count": len(contexts),
            "scores": scores,
        })

        logger.info(f"[Eval] {question[:30]}... → {scores}")

    # 计算平均值（跳过 error 项）
    agg: dict = {}
    for r in results:
        for k, v in r["scores"].items():
            if isinstance(v, (int, float)):
                agg[k] = agg.get(k, []) + [v]

    averages = {k: round(sum(v) / len(v), 4) for k, v in agg.items() if v}

    return {
        "total_questions": len(results),
        "averages": averages,
        "details": results,
    }

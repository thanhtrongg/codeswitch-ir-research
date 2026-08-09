from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def _relevance(doc_id: str, qrels: Mapping[str, float]) -> float:
    return float(qrels.get(doc_id, 0.0))


def ndcg_at_k(ranking: Sequence[str], qrels: Mapping[str, float], k: int = 10) -> float:
    actual = 0.0
    for index, doc_id in enumerate(ranking[:k], start=1):
        rel = _relevance(doc_id, qrels)
        actual += (2.0**rel - 1.0) / math.log2(index + 1.0)
    ideal = sorted((float(value) for value in qrels.values()), reverse=True)[:k]
    maximum = sum((2.0**rel - 1.0) / math.log2(index + 2.0) for index, rel in enumerate(ideal))
    return actual / maximum if maximum else 0.0


def recall_at_k(ranking: Sequence[str], qrels: Mapping[str, float], k: int = 10) -> float:
    relevant = {doc_id for doc_id, rel in qrels.items() if float(rel) > 0}
    if not relevant:
        return 0.0
    return len(set(ranking[:k]) & relevant) / len(relevant)


def mrr(ranking: Sequence[str], qrels: Mapping[str, float]) -> float:
    for index, doc_id in enumerate(ranking, start=1):
        if _relevance(doc_id, qrels) > 0:
            return 1.0 / index
    return 0.0


def evaluate_ranking(ranking: Sequence[str], qrels: Mapping[str, float], official_metric: str) -> dict[str, float]:
    metrics = {
        "ndcg@10": ndcg_at_k(ranking, qrels, 10),
        "recall@10": recall_at_k(ranking, qrels, 10),
        "mrr": mrr(ranking, qrels),
    }
    if official_metric == "pairwise_mrr":
        metrics["official"] = metrics["mrr"]
    else:
        metrics["official"] = metrics["ndcg@10"]
    return metrics


def degradation(original: float, code_switched: float) -> dict[str, float | None]:
    delta = code_switched - original
    relative = None if original == 0 else delta / abs(original)
    return {"delta_cs": delta, "relative_delta_cs": relative}

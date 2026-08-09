"""Run pinned dense candidates on a tiny local fixture.

This is a compatibility smoke test only. Its output is never used for model
selection; the full development run must still be performed on GPU/adequate
CPU time using ``csr-run``.
"""

from __future__ import annotations

import gc
import json
import time
from pathlib import Path

from csr_ir.catalog import load_catalog
from csr_ir.metrics import evaluate_ranking
from csr_ir.retrieval import DenseRetriever


def main() -> int:
    catalog = load_catalog("configs/benchmarks.yaml")
    corpus = {
        "d1": {"title": "Climate science", "text": "Evidence about carbon dioxide and global temperature."},
        "d2": {"title": "Programming", "text": "A function sorts an array of integers."},
        "d3": {"title": "Public health", "text": "Studies discuss respiratory virus transmission."},
    }
    cases = [
        ("q1", "What is evidence for climate change?", "什么 evidence supports climate change?", {"d1": 1.0}),
        ("q2", "How do I sort an array?", "如何 sort an array?", {"d2": 1.0}),
    ]
    output = []
    for model in catalog["models"]:
        runner = DenseRetriever(
            model["model_id"],
            model["revision"],
            model["name"],
            batch_size=2,
            device="cuda",
            require_cuda=True,
            dtype="float16",
        )
        started = time.perf_counter()
        runner.index(corpus)
        for query_id, original, switched, qrels in cases:
            for setting, query in (("original", original), ("code_switched", switched)):
                result = runner.retrieve(query, top_k=3)
                output.append({
                    "model": model["name"],
                    "model_id": model["model_id"],
                    "revision": model["revision"],
                    "query_id": query_id,
                    "setting": setting,
                    "ranking": result.ranking,
                    "scores": result.scores,
                    "metrics": evaluate_ranking(result.ranking, qrels, "ndcg_at_10"),
                    "runtime_ms": result.runtime_ms,
                })
        output.append({
            "model": model["name"],
            "scope": "smoke_fixture_not_selection",
            "device": runner.device,
            "inference_dtype": runner.inference_dtype,
            "runtime_seconds": time.perf_counter() - started,
        })
        del runner
        gc.collect()
    path = Path("results/runs/dense_smoke.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in output:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"models": [model["name"] for model in catalog["models"]], "output": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

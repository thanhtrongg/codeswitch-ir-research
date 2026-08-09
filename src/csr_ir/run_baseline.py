from __future__ import annotations

import argparse
import csv
import json
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import psutil
import yaml

from .catalog import load_resources, resources_by_id
from .data import load_pairs, load_corpus_and_qrels
from .metrics import degradation, evaluate_ranking
from .retrieval import BM25Retriever, DenseRetriever
from .schema import QueryRun, RankedDocument


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _model_from_config(model_name: str, config_path: str, batch_size: int, device: str, dtype: str, cache_root: str | None) -> DenseRetriever:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    for model in config["models"]:
        if model["name"] == model_name or model["model_id"] == model_name:
            return DenseRetriever(
                model["model_id"],
                model["revision"],
                model["name"],
                batch_size=batch_size,
                device=device,
                require_cuda=device.startswith("cuda"),
                dtype=dtype,
                cache_root=cache_root,
            )
    raise KeyError(f"model {model_name!r} not found in {config_path}")


def run_resource(resource_id: str, language: str, retriever: Any, output_dir: Path, config_path: str, top_k: int = 1000, max_queries: int | None = None) -> dict[str, Any]:
    experiment_started = time.perf_counter()
    experiment_started_unix = time.time()
    resource = resources_by_id(config_path)[resource_id]
    pairs = load_pairs(resource, language)
    index_started = time.perf_counter()
    if hasattr(retriever, "index"):
        corpus, _ = load_corpus_and_qrels(resource)
        if isinstance(retriever, DenseRetriever):
            retriever.index(corpus, resource_id=resource_id, resource_revision=resource.revision)
        else:
            retriever.index(corpus)
    index_seconds = time.perf_counter() - index_started
    per_query_count = 0
    metric_sums: dict[str, dict[str, float]] = {"original": {}, "code_switched": {}}
    query_started = time.perf_counter()
    run_dir = output_dir / resource.short_name / language / retriever.name
    run_dir.mkdir(parents=True, exist_ok=True)
    per_query_path = run_dir / "per_query.jsonl"
    per_query_handle = per_query_path.open("w", encoding="utf-8")
    try:
      for pair_index, pair in enumerate(pairs):
        if max_queries is not None and pair_index >= max_queries:
            break
        for setting, query in (("original", pair.original_query), ("code_switched", pair.code_switched_query)):
            result = retriever.retrieve(query, top_k=top_k)
            metrics = evaluate_ranking(result.ranking, pair.qrels, resource.official_metric)
            ranked = [
                RankedDocument(doc_id, index, result.scores[doc_id], pair.qrels.get(doc_id, 0.0))
                for index, doc_id in enumerate(result.ranking, start=1)
            ]
            run = QueryRun(
                dataset=resource.short_name,
                benchmark_family=resource.benchmark_family,
                source_query_id=pair.source_query_id,
                rewritten_query_id=pair.rewritten_query_id,
                language_pair=pair.language_pair,
                setting=setting,
                query=query,
                relevant_document_ids=sorted(pair.qrels),
                ranked_documents=ranked,
                metrics=metrics,
                runtime_ms=result.runtime_ms,
            )
            per_query_handle.write(json.dumps(run.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n")
            per_query_count += 1
            for metric, value in metrics.items():
                metric_sums[setting][metric] = metric_sums[setting].get(metric, 0.0) + float(value)
    finally:
        per_query_handle.close()
    pair_count = per_query_count // 2
    summary_rows = []
    for setting in ("original", "code_switched"):
        for metric in ("official", "ndcg@10", "recall@10", "mrr"):
            summary_rows.append({
                "dataset": resource.short_name,
                "benchmark_family": resource.benchmark_family,
                "language_pair": f"{language}-en",
                "retriever": retriever.name,
                "setting": setting,
                "metric": metric,
                "score": metric_sums[setting].get(metric, 0.0) / max(pair_count, 1),
                "query_count": pair_count,
            })
    original = {row["metric"]: row["score"] for row in summary_rows if row["setting"] == "original"}
    switched = {row["metric"]: row["score"] for row in summary_rows if row["setting"] == "code_switched"}
    for metric in ("official", "ndcg@10", "recall@10", "mrr"):
        summary_rows.append({
            "dataset": resource.short_name,
            "benchmark_family": resource.benchmark_family,
            "language_pair": f"{language}-en",
            "retriever": retriever.name,
            "setting": "degradation",
            "metric": metric,
            "score": switched[metric] - original[metric],
            "relative_score": degradation(original[metric], switched[metric])["relative_delta_cs"],
            "query_count": pair_count,
        })
    _write_jsonl(run_dir / "summary.jsonl", summary_rows)
    run_config = {
        "resource_id": resource_id,
        "resource_revision": resource.revision,
        "language": language,
        "retriever": retriever.name,
        "device": getattr(retriever, "device", "cpu"),
        "inference_dtype": getattr(retriever, "inference_dtype", None),
        "requested_dtype": getattr(retriever, "dtype", None),
        "batch_size": getattr(retriever, "batch_size", None),
        "corpus_size": len(getattr(retriever, "_document_ids", getattr(retriever, "document_ids", []))),
        "query_pairs": pair_count,
        "query_rows": per_query_count,
        "retrieval_depth": top_k,
        "embeddings_cached": getattr(retriever, "embeddings_cached", False),
        "embeddings_persisted": False,
        "started_unix": experiment_started_unix,
        "runtime_seconds": time.perf_counter() - experiment_started,
        "index_seconds": index_seconds,
        "query_retrieval_evaluation_seconds": time.perf_counter() - query_started,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu": platform.processor(),
        "memory_available_bytes": psutil.virtual_memory().available,
    }
    if isinstance(retriever, DenseRetriever):
        run_config.update(retriever.metadata())
        run_config["embeddings_persisted"] = retriever.cache_path is not None
    torch = getattr(retriever, "_torch", None)
    if torch is not None and getattr(retriever, "device", "").startswith("cuda"):
        run_config["cuda_device"] = torch.cuda.get_device_name(0)
        run_config["cuda_peak_memory_allocated_bytes"] = torch.cuda.max_memory_allocated()
        run_config["cuda_peak_memory_reserved_bytes"] = torch.cuda.max_memory_reserved()
    _write_json(run_dir / "run_config.json", run_config)
    return {"resource": resource.short_name, "retriever": retriever.name, "rows": per_query_count, "output": str(run_dir)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run BM25 or a pinned dense retriever.")
    parser.add_argument("--resource", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--retriever", required=True, help="BM25 or a pinned model name from configs/benchmarks.yaml")
    parser.add_argument("--config", default="configs/benchmarks.yaml")
    parser.add_argument("--output-dir", default="results/runs")
    parser.add_argument("--top-k", type=int, default=1000)
    parser.add_argument("--max-queries", type=int, default=None, help="optional smoke-test limit; omit for the complete split")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="cuda", help="dense device; CUDA is required by default")
    parser.add_argument("--dtype", choices=("float16", "float32"), default="float16", help="standard dense inference dtype")
    parser.add_argument("--cache-root", default=None, help="persistent corpus embedding cache root")
    args = parser.parse_args(argv)
    if args.retriever.lower() == "bm25":
        resource = resources_by_id(args.config)[args.resource]
        corpus, _ = load_corpus_and_qrels(resource)
        retriever = BM25Retriever(corpus)
    else:
        retriever = _model_from_config(args.retriever, args.config, args.batch_size, args.device, args.dtype, args.cache_root)
    result = run_resource(args.resource, args.language, retriever, Path(args.output_dir), args.config, top_k=args.top_k, max_queries=args.max_queries)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

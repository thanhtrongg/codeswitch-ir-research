from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping


def validate_run(
    path: str | Path,
    *,
    expected_pairs: Mapping[str, Mapping[str, float]] | None = None,
    corpus_ids: set[str] | None = None,
    expected_depth: int | None = None,
) -> dict[str, Any]:
    run_path = Path(path)
    config_path = run_path.parent / "run_config.json"
    if not config_path.exists():
        raise AssertionError(f"missing run_config.json beside {run_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    required_config = ("resource_id", "resource_revision", "language", "retriever", "query_pairs", "query_rows", "retrieval_depth")
    missing_config = [key for key in required_config if key not in config]
    if missing_config:
        raise AssertionError(f"run config missing required fields: {missing_config}")
    if config.get("retriever") != "BM25":
        dense_config = (
            "model_id", "model_revision", "device", "inference_dtype", "requested_dtype",
            "batch_size", "max_length", "truncation", "padding", "pooling", "normalization",
            "embedding_dimension", "cache_hit", "cache_lookup_reason", "cache_path",
        )
        missing_dense = [key for key in dense_config if key not in config]
        if missing_dense:
            raise AssertionError(f"dense run config missing required fields: {missing_dense}")
    expected_depth = expected_depth if expected_depth is not None else int(config["retrieval_depth"])
    seen_groups: dict[str, set[str]] = defaultdict(set)
    seen_rows: set[tuple[str, str]] = set()
    counts: dict[str, int] = defaultdict(int)
    with run_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            setting = row.get("setting")
            if setting not in {"original", "code_switched"}:
                raise AssertionError(f"line {line_number}: invalid setting")
            group = row.get("source_query_id")
            if not group:
                raise AssertionError(f"line {line_number}: missing source_query_id")
            row_key = (group, setting)
            if row_key in seen_rows:
                raise AssertionError(f"line {line_number}: duplicated source-query/setting row {row_key}")
            seen_rows.add(row_key)
            seen_groups[group].add(setting)
            if expected_pairs is not None and group not in expected_pairs:
                raise AssertionError(f"line {line_number}: unexpected source-query group {group}")
            expected_qrels = expected_pairs.get(group) if expected_pairs is not None else None
            qrel_ids = set(row.get("relevant_document_ids", []))
            if expected_qrels is not None and qrel_ids != set(expected_qrels):
                raise AssertionError(f"line {line_number}: qrel document IDs do not match source query {group}")
            ranking = row.get("ranked_documents", [])
            if len(ranking) != expected_depth:
                raise AssertionError(f"line {line_number}: ranking length {len(ranking)} != expected {expected_depth}")
            ranks = [int(item["rank"]) for item in ranking]
            if ranks != list(range(1, len(ranks) + 1)):
                raise AssertionError(f"line {line_number}: invalid ranking ranks")
            document_ids = [item["document_id"] for item in ranking]
            if len(set(document_ids)) != len(document_ids):
                raise AssertionError(f"line {line_number}: duplicate ranked document")
            if corpus_ids is not None and not set(document_ids).issubset(corpus_ids):
                invalid = sorted(set(document_ids) - corpus_ids)[:5]
                raise AssertionError(f"line {line_number}: ranked document IDs not in corpus: {invalid}")
            for item in ranking:
                score = float(item["score"])
                relevance = float(item["relevance"])
                if not math.isfinite(score) or not math.isfinite(relevance):
                    raise AssertionError(f"line {line_number}: non-finite score/relevance")
                expected_relevance = float((expected_qrels or {}).get(item["document_id"], 0.0))
                if not math.isclose(relevance, expected_relevance, rel_tol=0.0, abs_tol=1e-8):
                    raise AssertionError(f"line {line_number}: ranking/qrel relevance mismatch")
            for metric, value in row.get("metrics", {}).items():
                if not math.isfinite(float(value)):
                    raise AssertionError(f"line {line_number}: non-finite metric {metric}")
            counts[setting] += 1
    incomplete = [group for group, settings in seen_groups.items() if settings != {"original", "code_switched"}]
    if incomplete:
        raise AssertionError(f"source-query pairs missing one setting: {incomplete[:10]}")
    if expected_pairs is not None and set(seen_groups) != set(expected_pairs):
        missing = sorted(set(expected_pairs) - set(seen_groups))[:10]
        raise AssertionError(f"missing expected source-query groups: {missing}")
    expected_rows = 2 * len(expected_pairs) if expected_pairs is not None else None
    if expected_rows is not None and sum(counts.values()) != expected_rows:
        raise AssertionError(f"row count {sum(counts.values())} != expected {expected_rows}")
    if int(config["query_rows"]) != sum(counts.values()) or int(config["query_pairs"]) != len(seen_groups):
        raise AssertionError("run configuration query counts do not match artifact")
    return {
        "rows": sum(counts.values()),
        "original": counts["original"],
        "code_switched": counts["code_switched"],
        "groups": len(seen_groups),
        "config": config,
    }

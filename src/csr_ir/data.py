from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

from .catalog import Resource
from .leakage import source_query_group
from .schema import QueryRecord


def _field(row: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return default


def _load_dataset_rows(
    dataset_id: str,
    config: str,
    split: str,
    revision: str | None,
    streaming: bool = False,
) -> Iterable[Mapping[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:  # pragma: no cover - exercised only in minimal envs
        raise RuntimeError("datasets is required for Hugging Face benchmark loading") from exc
    kwargs: dict[str, Any] = {"split": split, "streaming": streaming}
    if revision:
        kwargs["revision"] = revision
    try:
        return load_dataset(dataset_id, config, **kwargs)
    except ValueError as first_error:
        for alternate in ("test", "train", "queries", "corpus", "qrels", "qrel_diff", "instruction", "top_ranked"):
            if alternate == split:
                continue
            kwargs["split"] = alternate
            try:
                return load_dataset(dataset_id, config, **kwargs)
            except ValueError:
                continue
        raise first_error


def _rows(dataset_id: str, config: str, split: str, revision: str | None, streaming: bool) -> list[Mapping[str, Any]]:
    return list(_load_dataset_rows(dataset_id, config, split, revision, streaming))


def row_id(row: Mapping[str, Any]) -> str:
    value = _field(row, "_id", "id", "query-id", "query_id", "corpus-id", "corpus_id")
    if value is None:
        raise ValueError(f"row has no identifier: {row}")
    return str(value)


def row_text(row: Mapping[str, Any]) -> str:
    value = _field(row, "text", "query", "sentence", "instruction", default="")
    return str(value)


def normalize_qrels(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    qrels: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        query_id = str(_field(row, "query-id", "query_id", "query_id", "qid"))
        corpus_id = str(_field(row, "corpus-id", "corpus_id", "doc_id", "document_id"))
        score = float(_field(row, "score", "relevance", "label", default=0.0))
        qrels[query_id][corpus_id] = score
    return dict(qrels)


def normalize_corpus(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    corpus: dict[str, dict[str, str]] = {}
    for row in rows:
        doc_id = row_id(row)
        corpus[doc_id] = {
            "title": str(_field(row, "title", default="") or ""),
            "text": str(_field(row, "text", "contents", default="") or ""),
        }
    return corpus


def load_corpus_and_qrels(resource: Resource, streaming: bool = False) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, float]]]:
    corpus_rows = _load_dataset_rows(resource.dataset_id, resource.corpus_config, resource.corpus_split, resource.revision, streaming)
    qrel_rows = _load_dataset_rows(resource.dataset_id, resource.qrels_config, resource.qrels_split, resource.revision, streaming)
    return normalize_corpus(corpus_rows), normalize_qrels(qrel_rows)


def load_qrels(resource: Resource, streaming: bool = False) -> dict[str, dict[str, float]]:
    return normalize_qrels(_load_dataset_rows(resource.dataset_id, resource.qrels_config, resource.qrels_split, resource.revision, streaming))


def load_original_queries(resource: Resource, streaming: bool = False) -> dict[str, str]:
    rows = _load_dataset_rows(
        resource.original_query_source,
        resource.original_query_config,
        resource.original_query_split,
        None,
        streaming,
    )
    return {row_id(row): row_text(row) for row in rows}


def load_code_switched_queries(resource: Resource, language: str, streaming: bool = False) -> dict[str, str]:
    config = resource.cs_query_configs[language]
    rows = _load_dataset_rows(resource.dataset_id, config, "test", resource.revision, streaming)
    return {row_id(row): row_text(row) for row in rows}


def load_pairs(resource: Resource, language: str, streaming: bool = False) -> list[QueryRecord]:
    if language not in resource.cs_query_configs:
        raise KeyError(f"language {language!r} is not available for {resource.dataset_id}")
    qrels = load_qrels(resource, streaming=streaming)
    original = load_original_queries(resource, streaming=streaming)
    switched = load_code_switched_queries(resource, language, streaming=streaming)
    missing_qrels = (set(original) | set(switched)) - set(qrels)
    if missing_qrels:
        raise AssertionError(f"{resource.dataset_id}: missing qrels for {len(missing_qrels)} queries")
    if set(original) != set(switched):
        raise AssertionError(f"{resource.dataset_id}: original/code-switched query IDs differ")
    return [
        QueryRecord(
            source_query_id=source_query_group(resource.source_dataset, query_id),
            rewritten_query_id=query_id,
            language_pair=f"{language}-en",
            original_query=original[query_id],
            code_switched_query=switched[query_id],
            qrels=qrels[query_id],
        )
        for query_id in sorted(original)
    ]


def load_local_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]

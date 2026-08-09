from __future__ import annotations

import hashlib
import random
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


def source_query_group(source_dataset: str, query_id: str, explicit_source_id: str | None = None) -> str:
    """Return one stable group for an original query and all rewrites.

    Official CSR-L/CS-MTEB files retain the original query ID for rewritten
    variants. The optional explicit ID supports future datasets that publish a
    separate source-query field.
    """
    stable = (explicit_source_id or query_id).strip()
    # FollowIR publishes paired IDs such as ``310-og`` and ``310-changed``.
    # They are two views of one source query and must share one split group.
    stable = re.sub(r"(?:[-_](?:og|original|changed|rewritten))$", "", stable, flags=re.IGNORECASE)
    if not stable:
        raise ValueError("empty query ID cannot define a leakage group")
    return f"{source_dataset}::{stable}"


def qrel_signature(qrels: Mapping[str, float]) -> str:
    payload = "\n".join(f"{key}\t{float(value):.12g}" for key, value in sorted(qrels.items()))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def corpus_signature(corpus: Mapping[str, Mapping[str, Any]]) -> str:
    rows = []
    for doc_id, document in sorted(corpus.items()):
        rows.append(f"{doc_id}\t{document.get('title', '')}\t{document.get('text', '')}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def split_groups(groups: Iterable[str], test_fraction: float, seed: int) -> tuple[set[str], set[str]]:
    unique = sorted(set(groups))
    rng = random.Random(seed)
    rng.shuffle(unique)
    test_count = round(len(unique) * test_fraction)
    test = set(unique[:test_count])
    return set(unique[test_count:]), test


def assert_disjoint(left: Iterable[str], right: Iterable[str], message: str) -> None:
    overlap = set(left) & set(right)
    if overlap:
        sample = sorted(overlap)[:10]
        raise AssertionError(f"{message}: {len(overlap)} overlapping groups; sample={sample}")


def assert_query_qrel_alignment(query_ids: Iterable[str], qrels: Mapping[str, Mapping[str, float]]) -> None:
    missing = set(query_ids) - set(qrels)
    if missing:
        raise AssertionError(f"queries without qrels: {len(missing)}; sample={sorted(missing)[:10]}")


def assert_variant_qrels_identical(original: Mapping[str, float], code_switched: Mapping[str, float]) -> None:
    if dict(original) != dict(code_switched):
        raise AssertionError("original and code-switched variants do not share identical qrels")


@dataclass
class OverlapReport:
    dataset_level: list[dict[str, Any]]
    corpus_level: list[dict[str, Any]]
    query_id_level: list[dict[str, Any]]
    source_query_level: list[dict[str, Any]]
    qrels_level: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_level": self.dataset_level,
            "corpus_level": self.corpus_level,
            "query_id_level": self.query_id_level,
            "source_query_level": self.source_query_level,
            "qrels_level": self.qrels_level,
        }


def compare_manifests(manifests: Sequence[Mapping[str, Any]]) -> OverlapReport:
    """Compare audit manifests without treating rewrite variants as independent.

    A manifest contains ``dataset_id``, ``source_dataset``, ``corpus_ids``,
    ``query_ids``, and ``qrel_signatures``. The function is intentionally
    backend-agnostic so the same assertions work for local fixtures and HF data.
    """
    by_source: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for manifest in manifests:
        by_source[str(manifest["source_dataset"])].append(manifest)
    dataset_level = [
        {"source_dataset": source, "datasets": sorted(item["dataset_id"] for item in items)}
        for source, items in sorted(by_source.items())
        if len(items) > 1
    ]
    corpus_level: list[dict[str, Any]] = []
    query_id_level: list[dict[str, Any]] = []
    source_query_level: list[dict[str, Any]] = []
    qrels_level: list[dict[str, Any]] = []
    for index, left in enumerate(manifests):
        for right in manifests[index + 1 :]:
            if left["source_dataset"] != right["source_dataset"]:
                continue
            left_corpus = set(left.get("corpus_ids", []))
            right_corpus = set(right.get("corpus_ids", []))
            left_queries = set(left.get("query_ids", []))
            right_queries = set(right.get("query_ids", []))
            left_groups = set(left.get("source_query_groups", []))
            right_groups = set(right.get("source_query_groups", []))
            left_qrels = set(left.get("qrel_signatures", []))
            right_qrels = set(right.get("qrel_signatures", []))
            pair = {"left": left["dataset_id"], "right": right["dataset_id"]}
            if left_corpus & right_corpus:
                corpus_level.append({**pair, "overlap_count": len(left_corpus & right_corpus)})
            if left_queries & right_queries:
                query_id_level.append({**pair, "overlap_count": len(left_queries & right_queries)})
            if left_groups & right_groups:
                source_query_level.append({**pair, "overlap_count": len(left_groups & right_groups)})
            if left_qrels & right_qrels:
                qrels_level.append({**pair, "overlap_count": len(left_qrels & right_qrels)})
    return OverlapReport(dataset_level, corpus_level, query_id_level, source_query_level, qrels_level)

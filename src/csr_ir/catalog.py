from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Resource:
    dataset_id: str
    short_name: str
    benchmark_family: str
    source_dataset: str
    task_type: str
    official_metric: str
    rewrite_authoring: str
    languages: tuple[str, ...]
    revision: str
    role: str
    shared_qrels: bool
    corpus_config: str = "corpus"
    corpus_split: str = "test"
    qrels_config: str = "default"
    qrels_split: str = "test"
    original_query_source: str = ""
    original_query_config: str = "queries"
    original_query_split: str = "test"
    cs_query_configs: dict[str, str] = field(default_factory=dict)
    cs_instruction_configs: dict[str, str] = field(default_factory=dict)
    qrel_diff_config: str | None = None
    qrel_diff_split: str | None = None

    @property
    def is_retrieval(self) -> bool:
        return self.task_type in {"document_retrieval", "instruction_retrieval"}

    @property
    def is_development(self) -> bool:
        return self.role == "development"

    @property
    def is_final(self) -> bool:
        return self.role == "final_test"


def _resource(raw: dict[str, Any]) -> Resource:
    return Resource(
        dataset_id=raw["dataset_id"],
        short_name=raw["short_name"],
        benchmark_family=raw["benchmark_family"],
        source_dataset=raw["source_dataset"],
        task_type=raw["task_type"],
        official_metric=raw["official_metric"],
        rewrite_authoring=raw["rewrite_authoring"],
        languages=tuple(raw["languages"]),
        revision=raw["revision"],
        role=raw["role"],
        shared_qrels=bool(raw["shared_qrels"]),
        corpus_config=raw.get("corpus_config", "corpus"),
        corpus_split=raw.get("corpus_split", "test"),
        qrels_config=raw.get("qrels_config", "default"),
        qrels_split=raw.get("qrels_split", "test"),
        original_query_source=raw.get("original_query_source", raw["source_dataset"]),
        original_query_config=raw.get("original_query_config", "queries"),
        original_query_split=raw.get("original_query_split", "test"),
        cs_query_configs=raw.get("cs_query_configs", {}),
        cs_instruction_configs=raw.get("cs_instruction_configs", {}),
        qrel_diff_config=raw.get("qrel_diff_config"),
        qrel_diff_split=raw.get("qrel_diff_split"),
    )


def load_catalog(path: str | Path = "configs/benchmarks.yaml") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_resources(path: str | Path = "configs/benchmarks.yaml") -> list[Resource]:
    return [_resource(raw) for raw in load_catalog(path)["resources"]]


def resources_by_id(path: str | Path = "configs/benchmarks.yaml") -> dict[str, Resource]:
    return {resource.dataset_id: resource for resource in load_resources(path)}

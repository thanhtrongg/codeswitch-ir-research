from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class QueryRecord:
    source_query_id: str
    rewritten_query_id: str
    language_pair: str
    original_query: str
    code_switched_query: str
    qrels: dict[str, float]

    @property
    def source_query_group(self) -> str:
        return self.source_query_id

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RankedDocument:
    document_id: str
    rank: int
    score: float
    relevance: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QueryRun:
    dataset: str
    benchmark_family: str
    source_query_id: str
    rewritten_query_id: str
    language_pair: str
    setting: str
    query: str
    relevant_document_ids: list[str]
    ranked_documents: list[RankedDocument]
    metrics: dict[str, float]
    runtime_ms: float

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["ranked_documents"] = [item.to_dict() for item in self.ranked_documents]
        return value

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


CACHE_VERSION = "corpus_embeddings_v1"


def default_cache_root() -> Path:
    configured = os.environ.get("CSR_IR_CACHE_ROOT")
    if configured:
        return Path(configured)
    return Path(".cache/csr_ir")


def _json_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def corpus_fingerprints(corpus: Mapping[str, Mapping[str, str]]) -> tuple[str, str, list[str]]:
    ordered_ids = [str(doc_id) for doc_id in corpus]
    id_hash = hashlib.sha256()
    corpus_hash = hashlib.sha256()
    for doc_id, document in zip(ordered_ids, corpus.values()):
        id_hash.update(doc_id.encode("utf-8"))
        id_hash.update(b"\0")
        corpus_hash.update(doc_id.encode("utf-8"))
        corpus_hash.update(b"\0")
        for field in ("title", "text"):
            corpus_hash.update(str(document.get(field, "") or "").encode("utf-8"))
            corpus_hash.update(b"\0")
    return corpus_hash.hexdigest(), id_hash.hexdigest(), ordered_ids


@dataclass(frozen=True)
class CacheResult:
    embeddings: np.ndarray | None
    document_ids: list[str] | None
    hit: bool
    reason: str
    path: str
    key: str


class EmbeddingCache:
    """Validated, crash-safe corpus embedding cache.

    Each key is an immutable directory containing metadata, ordered document
    IDs, and a NumPy embedding matrix. A cache hit requires exact equality of
    the complete request metadata and the stored matrix/document ordering.
    """

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else default_cache_root()

    def request(
        self,
        *,
        resource_id: str,
        resource_revision: str,
        corpus_size: int,
        corpus_fingerprint: str,
        document_ids_fingerprint: str,
        model_id: str,
        model_revision: str,
        embedding_dimension: int,
        pooling: str,
        normalization: bool,
        document_prefix: str,
        max_length: int,
        truncation: bool,
        padding: bool,
        model_dtype: str,
        stored_dtype: str = "float32",
    ) -> dict[str, Any]:
        payload = {
            "cache_version": CACHE_VERSION,
            "resource_id": resource_id,
            "resource_revision": resource_revision,
            "corpus_size": int(corpus_size),
            "corpus_fingerprint": corpus_fingerprint,
            "document_ids_fingerprint": document_ids_fingerprint,
            "model_id": model_id,
            "model_revision": model_revision,
            "embedding_dimension": int(embedding_dimension),
            "pooling": pooling,
            "normalization": bool(normalization),
            "document_prefix": document_prefix,
            "max_length": int(max_length),
            "truncation": bool(truncation),
            "padding": bool(padding),
            "model_dtype": model_dtype,
            "stored_dtype": stored_dtype,
        }
        payload["cache_key"] = _json_hash(payload)
        return payload

    def _entry_dir(self, request: Mapping[str, Any]) -> Path:
        return self.root / str(request["cache_key"])

    def load(self, request: Mapping[str, Any], expected_document_ids: Sequence[str]) -> CacheResult:
        entry = self._entry_dir(request)
        if not entry.exists():
            return CacheResult(None, None, False, "miss", str(entry), str(request["cache_key"]))
        try:
            metadata = json.loads((entry / "metadata.json").read_text(encoding="utf-8"))
            if metadata != dict(request):
                return CacheResult(None, None, False, "metadata_mismatch", str(entry), str(request["cache_key"]))
            document_ids = json.loads((entry / "document_ids.json").read_text(encoding="utf-8"))
            if document_ids != list(expected_document_ids):
                return CacheResult(None, None, False, "document_order_mismatch", str(entry), str(request["cache_key"]))
            embeddings = np.load(entry / "embeddings.npy", allow_pickle=False)
            self._validate_matrix(embeddings, request, len(document_ids))
            return CacheResult(embeddings, document_ids, True, "hit", str(entry), str(request["cache_key"]))
        except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError) as exc:
            return CacheResult(None, None, False, f"invalid_cache:{type(exc).__name__}", str(entry), str(request["cache_key"]))

    @staticmethod
    def _validate_matrix(embeddings: np.ndarray, request: Mapping[str, Any], document_count: int) -> None:
        if embeddings.ndim != 2:
            raise ValueError("cached embeddings must be a 2D matrix")
        expected_shape = (document_count, int(request["embedding_dimension"]))
        if embeddings.shape != expected_shape:
            raise ValueError(f"cached embedding shape {embeddings.shape} != {expected_shape}")
        if str(embeddings.dtype) != str(request["stored_dtype"]):
            raise ValueError(f"cached embedding dtype {embeddings.dtype} != {request['stored_dtype']}")
        if not np.isfinite(embeddings).all():
            raise ValueError("cached embeddings contain non-finite values")

    def save(
        self,
        request: Mapping[str, Any],
        document_ids: Sequence[str],
        embeddings: np.ndarray,
    ) -> CacheResult:
        self._validate_matrix(embeddings, request, len(document_ids))
        self.root.mkdir(parents=True, exist_ok=True)
        entry = self._entry_dir(request)
        if entry.exists():
            existing = self.load(request, document_ids)
            if existing.hit:
                return existing
            raise RuntimeError(f"refusing to overwrite incompatible cache entry: {entry}")
        temporary = Path(tempfile.mkdtemp(prefix=f".{request['cache_key']}-", dir=str(self.root)))
        try:
            np.save(temporary / "embeddings.npy", embeddings, allow_pickle=False)
            (temporary / "document_ids.json").write_text(
                json.dumps(list(document_ids), ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )
            (temporary / "metadata.json").write_text(
                json.dumps(dict(request), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
            )
            staged_metadata = json.loads((temporary / "metadata.json").read_text(encoding="utf-8"))
            if staged_metadata != dict(request):
                raise RuntimeError("staged cache metadata validation failed")
            staged_embeddings = np.load(temporary / "embeddings.npy", allow_pickle=False)
            self._validate_matrix(staged_embeddings, request, len(document_ids))
            temporary.replace(entry)
        finally:
            if temporary.exists():
                for child in temporary.iterdir():
                    child.unlink()
                temporary.rmdir()
        return CacheResult(embeddings, list(document_ids), False, "saved", str(entry), str(request["cache_key"]))

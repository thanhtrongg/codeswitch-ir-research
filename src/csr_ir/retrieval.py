from __future__ import annotations

import math
import re
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from .cache import EmbeddingCache, corpus_fingerprints


TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


@dataclass
class RetrievalResult:
    ranking: list[str]
    scores: dict[str, float]
    runtime_ms: float


class BM25Retriever:
    name = "BM25"

    def __init__(self, corpus: Mapping[str, Mapping[str, str]], k1: float = 0.9, b: float = 0.4):
        self.document_ids = list(corpus)
        self.documents = [tokenize(f"{doc.get('title', '')} {doc.get('text', '')}") for doc in corpus.values()]
        self.k1 = k1
        self.b = b
        self._average_length = sum(map(len, self.documents)) / max(len(self.documents), 1)
        self._postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        document_frequency: dict[str, int] = defaultdict(int)
        for index, document in enumerate(self.documents):
            frequencies: dict[str, int] = defaultdict(int)
            for token in document:
                frequencies[token] += 1
            for token, frequency in frequencies.items():
                self._postings[token].append((index, frequency))
                document_frequency[token] += 1
        document_count = max(len(self.documents), 1)
        self._idf = {
            token: math.log(1.0 + (document_count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }
        self._term_to_column = {token: index for index, token in enumerate(self._idf)}
        self._matrix = None
        try:
            from scipy.sparse import csr_matrix

            rows, columns, values = [], [], []
            for token, postings in self._postings.items():
                column = self._term_to_column[token]
                idf = self._idf[token]
                for document_index, term_frequency in postings:
                    document_length = len(self.documents[document_index])
                    denominator = term_frequency + self.k1 * (1.0 - self.b + self.b * document_length / max(self._average_length, 1e-9))
                    rows.append(document_index)
                    columns.append(column)
                    values.append(idf * term_frequency * (self.k1 + 1.0) / denominator)
            self._matrix = csr_matrix((values, (rows, columns)), shape=(len(self.documents), len(self._term_to_column)), dtype=np.float32)
        except ImportError:  # pragma: no cover
            self._matrix = None

    def retrieve(self, query: str, top_k: int = 1000) -> RetrievalResult:
        start = time.perf_counter()
        query_terms = tokenize(query)
        term_counts: dict[int, int] = defaultdict(int)
        for token in query_terms:
            column = self._term_to_column.get(token)
            if column is not None:
                term_counts[column] += 1
        if self._matrix is not None and term_counts:
            columns = np.fromiter(term_counts.keys(), dtype=np.int64)
            qtf = np.fromiter(term_counts.values(), dtype=np.float32)
            values = np.asarray(self._matrix[:, columns].dot(qtf)).reshape(-1)
        else:
            values = np.zeros(len(self.document_ids), dtype=np.float64)
            for token in set(query_terms):
                idf = self._idf.get(token)
                if idf is None:
                    continue
                for index, term_frequency in self._postings[token]:
                    document_length = len(self.documents[index])
                    denominator = term_frequency + self.k1 * (1.0 - self.b + self.b * document_length / max(self._average_length, 1e-9))
                    values[index] += idf * term_frequency * (self.k1 + 1.0) / denominator
        order = np.argsort(-values, kind="stable")[:top_k]
        ranking = [self.document_ids[index] for index in order]
        scores = {doc_id: float(values[index]) for doc_id, index in zip(ranking, order)}
        return RetrievalResult(ranking, scores, (time.perf_counter() - start) * 1000.0)


class DenseRetriever:
    def __init__(
        self,
        model_id: str,
        revision: str,
        model_name: str,
        batch_size: int = 16,
        device: str | None = None,
        require_cuda: bool = False,
        dtype: str = "float32",
        cache_root: str | None = None,
    ):
        self.model_id = model_id
        self.revision = revision
        self.name = model_name
        self.batch_size = batch_size
        self.device = device
        self.require_cuda = require_cuda
        self.dtype = dtype
        self.cache = EmbeddingCache(cache_root)
        self.cache_root = str(self.cache.root)
        self.max_length = 512
        self.truncation = True
        self.padding = True
        self.pooling = "mean_masked_last_hidden_state"
        self.normalization = True
        self._model = None
        self._tokenizer = None
        self._torch = None
        self._document_ids: list[str] = []
        self._document_embeddings: np.ndarray | None = None
        self.inference_dtype: str | None = None
        self.embeddings_cached = False
        self._embedding_dimension: int | None = None
        self.cache_hit = False
        self.cache_lookup_reason = "not_indexed"
        self.cache_reason = "not_indexed"
        self.cache_path: str | None = None
        self.cache_key: str | None = None

    def _load(self) -> Any:
        if self._model is None:
            # Use the Transformers backend directly. This keeps the runner
            # usable when a local sentence-transformers/torchvision build is
            # incompatible, while retaining pinned model revisions.
            from transformers import AutoModel, AutoTokenizer
            import torch

            self._torch = torch
            if self.require_cuda and not torch.cuda.is_available():
                raise RuntimeError("CUDA is required for this dense run but torch.cuda.is_available() is False")
            device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
            if device.startswith("cuda") and not torch.cuda.is_available():
                raise RuntimeError(f"requested dense device {device!r}, but CUDA is unavailable")
            model_kwargs = {}
            if self.dtype == "float16":
                if not device.startswith("cuda"):
                    raise ValueError("float16 dense inference is only enabled for CUDA")
                model_kwargs["torch_dtype"] = torch.float16
            elif self.dtype != "float32":
                raise ValueError(f"unsupported dense inference dtype: {self.dtype}")
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
            self._model = AutoModel.from_pretrained(self.model_id, revision=self.revision, **model_kwargs)
            self._model.to(device)
            self._model.eval()
            self.device = device
            parameter_device = next(self._model.parameters()).device
            if parameter_device.type != torch.device(device).type:
                raise RuntimeError(f"dense model placement failed: {parameter_device} != {device}")
            if self.require_cuda and parameter_device.type != "cuda":
                raise RuntimeError(f"dense model is not on CUDA: {parameter_device}")
            self.inference_dtype = str(next(self._model.parameters()).dtype)
            self._embedding_dimension = int(
                getattr(self._model.config, "hidden_size", getattr(self._model.config, "projection_dim", 0))
            )
            if self._embedding_dimension <= 0:
                raise RuntimeError("could not determine dense embedding dimension from model config")
        return self._model

    def _encode(self, texts: Sequence[str], prompt_name: str | None = None) -> np.ndarray:
        model = self._load()
        torch = self._torch
        assert torch is not None and self._tokenizer is not None and self.device is not None
        prepared = list(texts)
        if self.model_id == "intfloat/multilingual-e5-large":
            prefix = "query: " if prompt_name == "query" else "passage: "
            prepared = [prefix + text for text in prepared]
        outputs = []
        for start in range(0, len(prepared), self.batch_size):
            batch = self._tokenizer(
                prepared[start : start + self.batch_size],
                padding=self.padding,
                truncation=self.truncation,
                max_length=self.max_length,
                return_tensors="pt",
            )
            batch = {key: value.to(self.device) for key, value in batch.items()}
            if self.require_cuda and any(value.device.type != "cuda" for value in batch.values()):
                raise RuntimeError("dense input tensors are not on CUDA")
            with torch.inference_mode():
                hidden = model(**batch).last_hidden_state
            if self.require_cuda and hidden.device.type != "cuda":
                raise RuntimeError("dense embedding computation did not execute on CUDA")
            mask = batch["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
            if self.normalization:
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            outputs.append(pooled.cpu().numpy())
        return np.concatenate(outputs, axis=0).astype(np.float32)

    def index(
        self,
        corpus: Mapping[str, Mapping[str, str]],
        *,
        resource_id: str = "unscoped",
        resource_revision: str = "unscoped",
    ) -> None:
        self._load()
        corpus_hash, document_ids_hash, document_ids = corpus_fingerprints(corpus)
        if self._embedding_dimension is None:
            raise RuntimeError("dense embedding dimension is unavailable before cache lookup")
        document_prefix = "passage: " if self.model_id == "intfloat/multilingual-e5-large" else ""
        request = self.cache.request(
            resource_id=resource_id,
            resource_revision=resource_revision,
            corpus_size=len(document_ids),
            corpus_fingerprint=corpus_hash,
            document_ids_fingerprint=document_ids_hash,
            model_id=self.model_id,
            model_revision=self.revision,
            embedding_dimension=self._embedding_dimension,
            pooling=self.pooling,
            normalization=self.normalization,
            document_prefix=document_prefix,
            max_length=self.max_length,
            truncation=self.truncation,
            padding=self.padding,
            model_dtype=self.inference_dtype or self.dtype,
        )
        cached = self.cache.load(request, document_ids)
        self.cache_hit = cached.hit
        self.cache_lookup_reason = cached.reason
        self.cache_reason = cached.reason
        self.cache_path = cached.path
        self.cache_key = cached.key
        self._document_ids = document_ids
        if cached.hit:
            assert cached.embeddings is not None
            self._document_embeddings = cached.embeddings
            self.embeddings_cached = True
            return
        texts = [f"{doc.get('title', '')} {doc.get('text', '')}" for doc in corpus.values()]
        self._document_embeddings = self._encode(texts, prompt_name="document")
        self.embeddings_cached = True
        saved = self.cache.save(request, self._document_ids, self._document_embeddings)
        self.cache_reason = saved.reason

    def metadata(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_revision": self.revision,
            "device": self.device,
            "inference_dtype": self.inference_dtype,
            "requested_dtype": self.dtype,
            "batch_size": self.batch_size,
            "max_length": self.max_length,
            "truncation": self.truncation,
            "padding": self.padding,
            "pooling": self.pooling,
            "normalization": self.normalization,
            "document_prefix": "passage: " if self.model_id == "intfloat/multilingual-e5-large" else "",
            "embedding_dimension": self._embedding_dimension,
            "cache_root": self.cache_root,
            "cache_key": self.cache_key,
            "cache_path": self.cache_path,
            "cache_hit": self.cache_hit,
            "cache_lookup_reason": self.cache_lookup_reason,
            "cache_reason": self.cache_reason,
        }

    def retrieve(self, query: str, top_k: int = 1000) -> RetrievalResult:
        if self._document_embeddings is None:
            raise RuntimeError("call index(corpus) before retrieve")
        start = time.perf_counter()
        query_embedding = self._encode([query], prompt_name="query")[0]
        values = self._document_embeddings @ query_embedding
        order = np.argsort(-values, kind="stable")[:top_k]
        ranking = [self._document_ids[index] for index in order]
        scores = {doc_id: float(values[index]) for doc_id, index in zip(ranking, order)}
        return RetrievalResult(ranking, scores, (time.perf_counter() - start) * 1000.0)

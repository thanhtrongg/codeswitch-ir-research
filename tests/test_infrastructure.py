from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from csr_ir.cache import EmbeddingCache, corpus_fingerprints
from csr_ir.catalog import load_resources
from csr_ir.leakage import (
    assert_disjoint,
    assert_query_qrel_alignment,
    assert_variant_qrels_identical,
    compare_manifests,
    source_query_group,
    split_groups,
)
from csr_ir.metrics import evaluate_ranking
from csr_ir.protocol import assert_protocol


class LeakageTests(unittest.TestCase):
    def test_rewritten_variants_share_one_group(self) -> None:
        self.assertEqual(
            source_query_group("mteb/arguana", "q123"),
            source_query_group("mteb/arguana", "q123"),
        )
        self.assertNotEqual(
            source_query_group("mteb/arguana", "q123"),
            source_query_group("mteb/arguana", "q124"),
        )

    def test_group_split_is_deterministic_and_disjoint(self) -> None:
        groups = [f"mteb/x::{index}" for index in range(20)]
        train_a, test_a = split_groups(groups, 0.2, 20260809)
        train_b, test_b = split_groups(groups, 0.2, 20260809)
        self.assertEqual((train_a, test_a), (train_b, test_b))
        assert_disjoint(train_a, test_a, "split")

    def test_qrel_alignment_and_variant_identity(self) -> None:
        qrels = {"q1": {"d1": 1.0}}
        assert_query_qrel_alignment(["q1"], qrels)
        assert_variant_qrels_identical(qrels["q1"], {"d1": 1.0})
        with self.assertRaises(AssertionError):
            assert_variant_qrels_identical(qrels["q1"], {"d2": 1.0})

    def test_overlap_is_reported_at_source_query_level(self) -> None:
        report = compare_manifests([
            {"dataset_id": "a", "source_dataset": "mteb/x", "query_ids": ["q1"], "source_query_groups": ["mteb/x::q1"], "qrel_signatures": ["s1"]},
            {"dataset_id": "b", "source_dataset": "mteb/x", "query_ids": ["q1"], "source_query_groups": ["mteb/x::q1"], "qrel_signatures": ["s1"]},
        ])
        self.assertEqual(report.source_query_level[0]["overlap_count"], 1)


class IntegrityTests(unittest.TestCase):
    @staticmethod
    def _cache_request(cache: EmbeddingCache, corpus: dict[str, dict[str, str]], model_id: str = "model/a") -> dict:
        corpus_hash, ids_hash, ids = corpus_fingerprints(corpus)
        return cache.request(
            resource_id="resource/a",
            resource_revision="rev-a",
            corpus_size=len(ids),
            corpus_fingerprint=corpus_hash,
            document_ids_fingerprint=ids_hash,
            model_id=model_id,
            model_revision="model-rev-a",
            embedding_dimension=2,
            pooling="mean_masked_last_hidden_state",
            normalization=True,
            document_prefix="",
            max_length=512,
            truncation=True,
            padding=True,
            model_dtype="torch.float16",
        )

    def test_embedding_cache_miss_save_hit_and_mismatch_rejection(self) -> None:
        corpus = {
            "d1": {"title": "one", "text": "first"},
            "d2": {"title": "two", "text": "second"},
        }
        embeddings = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        with tempfile.TemporaryDirectory() as directory:
            cache = EmbeddingCache(directory)
            request = self._cache_request(cache, corpus)
            _, _, document_ids = corpus_fingerprints(corpus)
            first = cache.load(request, document_ids)
            self.assertFalse(first.hit)
            self.assertEqual(first.reason, "miss")
            saved = cache.save(request, document_ids, embeddings)
            self.assertEqual(saved.reason, "saved")
            hit = cache.load(request, document_ids)
            self.assertTrue(hit.hit)
            np.testing.assert_array_equal(hit.embeddings, embeddings)

            different_model = self._cache_request(cache, corpus, model_id="model/b")
            rejected_model = cache.load(different_model, document_ids)
            self.assertFalse(rejected_model.hit)
            self.assertEqual(rejected_model.reason, "miss")

            rejected_order = cache.load(request, list(reversed(document_ids)))
            self.assertFalse(rejected_order.hit)
            self.assertEqual(rejected_order.reason, "document_order_mismatch")

    def test_catalog_and_protocol(self) -> None:
        resources = load_resources("configs/benchmarks.yaml")
        self.assertEqual(len(resources), 14)
        self.assertTrue(any(resource.short_name == "ArguAna" for resource in resources))
        assert_protocol("configs/benchmarks.yaml", "configs/data_protocol.yaml")

    def test_metrics_are_finite_and_valid(self) -> None:
        metrics = evaluate_ranking(["d1", "d2", "d3"], {"d2": 1.0}, "ndcg_at_10")
        self.assertTrue(all(value == value and abs(value) < float("inf") for value in metrics.values()))
        self.assertGreaterEqual(metrics["official"], 0.0)

    def test_artifact_reload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.jsonl"
            path.write_text(json.dumps({"source_query_id": "mteb/x::q1", "metrics": {"official": 1.0}}) + "\n", encoding="utf-8")
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[0]["source_query_id"], "mteb/x::q1")


if __name__ == "__main__":
    unittest.main()

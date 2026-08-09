from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import yaml

from csr_ir.milestone2 import (
    ACTIVE_SIGNALS,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    EPSILON,
    RRF_K,
    THRESHOLD_GRID,
    CompactRun,
    EmpiricalCDF,
    assert_development_dataset,
    actual_winner,
    fit_signal_candidates,
    hard_choice,
    normalized_margin,
    paired_bootstrap,
    rrf_ranking,
    select_tau,
    signal_value,
    top_k_dispersion,
)


ROOT = Path(__file__).resolve().parents[1]


def run_row(group: str, setting: str, scores: list[float], ndcg: float) -> CompactRun:
    return CompactRun(
        source_query_id=group,
        setting=setting,
        top_scores=tuple(scores),
        metrics={"ndcg@10": ndcg, "recall@10": ndcg, "mrr": ndcg, "official": ndcg},
    )


class SignalTests(unittest.TestCase):
    def test_margin_equation_and_strictly_decreasing_scores(self) -> None:
        scores = [1.0, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1]
        expected = (1.0 - 0.8) / (abs(1.0 - 0.1) + EPSILON)
        self.assertAlmostEqual(normalized_margin(scores), expected)

    def test_margin_zero_range_top_tie_and_positive_bm25_scores(self) -> None:
        self.assertEqual(normalized_margin([3.0] * 10), 0.0)
        self.assertEqual(normalized_margin([3.0, 3.0, 2.8, 2.7, 2.6, 2.5, 2.4, 2.3, 2.2, 2.1]), 0.0)
        self.assertGreater(normalized_margin([10, 9, 8, 7, 6, 5, 4, 3, 2, 1]), 0.0)

    def test_dispersion_equation_ddof_zero_and_dense_scores(self) -> None:
        scores = np.asarray([0.91, 0.88, 0.83, 0.80, 0.77, 0.73, 0.70, 0.66, 0.63, 0.60])
        normalized = (scores - scores[-1]) / (scores[0] - scores[-1] + EPSILON)
        self.assertAlmostEqual(top_k_dispersion(scores), float(np.std(normalized, ddof=0)))

    def test_dispersion_zero_and_very_small_range(self) -> None:
        self.assertEqual(top_k_dispersion([0.5] * 10), 0.0)
        tiny = [1.0 - index * 5e-14 for index in range(10)]
        self.assertEqual(top_k_dispersion(tiny), 0.0)

    def test_exactly_ten_and_deterministic(self) -> None:
        scores = [float(10 - index) for index in range(10)]
        first = (normalized_margin(scores), top_k_dispersion(scores))
        second = (normalized_margin(scores), top_k_dispersion(scores))
        self.assertEqual(first, second)
        with self.assertRaises(AssertionError):
            normalized_margin(scores[:9])
        with self.assertRaises(AssertionError):
            top_k_dispersion(scores[:9])


class CalibrationTests(unittest.TestCase):
    def test_empirical_cdf_includes_ties(self) -> None:
        cdf = EmpiricalCDF.fit([1.0, 1.0, 2.0])
        self.assertEqual(cdf.apply(1.0), 2.0 / 3.0)
        self.assertEqual(cdf.apply(2.0), 1.0)

    def test_bm25_and_qwen_cdfs_are_separate(self) -> None:
        bm25 = EmpiricalCDF.fit([1.0, 2.0])
        qwen = EmpiricalCDF.fit([10.0, 20.0])
        self.assertNotEqual(bm25.sorted_values, qwen.sorted_values)
        self.assertNotEqual(bm25.apply(1.5), qwen.apply(1.5))

    def test_fit_uses_code_switched_only_and_signal_tie_selects_margin(self) -> None:
        groups = ["g1", "g2"]
        equal = [1.0] * 10
        bm25 = {}
        qwen = {}
        for group in groups:
            bm25[(group, "code_switched")] = run_row(group, "code_switched", equal, 0.0)
            qwen[(group, "code_switched")] = run_row(group, "code_switched", equal, 0.0)
            # Poisoned originals would change labels if the implementation accessed them.
            bm25[(group, "original")] = run_row(group, "original", equal, 1.0)
            qwen[(group, "original")] = run_row(group, "original", equal, 0.0)
        result = fit_signal_candidates(groups, bm25, qwen)
        self.assertEqual(result["selected_signal"], ACTIVE_SIGNALS[0])
        self.assertTrue(result["tie_break_applied"])
        for candidate in result["candidates"].values():
            self.assertEqual(candidate["bm25_cdf"].to_dict()["sample_count"], 2)
            self.assertEqual(candidate["qwen_cdf"].to_dict()["sample_count"], 2)

    def test_winner_ties_go_to_qwen(self) -> None:
        self.assertEqual(actual_winner(0.5, 0.5), "Qwen")
        self.assertEqual(actual_winner(0.6, 0.5), "BM25")

    def test_hard_rule_and_qwen_fallback(self) -> None:
        self.assertEqual(hard_choice(-0.1000001, 0.1), "BM25")
        self.assertEqual(hard_choice(-0.1, 0.1), "Qwen")
        self.assertEqual(hard_choice(0.0, 0.1), "Qwen")
        self.assertEqual(hard_choice(0.5, 0.1), "Qwen")

    def test_validation_uses_selected_signal_and_tau_tie_prefers_smaller(self) -> None:
        groups = ["g1", "g2"]
        scores = [1.0] * 10
        bm25 = {(group, "code_switched"): run_row(group, "code_switched", scores, 0.2) for group in groups}
        qwen = {(group, "code_switched"): run_row(group, "code_switched", scores, 0.3) for group in groups}
        cdf = EmpiricalCDF.fit([0.0, 0.0])
        result = select_tau(
            groups,
            bm25,
            qwen,
            signal=ACTIVE_SIGNALS[0],
            bm25_cdf=cdf,
            qwen_cdf=cdf,
        )
        self.assertEqual(result["selected_tau"], 0.0)
        self.assertEqual(tuple(row["tau"] for row in result["sweep"]), THRESHOLD_GRID)


class StatisticalAndBoundaryTests(unittest.TestCase):
    def test_bootstrap_is_deterministic(self) -> None:
        differences = [0.1, -0.1, 0.2, 0.0]
        first = paired_bootstrap(differences)
        second = paired_bootstrap(differences)
        self.assertEqual(first, second)
        self.assertEqual(first["replicates"], BOOTSTRAP_REPLICATES)
        self.assertEqual(first["seed"], BOOTSTRAP_SEED)

    def test_rrf_uses_k_60(self) -> None:
        self.assertEqual(RRF_K, 60)
        ranking = rrf_ranking(["a", "b"], ["b", "c"])
        scores = {
            "a": 1 / 61,
            "b": 1 / 62 + 1 / 61,
            "c": 1 / 62,
        }
        expected = sorted(scores, key=lambda document_id: (-scores[document_id], document_id))
        self.assertEqual(ranking, expected)

    def test_protocol_blocks_original_outcomes_and_target_recalibration(self) -> None:
        protocol = yaml.safe_load((ROOT / "configs/milestone2_protocol.yaml").read_text(encoding="utf-8"))
        threshold = protocol["candidate_method"]["threshold_selection"]
        self.assertEqual(threshold["grid"], list(THRESHOLD_GRID))
        self.assertFalse(threshold["original_query_outcomes_for_threshold_selection"])
        self.assertFalse(threshold["Delta_CS_for_threshold_selection"])
        self.assertFalse(protocol["development_splits"]["fixed_transfer_target"]["target_cdf_recalibration"])

    def test_split_checksums(self) -> None:
        split = json.loads((ROOT / "results/protocol/milestone2_climate_source_split.json").read_text(encoding="utf-8"))
        self.assertEqual(split["source_query_groups_sha256"], "49d53e935f3e9e54c252d9aa130107f0bff1e5e678d39d8aa325916f307dab5b")
        self.assertEqual(split["assignment_sha256"], "fb1514ce76470601464f51ade05877fe33b5850b5d1087a1f4dc52ddd0fcdf9b")

    def test_csr_l_access_is_disabled(self) -> None:
        assert_development_dataset("ClimateFEVERHardNegatives")
        assert_development_dataset("ArguAna")
        with self.assertRaises(AssertionError):
            assert_development_dataset("Touche2020")
        with self.assertRaises(AssertionError):
            assert_development_dataset("UTokyo-Yokoya-Lab/webis-touche2020-v3-CSR-L")


if __name__ == "__main__":
    unittest.main()

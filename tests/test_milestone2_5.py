from __future__ import annotations

import unittest

from scripts.run_milestone2_5 import (
    auroc_positive,
    classification_metrics,
    holdout_decomposition,
    ks_statistic,
    spearman,
    wasserstein_1d,
)


class PostmortemMathTests(unittest.TestCase):
    def test_auc_handles_ties_and_positive_direction(self) -> None:
        self.assertAlmostEqual(auroc_positive([True, False], [2.0, 1.0]), 1.0)
        self.assertAlmostEqual(auroc_positive([True, False], [1.0, 1.0]), 0.5)

    def test_classification_metrics_report_imbalance_and_mcc(self) -> None:
        rows = [
            {"observed_winner": "BM25", "predicted": "BM25"},
            {"observed_winner": "BM25", "predicted": "Qwen"},
            {"observed_winner": "Qwen", "predicted": "Qwen"},
            {"observed_winner": "Qwen", "predicted": "Qwen"},
        ]
        result = classification_metrics(rows, "predicted")
        self.assertEqual(result["confusion_matrix"], {
            "actual_BM25_predicted_BM25": 1,
            "actual_BM25_predicted_Qwen": 1,
            "actual_Qwen_predicted_BM25": 0,
            "actual_Qwen_predicted_Qwen": 2,
        })
        self.assertAlmostEqual(result["majority_baseline_accuracy"], 0.5)
        self.assertAlmostEqual(result["balanced_accuracy"], 0.75)

    def test_decomposition_separates_beneficial_harmful_and_missed(self) -> None:
        rows = [
            {"choice": "BM25", "observed_winner": "BM25", "bm25_ndcg_at_10": "0.8", "qwen_ndcg_at_10": "0.2"},
            {"choice": "BM25", "observed_winner": "Qwen", "bm25_ndcg_at_10": "0.1", "qwen_ndcg_at_10": "0.5"},
            {"choice": "Qwen", "observed_winner": "Qwen", "bm25_ndcg_at_10": "0.2", "qwen_ndcg_at_10": "0.6"},
            {"choice": "Qwen", "observed_winner": "BM25", "bm25_ndcg_at_10": "0.7", "qwen_ndcg_at_10": "0.1"},
        ]
        result = holdout_decomposition(rows)
        self.assertEqual(result["beneficial_switch_count"], 1)
        self.assertEqual(result["harmful_switch_count"], 1)
        self.assertEqual(result["missed_opportunity_count"], 1)
        self.assertAlmostEqual(result["bm25_switch_precision"], 0.5)
        self.assertAlmostEqual(result["bm25_opportunity_recall"], 0.5)
        self.assertAlmostEqual(result["harmful_switch_rate"], 0.5)

    def test_rank_and_distribution_diagnostics_are_deterministic(self) -> None:
        self.assertAlmostEqual(spearman([1.0, 2.0, 3.0], [10.0, 20.0, 30.0]), 1.0)
        self.assertAlmostEqual(ks_statistic([0.0, 1.0], [0.0, 1.0]), 0.0)
        self.assertAlmostEqual(wasserstein_1d([0.0, 1.0], [0.0, 1.0]), 0.0)


if __name__ == "__main__":
    unittest.main()

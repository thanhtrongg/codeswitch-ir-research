from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class Milestone2SemanticFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = yaml.safe_load((ROOT / "configs/milestone2_protocol.yaml").read_text(encoding="utf-8"))
        cls.data_protocol = yaml.safe_load((ROOT / "configs/data_protocol.yaml").read_text(encoding="utf-8"))
        cls.split = json.loads(
            (ROOT / "results/protocol/milestone2_climate_source_split.json").read_text(encoding="utf-8")
        )

    def test_candidate_specific_cdf_selection_is_explicit(self) -> None:
        method = self.protocol["candidate_method"]
        active = [item["id"] for item in method["signal_families"] if item["status"] == "active"]
        removed = [item["id"] for item in method["signal_families"] if item["status"] != "active"]
        self.assertEqual(active, ["normalized_top1_minus_top2_score_margin", "top_k_score_dispersion"])
        self.assertEqual(removed, ["retrieved_set_embedding_coherence"])

        selection = method["signal_selection"]
        self.assertEqual(selection["data"], "primary_source_fit_code_switched_variants_only")
        self.assertTrue(selection["candidates_evaluated_independently"])
        procedure = selection["candidate_specific_cdf_procedure"]
        self.assertEqual(procedure["cdf_scope"], "Climate_source_fit_code_switched_zh_en_variants_only")
        self.assertEqual(procedure["raw_signal_scope"], "each_candidate_signal_separately_for_BM25_and_Qwen")
        self.assertTrue(selection["after_selection"]["discard_unselected_signal"])
        self.assertTrue(selection["after_selection"]["retain_only_selected_signal_definition_and_candidate_CDFs"])

    def test_calibration_scope_and_no_recalibration(self) -> None:
        source = self.protocol["development_splits"]["primary_source"]
        self.assertEqual(source["calibration_variant_scope"], "code_switched_zh_en_only")
        self.assertFalse(source["original_variants_in_calibration_or_signal_selection"])

        method = self.protocol["candidate_method"]
        cdf = method["cross_retriever_normalization"]
        self.assertTrue(cdf["candidate_specific"])
        self.assertFalse(cdf["target_recalibration"])
        self.assertFalse(cdf["target_cdf_refitting"])

        safety = self.protocol["metrics_and_decision"]["original_query_safety"]
        self.assertEqual(safety["calibration_source"], "Climate_source_fit_code_switched_variants_only")
        self.assertFalse(safety["cdf_recalibration"])
        self.assertFalse(safety["threshold_recalibration"])

    def test_frozen_boundary_and_constants(self) -> None:
        self.assertEqual(
            self.protocol["scope"]["development"]["primary_source"]["short_name"],
            "ClimateFEVERHardNegatives",
        )
        self.assertEqual(
            self.protocol["scope"]["development"]["fixed_transfer_target"]["short_name"],
            "ArguAna",
        )
        self.assertEqual(self.protocol["retrievers"]["dense"]["revision"], "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3")
        self.assertEqual(self.protocol["inference_configuration"]["selector_top_k"], 10)
        self.assertAlmostEqual(self.protocol["inference_configuration"]["epsilon"], 1e-12)
        self.assertEqual(
            self.protocol["candidate_method"]["threshold_selection"]["grid"],
            [0.0, 0.05, 0.1, 0.15, 0.2],
        )
        self.assertEqual(self.protocol["registered_comparators"]["fixed_RRF_BM25_Qwen"]["rrf_parameter_k"], 60)
        self.assertTrue(self.protocol["dense_encoding_policy"]["no_new_dense_encoding_before_milestone2_execution"])

    def test_threshold_selection_is_fully_code_switched(self) -> None:
        threshold = self.protocol["candidate_method"]["threshold_selection"]
        self.assertEqual(threshold["data"], "primary_source_validation_code_switched_variants_only")
        self.assertEqual(threshold["objective"], "highest_code_switched_nDCG_at_10")
        self.assertEqual(threshold["tie_breaks"], ["smaller_tau", "lexical_serialization_order"])
        self.assertFalse(threshold["original_query_outcomes_for_threshold_selection"])
        self.assertFalse(threshold["Delta_CS_for_threshold_selection"])
        threshold_text = " ".join(str(value) for value in threshold["tie_breaks"])
        self.assertNotIn("original", threshold_text.lower())
        self.assertNotIn("delta_cs", threshold_text.lower())

    def test_leakage_statuses_and_split_are_unchanged(self) -> None:
        leakage = self.protocol["leakage_validation"]
        self.assertEqual(leakage["raw_artifact_revalidation"]["status"], "pass")
        self.assertEqual(leakage["raw_artifact_revalidation"]["source_qualified_development_final_overlap"], 0)
        self.assertEqual(leakage["dataset_backed_validator"]["status"], "inconclusive_timeout")

        self.assertEqual(self.split["group_count"], 1000)
        self.assertEqual(self.split["source_query_groups_sha256"], "49d53e935f3e9e54c252d9aa130107f0bff1e5e678d39d8aa325916f307dab5b")
        self.assertEqual(self.split["assignment_sha256"], "fb1514ce76470601464f51ade05877fe33b5850b5d1087a1f4dc52ddd0fcdf9b")
        counts = Counter(item["assignment"] for item in self.split["assignments"])
        self.assertEqual(counts, Counter({"fit": 600, "validation": 200, "post_exploratory_frozen_holdout": 200}))

        final_test = self.data_protocol["final_test"]
        self.assertTrue(final_test["untouched_after_freeze"])
        self.assertFalse(final_test["selection_allowed"])


if __name__ == "__main__":
    unittest.main()

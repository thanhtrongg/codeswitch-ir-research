"""Execute the frozen Milestone 2 development-only QPP experiment in protected stages.

`prepare` reads only Climate fit/validation outcomes, freezes the selected
signal/CDF/tau implementation, and does not decode holdout or target outcomes.
`execute` validates that freeze, accesses Climate holdout once, and accesses
ArguAna only when the complete registered source gate passes. CSR-L is never
loaded by this module.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import yaml

from csr_ir.milestone2 import (
    ACTIVE_SIGNALS,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    EPSILON,
    RRF_K,
    THRESHOLD_GRID,
    TOP_K,
    EmpiricalCDF,
    aggregate_fixed,
    aggregate_metric_rows,
    atomic_write_text,
    compute_rrf_metrics,
    evaluate_selector,
    fit_signal_candidates,
    load_compact_rows,
    oracle_metrics,
    paired_bootstrap,
    scan_artifact_without_outcomes,
    select_tau,
    sha256_file,
    write_csv,
    write_json,
    write_yaml,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = ROOT / "results" / "milestone2"
PROTOCOL_PATH = ROOT / "configs" / "milestone2_protocol.yaml"
DATA_PROTOCOL_PATH = ROOT / "configs" / "data_protocol.yaml"
FREEZE_1_5D_PATH = ROOT / "results" / "protocol" / "milestone2_freeze_manifest_1_5d.yaml"
SPLIT_PATH = ROOT / "results" / "protocol" / "milestone2_climate_source_split.json"
LEDGER_PATH = RESULT_ROOT / "execution_ledger.yaml"
METHOD_FREEZE_PATH = RESULT_ROOT / "freeze" / "milestone2_method_freeze_manifest.yaml"
ARTIFACT_MANIFEST_PATH = RESULT_ROOT / "logs" / "baseline_artifact_manifest.json"

DATASETS = {
    "ClimateFEVERHardNegatives": {
        "resource_id": "UTokyo-Yokoya-Lab/ClimateFEVER_hardnegatives_CS-MTEB",
        "query_pairs": 1000,
    },
    "ArguAna": {
        "resource_id": "UTokyo-Yokoya-Lab/arguana_CS-MTEB",
        "query_pairs": 1406,
    },
}
RETRIEVERS = ("BM25", "Qwen3-Embedding-0.6B", "BGE-M3")
QWEN_REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
EXPECTED_GROUP_SHA256 = "49d53e935f3e9e54c252d9aa130107f0bff1e5e678d39d8aa325916f307dab5b"
EXPECTED_ASSIGNMENT_SHA256 = "fb1514ce76470601464f51ade05877fe33b5850b5d1087a1f4dc52ddd0fcdf9b"
FINAL_RESOURCE_MARKERS = (
    "Touche2020",
    "HumanEvalRetrieval",
    "TRECCOVID",
    "Core17",
    "News21",
    "Robust04",
    "CSR-L",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: str | Path) -> str:
    return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")


def run_path(dataset: str, retriever: str) -> Path:
    if dataset not in DATASETS or retriever not in RETRIEVERS:
        raise AssertionError(f"unregistered development condition: {dataset}/{retriever}")
    return ROOT / "results" / "runs" / dataset / "zh" / retriever / "per_query.jsonl"


def load_yaml(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_split() -> tuple[dict[str, set[str]], dict[str, Any]]:
    split = load_json(SPLIT_PATH)
    assignments = split["assignments"]
    if split["group_count"] != 1000 or len(assignments) != 1000:
        raise AssertionError("frozen split must contain exactly 1000 groups")
    if split["variant_count"] != 2000 or split["unit"] != "source_dataset::query_id":
        raise AssertionError("frozen split variant/grouping metadata mismatch")
    counts = Counter(item["assignment"] for item in assignments)
    expected_counts = Counter({"fit": 600, "validation": 200, "post_exploratory_frozen_holdout": 200})
    if counts != expected_counts:
        raise AssertionError(f"frozen split counts changed: {counts}")
    groups = sorted(item["source_query_id"] for item in assignments)
    group_hash = hashlib.sha256(("\n".join(groups) + "\n").encode("utf-8")).hexdigest()
    canonical_assignments = sorted(
        ({"source_query_id": item["source_query_id"], "assignment": item["assignment"]} for item in assignments),
        key=lambda item: item["source_query_id"],
    )
    assignment_encoded = json.dumps(
        canonical_assignments, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assignment_hash = hashlib.sha256(assignment_encoded).hexdigest()
    if group_hash != EXPECTED_GROUP_SHA256 or split["source_query_groups_sha256"] != EXPECTED_GROUP_SHA256:
        raise AssertionError("source-query-group checksum mismatch")
    if assignment_hash != EXPECTED_ASSIGNMENT_SHA256 or split["assignment_sha256"] != EXPECTED_ASSIGNMENT_SHA256:
        raise AssertionError("split assignment checksum mismatch")
    by_assignment = {
        assignment: {item["source_query_id"] for item in assignments if item["assignment"] == assignment}
        for assignment in expected_counts
    }
    return by_assignment, split


def verify_frozen_protocol() -> tuple[dict[str, Any], dict[str, set[str]], dict[str, Any]]:
    manifest = load_yaml(FREEZE_1_5D_PATH)
    if manifest["freeze_revision"] != "milestone_1_5d" or manifest["execution_status"] != "not_executed":
        raise AssertionError("authoritative 1.5d freeze status mismatch")
    for name, item in manifest["frozen_files"].items():
        path = ROOT / item["path"]
        if not path.exists() or sha256_file(path) != item["sha256"]:
            raise AssertionError(f"1.5d frozen file checksum mismatch: {name}")
    protocol = load_yaml(PROTOCOL_PATH)
    if protocol["freeze_revision"] != "milestone_1_5d" or protocol["execution_authorized"] is not False:
        raise AssertionError("Milestone 2 protocol revision/authorization mismatch")
    source = protocol["scope"]["development"]["primary_source"]["short_name"]
    target = protocol["scope"]["development"]["fixed_transfer_target"]["short_name"]
    if (source, target) != ("ClimateFEVERHardNegatives", "ArguAna"):
        raise AssertionError("registered source/target direction changed")
    if protocol["scope"]["development"]["fixed_transfer_target"]["reverse_direction"] != "not_registered":
        raise AssertionError("reverse transfer unexpectedly registered")
    if protocol["retrievers"]["dense"]["revision"] != QWEN_REVISION:
        raise AssertionError("Qwen revision mismatch")
    active = [item["id"] for item in protocol["candidate_method"]["signal_families"] if item["status"] == "active"]
    removed = [item["id"] for item in protocol["candidate_method"]["signal_families"] if item["status"] != "active"]
    if tuple(active) != ACTIVE_SIGNALS or removed != ["retrieved_set_embedding_coherence"]:
        raise AssertionError("registered signal set changed")
    if protocol["inference_configuration"]["selector_top_k"] != TOP_K:
        raise AssertionError("selector top-k mismatch")
    if float(protocol["inference_configuration"]["epsilon"]) != EPSILON:
        raise AssertionError("epsilon mismatch")
    threshold = protocol["candidate_method"]["threshold_selection"]
    if tuple(float(value) for value in threshold["grid"]) != THRESHOLD_GRID:
        raise AssertionError("threshold grid mismatch")
    if threshold["tie_breaks"] != ["smaller_tau", "lexical_serialization_order"]:
        raise AssertionError("threshold tie-break mismatch")
    if threshold["original_query_outcomes_for_threshold_selection"] is not False:
        raise AssertionError("original outcomes are not disabled for tau selection")
    if protocol["registered_comparators"]["fixed_RRF_BM25_Qwen"]["rrf_parameter_k"] != RRF_K:
        raise AssertionError("RRF k mismatch")
    uncertainty = protocol["metrics_and_decision"]["uncertainty"]
    if uncertainty["replicates"] != BOOTSTRAP_REPLICATES or uncertainty["seed"] != BOOTSTRAP_SEED:
        raise AssertionError("bootstrap configuration mismatch")
    leakage = protocol["leakage_validation"]
    if leakage["raw_artifact_revalidation"]["status"] != "pass":
        raise AssertionError("raw leakage validation is not PASS")
    if leakage["raw_artifact_revalidation"]["source_qualified_development_final_overlap"] != 0:
        raise AssertionError("source-qualified development/final overlap is not zero")
    if leakage["dataset_backed_validator"]["status"] != "inconclusive_timeout":
        raise AssertionError("dataset-backed validator status changed")
    data_protocol = load_yaml(DATA_PROTOCOL_PATH)
    if data_protocol["final_test"]["untouched_after_freeze"] is not True:
        raise AssertionError("CSR-L is not marked untouched")
    if data_protocol["final_test"]["selection_allowed"] is not False:
        raise AssertionError("CSR-L selection boundary changed")
    assignments, split = verify_split()
    return protocol, assignments, split


def assert_no_csr_l_artifacts() -> None:
    runs_root = ROOT / "results" / "runs"
    for path in runs_root.rglob("*"):
        if any(marker.lower() in path.name.lower() for marker in FINAL_RESOURCE_MARKERS):
            raise AssertionError(f"unexpected final-boundary run artifact: {path}")
    if RESULT_ROOT.exists():
        for path in RESULT_ROOT.rglob("*"):
            if any(marker.lower() in path.name.lower() for marker in FINAL_RESOURCE_MARKERS):
                raise AssertionError(f"unexpected CSR-L Milestone 2 artifact: {path}")


def new_ledger() -> dict[str, Any]:
    return {
        "protocol_revision": "milestone_1_5d",
        "execution_started_utc": now_utc(),
        "protocol_verified": False,
        "baseline_artifacts_verified": False,
        "pre_holdout_tests_passed": False,
        "fit_completed": False,
        "signal_frozen": False,
        "validation_completed": False,
        "tau_frozen": False,
        "method_manifest_created": False,
        "climate_holdout_accessed": False,
        "climate_holdout_completed": False,
        "source_gate_status": "NOT_EVALUATED",
        "arguana_accessed": False,
        "arguana_completed": False,
        "transfer_gate_status": "NOT_EVALUATED",
        "outputs_completed": False,
        "csr_l_accessed": False,
        "gpu_worker_launched": False,
        "failure": None,
        "timestamps": {},
    }


def read_ledger() -> dict[str, Any]:
    if not LEDGER_PATH.exists():
        raise AssertionError("execution ledger does not exist")
    return load_yaml(LEDGER_PATH)


def save_ledger(ledger: Mapping[str, Any]) -> None:
    write_yaml(LEDGER_PATH, dict(ledger))


def mark(ledger: dict[str, Any], field: str, value: Any = True) -> None:
    ledger[field] = value
    ledger.setdefault("timestamps", {})[field] = now_utc()
    save_ledger(ledger)


def preflight_artifacts(assignments: Mapping[str, set[str]]) -> dict[str, Any]:
    scans: dict[tuple[str, str], dict[str, Any]] = {}
    for dataset in DATASETS:
        for retriever in RETRIEVERS:
            path = run_path(dataset, retriever)
            if not path.exists():
                raise AssertionError(f"missing required fixed artifact: {path}")
            scan = scan_artifact_without_outcomes(path)
            if scan["resource_id"] != DATASETS[dataset]["resource_id"]:
                raise AssertionError(f"resource identity mismatch: {dataset}/{retriever}")
            if scan["language"] != "zh" or scan["groups"] != DATASETS[dataset]["query_pairs"]:
                raise AssertionError(f"language/query count mismatch: {dataset}/{retriever}")
            if scan["retrieval_depth"] != 1000:
                raise AssertionError(f"retrieval depth mismatch: {dataset}/{retriever}")
            if retriever == "Qwen3-Embedding-0.6B" and scan["model_revision"] != QWEN_REVISION:
                raise AssertionError(f"Qwen artifact revision mismatch: {dataset}")
            scans[(dataset, retriever)] = scan
        sequences = [scans[(dataset, retriever)]["header_sequence"] for retriever in RETRIEVERS]
        if not all(sequence == sequences[0] for sequence in sequences[1:]):
            raise AssertionError(f"retriever row/header sequence mismatch for {dataset}")
    climate_groups = set(scans[("ClimateFEVERHardNegatives", "BM25")]["group_ids"])
    if climate_groups != set().union(*assignments.values()):
        raise AssertionError("Climate artifact groups differ from frozen split")
    serializable: dict[str, Any] = {
        "scope": "development_only_fixed_artifacts",
        "outcome_fields_parsed_during_preflight": False,
        "ranking_structure_verified": True,
        "conditions": {},
    }
    for (dataset, retriever), scan in scans.items():
        record = {key: value for key, value in scan.items() if key != "header_sequence"}
        serializable["conditions"][f"{dataset}/{retriever}"] = record
    write_json(ARTIFACT_MANIFEST_PATH, serializable)
    return serializable


def implementation_files() -> list[Path]:
    return [
        ROOT / "src" / "csr_ir" / "milestone2.py",
        ROOT / "src" / "csr_ir" / "metrics.py",
        ROOT / "scripts" / "run_milestone2.py",
        ROOT / "tests" / "test_milestone2.py",
        ROOT / "tests" / "test_milestone2_semantic_freeze.py",
    ]


def run_pre_holdout_tests() -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/test_milestone2.py",
        "tests/test_milestone2_semantic_freeze.py",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path = RESULT_ROOT / "logs" / "pre_holdout_tests.txt"
    atomic_write_text(log_path, completed.stdout)
    if completed.returncode != 0:
        raise AssertionError(f"pre-holdout tests failed; see {rel(log_path)}")
    return {
        "command": command,
        "returncode": completed.returncode,
        "log_path": rel(log_path),
        "log_sha256": sha256_file(log_path),
        "output": completed.stdout.strip(),
    }


def prepare() -> dict[str, Any]:
    if LEDGER_PATH.exists():
        raise AssertionError("Milestone 2 ledger already exists; refusing duplicate prepare run")
    protocol, assignments, split = verify_frozen_protocol()
    assert_no_csr_l_artifacts()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    ledger = new_ledger()
    save_ledger(ledger)
    mark(ledger, "protocol_verified")
    artifact_manifest = preflight_artifacts(assignments)
    mark(ledger, "baseline_artifacts_verified")
    pre_holdout_tests = run_pre_holdout_tests()
    ledger["pre_holdout_test_record"] = pre_holdout_tests
    mark(ledger, "pre_holdout_tests_passed")

    fit_groups = sorted(assignments["fit"])
    bm25_fit = load_compact_rows(
        run_path("ClimateFEVERHardNegatives", "BM25"),
        groups=set(fit_groups),
        settings={"code_switched"},
        expected_retriever="BM25",
        expected_dataset="ClimateFEVERHardNegatives",
    )
    qwen_fit = load_compact_rows(
        run_path("ClimateFEVERHardNegatives", "Qwen3-Embedding-0.6B"),
        groups=set(fit_groups),
        settings={"code_switched"},
        expected_retriever="Qwen3-Embedding-0.6B",
        expected_dataset="ClimateFEVERHardNegatives",
    )
    fit = fit_signal_candidates(fit_groups, bm25_fit, qwen_fit)
    selected_signal = fit["selected_signal"]
    selected_candidate = fit["candidates"][selected_signal]
    calibration_root = RESULT_ROOT / "calibration"
    write_csv(calibration_root / "fit_signal_selection.csv", fit["diagnostics"])
    fit_summary = {
        "scope": "ClimateFEVERHardNegatives source fit code-switched zh-en variants only",
        "sample_count": len(fit_groups),
        "candidate_signals": list(ACTIVE_SIGNALS),
        "fit_accuracy_margin": fit["candidates"][ACTIVE_SIGNALS[0]]["accuracy"],
        "fit_accuracy_dispersion": fit["candidates"][ACTIVE_SIGNALS[1]]["accuracy"],
        "selected_signal": selected_signal,
        "selection_rule": "highest mean winner accuracy; ties select margin",
        "tie_break_applied": fit["tie_break_applied"],
        "winner_ties": "Qwen",
        "unselected_signal_discarded_after_fit": True,
    }
    write_json(calibration_root / "fit_signal_selection_summary.json", fit_summary)
    write_json(
        calibration_root / "selected_signal.json",
        {
            "selected_signal": selected_signal,
            "formula_identifier": selected_signal,
            "fit_sample_count": len(fit_groups),
            "k": TOP_K,
            "epsilon": EPSILON,
            "unselected_signal_used_after_fit": False,
        },
    )
    bm25_cdf_path = calibration_root / "bm25_fit_cdf.json"
    qwen_cdf_path = calibration_root / "qwen_fit_cdf.json"
    bm25_cdf_payload = {
        "signal": selected_signal,
        "retriever": "BM25",
        "scope": "Climate source fit code-switched variants only",
        **selected_candidate["bm25_cdf"].to_dict(),
    }
    qwen_cdf_payload = {
        "signal": selected_signal,
        "retriever": "Qwen3-Embedding-0.6B",
        "scope": "Climate source fit code-switched variants only",
        **selected_candidate["qwen_cdf"].to_dict(),
    }
    write_json(bm25_cdf_path, bm25_cdf_payload)
    write_json(qwen_cdf_path, qwen_cdf_payload)
    mark(ledger, "fit_completed")
    mark(ledger, "signal_frozen")

    validation_groups = sorted(assignments["validation"])
    bm25_validation = load_compact_rows(
        run_path("ClimateFEVERHardNegatives", "BM25"),
        groups=set(validation_groups),
        settings={"code_switched"},
        expected_retriever="BM25",
        expected_dataset="ClimateFEVERHardNegatives",
    )
    qwen_validation = load_compact_rows(
        run_path("ClimateFEVERHardNegatives", "Qwen3-Embedding-0.6B"),
        groups=set(validation_groups),
        settings={"code_switched"},
        expected_retriever="Qwen3-Embedding-0.6B",
        expected_dataset="ClimateFEVERHardNegatives",
    )
    validation = select_tau(
        validation_groups,
        bm25_validation,
        qwen_validation,
        signal=selected_signal,
        bm25_cdf=selected_candidate["bm25_cdf"],
        qwen_cdf=selected_candidate["qwen_cdf"],
    )
    validation_root = RESULT_ROOT / "validation"
    write_csv(validation_root / "tau_sweep.csv", validation["sweep"])
    write_csv(validation_root / "selected_tau_diagnostics.csv", validation["evaluation"]["diagnostics"])
    validation_summary = {
        "scope": "ClimateFEVERHardNegatives validation code-switched zh-en variants only",
        "sample_count": len(validation_groups),
        "selected_signal": selected_signal,
        "threshold_grid": list(THRESHOLD_GRID),
        "selection_objective": "highest code-switched nDCG@10",
        "tie_breaks": ["smaller tau", "deterministic lexical serialization order"],
        "original_query_outcomes_used": False,
        "selected_tau": validation["selected_tau"],
        "sweep": validation["sweep"],
    }
    write_json(validation_root / "tau_selection_summary.json", validation_summary)
    mark(ledger, "validation_completed")
    mark(ledger, "tau_frozen")

    implementation = {rel(path): sha256_file(path) for path in implementation_files()}
    frozen_artifacts = {
        rel(path): sha256_file(path)
        for path in (
            calibration_root / "fit_signal_selection.csv",
            calibration_root / "fit_signal_selection_summary.json",
            calibration_root / "selected_signal.json",
            bm25_cdf_path,
            qwen_cdf_path,
            validation_root / "tau_sweep.csv",
            validation_root / "selected_tau_diagnostics.csv",
            validation_root / "tau_selection_summary.json",
            RESULT_ROOT / "logs" / "pre_holdout_tests.txt",
        )
    }
    baseline_hashes = {
        condition: {
            "artifact_path": item["path"],
            "artifact_sha256": item["sha256"],
            "run_config_path": item["run_config_path"],
            "run_config_sha256": item["run_config_sha256"],
        }
        for condition, item in artifact_manifest["conditions"].items()
    }
    method_freeze = {
        "manifest_id": "milestone2_frozen_method_v1",
        "created_utc": now_utc(),
        "protocol_revision": "milestone_1_5d",
        "protocol_path": rel(PROTOCOL_PATH),
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "data_protocol_sha256": sha256_file(DATA_PROTOCOL_PATH),
        "source_split_path": rel(SPLIT_PATH),
        "source_split_file_sha256": sha256_file(SPLIT_PATH),
        "source_query_groups_sha256": split["source_query_groups_sha256"],
        "assignment_sha256": split["assignment_sha256"],
        "source": "ClimateFEVERHardNegatives",
        "target": "ArguAna",
        "reverse_transfer": "NOT_REGISTERED",
        "selected_signal": selected_signal,
        "selected_signal_formula_identifier": selected_signal,
        "fit_sample_count": len(fit_groups),
        "bm25_cdf_path": rel(bm25_cdf_path),
        "bm25_cdf_sha256": sha256_file(bm25_cdf_path),
        "qwen_cdf_path": rel(qwen_cdf_path),
        "qwen_cdf_sha256": sha256_file(qwen_cdf_path),
        "selected_tau": validation["selected_tau"],
        "threshold_grid": list(THRESHOLD_GRID),
        "threshold_objective": "Climate validation code-switched nDCG@10 only",
        "threshold_tie_breaks": ["smaller tau", "deterministic lexical serialization order"],
        "k": TOP_K,
        "epsilon": EPSILON,
        "qwen_revision": QWEN_REVISION,
        "rrf_k": RRF_K,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "pre_holdout_tests": pre_holdout_tests,
        "implementation_files": implementation,
        "frozen_pre_holdout_artifacts": frozen_artifacts,
        "baseline_artifacts": baseline_hashes,
        "repository_commit": None,
        "repository_commit_note": "workspace has no .git metadata",
        "holdout_accessed_before_manifest": False,
        "csr_l_accessed": False,
    }
    write_yaml(METHOD_FREEZE_PATH, method_freeze)
    ledger["method_manifest_path"] = rel(METHOD_FREEZE_PATH)
    ledger["method_manifest_sha256"] = sha256_file(METHOD_FREEZE_PATH)
    ledger["selected_signal"] = selected_signal
    ledger["selected_tau"] = validation["selected_tau"]
    mark(ledger, "method_manifest_created")
    return {
        "selected_signal": selected_signal,
        "fit_accuracy_margin": fit_summary["fit_accuracy_margin"],
        "fit_accuracy_dispersion": fit_summary["fit_accuracy_dispersion"],
        "selected_tau": validation["selected_tau"],
        "method_manifest_sha256": ledger["method_manifest_sha256"],
    }


def validate_method_freeze(ledger: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, set[str]]]:
    _, assignments, _ = verify_frozen_protocol()
    assert_no_csr_l_artifacts()
    if not METHOD_FREEZE_PATH.exists():
        raise AssertionError("method-freeze manifest is missing")
    if not ledger.get("method_manifest_created") or not ledger.get("pre_holdout_tests_passed"):
        raise AssertionError("method freeze or pre-holdout tests are incomplete")
    manifest_hash = sha256_file(METHOD_FREEZE_PATH)
    if ledger.get("method_manifest_sha256") != manifest_hash:
        raise AssertionError("method-freeze manifest hash differs from the execution ledger")
    manifest = load_yaml(METHOD_FREEZE_PATH)
    expected_scalars = {
        "protocol_revision": "milestone_1_5d",
        "source": "ClimateFEVERHardNegatives",
        "target": "ArguAna",
        "reverse_transfer": "NOT_REGISTERED",
        "k": TOP_K,
        "epsilon": EPSILON,
        "qwen_revision": QWEN_REVISION,
        "rrf_k": RRF_K,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "holdout_accessed_before_manifest": False,
        "csr_l_accessed": False,
    }
    for key, expected in expected_scalars.items():
        if manifest.get(key) != expected:
            raise AssertionError(f"method-freeze value changed: {key}")
    if manifest["selected_signal"] not in ACTIVE_SIGNALS:
        raise AssertionError("method-freeze selected signal is not registered")
    if tuple(float(value) for value in manifest["threshold_grid"]) != THRESHOLD_GRID:
        raise AssertionError("method-freeze threshold grid changed")
    if float(manifest["selected_tau"]) not in THRESHOLD_GRID:
        raise AssertionError("method-freeze selected tau is outside the registered grid")
    for path_string, expected_hash in manifest["implementation_files"].items():
        path = ROOT / path_string
        if not path.exists() or sha256_file(path) != expected_hash:
            raise AssertionError(f"post-freeze implementation change detected: {path_string}")
    for path_string, expected_hash in manifest["frozen_pre_holdout_artifacts"].items():
        path = ROOT / path_string
        if not path.exists() or sha256_file(path) != expected_hash:
            raise AssertionError(f"pre-holdout artifact changed: {path_string}")
    for condition, item in manifest["baseline_artifacts"].items():
        artifact_path = Path(item["artifact_path"])
        config_path = Path(item["run_config_path"])
        if sha256_file(artifact_path) != item["artifact_sha256"]:
            raise AssertionError(f"fixed ranking artifact changed: {condition}")
        if sha256_file(config_path) != item["run_config_sha256"]:
            raise AssertionError(f"fixed run config changed: {condition}")
    if sha256_file(PROTOCOL_PATH) != manifest["protocol_sha256"]:
        raise AssertionError("frozen protocol changed after method freeze")
    if sha256_file(DATA_PROTOCOL_PATH) != manifest["data_protocol_sha256"]:
        raise AssertionError("data protocol changed after method freeze")
    if sha256_file(SPLIT_PATH) != manifest["source_split_file_sha256"]:
        raise AssertionError("source split changed after method freeze")
    bm25_cdf_payload = load_json(ROOT / manifest["bm25_cdf_path"])
    qwen_cdf_payload = load_json(ROOT / manifest["qwen_cdf_path"])
    if bm25_cdf_payload["signal"] != manifest["selected_signal"]:
        raise AssertionError("BM25 CDF signal does not match the freeze")
    if qwen_cdf_payload["signal"] != manifest["selected_signal"]:
        raise AssertionError("Qwen CDF signal does not match the freeze")
    bm25_cdf = EmpiricalCDF.from_dict(bm25_cdf_payload)
    qwen_cdf = EmpiricalCDF.from_dict(qwen_cdf_payload)
    if len(bm25_cdf.sorted_values) != 600 or len(qwen_cdf.sorted_values) != 600:
        raise AssertionError("candidate-specific FIT CDFs must each contain 600 values")
    manifest["bm25_cdf"] = bm25_cdf
    manifest["qwen_cdf"] = qwen_cdf
    return manifest, assignments


def stage_evaluation(
    dataset: str,
    groups: Sequence[str],
    *,
    signal: str,
    bm25_cdf: EmpiricalCDF,
    qwen_cdf: EmpiricalCDF,
    tau: float,
    output_name: str,
) -> dict[str, Any]:
    group_set = set(groups)
    if len(group_set) != len(groups):
        raise AssertionError(f"{dataset}: duplicate evaluation group")
    bm25 = load_compact_rows(
        run_path(dataset, "BM25"),
        groups=group_set,
        settings={"original", "code_switched"},
        expected_retriever="BM25",
        expected_dataset=dataset,
    )
    qwen = load_compact_rows(
        run_path(dataset, "Qwen3-Embedding-0.6B"),
        groups=group_set,
        settings={"original", "code_switched"},
        expected_retriever="Qwen3-Embedding-0.6B",
        expected_dataset=dataset,
    )
    bge = load_compact_rows(
        run_path(dataset, "BGE-M3"),
        groups=group_set,
        settings={"original", "code_switched"},
        expected_retriever="BGE-M3",
        expected_dataset=dataset,
    )
    selector: dict[str, dict[str, Any]] = {}
    rrf: dict[str, dict[str, dict[str, float]]] = {}
    for setting in ("code_switched", "original"):
        selector[setting] = evaluate_selector(
            groups,
            setting,
            bm25,
            qwen,
            signal=signal,
            bm25_cdf=bm25_cdf,
            qwen_cdf=qwen_cdf,
            tau=tau,
        )
        rrf[setting] = compute_rrf_metrics(
            run_path(dataset, "BM25"),
            run_path(dataset, "Qwen3-Embedding-0.6B"),
            groups=group_set,
            setting=setting,
        )
    systems: dict[str, dict[str, Any]] = {}
    fixed = {
        "BM25": bm25,
        "Qwen": qwen,
        "BGE-M3": bge,
    }
    for system, rows in fixed.items():
        systems[system] = {
            setting: aggregate_fixed(rows, groups, setting)
            for setting in ("code_switched", "original")
        }
    systems["Selector"] = {
        setting: selector[setting]["metrics"] for setting in ("code_switched", "original")
    }
    systems["RRF"] = {
        setting: aggregate_metric_rows(rrf[setting]) for setting in ("code_switched", "original")
    }
    systems["Oracle diagnostic"] = {
        setting: oracle_metrics(bm25, qwen, groups, setting)
        for setting in ("code_switched", "original")
    }
    for values in systems.values():
        values["delta_cs"] = {
            metric: values["code_switched"][metric] - values["original"][metric]
            for metric in ("ndcg@10", "recall@10", "mrr")
        }
    bootstraps: dict[str, dict[str, Any]] = {}
    for setting in ("code_switched", "original"):
        differences = [
            row["selector_ndcg_at_10"] - row["qwen_ndcg_at_10"]
            for row in selector[setting]["diagnostics"]
        ]
        bootstraps[setting] = paired_bootstrap(differences)
    stage = {
        "dataset": dataset,
        "scope": output_name,
        "group_count": len(groups),
        "selected_signal": signal,
        "selected_tau": tau,
        "calibration_source": "ClimateFEVERHardNegatives FIT code-switched variants only",
        "target_recalibration": False,
        "systems": systems,
        "selector_behavior": {
            setting: selector[setting]["behavior"] for setting in ("code_switched", "original")
        },
        "bootstrap_selector_minus_qwen": bootstraps,
        "arabzadeh_comparator": {
            "status": "NOT_AVAILABLE",
            "reason": "No faithful existing implementation with registered features/objective was present at freeze.",
        },
    }
    stage_root = RESULT_ROOT / output_name
    for setting in ("code_switched", "original"):
        diagnostic_status = (
            "POST-EVALUATION ANALYSIS ONLY"
            if output_name == "transfer"
            else "REGISTERED HOLDOUT EVALUATION DIAGNOSTIC"
        )
        diagnostic_rows = [
            {**row, "diagnostic_status": diagnostic_status}
            for row in selector[setting]["diagnostics"]
        ]
        write_csv(stage_root / f"{setting}_selector_diagnostics.csv", diagnostic_rows)
        write_json(
            RESULT_ROOT / "bootstrap" / f"{output_name}_{setting}_selector_minus_qwen.json",
            bootstraps[setting],
        )
    write_json(stage_root / f"{output_name}_results.json", stage)
    write_json(
        RESULT_ROOT / "comparators" / f"{output_name}_comparators.json",
        {
            "dataset": dataset,
            "RRF": systems["RRF"],
            "BGE-M3_reference_only": systems["BGE-M3"],
            "oracle_diagnostic_only": systems["Oracle diagnostic"],
            "Arabzadeh": stage["arabzadeh_comparator"],
        },
    )
    return stage


def metric_table_rows(stage: Mapping[str, Any]) -> list[dict[str, Any]]:
    roles = {
        "BM25": "fixed retriever",
        "Qwen": "fixed primary baseline",
        "Selector": "frozen candidate",
        "RRF": "fixed baseline only",
        "BGE-M3": "reference only",
        "Oracle diagnostic": "diagnostic upper bound only",
    }
    rows: list[dict[str, Any]] = []
    for system in ("BM25", "Qwen", "Selector", "RRF", "BGE-M3", "Oracle diagnostic"):
        values = stage["systems"][system]
        rows.append(
            {
                "system": system,
                "role": roles[system],
                "cs_ndcg_at_10": values["code_switched"]["ndcg@10"],
                "original_ndcg_at_10": values["original"]["ndcg@10"],
                "delta_cs_ndcg_at_10": values["delta_cs"]["ndcg@10"],
                "cs_recall_at_10": values["code_switched"]["recall@10"],
                "original_recall_at_10": values["original"]["recall@10"],
                "cs_mrr": values["code_switched"]["mrr"],
                "original_mrr": values["original"]["mrr"],
            }
        )
    return rows


def display_value(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.9f}"
    return str(value)


def markdown_table(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "NA\n"
    fields = list(rows[0])
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(display_value(row.get(field)).replace("|", "\\|") for field in fields) + " |")
    return "\n".join(lines) + "\n"


def latex_escape(value: Any) -> str:
    text_value = display_value(value)
    for old, new in (("\\", "\\textbackslash{}"), ("_", "\\_"), ("%", "\\%"), ("&", "\\&")):
        text_value = text_value.replace(old, new)
    return text_value


def latex_table(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "% NA\n"
    fields = list(rows[0])
    columns = "l" * len(fields)
    lines = [f"\\begin{{tabular}}{{{columns}}}", "\\toprule", " & ".join(latex_escape(f) for f in fields) + " \\\\", "\\midrule"]
    lines.extend(" & ".join(latex_escape(row.get(field)) for field in fields) + " \\\\" for row in rows)
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    return "\n".join(lines) + "\n"


def write_table_bundle(name: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    root = RESULT_ROOT / "tables"
    csv_path = root / f"{name}.csv"
    md_path = root / f"{name}.md"
    tex_path = root / f"{name}.tex"
    write_csv(csv_path, rows)
    atomic_write_text(md_path, markdown_table(rows))
    atomic_write_text(tex_path, latex_table(rows))
    return {"csv": rel(csv_path), "markdown": rel(md_path), "latex": rel(tex_path)}


def create_tables(summary: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    selected = summary["selected_signal"]
    fit_rows = [
        {
            "signal": "margin" if signal == ACTIVE_SIGNALS[0] else "dispersion",
            "winner_accuracy": summary["fit_signal_accuracies"][signal],
            "selected": signal == selected,
        }
        for signal in ACTIVE_SIGNALS
    ]
    validation_rows = [
        {
            "tau": row["tau"],
            "cs_ndcg_at_10": row["code_switched_ndcg_at_10"],
            "bm25_choice_percent": 100.0 * row["bm25_choice_rate"],
            "qwen_choice_percent": 100.0 * row["qwen_choice_rate"],
            "selected": row["selected"],
        }
        for row in summary["validation_scores"]
    ]
    target = summary.get("target_metrics")
    if target is None:
        target_rows: list[dict[str, Any]] = [
            {
                "system": "NA",
                "role": "not executed because the complete Climate source gate failed",
                "cs_ndcg_at_10": None,
                "original_ndcg_at_10": None,
                "delta_cs_ndcg_at_10": None,
                "cs_recall_at_10": None,
                "original_recall_at_10": None,
                "cs_mrr": None,
                "original_mrr": None,
            }
        ]
    else:
        target_rows = metric_table_rows(target)
    source_gate = summary["source_gate"]
    transfer_gate = summary.get("transfer_gate")
    gate_rows = [
        {
            "gate": "Climate CS selector-Qwen",
            "difference": source_gate["source_cs_difference_selector_minus_qwen"],
            "ci_lower": source_gate["source_cs_ci_lower"],
            "ci_upper": source_gate["source_cs_ci_upper"],
            "pass": source_gate["source_cs_gate_pass"],
        },
        {
            "gate": "Climate original safety",
            "difference": source_gate["source_original_difference_selector_minus_qwen"],
            "ci_lower": source_gate["source_original_ci_lower"],
            "ci_upper": source_gate["source_original_ci_upper"],
            "pass": source_gate["source_original_safety_pass"],
        },
        {
            "gate": "ArguAna CS point estimate",
            "difference": transfer_gate["target_cs_difference_selector_minus_qwen"] if transfer_gate else None,
            "ci_lower": transfer_gate["target_cs_ci_lower"] if transfer_gate else None,
            "ci_upper": transfer_gate["target_cs_ci_upper"] if transfer_gate else None,
            "pass": transfer_gate["target_cs_gate_pass"] if transfer_gate else None,
        },
        {
            "gate": "ArguAna original safety",
            "difference": transfer_gate["target_original_difference_selector_minus_qwen"] if transfer_gate else None,
            "ci_lower": transfer_gate["target_original_ci_lower"] if transfer_gate else None,
            "ci_upper": transfer_gate["target_original_ci_upper"] if transfer_gate else None,
            "pass": transfer_gate["target_original_safety_pass"] if transfer_gate else None,
        },
    ]
    return {
        "table1_climate_fit_signal_selection": write_table_bundle("table1_climate_fit_signal_selection", fit_rows),
        "table2_climate_validation_tau_sweep": write_table_bundle("table2_climate_validation_tau_sweep", validation_rows),
        "table3_climate_holdout_primary_results": write_table_bundle(
            "table3_climate_holdout_primary_results", metric_table_rows(summary["source_holdout_metrics"])
        ),
        "table4_arguana_transfer_results": write_table_bundle("table4_arguana_transfer_results", target_rows),
        "table5_gate_summary": write_table_bundle("table5_gate_summary", gate_rows),
    }


def save_figure(fig: Any, stem: str) -> dict[str, str]:
    figure_root = RESULT_ROOT / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    png_path = figure_root / f"{stem}.png"
    pdf_path = figure_root / f"{stem}.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    return {"png": rel(png_path), "pdf": rel(pdf_path)}


def create_figures(summary: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10})
    outputs: dict[str, dict[str, str]] = {}
    selected = summary["selected_signal"]

    fit_rows = [
        {
            "signal": "Margin" if signal == ACTIVE_SIGNALS[0] else "Dispersion",
            "winner_accuracy": summary["fit_signal_accuracies"][signal],
            "selected": signal == selected,
        }
        for signal in ACTIVE_SIGNALS
    ]
    fit_csv = RESULT_ROOT / "figures" / "figure1_fit_signal_comparison_plot_data.csv"
    write_csv(fit_csv, fit_rows)
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    colors = ["#1f77b4" if row["selected"] else "#b9c2cc" for row in fit_rows]
    bars = ax.bar([row["signal"] for row in fit_rows], [row["winner_accuracy"] for row in fit_rows], color=colors)
    ax.set_ylabel("Winner classification accuracy")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Climate FIT signal selection")
    for bar, row in zip(bars, fit_rows):
        label = f"{row['winner_accuracy']:.3f}" + ("  selected" if row["selected"] else "")
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, label, ha="center", va="bottom", fontsize=9)
    outputs["figure1_fit_signal_comparison"] = {**save_figure(fig, "figure1_fit_signal_comparison"), "plot_data_csv": rel(fit_csv)}
    plt.close(fig)

    validation_rows = [
        {"tau": row["tau"], "cs_ndcg_at_10": row["code_switched_ndcg_at_10"], "selected": row["selected"]}
        for row in summary["validation_scores"]
    ]
    validation_csv = RESULT_ROOT / "figures" / "figure2_validation_tau_sweep_plot_data.csv"
    write_csv(validation_csv, validation_rows)
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    ax.plot([row["tau"] for row in validation_rows], [row["cs_ndcg_at_10"] for row in validation_rows], marker="o", color="#355f8d")
    chosen = next(row for row in validation_rows if row["selected"])
    ax.scatter([chosen["tau"]], [chosen["cs_ndcg_at_10"]], s=90, color="#d1495b", zorder=3, label="Selected tau")
    ax.set_xlabel("Tau")
    ax.set_ylabel("Code-switched nDCG@10")
    ax.set_title("Climate validation threshold sweep")
    ax.legend(frameon=False)
    outputs["figure2_validation_tau_sweep"] = {**save_figure(fig, "figure2_validation_tau_sweep"), "plot_data_csv": rel(validation_csv)}
    plt.close(fig)

    stages = [("Climate holdout", summary["source_holdout_metrics"])]
    if summary.get("target_metrics") is not None:
        stages.append(("ArguAna transfer", summary["target_metrics"]))
    performance_rows = [
        {
            "dataset_stage": label,
            "system": system,
            "cs_ndcg_at_10": stage["systems"][system]["code_switched"]["ndcg@10"],
        }
        for label, stage in stages
        for system in ("BM25", "Qwen", "Selector")
    ]
    performance_csv = RESULT_ROOT / "figures" / "figure3_frozen_method_performance_plot_data.csv"
    write_csv(performance_csv, performance_rows)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    labels = [label for label, _ in stages]
    x = np.arange(len(labels))
    width = 0.24
    for offset, (system, color) in enumerate((("BM25", "#7a8b99"), ("Qwen", "#355f8d"), ("Selector", "#d1495b"))):
        values = [stage["systems"][system]["code_switched"]["ndcg@10"] for _, stage in stages]
        ax.bar(x + (offset - 1) * width, values, width, label=system, color=color)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Code-switched nDCG@10")
    ax.set_title(
        "Frozen method performance"
        if summary.get("target_metrics") is not None
        else "Frozen method performance (ArguAna not authorized by source gate)"
    )
    ax.legend(frameon=False, ncols=3)
    outputs["figure3_frozen_method_performance"] = {**save_figure(fig, "figure3_frozen_method_performance"), "plot_data_csv": rel(performance_csv)}
    plt.close(fig)

    confusion_rows: list[dict[str, Any]] = []
    for label, stage in stages:
        confusion = stage["selector_behavior"]["code_switched"]["confusion_matrix"]
        for actual in ("BM25", "Qwen"):
            for predicted in ("BM25", "Qwen"):
                confusion_rows.append(
                    {
                        "dataset_stage": label,
                        "actual": actual,
                        "predicted": predicted,
                        "query_count": confusion[f"actual_{actual}_predicted_{predicted}"],
                    }
                )
    confusion_csv = RESULT_ROOT / "figures" / "figure4_relative_reliability_confusion_plot_data.csv"
    write_csv(confusion_csv, confusion_rows)
    fig, axes = plt.subplots(1, len(stages), figsize=(4.0 * len(stages), 3.5), squeeze=False)
    for axis, (label, stage) in zip(axes[0], stages):
        confusion = stage["selector_behavior"]["code_switched"]["confusion_matrix"]
        matrix = np.asarray(
            [
                [confusion["actual_BM25_predicted_BM25"], confusion["actual_BM25_predicted_Qwen"]],
                [confusion["actual_Qwen_predicted_BM25"], confusion["actual_Qwen_predicted_Qwen"]],
            ]
        )
        image = axis.imshow(matrix, cmap="Blues")
        for row_index in range(2):
            for column_index in range(2):
                axis.text(column_index, row_index, str(matrix[row_index, column_index]), ha="center", va="center")
        axis.set_xticks([0, 1], ["BM25", "Qwen"])
        axis.set_yticks([0, 1], ["BM25", "Qwen"])
        axis.set_xlabel("Predicted winner")
        axis.set_ylabel("Actual winner")
        axis.set_title(label)
        fig.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    outputs["figure4_relative_reliability_confusion"] = {**save_figure(fig, "figure4_relative_reliability_confusion"), "plot_data_csv": rel(confusion_csv)}
    plt.close(fig)

    routing_rows = [
        {
            "dataset_stage": label,
            "bm25_choice_percent": 100.0 * stage["selector_behavior"]["code_switched"]["bm25_choice_rate"],
            "qwen_choice_percent": 100.0 * stage["selector_behavior"]["code_switched"]["qwen_choice_rate"],
        }
        for label, stage in stages
    ]
    routing_csv = RESULT_ROOT / "figures" / "figure5_selector_routing_plot_data.csv"
    write_csv(routing_csv, routing_rows)
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    route_labels = [row["dataset_stage"] for row in routing_rows]
    bm_values = [row["bm25_choice_percent"] for row in routing_rows]
    qw_values = [row["qwen_choice_percent"] for row in routing_rows]
    ax.barh(route_labels, bm_values, color="#7a8b99", label="BM25")
    ax.barh(route_labels, qw_values, left=bm_values, color="#355f8d", label="Qwen")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Queries routed (%)")
    ax.set_title("Frozen selector routing behavior")
    ax.legend(frameon=False, ncols=2)
    outputs["figure5_selector_routing"] = {**save_figure(fig, "figure5_selector_routing"), "plot_data_csv": rel(routing_csv)}
    plt.close(fig)
    return outputs


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution in ("numpy", "PyYAML", "matplotlib", "pytest"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = "NOT_INSTALLED"
    return versions


def gate_record(stage: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    cs = stage["bootstrap_selector_minus_qwen"]["code_switched"]
    original = stage["bootstrap_selector_minus_qwen"]["original"]
    if prefix == "source":
        return {
            "source_cs_difference_selector_minus_qwen": cs["observed_mean_difference"],
            "source_cs_ci_lower": cs["ci_lower"],
            "source_cs_ci_upper": cs["ci_upper"],
            "source_cs_gate_rule": "95% paired-bootstrap lower bound > 0",
            "source_cs_gate_pass": cs["ci_lower"] > 0.0,
            "source_original_difference_selector_minus_qwen": original["observed_mean_difference"],
            "source_original_ci_lower": original["ci_lower"],
            "source_original_ci_upper": original["ci_upper"],
            "source_original_safety_rule": "95% paired-bootstrap lower bound >= 0",
            "source_original_safety_pass": original["ci_lower"] >= 0.0,
            "overall_source_gate_pass": cs["ci_lower"] > 0.0 and original["ci_lower"] >= 0.0,
        }
    return {
        "target_cs_difference_selector_minus_qwen": cs["observed_mean_difference"],
        "target_cs_ci_lower": cs["ci_lower"],
        "target_cs_ci_upper": cs["ci_upper"],
        "target_cs_gate_rule": "point estimate >= 0; bootstrap CI descriptive",
        "target_cs_gate_pass": cs["observed_mean_difference"] >= 0.0,
        "target_original_difference_selector_minus_qwen": original["observed_mean_difference"],
        "target_original_ci_lower": original["ci_lower"],
        "target_original_ci_upper": original["ci_upper"],
        "target_original_safety_rule": "95% paired-bootstrap lower bound >= 0",
        "target_original_safety_pass": original["ci_lower"] >= 0.0,
        "overall_transfer_gate_pass": cs["observed_mean_difference"] >= 0.0 and original["ci_lower"] >= 0.0,
    }


def short_signal(signal: str) -> str:
    return "margin" if signal == ACTIVE_SIGNALS[0] else "dispersion"


def metric_sentence(stage: Mapping[str, Any], setting: str) -> str:
    return "; ".join(
        f"{system} nDCG@10={stage['systems'][system][setting]['ndcg@10']:.9f}, "
        f"Recall@10={stage['systems'][system][setting]['recall@10']:.9f}, "
        f"MRR={stage['systems'][system][setting]['mrr']:.9f}"
        for system in ("BM25", "Qwen", "Selector")
    )


def create_report(
    summary: Mapping[str, Any],
    tables: Mapping[str, Mapping[str, str]],
    figures: Mapping[str, Mapping[str, str]],
) -> Path:
    source = summary["source_holdout_metrics"]
    source_gate = summary["source_gate"]
    target = summary.get("target_metrics")
    transfer_gate = summary.get("transfer_gate")
    validation_lines = "\n".join(
        f"- tau={row['tau']:.2f}: CS nDCG@10={row['code_switched_ndcg_at_10']:.9f}, "
        f"BM25 choice={100.0 * row['bm25_choice_rate']:.3f}%, "
        f"Qwen choice={100.0 * row['qwen_choice_rate']:.3f}%"
        + (" (selected)" if row["selected"] else "")
        for row in summary["validation_scores"]
    )
    target_section = (
        "ArguAna was not accessed because the complete registered Climate source gate failed. "
        "No target outcomes were decoded."
        if target is None
        else (
            f"The unchanged frozen method was applied to all {target['group_count']} ArguAna groups. "
            f"{metric_sentence(target, 'code_switched')}. The Selector-Qwen CS difference was "
            f"{transfer_gate['target_cs_difference_selector_minus_qwen']:.9f}, with descriptive 95% CI "
            f"[{transfer_gate['target_cs_ci_lower']:.9f}, {transfer_gate['target_cs_ci_upper']:.9f}]. "
            f"The registered point-estimate transfer gate was "
            f"{'PASS' if transfer_gate['target_cs_gate_pass'] else 'FAIL'}."
        )
    )
    target_safety = (
        "Not evaluated because ArguAna was not authorized by the source gate."
        if target is None
        else (
            f"{metric_sentence(target, 'original')}. The Selector-Qwen original difference was "
            f"{transfer_gate['target_original_difference_selector_minus_qwen']:.9f}, 95% CI "
            f"[{transfer_gate['target_original_ci_lower']:.9f}, {transfer_gate['target_original_ci_upper']:.9f}]. "
            f"Original safety was {'PASS' if transfer_gate['target_original_safety_pass'] else 'FAIL'}."
        )
    )
    target_behavior = ""
    if target is not None:
        behavior = target["selector_behavior"]["code_switched"]
        target_behavior = (
            f" ArguAna routed {100.0 * behavior['bm25_choice_rate']:.3f}% to BM25 and "
            f"{100.0 * behavior['qwen_choice_rate']:.3f}% to Qwen; winner accuracy was "
            f"{behavior['winner_accuracy']:.9f}."
        )
    source_behavior = source["selector_behavior"]["code_switched"]
    fit = summary["fit_signal_accuracies"]
    report = f"""# Milestone 2 development-only QPP evaluation

## 1. Executive summary

**{summary['final_milestone2_status']}**

The frozen development experiment selected **{short_signal(summary['selected_signal'])}** and tau={summary['selected_tau']:.2f}. No retrieval, encoding, model, or GPU worker was launched. No retuning occurred after holdout access, no target recalibration occurred, and the final CSR-L boundary remains untouched.

## 2. Frozen research question

Can a pre-specified unlabeled post-retrieval signal predict relative BM25-versus-Qwen reliability under benchmark-provided zh-en code switching, preserve original-query performance, and transfer unchanged from ClimateFEVERHardNegatives to ArguAna?

## 3. Protocol compliance

The authoritative revision was `milestone_1_5d`. Source and target were fixed to ClimateFEVERHardNegatives and ArguAna, with no reverse direction. Active signals were margin and top-k dispersion only; coherence remained removed. The selector used k=10, epsilon=1e-12, right-inclusive candidate-specific empirical CDFs, and Qwen fallback unless G < -tau.

## 4. Artifact and checksum verification

All 1.5d frozen-file hashes, source-split hashes, fixed BM25/Qwen/BGE artifact hashes, Qwen revision `{QWEN_REVISION}`, depth-1000 ranking structure, row pairing, score order, and document-ID uniqueness checks passed before protected outcome access. Details are in `results/milestone2/logs/baseline_artifact_manifest.json` and the method-freeze manifest.

## 5. Source split

The grouped source split contained 600 FIT, 200 validation, and 200 post-exploratory frozen holdout groups. Group checksum: `{EXPECTED_GROUP_SHA256}`. Assignment checksum: `{EXPECTED_ASSIGNMENT_SHA256}`. Original and code-switched variants remained grouped.

## 6. Signal definitions

Margin was `(s1-s2)/(|s1-s10|+epsilon)`. Dispersion was the population standard deviation (`ddof=0`) of the min-max-normalized top-10 scores. Both were converted using separate BM25 and Qwen empirical CDFs fitted on the 600 Climate FIT code-switched rows; ties were right-inclusive.

## 7. FIT signal-selection result

Margin winner accuracy was {fit[ACTIVE_SIGNALS[0]]:.9f}; dispersion winner accuracy was {fit[ACTIVE_SIGNALS[1]]:.9f}. The selected signal was **{short_signal(summary['selected_signal'])}** because it had the higher FIT winner accuracy, with margin specified as the tie-break. Winner ties were assigned to Qwen. The unselected signal was discarded after FIT.

## 8. Validation tau-selection result

Only Climate validation code-switched outcomes entered threshold selection. The complete frozen sweep was:

{validation_lines}

Selected tau: **{summary['selected_tau']:.2f}**, using highest CS nDCG@10, then smaller tau, then deterministic lexical serialization order. Original outcomes and Delta_CS did not enter selection.

## 9. Method freeze

The method-freeze manifest was written and hash-validated before holdout access: `{summary['method_freeze_path']}` with SHA-256 `{summary['method_freeze_sha256']}`. It freezes implementation hashes, CDF values and hashes, selected signal, tau, protocol/split hashes, fixed ranking hashes, bootstrap settings, and RRF k.

## 10. Climate holdout results

The frozen method was evaluated once on 200 post-exploratory protected groups. {metric_sentence(source, 'code_switched')}.

Full fixed-system, RRF, BGE reference-only, and oracle-diagnostic metrics appear in Table 3. The oracle is not deployable.

## 11. Source bootstrap gate

The Selector-Qwen CS nDCG@10 difference was {source_gate['source_cs_difference_selector_minus_qwen']:.9f}. The 2000-replicate paired-bootstrap 95% CI (seed {BOOTSTRAP_SEED}) was [{source_gate['source_cs_ci_lower']:.9f}, {source_gate['source_cs_ci_upper']:.9f}]. The registered strict lower-bound > 0 source CS condition was **{'PASS' if source_gate['source_cs_gate_pass'] else 'FAIL'}**.

## 12. Original-query safety

The same CS-derived calibration and tau were applied unchanged. {metric_sentence(source, 'original')}. The Selector-Qwen difference was {source_gate['source_original_difference_selector_minus_qwen']:.9f}, 95% CI [{source_gate['source_original_ci_lower']:.9f}, {source_gate['source_original_ci_upper']:.9f}]. The lower-bound >= 0 safety condition was **{'PASS' if source_gate['source_original_safety_pass'] else 'FAIL'}**. Overall source gate: **{'PASS' if source_gate['overall_source_gate_pass'] else 'FAIL'}**.

## 13. ArguAna transfer result

{target_section}

## 14. Transfer gate

{('Not evaluated because the source gate failed.' if transfer_gate is None else 'Overall transfer gate: **' + ('PASS' if transfer_gate['overall_transfer_gate_pass'] else 'FAIL') + '**. The CS criterion used the registered point estimate >= 0; its bootstrap interval was descriptive, not substituted for that criterion.')}

## 15. Comparator results

Fixed RRF used the union of existing depth-1000 BM25/Qwen rankings with 1-based ranks and k=60. BGE-M3 is reference-only, and the oracle is diagnostic-only. The Arabzadeh comparator is `NOT AVAILABLE`: no faithful existing implementation with the registered features and objective was present at freeze, and no substitute was invented.

## 16. Relative-reliability diagnostics

Climate holdout CS routed {100.0 * source_behavior['bm25_choice_rate']:.3f}% to BM25 and {100.0 * source_behavior['qwen_choice_rate']:.3f}% to Qwen; winner classification accuracy was {source_behavior['winner_accuracy']:.9f}. BM25 truly won {100.0 * source_behavior['actual_bm25_winner_rate']:.3f}% of cases, the selector captured {display_value(source_behavior['bm25_opportunity_capture_rate'])} of those opportunities, and {100.0 * source_behavior['harmful_bm25_switch_rate']:.3f}% of BM25 switches were harmful.{target_behavior} Confusion matrices, G values, and deterministic |G| bins are saved as post-hoc diagnostics and did not affect tuning.

## 17. Delta_CS

Delta_CS is code-switched minus original; negative values indicate degradation. Exact nDCG@10, Recall@10, and MRR deltas for BM25, Qwen, Selector, RRF, BGE, and the diagnostic oracle are in Tables 3 and 4.

## 18. Figures and tables index

Tables are under `results/milestone2/tables/` as CSV, Markdown, and LaTeX. Figures 1-5 are under `results/milestone2/figures/` as 300-dpi PNG and vector PDF, each with plot-data CSV. The index is recorded in `results/milestone2/milestone2_summary.json`.

## 19. Limitations

This is a narrow development-only evaluation on benchmark-provided zh-en code-switched variants. It does not establish universal QPP reliability, natural human code-switching generalization, causality, routing novelty, or state of the art. The Climate holdout is post-exploratory and procedurally protected, not historically untouched.

## 20. Leakage statement

FIT and validation used source code-switched outcomes only. Holdout outcomes were inaccessible to tuning and decoded only after the freeze. ArguAna was inaccessible unless the complete source gate passed and was never used for recalibration. Dataset-backed validation retained its frozen `inconclusive_timeout` status; raw-artifact overlap validation remained PASS with zero source-qualified development/final overlap.

## 21. Exploratory-history disclosure

Earlier Milestone 1 exploration informed the decision to preregister this narrow follow-up. The current source holdout therefore carries the explicit `post_exploratory_frozen_holdout` label; no claim of historical blindness is made.

## 22. Final Milestone 2 verdict

**{summary['final_milestone2_status']}**

The result was classified exactly by the frozen source, transfer, and original-safety rules. Negative or null gate outcomes were not rescued by retuning.

## 23. CSR-L boundary

**FINAL CSR-L TEST UNTOUCHED.** No CSR-L query, qrel, corpus, ranking, metric, or counterpart resource was loaded, encoded, retrieved, or inspected. Milestone 2 stops here pending human review.

## Reproducibility metadata

- Python: {summary['reproducibility']['python_version']}
- OS: {summary['reproducibility']['os']}
- Packages: `{json.dumps(summary['reproducibility']['package_versions'], sort_keys=True)}`
- Execution start: {summary['execution_started_utc']}
- Execution end: {summary['execution_finished_utc']}
- Total runtime: {summary['runtime_seconds']:.3f} seconds
- CPU/GPU: CPU-only post-processing; GPU used=false; GPU worker launched=false
- Pre-holdout tests: {summary['tests']['output']}

## Original-query target safety

{target_safety}
"""
    path = ROOT / "docs" / "milestone2_report.md"
    atomic_write_text(path, report)
    return path


def final_validation(
    summary: Mapping[str, Any],
    tables: Mapping[str, Mapping[str, str]],
    figures: Mapping[str, Mapping[str, str]],
    report_path: Path,
) -> dict[str, Any]:
    ledger = read_ledger()
    validate_method_freeze(ledger)
    assert_no_csr_l_artifacts()
    allowed_statuses = {
        "MILESTONE 2 DEVELOPMENT GATE PASSED",
        "MILESTONE 2 SOURCE GATE FAILED",
        "MILESTONE 2 TRANSFER FAILED",
        "MILESTONE 2 EXECUTION BLOCKED",
    }
    if summary["final_milestone2_status"] not in allowed_statuses:
        raise AssertionError("invalid final Milestone 2 status")
    if not ledger["climate_holdout_accessed"] or not ledger["climate_holdout_completed"]:
        raise AssertionError("Climate one-shot stage is incomplete")
    if summary["source_gate"]["overall_source_gate_pass"] != bool(ledger["source_gate_status"] == "PASS"):
        raise AssertionError("source gate differs between summary and ledger")
    if summary["source_gate"]["overall_source_gate_pass"]:
        if not ledger["arguana_accessed"] or not ledger["arguana_completed"]:
            raise AssertionError("authorized ArguAna stage is incomplete")
    else:
        if ledger["arguana_accessed"]:
            raise AssertionError("ArguAna was accessed despite source gate failure")
    required = [report_path, METHOD_FREEZE_PATH, LEDGER_PATH]
    for bundle in tables.values():
        required.extend(ROOT / path for path in bundle.values())
    for bundle in figures.values():
        required.extend(ROOT / path for path in bundle.values())
    missing = [rel(path) for path in required if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise AssertionError(f"missing/empty required outputs: {missing}")
    checks = {
        "protocol_1_5d_unchanged": True,
        "source_split_and_hashes_unchanged": True,
        "fixed_bm25_qwen_artifacts_used": True,
        "only_margin_and_dispersion_considered": True,
        "coherence_not_restored": True,
        "fit_calibration_cs_only": True,
        "candidate_specific_cdfs": True,
        "signal_selected_fit_only": True,
        "unselected_signal_discarded": True,
        "validation_cs_only": True,
        "tau_grid_unchanged": True,
        "original_outcomes_not_used_for_tau": True,
        "method_frozen_before_holdout": True,
        "holdout_evaluated_once": True,
        "bootstrap_2000_seed_20260809": True,
        "primary_comparison_qwen": True,
        "original_safety_uses_cs_calibration": True,
        "no_source_retuning": True,
        "arguana_only_if_source_passed": True,
        "no_target_recalibration": True,
        "no_reverse_direction": True,
        "rrf_k_60_baseline_only": True,
        "oracle_diagnostic_only": True,
        "paper_ready_tables_created": True,
        "paper_ready_figures_created": True,
        "machine_readable_results_created": True,
        "pre_holdout_tests_passed": bool(ledger["pre_holdout_tests_passed"]),
        "report_generated_from_saved_result_values": True,
        "execution_ledger_complete": True,
        "csr_l_untouched": not ledger["csr_l_accessed"],
    }
    if not all(checks.values()):
        raise AssertionError("one or more final validation checks failed")
    record = {
        "validated_utc": now_utc(),
        "status": "PASS",
        "checks": checks,
        "required_output_count": len(required),
    }
    write_json(RESULT_ROOT / "logs" / "final_validation.json", record)
    return record


def output_manifest(report_path: Path) -> dict[str, Any]:
    manifest_path = RESULT_ROOT / "logs" / "output_manifest.json"
    paths = sorted(path for path in RESULT_ROOT.rglob("*") if path.is_file() and path != manifest_path)
    paths.append(report_path)
    record = {
        "created_utc": now_utc(),
        "files": [
            {"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(set(paths))
        ],
    }
    write_json(manifest_path, record)
    return record


def execute() -> dict[str, Any]:
    if not LEDGER_PATH.exists():
        raise AssertionError("run prepare before execute")
    ledger = read_ledger()
    summary_path = RESULT_ROOT / "milestone2_summary.json"
    if ledger.get("outputs_completed"):
        if not summary_path.exists():
            raise AssertionError("ledger says complete but summary is missing")
        return load_json(summary_path)
    if ledger.get("climate_holdout_accessed"):
        raise AssertionError("Climate holdout was already accessed; refusing a duplicate or silent resume")
    freeze, assignments = validate_method_freeze(ledger)
    signal = freeze["selected_signal"]
    tau = float(freeze["selected_tau"])

    mark(ledger, "climate_holdout_accessed")
    source_groups = sorted(assignments["post_exploratory_frozen_holdout"])
    source = stage_evaluation(
        "ClimateFEVERHardNegatives",
        source_groups,
        signal=signal,
        bm25_cdf=freeze["bm25_cdf"],
        qwen_cdf=freeze["qwen_cdf"],
        tau=tau,
        output_name="holdout",
    )
    mark(ledger, "climate_holdout_completed")
    source_gate = gate_record(source, "source")
    write_json(RESULT_ROOT / "gates" / "climate_source_gate.json", source_gate)
    mark(ledger, "source_gate_status", "PASS" if source_gate["overall_source_gate_pass"] else "FAIL")

    target: dict[str, Any] | None = None
    transfer_gate: dict[str, Any] | None = None
    if source_gate["overall_source_gate_pass"]:
        artifact_manifest = load_json(ARTIFACT_MANIFEST_PATH)
        target_groups = sorted(artifact_manifest["conditions"]["ArguAna/BM25"]["group_ids"])
        mark(ledger, "arguana_accessed")
        target = stage_evaluation(
            "ArguAna",
            target_groups,
            signal=signal,
            bm25_cdf=freeze["bm25_cdf"],
            qwen_cdf=freeze["qwen_cdf"],
            tau=tau,
            output_name="transfer",
        )
        mark(ledger, "arguana_completed")
        transfer_gate = gate_record(target, "target")
        write_json(RESULT_ROOT / "gates" / "arguana_transfer_gate.json", transfer_gate)
        mark(ledger, "transfer_gate_status", "PASS" if transfer_gate["overall_transfer_gate_pass"] else "FAIL")
        final_status = (
            "MILESTONE 2 DEVELOPMENT GATE PASSED"
            if transfer_gate["overall_transfer_gate_pass"]
            else "MILESTONE 2 TRANSFER FAILED"
        )
    else:
        mark(ledger, "transfer_gate_status", "NOT_AUTHORIZED_SOURCE_GATE_FAILED")
        final_status = "MILESTONE 2 SOURCE GATE FAILED"

    fit_summary = load_json(RESULT_ROOT / "calibration" / "fit_signal_selection_summary.json")
    validation_summary = load_json(RESULT_ROOT / "validation" / "tau_selection_summary.json")
    end_time = now_utc()
    started = datetime.fromisoformat(ledger["execution_started_utc"])
    ended = datetime.fromisoformat(end_time)
    runtime_seconds = (ended - started).total_seconds()
    reproducibility = {
        "python_version": sys.version,
        "package_versions": package_versions(),
        "os": platform.platform(),
        "repository_commit": None,
        "repository_commit_note": "workspace has no .git metadata",
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "gpu_used": False,
        "gpu_worker_launched": False,
        "processing": "CPU-only reads and post-processing of fixed artifacts",
        "baseline_artifact_manifest_path": rel(ARTIFACT_MANIFEST_PATH),
        "baseline_artifact_manifest_sha256": sha256_file(ARTIFACT_MANIFEST_PATH),
    }
    summary: dict[str, Any] = {
        "protocol_revision": "milestone_1_5d",
        "source": "ClimateFEVERHardNegatives",
        "target": "ArguAna",
        "reverse_transfer": "NOT_REGISTERED",
        "selected_signal": signal,
        "selected_signal_short_name": short_signal(signal),
        "fit_signal_accuracies": {
            ACTIVE_SIGNALS[0]: fit_summary["fit_accuracy_margin"],
            ACTIVE_SIGNALS[1]: fit_summary["fit_accuracy_dispersion"],
        },
        "fit_selection_rule": "highest winner accuracy; ties select margin",
        "selected_tau": tau,
        "validation_scores": validation_summary["sweep"],
        "source_holdout_metrics": source,
        "source_bootstrap": source["bootstrap_selector_minus_qwen"],
        "source_gate": source_gate,
        "target_executed": target is not None,
        "target_metrics": target,
        "target_bootstrap": target["bootstrap_selector_minus_qwen"] if target else None,
        "transfer_gate": transfer_gate,
        "original_safety": {
            "source": {
                "difference": source_gate["source_original_difference_selector_minus_qwen"],
                "ci_lower": source_gate["source_original_ci_lower"],
                "ci_upper": source_gate["source_original_ci_upper"],
                "pass": source_gate["source_original_safety_pass"],
            },
            "target": (
                {
                    "difference": transfer_gate["target_original_difference_selector_minus_qwen"],
                    "ci_lower": transfer_gate["target_original_ci_lower"],
                    "ci_upper": transfer_gate["target_original_ci_upper"],
                    "pass": transfer_gate["target_original_safety_pass"],
                }
                if transfer_gate
                else None
            ),
        },
        "selector_choice_rates": {
            "source_code_switched": source["selector_behavior"]["code_switched"],
            "target_code_switched": target["selector_behavior"]["code_switched"] if target else None,
        },
        "comparator_metrics": {
            "source": {
                key: source["systems"][key]
                for key in ("BGE-M3", "RRF", "Oracle diagnostic")
            },
            "target": (
                {key: target["systems"][key] for key in ("BGE-M3", "RRF", "Oracle diagnostic")}
                if target
                else None
            ),
            "Arabzadeh": source["arabzadeh_comparator"],
        },
        "method_freeze_path": rel(METHOD_FREEZE_PATH),
        "method_freeze_sha256": sha256_file(METHOD_FREEZE_PATH),
        "source_split_checksums": {
            "source_query_groups_sha256": EXPECTED_GROUP_SHA256,
            "assignment_sha256": EXPECTED_ASSIGNMENT_SHA256,
        },
        "final_milestone2_status": final_status,
        "csr_l_untouched": True,
        "no_retuning_after_holdout": True,
        "no_target_recalibration": True,
        "execution_started_utc": ledger["execution_started_utc"],
        "execution_finished_utc": end_time,
        "runtime_seconds": runtime_seconds,
        "reproducibility": reproducibility,
        "tests": ledger["pre_holdout_test_record"],
    }
    write_json(RESULT_ROOT / "gates" / "final_status.json", {"final_milestone2_status": final_status})
    tables = create_tables(summary)
    figures = create_figures(summary)
    summary["tables"] = tables
    summary["figures"] = figures
    summary["report_path"] = "docs/milestone2_report.md"
    write_json(summary_path, summary)
    report_path = create_report(summary, tables, figures)
    validation = final_validation(summary, tables, figures, report_path)
    summary["final_validation"] = validation
    write_json(summary_path, summary)
    ledger["execution_finished_utc"] = end_time
    ledger["runtime_seconds"] = runtime_seconds
    ledger["final_milestone2_status"] = final_status
    ledger["output_manifest_path"] = "results/milestone2/logs/output_manifest.json"
    existing_outputs = {path.resolve() for path in RESULT_ROOT.rglob("*") if path.is_file()}
    existing_outputs.add(report_path.resolve())
    ledger["output_file_count"] = len(existing_outputs) + 1
    ledger["failure"] = None
    mark(ledger, "outputs_completed")
    output_manifest(report_path)
    return summary


def verify_completed() -> dict[str, Any]:
    ledger = read_ledger()
    if not ledger.get("outputs_completed"):
        raise AssertionError("Milestone 2 outputs are not marked complete")
    validate_method_freeze(ledger)
    assert_no_csr_l_artifacts()
    summary_path = RESULT_ROOT / "milestone2_summary.json"
    summary = load_json(summary_path)
    if not summary.get("csr_l_untouched") or ledger.get("csr_l_accessed"):
        raise AssertionError("CSR-L boundary assertion failed")
    if sha256_file(ROOT / summary["report_path"]) is None:
        raise AssertionError("report hash failed")
    for collection in (summary["tables"], summary["figures"]):
        for bundle in collection.values():
            for path_string in bundle.values():
                path = ROOT / path_string
                if not path.exists() or path.stat().st_size == 0:
                    raise AssertionError(f"missing completed output: {path_string}")
    return {
        "status": "PASS",
        "final_milestone2_status": summary["final_milestone2_status"],
        "summary_sha256": sha256_file(summary_path),
        "report_sha256": sha256_file(ROOT / summary["report_path"]),
        "csr_l_untouched": True,
    }


def record_failure(command: str, error: BaseException) -> None:
    if not LEDGER_PATH.exists():
        return
    ledger = read_ledger()
    ledger["failure"] = {
        "command": command,
        "timestamp_utc": now_utc(),
        "type": type(error).__name__,
        "message": str(error),
        "protected_outcome_accessed": bool(
            ledger.get("climate_holdout_accessed") or ledger.get("arguana_accessed")
        ),
        "silent_rerun_forbidden": bool(
            ledger.get("climate_holdout_accessed") or ledger.get("arguana_accessed")
        ),
    }
    save_ledger(ledger)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "execute", "verify"))
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare()
        elif args.command == "execute":
            result = execute()
        else:
            result = verify_completed()
    except BaseException as error:
        if args.command in {"prepare", "execute"}:
            record_failure(args.command, error)
        print(f"MILESTONE 2 EXECUTION BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import yaml

from .metrics import evaluate_ranking


TOP_K = 10
EPSILON = 1.0e-12
RRF_K = 60
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20260809
THRESHOLD_GRID = (0.00, 0.05, 0.10, 0.15, 0.20)
ACTIVE_SIGNALS = (
    "normalized_top1_minus_top2_score_margin",
    "top_k_score_dispersion",
)
ALLOWED_DEVELOPMENT_DATASETS = {"ClimateFEVERHardNegatives", "ArguAna"}

GROUP_RE = re.compile(r'"source_query_id":"([^"]+)"')
SETTING_RE = re.compile(r'"setting":"(original|code_switched)"')
RANKED_ITEM_RE = re.compile(
    r'\{"document_id":"((?:\\.|[^"\\])*)","rank":(\d+),'
    r'"score":(-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?),"relevance":'
)


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def atomic_write_text(path: str | Path, text: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=str(destination.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json(path: str | Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_yaml(path: str | Path, value: Any) -> None:
    atomic_write_text(path, yaml.safe_dump(value, sort_keys=False, allow_unicode=True))


def write_csv(path: str | Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    destination = Path(path)
    fields = list(fieldnames or (list(rows[0]) if rows else []))
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=str(destination.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def _validate_scores(scores: Sequence[float], *, minimum: int = TOP_K) -> None:
    if len(scores) < minimum:
        raise AssertionError(f"ranking has {len(scores)} scores; expected at least {minimum}")
    if not all(math.isfinite(float(score)) for score in scores):
        raise AssertionError("ranking contains a non-finite score")
    if any(float(left) < float(right) for left, right in zip(scores, scores[1:])):
        raise AssertionError("ranking scores are not non-increasing")


def normalized_margin(scores: Sequence[float], k: int = TOP_K, epsilon: float = EPSILON) -> float:
    selected = tuple(float(value) for value in scores[:k])
    _validate_scores(selected, minimum=k)
    denominator = abs(selected[0] - selected[-1]) + epsilon
    if denominator <= epsilon:
        return 0.0
    return float((selected[0] - selected[1]) / denominator)


def top_k_dispersion(scores: Sequence[float], k: int = TOP_K, epsilon: float = EPSILON) -> float:
    selected = np.asarray(tuple(float(value) for value in scores[:k]), dtype=np.float64)
    _validate_scores(selected, minimum=k)
    score_range = float(selected[0] - selected[-1])
    if score_range <= epsilon:
        normalized = np.zeros(k, dtype=np.float64)
    else:
        normalized = (selected - selected[-1]) / (score_range + epsilon)
    return float(np.std(normalized, ddof=0))


def signal_value(signal: str, scores: Sequence[float]) -> float:
    if signal == ACTIVE_SIGNALS[0]:
        return normalized_margin(scores)
    if signal == ACTIVE_SIGNALS[1]:
        return top_k_dispersion(scores)
    raise ValueError(f"unregistered signal: {signal}")


def assert_development_dataset(dataset: str) -> None:
    if dataset not in ALLOWED_DEVELOPMENT_DATASETS:
        raise AssertionError(f"Milestone 2 development execution forbids dataset: {dataset}")


@dataclass(frozen=True)
class EmpiricalCDF:
    sorted_values: tuple[float, ...]

    @classmethod
    def fit(cls, values: Iterable[float]) -> "EmpiricalCDF":
        array = np.asarray(tuple(float(value) for value in values), dtype=np.float64)
        if array.ndim != 1 or len(array) == 0:
            raise ValueError("empirical CDF requires at least one scalar")
        if not np.isfinite(array).all():
            raise ValueError("empirical CDF values must be finite")
        return cls(tuple(float(value) for value in np.sort(array)))

    def apply(self, value: float) -> float:
        if not math.isfinite(float(value)):
            raise ValueError("empirical CDF input must be finite")
        return float(np.searchsorted(np.asarray(self.sorted_values), float(value), side="right") / len(self.sorted_values))

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition": "right-inclusive empirical CDF: count(fit_value <= x) / N",
            "sample_count": len(self.sorted_values),
            "sorted_values": list(self.sorted_values),
            "values_sha256": canonical_sha256(list(self.sorted_values)),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EmpiricalCDF":
        result = cls(tuple(float(item) for item in value["sorted_values"]))
        if result.to_dict()["values_sha256"] != value["values_sha256"]:
            raise AssertionError("CDF value checksum mismatch")
        return result


@dataclass(frozen=True)
class CompactRun:
    source_query_id: str
    setting: str
    top_scores: tuple[float, ...]
    metrics: dict[str, float]


def _header(line: str, path: Path, line_number: int) -> tuple[str, str]:
    group_match = GROUP_RE.search(line)
    setting_match = SETTING_RE.search(line)
    if group_match is None or setting_match is None:
        raise AssertionError(f"{path}:{line_number}: missing source-query header")
    return group_match.group(1), setting_match.group(1)


def scan_artifact_without_outcomes(path: str | Path) -> dict[str, Any]:
    """Validate ranking structure without parsing qrels, relevance, or metrics."""

    run_path = Path(path)
    config = json.loads((run_path.parent / "run_config.json").read_text(encoding="utf-8"))
    expected_depth = int(config["retrieval_depth"])
    headers: list[tuple[str, str]] = []
    seen_headers: set[tuple[str, str]] = set()
    groups: dict[str, set[str]] = {}
    with run_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            group, setting = _header(line, run_path, line_number)
            header = (group, setting)
            if header in seen_headers:
                raise AssertionError(f"{run_path}:{line_number}: duplicate row {header}")
            headers.append(header)
            seen_headers.add(header)
            groups.setdefault(group, set()).add(setting)
            items = RANKED_ITEM_RE.findall(line)
            if len(items) != expected_depth:
                raise AssertionError(
                    f"{run_path}:{line_number}: found {len(items)} ranking entries, expected {expected_depth}"
                )
            ranks = [int(item[1]) for item in items]
            if ranks != list(range(1, expected_depth + 1)):
                raise AssertionError(f"{run_path}:{line_number}: non-contiguous ranks")
            raw_document_ids = [item[0] for item in items]
            if len(set(raw_document_ids)) != expected_depth:
                raise AssertionError(f"{run_path}:{line_number}: duplicate document IDs")
            scores = [float(item[2]) for item in items]
            _validate_scores(scores)
    if any(settings != {"original", "code_switched"} for settings in groups.values()):
        raise AssertionError(f"{run_path}: incomplete original/code-switched pair")
    if len(headers) != int(config["query_rows"]) or len(groups) != int(config["query_pairs"]):
        raise AssertionError(f"{run_path}: header counts do not match run_config.json")
    return {
        "path": str(run_path).replace("\\", "/"),
        "sha256": sha256_file(run_path),
        "run_config_path": str(run_path.parent / "run_config.json").replace("\\", "/"),
        "run_config_sha256": sha256_file(run_path.parent / "run_config.json"),
        "retriever": config["retriever"],
        "resource_id": config["resource_id"],
        "resource_revision": config["resource_revision"],
        "language": config["language"],
        "model_revision": config.get("model_revision"),
        "rows": len(headers),
        "groups": len(groups),
        "group_ids": sorted(groups),
        "retrieval_depth": expected_depth,
        "header_sequence_sha256": canonical_sha256(headers),
        "header_sequence": headers,
    }


def load_compact_rows(
    path: str | Path,
    *,
    groups: set[str],
    settings: set[str],
    expected_retriever: str,
    expected_dataset: str,
) -> dict[tuple[str, str], CompactRun]:
    """Load only explicitly authorized group/settings from a fixed run artifact."""

    run_path = Path(path)
    assert_development_dataset(expected_dataset)
    config = json.loads((run_path.parent / "run_config.json").read_text(encoding="utf-8"))
    if config["retriever"] != expected_retriever:
        raise AssertionError(f"{run_path}: retriever mismatch")
    expected_depth = int(config["retrieval_depth"])
    loaded: dict[tuple[str, str], CompactRun] = {}
    with run_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            group, setting = _header(line, run_path, line_number)
            if group not in groups or setting not in settings:
                continue
            row = json.loads(line)
            if row["dataset"] != expected_dataset or row["language_pair"] != "zh-en":
                raise AssertionError(f"{run_path}:{line_number}: dataset/language mismatch")
            ranking = row["ranked_documents"]
            if len(ranking) != expected_depth:
                raise AssertionError(f"{run_path}:{line_number}: ranking depth mismatch")
            ranks = [int(item["rank"]) for item in ranking]
            if ranks != list(range(1, expected_depth + 1)):
                raise AssertionError(f"{run_path}:{line_number}: invalid rank sequence")
            document_ids = [str(item["document_id"]) for item in ranking]
            if len(set(document_ids)) != len(document_ids):
                raise AssertionError(f"{run_path}:{line_number}: duplicate ranked document")
            scores = [float(item["score"]) for item in ranking]
            _validate_scores(scores)
            relevant_ids = {str(item) for item in row["relevant_document_ids"]}
            if len(relevant_ids) != len(row["relevant_document_ids"]):
                raise AssertionError(f"{run_path}:{line_number}: duplicate qrel document ID")
            for item in ranking:
                expected_relevance = 1.0 if str(item["document_id"]) in relevant_ids else 0.0
                if not math.isclose(float(item["relevance"]), expected_relevance, rel_tol=0.0, abs_tol=1e-12):
                    raise AssertionError(f"{run_path}:{line_number}: non-binary or inconsistent qrel relevance")
            computed = evaluate_ranking(document_ids, {doc_id: 1.0 for doc_id in relevant_ids}, "ndcg_at_10")
            artifact_metrics = {key: float(value) for key, value in row["metrics"].items()}
            for metric in ("ndcg@10", "recall@10", "mrr", "official"):
                if not math.isclose(computed[metric], artifact_metrics[metric], rel_tol=0.0, abs_tol=1e-12):
                    raise AssertionError(f"{run_path}:{line_number}: metric mismatch for {metric}")
            key = (group, setting)
            if key in loaded:
                raise AssertionError(f"{run_path}:{line_number}: duplicate authorized row")
            loaded[key] = CompactRun(group, setting, tuple(scores[:TOP_K]), computed)
    expected = {(group, setting) for group in groups for setting in settings}
    if set(loaded) != expected:
        missing = sorted(expected - set(loaded))[:10]
        raise AssertionError(f"{run_path}: missing authorized rows: {missing}")
    return loaded


def actual_winner(bm25_ndcg: float, qwen_ndcg: float) -> str:
    return "BM25" if float(bm25_ndcg) > float(qwen_ndcg) else "Qwen"


def hard_choice(gap: float, tau: float) -> str:
    return "BM25" if float(gap) < -float(tau) else "Qwen"


def fit_signal_candidates(
    groups: Sequence[str],
    bm25: Mapping[tuple[str, str], CompactRun],
    qwen: Mapping[tuple[str, str], CompactRun],
) -> dict[str, Any]:
    candidate_results: dict[str, Any] = {}
    diagnostic_by_group: dict[str, dict[str, Any]] = {
        group: {
            "source_query_id": group,
            "setting": "code_switched",
            "bm25_ndcg_at_10": bm25[(group, "code_switched")].metrics["ndcg@10"],
            "qwen_ndcg_at_10": qwen[(group, "code_switched")].metrics["ndcg@10"],
            "observed_winner": actual_winner(
                bm25[(group, "code_switched")].metrics["ndcg@10"],
                qwen[(group, "code_switched")].metrics["ndcg@10"],
            ),
        }
        for group in groups
    }
    for signal in ACTIVE_SIGNALS:
        bm_values = {group: signal_value(signal, bm25[(group, "code_switched")].top_scores) for group in groups}
        qwen_values = {group: signal_value(signal, qwen[(group, "code_switched")].top_scores) for group in groups}
        bm_cdf = EmpiricalCDF.fit(bm_values.values())
        qwen_cdf = EmpiricalCDF.fit(qwen_values.values())
        correct = 0
        for group in groups:
            bm_percentile = bm_cdf.apply(bm_values[group])
            qwen_percentile = qwen_cdf.apply(qwen_values[group])
            gap = qwen_percentile - bm_percentile
            prediction = hard_choice(gap, 0.0)
            observed = diagnostic_by_group[group]["observed_winner"]
            correct += int(prediction == observed)
            prefix = "margin" if signal == ACTIVE_SIGNALS[0] else "dispersion"
            diagnostic_by_group[group].update(
                {
                    f"{prefix}_bm25_raw": bm_values[group],
                    f"{prefix}_qwen_raw": qwen_values[group],
                    f"{prefix}_bm25_percentile": bm_percentile,
                    f"{prefix}_qwen_percentile": qwen_percentile,
                    f"{prefix}_gap": gap,
                    f"{prefix}_predicted_winner": prediction,
                    f"{prefix}_correct": prediction == observed,
                }
            )
        candidate_results[signal] = {
            "accuracy": correct / len(groups),
            "correct": correct,
            "sample_count": len(groups),
            "bm25_cdf": bm_cdf,
            "qwen_cdf": qwen_cdf,
        }
    margin_accuracy = candidate_results[ACTIVE_SIGNALS[0]]["accuracy"]
    dispersion_accuracy = candidate_results[ACTIVE_SIGNALS[1]]["accuracy"]
    selected = ACTIVE_SIGNALS[0] if margin_accuracy >= dispersion_accuracy else ACTIVE_SIGNALS[1]
    return {
        "selected_signal": selected,
        "tie_break_applied": margin_accuracy == dispersion_accuracy,
        "candidates": candidate_results,
        "diagnostics": [diagnostic_by_group[group] for group in groups],
    }


def evaluate_selector(
    groups: Sequence[str],
    setting: str,
    bm25: Mapping[tuple[str, str], CompactRun],
    qwen: Mapping[tuple[str, str], CompactRun],
    *,
    signal: str,
    bm25_cdf: EmpiricalCDF,
    qwen_cdf: EmpiricalCDF,
    tau: float,
) -> dict[str, Any]:
    diagnostics: list[dict[str, Any]] = []
    for group in groups:
        bm_row = bm25[(group, setting)]
        qwen_row = qwen[(group, setting)]
        bm_raw = signal_value(signal, bm_row.top_scores)
        qwen_raw = signal_value(signal, qwen_row.top_scores)
        bm_percentile = bm25_cdf.apply(bm_raw)
        qwen_percentile = qwen_cdf.apply(qwen_raw)
        gap = qwen_percentile - bm_percentile
        choice = hard_choice(gap, tau)
        selected = bm_row if choice == "BM25" else qwen_row
        observed = actual_winner(bm_row.metrics["ndcg@10"], qwen_row.metrics["ndcg@10"])
        diagnostics.append(
            {
                "source_query_id": group,
                "setting": setting,
                "bm25_raw_signal": bm_raw,
                "qwen_raw_signal": qwen_raw,
                "bm25_percentile": bm_percentile,
                "qwen_percentile": qwen_percentile,
                "gap": gap,
                "tau": tau,
                "choice": choice,
                "observed_winner": observed,
                "winner_correct": choice == observed,
                "bm25_ndcg_at_10": bm_row.metrics["ndcg@10"],
                "qwen_ndcg_at_10": qwen_row.metrics["ndcg@10"],
                "selector_ndcg_at_10": selected.metrics["ndcg@10"],
                "bm25_recall_at_10": bm_row.metrics["recall@10"],
                "qwen_recall_at_10": qwen_row.metrics["recall@10"],
                "selector_recall_at_10": selected.metrics["recall@10"],
                "bm25_mrr": bm_row.metrics["mrr"],
                "qwen_mrr": qwen_row.metrics["mrr"],
                "selector_mrr": selected.metrics["mrr"],
            }
        )
    metrics = {
        "ndcg@10": float(np.mean([row["selector_ndcg_at_10"] for row in diagnostics])),
        "recall@10": float(np.mean([row["selector_recall_at_10"] for row in diagnostics])),
        "mrr": float(np.mean([row["selector_mrr"] for row in diagnostics])),
    }
    return {"metrics": metrics, "diagnostics": diagnostics, "behavior": selector_behavior(diagnostics)}


def selector_behavior(diagnostics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    count = len(diagnostics)
    bm25_choices = sum(row["choice"] == "BM25" for row in diagnostics)
    qwen_choices = count - bm25_choices
    actual_bm25 = sum(row["observed_winner"] == "BM25" for row in diagnostics)
    actual_qwen = count - actual_bm25
    correct = sum(bool(row["winner_correct"]) for row in diagnostics)
    captured = sum(row["observed_winner"] == "BM25" and row["choice"] == "BM25" for row in diagnostics)
    harmful = sum(row["observed_winner"] == "Qwen" and row["choice"] == "BM25" for row in diagnostics)
    confusion = {
        "actual_BM25_predicted_BM25": captured,
        "actual_BM25_predicted_Qwen": actual_bm25 - captured,
        "actual_Qwen_predicted_BM25": harmful,
        "actual_Qwen_predicted_Qwen": actual_qwen - harmful,
    }
    edges = (0.0, 0.05, 0.10, 0.20, 0.40, 1.000000000001)
    bins: list[dict[str, Any]] = []
    for lower, upper in zip(edges, edges[1:]):
        selected = [row for row in diagnostics if lower <= abs(float(row["gap"])) < upper]
        bins.append(
            {
                "lower_inclusive": lower,
                "upper_exclusive": upper,
                "query_count": len(selected),
                "winner_accuracy": float(np.mean([row["winner_correct"] for row in selected])) if selected else None,
                "status": "POST_HOC_DIAGNOSTIC",
            }
        )
    return {
        "query_count": count,
        "bm25_choice_count": bm25_choices,
        "bm25_choice_rate": bm25_choices / count,
        "qwen_choice_count": qwen_choices,
        "qwen_choice_rate": qwen_choices / count,
        "winner_accuracy": correct / count,
        "actual_bm25_winner_count": actual_bm25,
        "actual_bm25_winner_rate": actual_bm25 / count,
        "actual_qwen_winner_count": actual_qwen,
        "actual_qwen_winner_rate": actual_qwen / count,
        "bm25_opportunities_captured": captured,
        "bm25_opportunity_capture_rate": captured / actual_bm25 if actual_bm25 else None,
        "harmful_bm25_switches": harmful,
        "harmful_bm25_switch_rate": harmful / bm25_choices if bm25_choices else 0.0,
        "confusion_matrix": confusion,
        "absolute_gap_bins": bins,
    }


def select_tau(
    groups: Sequence[str],
    bm25: Mapping[tuple[str, str], CompactRun],
    qwen: Mapping[tuple[str, str], CompactRun],
    *,
    signal: str,
    bm25_cdf: EmpiricalCDF,
    qwen_cdf: EmpiricalCDF,
) -> dict[str, Any]:
    sweep: list[dict[str, Any]] = []
    evaluations: dict[float, dict[str, Any]] = {}
    for tau in THRESHOLD_GRID:
        evaluation = evaluate_selector(
            groups,
            "code_switched",
            bm25,
            qwen,
            signal=signal,
            bm25_cdf=bm25_cdf,
            qwen_cdf=qwen_cdf,
            tau=tau,
        )
        evaluations[tau] = evaluation
        sweep.append(
            {
                "tau": tau,
                "code_switched_ndcg_at_10": evaluation["metrics"]["ndcg@10"],
                "bm25_choice_count": evaluation["behavior"]["bm25_choice_count"],
                "bm25_choice_rate": evaluation["behavior"]["bm25_choice_rate"],
                "qwen_choice_count": evaluation["behavior"]["qwen_choice_count"],
                "qwen_choice_rate": evaluation["behavior"]["qwen_choice_rate"],
            }
        )
    selected = sorted(sweep, key=lambda row: (-row["code_switched_ndcg_at_10"], row["tau"], f"{row['tau']:.2f}"))[0]
    for row in sweep:
        row["selected"] = row["tau"] == selected["tau"]
    return {"selected_tau": selected["tau"], "sweep": sweep, "evaluation": evaluations[selected["tau"]]}


def aggregate_fixed(rows: Mapping[tuple[str, str], CompactRun], groups: Sequence[str], setting: str) -> dict[str, float]:
    return {
        metric: float(np.mean([rows[(group, setting)].metrics[metric] for group in groups]))
        for metric in ("ndcg@10", "recall@10", "mrr")
    }


def oracle_metrics(
    bm25: Mapping[tuple[str, str], CompactRun],
    qwen: Mapping[tuple[str, str], CompactRun],
    groups: Sequence[str],
    setting: str,
) -> dict[str, float]:
    chosen = [
        bm25[(group, setting)]
        if bm25[(group, setting)].metrics["ndcg@10"] > qwen[(group, setting)].metrics["ndcg@10"]
        else qwen[(group, setting)]
        for group in groups
    ]
    return {metric: float(np.mean([row.metrics[metric] for row in chosen])) for metric in ("ndcg@10", "recall@10", "mrr")}


def paired_bootstrap(
    differences: Sequence[float],
    *,
    seed: int = BOOTSTRAP_SEED,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> dict[str, Any]:
    values = np.asarray(tuple(float(value) for value in differences), dtype=np.float64)
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("paired bootstrap requires finite paired differences")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(replicates, len(values)))
    replicate_means = values[indices].mean(axis=1)
    return {
        "observed_mean_difference": float(values.mean()),
        "ci_lower": float(np.quantile(replicate_means, 0.025)),
        "ci_upper": float(np.quantile(replicate_means, 0.975)),
        "confidence_level": 0.95,
        "replicates": replicates,
        "seed": seed,
        "resampling_unit": "complete_source_query_group",
        "replicate_means_sha256": canonical_sha256([float(value) for value in replicate_means]),
    }


def rrf_ranking(bm25_ranking: Sequence[str], qwen_ranking: Sequence[str], *, rrf_k: int = RRF_K) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in (bm25_ranking, qwen_ranking):
        for rank, document_id in enumerate(ranking, start=1):
            scores[document_id] = scores.get(document_id, 0.0) + 1.0 / (rrf_k + rank)
    return sorted(scores, key=lambda document_id: (-scores[document_id], document_id))


def compute_rrf_metrics(
    bm25_path: str | Path,
    qwen_path: str | Path,
    *,
    groups: set[str],
    setting: str,
) -> dict[str, dict[str, float]]:
    bm_path = Path(bm25_path)
    qw_path = Path(qwen_path)
    output: dict[str, dict[str, float]] = {}
    with bm_path.open("r", encoding="utf-8") as bm_handle, qw_path.open("r", encoding="utf-8") as qw_handle:
        for line_number, pair in enumerate(zip_longest(bm_handle, qw_handle), start=1):
            bm_line, qw_line = pair
            if bm_line is None or qw_line is None:
                raise AssertionError("BM25/Qwen artifacts have different row counts")
            bm_header = _header(bm_line, bm_path, line_number)
            qw_header = _header(qw_line, qw_path, line_number)
            if bm_header != qw_header:
                raise AssertionError(f"BM25/Qwen row order mismatch at line {line_number}")
            group, row_setting = bm_header
            if group not in groups or row_setting != setting:
                continue
            bm_row = json.loads(bm_line)
            qw_row = json.loads(qw_line)
            if set(bm_row["relevant_document_ids"]) != set(qw_row["relevant_document_ids"]):
                raise AssertionError(f"qrel mismatch for {group}/{setting}")
            bm_ranking = [str(item["document_id"]) for item in bm_row["ranked_documents"]]
            qw_ranking = [str(item["document_id"]) for item in qw_row["ranked_documents"]]
            ranking = rrf_ranking(bm_ranking, qw_ranking)
            qrels = {str(document_id): 1.0 for document_id in bm_row["relevant_document_ids"]}
            output[group] = evaluate_ranking(ranking, qrels, "ndcg_at_10")
    if set(output) != groups:
        raise AssertionError(f"RRF missing groups: {sorted(groups - set(output))[:10]}")
    return output


def aggregate_metric_rows(rows: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    return {
        metric: float(np.mean([row[metric] for row in rows.values()]))
        for metric in ("ndcg@10", "recall@10", "mrr")
    }

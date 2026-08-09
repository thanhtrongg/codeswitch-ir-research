"""Generate the Milestone 2.5 saved-data-only scientific postmortem.

This script intentionally reads only the already-saved Milestone 2 Climate
diagnostics and frozen prior-work documents. It has no retriever, model,
dataset, target-outcome, or GPU entry point. In particular, it never opens an
ArguAna ranking artifact or any CSR-L resource.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import yaml

from csr_ir.milestone2 import atomic_write_text, write_csv, write_json


ROOT = Path(__file__).resolve().parents[1]
M2_ROOT = ROOT / "results" / "milestone2"
OUT_ROOT = ROOT / "results" / "milestone2_5"
SUMMARY_PATH = OUT_ROOT / "milestone2_5_summary.json"
REPORT_PATH = ROOT / "docs" / "milestone2_5_scientific_postmortem.md"
TAU = 0.20
ANALYSIS_STATUS = "POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA"

PRIOR_WORK_FILES = (
    ROOT / "docs" / "milestone1_5_decision.md",
    ROOT / "docs" / "novelty_audit_m1_5.md",
    ROOT / "docs" / "claim_novelty_matrix.md",
    ROOT / "docs" / "complementarity_interpretation_m1_5.md",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: str | Path) -> str:
    return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_yaml(path: str | Path) -> Any:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def f(value: str | int | float | bool | None) -> float:
    return float(value)  # type: ignore[arg-type]


def finite_values(values: Iterable[float]) -> np.ndarray:
    array = np.asarray(tuple(float(value) for value in values), dtype=np.float64)
    if array.ndim != 1 or len(array) == 0 or not np.isfinite(array).all():
        raise AssertionError("postmortem values must be a non-empty finite vector")
    return array


def scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): scalar(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [scalar(item) for item in value]
    return value


def stats(values: Iterable[float]) -> dict[str, Any]:
    array = finite_values(values)
    return {
        "n": int(len(array)),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "std_ddof0": float(np.std(array, ddof=0)),
        "q1": float(np.quantile(array, 0.25)),
        "q3": float(np.quantile(array, 0.75)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


def average_ranks(values: Sequence[float]) -> np.ndarray:
    array = finite_values(values)
    order = np.argsort(array, kind="mergesort")
    ranks = np.empty(len(array), dtype=np.float64)
    index = 0
    while index < len(array):
        end = index + 1
        while end < len(array) and array[order[end]] == array[order[index]]:
            end += 1
        ranks[order[index:end]] = (index + 1 + end) / 2.0
        index = end
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) == 0:
        raise AssertionError("rank-correlation vectors must have equal non-zero length")
    rx = average_ranks(x)
    ry = average_ranks(y)
    if np.std(rx) == 0.0 or np.std(ry) == 0.0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def auroc_positive(y_true: Sequence[bool], scores: Sequence[float]) -> float | None:
    labels = np.asarray(tuple(bool(value) for value in y_true), dtype=bool)
    values = finite_values(scores)
    positives = int(labels.sum())
    negatives = int(len(labels) - positives)
    if positives == 0 or negatives == 0:
        return None
    positive_scores = values[labels]
    negative_scores = values[~labels]
    comparisons = positive_scores[:, None] - negative_scores[None, :]
    return float((np.sum(comparisons > 0.0) + 0.5 * np.sum(comparisons == 0.0)) / (positives * negatives))


def classification_metrics(rows: Sequence[Mapping[str, str]], predicted_field: str) -> dict[str, Any]:
    actual_bm25 = np.asarray([row["observed_winner"] == "BM25" for row in rows], dtype=bool)
    predicted_bm25 = np.asarray([row[predicted_field] == "BM25" for row in rows], dtype=bool)
    tp = int(np.sum(actual_bm25 & predicted_bm25))
    fp = int(np.sum(~actual_bm25 & predicted_bm25))
    fn = int(np.sum(actual_bm25 & ~predicted_bm25))
    tn = int(np.sum(~actual_bm25 & ~predicted_bm25))
    actual_bm25_count = tp + fn
    actual_qwen_count = tn + fp
    predicted_bm25_count = tp + fp
    accuracy = (tp + tn) / len(rows)
    precision = tp / predicted_bm25_count if predicted_bm25_count else None
    recall = tp / actual_bm25_count if actual_bm25_count else None
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    specificity = tn / actual_qwen_count if actual_qwen_count else None
    balanced = (recall + specificity) / 2.0 if recall is not None and specificity is not None else None
    mcc_denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / mcc_denominator if mcc_denominator else None
    majority = max(actual_bm25_count, actual_qwen_count) / len(rows)
    return {
        "n": len(rows),
        "accuracy": accuracy,
        "actual_bm25_winner_count": actual_bm25_count,
        "actual_bm25_winner_rate": actual_bm25_count / len(rows),
        "actual_qwen_winner_count": actual_qwen_count,
        "actual_qwen_winner_rate": actual_qwen_count / len(rows),
        "majority_class": "BM25" if actual_bm25_count > actual_qwen_count else "Qwen",
        "majority_baseline_accuracy": majority,
        "improvement_over_majority": accuracy - majority,
        "balanced_accuracy": balanced,
        "bm25_precision": precision,
        "bm25_recall": recall,
        "bm25_f1": f1,
        "matthews_correlation_coefficient": mcc,
        "confusion_matrix": {
            "actual_BM25_predicted_BM25": tp,
            "actual_BM25_predicted_Qwen": fn,
            "actual_Qwen_predicted_BM25": fp,
            "actual_Qwen_predicted_Qwen": tn,
        },
    }


def signal_posthoc_metrics(rows: Sequence[Mapping[str, str]], gap_field: str, predicted_field: str) -> dict[str, Any]:
    g_values = [f(row[gap_field]) for row in rows]
    qwen_minus_bm25 = [f(row["qwen_ndcg_at_10"]) - f(row["bm25_ndcg_at_10"]) for row in rows]
    bm25_winner = [row["observed_winner"] == "BM25" for row in rows]
    result = classification_metrics(rows, predicted_field)
    result.update(
        {
            "auroc_for_BM25_winner_using_minus_G": auroc_positive(bm25_winner, [-value for value in g_values]),
            "spearman_G_vs_Qwen_minus_BM25_ndcg_at_10": spearman(g_values, qwen_minus_bm25),
            "spearman_minus_G_vs_BM25_minus_Qwen_ndcg_at_10": spearman(
                [-value for value in g_values], [-value for value in qwen_minus_bm25]
            ),
            "diagnostic_label": ANALYSIS_STATUS,
        }
    )
    return result


def ks_statistic(first: Sequence[float], second: Sequence[float]) -> float:
    a = np.sort(finite_values(first))
    b = np.sort(finite_values(second))
    points = np.sort(np.concatenate((a, b)))
    cdf_a = np.searchsorted(a, points, side="right") / len(a)
    cdf_b = np.searchsorted(b, points, side="right") / len(b)
    return float(np.max(np.abs(cdf_a - cdf_b)))


def wasserstein_1d(first: Sequence[float], second: Sequence[float]) -> float:
    a = np.sort(finite_values(first))
    b = np.sort(finite_values(second))
    points = np.sort(np.unique(np.concatenate((a, b))))
    cdf_a = 0.0
    cdf_b = 0.0
    previous = float(points[0])
    area = 0.0
    for point in points:
        point = float(point)
        area += abs(cdf_a - cdf_b) * (point - previous)
        cdf_a = float(np.searchsorted(a, point, side="right") / len(a))
        cdf_b = float(np.searchsorted(b, point, side="right") / len(b))
        previous = point
    return float(area)


def split_signal_stats(rows: Sequence[Mapping[str, str]], *, raw_bm25: str, raw_qwen: str, gap: str) -> dict[str, Any]:
    g = [f(row[gap]) for row in rows]
    result = {
        "n": len(rows),
        "raw_BM25": stats(f(row[raw_bm25]) for row in rows),
        "raw_Qwen": stats(f(row[raw_qwen]) for row in rows),
        "G": stats(g),
        "percentage_G_lt_negative_tau": 100.0 * sum(value < -TAU for value in g) / len(g),
        "tau": TAU,
        "diagnostic_label": ANALYSIS_STATUS,
    }
    return result


def holdout_decomposition(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    categories = {
        "beneficial_BM25_switches": lambda row: row["choice"] == "BM25" and row["observed_winner"] == "BM25",
        "harmful_BM25_switches": lambda row: row["choice"] == "BM25" and row["observed_winner"] == "Qwen",
        "correct_Qwen_keeps": lambda row: row["choice"] == "Qwen" and row["observed_winner"] == "Qwen",
        "missed_BM25_opportunities": lambda row: row["choice"] == "Qwen" and row["observed_winner"] == "BM25",
    }
    records: list[dict[str, Any]] = []
    for name, predicate in categories.items():
        selected = [row for row in rows if predicate(row)]
        signed_effect = [f(row["bm25_ndcg_at_10"]) - f(row["qwen_ndcg_at_10"]) for row in selected]
        if name == "harmful_BM25_switches":
            opportunity_values = [-value for value in signed_effect]
            interpretation = "Qwen-minus-BM25 loss from an incorrect BM25 switch"
        elif name == "correct_Qwen_keeps":
            opportunity_values = [-value for value in signed_effect]
            interpretation = "Qwen-minus-BM25 advantage retained by the Qwen fallback"
        else:
            opportunity_values = signed_effect
            interpretation = (
                "BM25-minus-Qwen gain from a beneficial switch"
                if name == "beneficial_BM25_switches"
                else "BM25-minus-Qwen gain left unrealized by a missed opportunity"
            )
        records.append(
            {
                "category": name,
                "count": len(selected),
                "percentage_of_holdout": 100.0 * len(selected) / len(rows),
                "mean_signed_BM25_minus_Qwen_ndcg_at_10": float(np.mean(signed_effect)) if selected else None,
                "total_signed_BM25_minus_Qwen_ndcg_at_10": float(np.sum(signed_effect)) if selected else None,
                "mean_gain_or_loss_ndcg_at_10": float(np.mean(opportunity_values)) if selected else None,
                "total_gain_or_loss_ndcg_at_10": float(np.sum(opportunity_values)) if selected else None,
                "interpretation": interpretation,
                "diagnostic_label": ANALYSIS_STATUS,
            }
        )
    beneficial = records[0]
    harmful = records[1]
    missed = records[3]
    switch_count = beneficial["count"] + harmful["count"]
    opportunity_count = beneficial["count"] + missed["count"]
    return {
        "categories": records,
        "beneficial_switch_count": records[0]["count"],
        "harmful_switch_count": records[1]["count"],
        "correct_qwen_keep_count": records[2]["count"],
        "missed_opportunity_count": records[3]["count"],
        "bm25_switch_count": switch_count,
        "bm25_switch_precision": beneficial["count"] / switch_count,
        "bm25_opportunity_count": opportunity_count,
        "bm25_opportunity_recall": beneficial["count"] / opportunity_count,
        "harmful_switch_rate": harmful["count"] / switch_count,
        "missed_opportunity_rate": missed["count"] / opportunity_count,
        "beneficial_gain_total": beneficial["total_gain_or_loss_ndcg_at_10"],
        "beneficial_gain_mean": beneficial["mean_gain_or_loss_ndcg_at_10"],
        "harmful_loss_total": harmful["total_gain_or_loss_ndcg_at_10"],
        "harmful_loss_mean": harmful["mean_gain_or_loss_ndcg_at_10"],
        "missed_gain_total": missed["total_gain_or_loss_ndcg_at_10"],
        "missed_gain_mean": missed["mean_gain_or_loss_ndcg_at_10"],
        "diagnostic_label": ANALYSIS_STATUS,
    }


def table_markdown(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "NA\n"
    fields = list(rows[0])
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        values = []
        for field in fields:
            value = row.get(field)
            if value is None:
                rendered = "NA"
            elif isinstance(value, float):
                rendered = f"{value:.9f}"
            else:
                rendered = str(value)
            values.append(rendered.replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def latex_escape(value: Any) -> str:
    rendered = "NA" if value is None else (f"{value:.9f}" if isinstance(value, float) else str(value))
    return rendered.replace("\\", "\\textbackslash{}").replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")


def table_latex(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "% NA\n"
    fields = list(rows[0])
    lines = [f"\\begin{{tabular}}{{{'l' * len(fields)}}}", "\\toprule"]
    lines.append(" & ".join(latex_escape(field) for field in fields) + " \\\\")
    lines.append("\\midrule")
    for row in rows:
        lines.append(" & ".join(latex_escape(row.get(field)) for field in fields) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    return "\n".join(lines) + "\n"


def write_table_bundle(name: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    root = OUT_ROOT / "tables"
    csv_path = root / f"{name}.csv"
    md_path = root / f"{name}.md"
    tex_path = root / f"{name}.tex"
    write_csv(csv_path, [scalar(row) for row in rows])
    atomic_write_text(md_path, table_markdown(rows))
    atomic_write_text(tex_path, table_latex(rows))
    return {"csv": rel(csv_path), "markdown": rel(md_path), "latex": rel(tex_path)}


def save_figure(fig: Any, name: str) -> dict[str, str]:
    root = OUT_ROOT / "figures"
    png = root / f"{name}.png"
    pdf = root / f"{name}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    return {"png": rel(png), "pdf": rel(pdf)}


def create_figures(
    holdout: Sequence[Mapping[str, str]],
    split_rows: Mapping[str, Sequence[Mapping[str, str]]],
    decomposition: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10})
    result: dict[str, dict[str, str]] = {}

    confusion_rows: list[dict[str, Any]] = []
    for actual in ("BM25", "Qwen"):
        for predicted in ("BM25", "Qwen"):
            count = sum(row["observed_winner"] == actual and row["choice"] == predicted for row in holdout)
            confusion_rows.append(
                {
                    "actual_winner": actual,
                    "predicted_winner": predicted,
                    "count": count,
                    "percentage": 100.0 * count / len(holdout),
                    "analysis_status": ANALYSIS_STATUS,
                }
            )
    confusion_csv = OUT_ROOT / "figures" / "figure1_holdout_confusion_plot_data.csv"
    write_csv(confusion_csv, confusion_rows)
    fig, ax = plt.subplots(figsize=(4.8, 4.0))
    matrix = np.asarray(
        [
            [confusion_rows[0]["count"], confusion_rows[1]["count"]],
            [confusion_rows[2]["count"], confusion_rows[3]["count"]],
        ]
    )
    image = ax.imshow(matrix, cmap="Blues")
    for row_index in range(2):
        for column_index in range(2):
            ax.text(column_index, row_index, str(matrix[row_index, column_index]), ha="center", va="center")
    ax.set_xticks([0, 1], ["BM25", "Qwen"])
    ax.set_yticks([0, 1], ["BM25", "Qwen"])
    ax.set_xlabel("Selector prediction")
    ax.set_ylabel("Actual winner")
    ax.set_title("POST-HOC: Climate holdout routing")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    result["figure1_holdout_confusion"] = {**save_figure(fig, "figure1_holdout_confusion"), "plot_data_csv": rel(confusion_csv)}
    plt.close(fig)

    scatter_rows = [
        {
            "source_query_id": row["source_query_id"],
            "G": f(row["gap"]),
            "bm25_minus_qwen_ndcg_at_10": f(row["bm25_ndcg_at_10"]) - f(row["qwen_ndcg_at_10"]),
            "actual_winner": row["observed_winner"],
            "analysis_status": ANALYSIS_STATUS,
        }
        for row in holdout
    ]
    scatter_csv = OUT_ROOT / "figures" / "figure2_G_vs_actual_gain_plot_data.csv"
    write_csv(scatter_csv, scatter_rows)
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    colors = ["#d1495b" if row["actual_winner"] == "BM25" else "#355f8d" for row in scatter_rows]
    ax.scatter([row["G"] for row in scatter_rows], [row["bm25_minus_qwen_ndcg_at_10"] for row in scatter_rows], c=colors, alpha=0.65, s=22)
    ax.axvline(-TAU, color="#555555", linestyle="--", linewidth=1, label="Frozen BM25 boundary")
    ax.axhline(0.0, color="#999999", linewidth=0.8)
    ax.set_xlabel("Frozen normalized gap G")
    ax.set_ylabel("BM25 - Qwen nDCG@10")
    ax.set_title("POST-HOC: confidence gap vs actual advantage")
    ax.legend(frameon=False, fontsize=8)
    result["figure2_G_vs_actual_gain"] = {**save_figure(fig, "figure2_G_vs_actual_gain"), "plot_data_csv": rel(scatter_csv)}
    plt.close(fig)

    distribution_rows: list[dict[str, Any]] = []
    for split_name, rows in split_rows.items():
        for row in rows:
            distribution_rows.append(
                {
                    "split": split_name,
                    "source_query_id": row["source_query_id"],
                    "G": f(row["margin_gap"] if "margin_gap" in row else row["gap"]),
                    "analysis_status": ANALYSIS_STATUS,
                }
            )
    distribution_csv = OUT_ROOT / "figures" / "figure3_G_distributions_plot_data.csv"
    write_csv(distribution_csv, distribution_rows)
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    for split_name, color in (("FIT", "#7a8b99"), ("VALIDATION", "#355f8d"), ("HOLDOUT", "#d1495b")):
        values = [row["G"] for row in distribution_rows if row["split"] == split_name]
        ax.hist(values, bins=24, alpha=0.45, label=split_name, color=color, density=True)
    ax.axvline(-TAU, color="#555555", linestyle="--", linewidth=1, label="-tau")
    ax.set_xlabel("Normalized gap G")
    ax.set_ylabel("Density")
    ax.set_title("POST-HOC: FIT / validation / holdout G distributions")
    ax.legend(frameon=False, fontsize=8)
    result["figure3_G_distributions"] = {**save_figure(fig, "figure3_G_distributions"), "plot_data_csv": rel(distribution_csv)}
    plt.close(fig)

    opportunity_rows = [
        {
            "category": row["category"],
            "count": row["count"],
            "percentage": row["percentage_of_holdout"],
            "analysis_status": ANALYSIS_STATUS,
        }
        for row in decomposition["categories"]
    ]
    opportunity_csv = OUT_ROOT / "figures" / "figure4_opportunity_capture_plot_data.csv"
    write_csv(opportunity_csv, opportunity_rows)
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    labels = [row["category"].replace("_", "\n") for row in opportunity_rows]
    colors = ["#4c956c", "#d1495b", "#355f8d", "#e09f3e"]
    bars = ax.bar(labels, [row["count"] for row in opportunity_rows], color=colors)
    ax.set_ylabel("Query count")
    ax.set_title("POST-HOC: BM25 opportunity and switching decomposition")
    for bar, row in zip(bars, opportunity_rows):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, str(row["count"]), ha="center", va="bottom")
    result["figure4_opportunity_capture"] = {**save_figure(fig, "figure4_opportunity_capture"), "plot_data_csv": rel(opportunity_csv)}
    plt.close(fig)
    return result


def verify_milestone2_record() -> dict[str, Any]:
    summary = read_json(M2_ROOT / "milestone2_summary.json")
    ledger = read_yaml(M2_ROOT / "execution_ledger.yaml")
    gate = read_json(M2_ROOT / "gates" / "climate_source_gate.json")
    if summary["final_milestone2_status"] != "MILESTONE 2 SOURCE GATE FAILED":
        raise AssertionError("saved Milestone 2 verdict changed")
    expected = {
        "selected_signal": "normalized_top1_minus_top2_score_margin",
        "selected_tau": 0.2,
        "source": "ClimateFEVERHardNegatives",
        "target": "ArguAna",
    }
    for key, value in expected.items():
        if summary[key] != value:
            raise AssertionError(f"saved Milestone 2 value changed: {key}")
    if ledger["arguana_accessed"] or ledger["arguana_completed"] or summary["target_executed"]:
        raise AssertionError("saved record indicates ArguAna evaluation")
    if ledger["csr_l_accessed"] or not summary["csr_l_untouched"]:
        raise AssertionError("saved record indicates CSR-L access")
    source = summary["source_holdout_metrics"]
    checks = {
        "source_selector_ndcg": math.isclose(source["systems"]["Selector"]["code_switched"]["ndcg@10"], 0.18251742266413287, abs_tol=1e-12),
        "source_qwen_ndcg": math.isclose(source["systems"]["Qwen"]["code_switched"]["ndcg@10"], 0.19607871770934174, abs_tol=1e-12),
        "source_diff": math.isclose(gate["source_cs_difference_selector_minus_qwen"], -0.01356129504520883, abs_tol=1e-12),
        "source_ci": math.isclose(gate["source_cs_ci_lower"], -0.032543918000253934, abs_tol=1e-12) and math.isclose(gate["source_cs_ci_upper"], 0.0048113375672271955, abs_tol=1e-12),
        "original_diff": math.isclose(gate["source_original_difference_selector_minus_qwen"], -0.01487788451846475, abs_tol=1e-12),
        "routing": source["selector_behavior"]["code_switched"]["bm25_choice_count"] == 68 and source["selector_behavior"]["code_switched"]["qwen_choice_count"] == 132,
    }
    if not all(checks.values()):
        raise AssertionError(f"saved Milestone 2 headline discrepancy: {checks}")
    output_manifest_path = M2_ROOT / "logs" / "output_manifest.json"
    output_manifest = read_json(output_manifest_path)
    bad_files: list[str] = []
    for item in output_manifest["files"]:
        path = ROOT / item["path"]
        if not path.exists() or sha256_file(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            bad_files.append(item["path"])
    if bad_files:
        raise AssertionError(f"original Milestone 2 artifacts changed: {bad_files}")
    return {
        "summary": summary,
        "ledger": ledger,
        "gate": gate,
        "output_manifest_sha256": sha256_file(output_manifest_path),
        "output_manifest_entry_count": len(output_manifest["files"]),
        "headline_checks": checks,
    }


def fit_table_rows(fit_rows: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for signal, predicted, gap in (
        ("margin", "margin_predicted_winner", "margin_gap"),
        ("dispersion", "dispersion_predicted_winner", "dispersion_gap"),
    ):
        diagnostics = signal_posthoc_metrics(fit_rows, gap, predicted)
        rows.append(
            {
                "signal": signal,
                "winner_accuracy": diagnostics["accuracy"],
                "majority_baseline": diagnostics["majority_baseline_accuracy"],
                "improvement_over_majority": diagnostics["improvement_over_majority"],
                "balanced_accuracy": diagnostics["balanced_accuracy"],
                "BM25_precision": diagnostics["bm25_precision"],
                "BM25_recall": diagnostics["bm25_recall"],
                "BM25_F1": diagnostics["bm25_f1"],
                "MCC": diagnostics["matthews_correlation_coefficient"],
                "actual_BM25_count": diagnostics["actual_bm25_winner_count"],
                "actual_Qwen_count": diagnostics["actual_qwen_winner_count"],
                "POSTHOC_AUROC_BM25": diagnostics["auroc_for_BM25_winner_using_minus_G"],
                "POSTHOC_Spearman_G_vs_Qwen_minus_BM25": diagnostics["spearman_G_vs_Qwen_minus_BM25_ndcg_at_10"],
                "diagnostic_status": ANALYSIS_STATUS,
            }
        )
    return rows


def publication_rows() -> list[dict[str, Any]]:
    return [
        {
            "criterion": "Novelty of exact empirical question",
            "assessment": "Narrow distinction remains, but it is high-risk rather than a method novelty claim.",
            "evidence": "Existing audit found no exact all-conditions match, while generic QPP, confidence, routing, and complementarity mechanisms are established.",
            "confidence": "MODERATE",
        },
        {
            "criterion": "Strength of evidence",
            "assessment": "Useful preregistered source failure; not a statistically proven universal negative.",
            "evidence": "One frozen 200-query Climate holdout; selector-Qwen CI includes zero.",
            "confidence": "STRONG",
        },
        {
            "criterion": "Benchmark breadth",
            "assessment": "Insufficient for a broad standalone claim.",
            "evidence": "One source benchmark; ArguAna was correctly not executed after the source gate failed.",
            "confidence": "STRONG",
        },
        {
            "criterion": "Explanatory value",
            "assessment": "Moderate postmortem value: complementarity exists, but false switches dominate.",
            "evidence": "28 BM25 opportunities, 8 captured, 60 harmful switches, and oracle headroom above Qwen.",
            "confidence": "STRONG",
        },
        {
            "criterion": "Prior-work comparison",
            "assessment": "High novelty risk.",
            "evidence": "Novelty audit identifies QuDAR, Arabzadeh, MoR, Query-Adaptive Hybrid Search, QPP, and code-mixed hybrid precedents.",
            "confidence": "STRONG",
        },
        {
            "criterion": "Best publication form",
            "assessment": "Secondary analysis, workshop/short-paper finding, or motivation for a new preregistered hypothesis.",
            "evidence": "The negative is narrow, source-only, and transfer was not observed.",
            "confidence": "MODERATE",
        },
        {
            "criterion": "Standalone negative paper now",
            "assessment": "Insufficient by itself.",
            "evidence": "No ArguAna transfer result, one source benchmark, and high mechanism-overlap risk.",
            "confidence": "STRONG",
        },
    ]


def failure_rows(
    fit_rows: Sequence[Mapping[str, Any]],
    holdout_diag: Mapping[str, Any],
    shift: Mapping[str, Any],
    gain_corr: Mapping[str, Any],
) -> list[dict[str, Any]]:
    margin_fit = fit_rows[0]
    signal_auc = margin_fit["POSTHOC_AUROC_BM25"]
    harmful = holdout_diag["harmful_switch_count"] if "harmful_switch_count" in holdout_diag else holdout_diag["categories"][1]["count"]
    beneficial = holdout_diag["beneficial_switch_count"] if "beneficial_switch_count" in holdout_diag else holdout_diag["categories"][0]["count"]
    shift_confidence = "MODERATE" if max(item["ks_G"] for item in shift["pairwise_G_shift"]) >= 0.2 else "WEAK"
    signal_confidence = "STRONG" if signal_auc is not None and signal_auc < 0.60 else "MODERATE"
    return [
        {
            "failure_mode": "Signal has almost no predictive information",
            "evidence_for": f"FIT margin accuracy={margin_fit['winner_accuracy']:.6f}; POST-HOC AUROC for BM25 winners={signal_auc:.6f}; holdout gain correlation={gain_corr['holdout_spearman_minus_G_vs_BM25_minus_Qwen']:.6f}.",
            "evidence_against": "FIT is above chance and the diagnostic AUROC is not necessarily exactly 0.5; the result does not prove no information exists.",
            "confidence": signal_confidence,
        },
        {
            "failure_mode": "Class imbalance makes winner accuracy misleading",
            "evidence_for": "Qwen is the majority winner in FIT, validation, and holdout; always-Qwen accuracy exceeds both candidate FIT accuracies.",
            "evidence_against": "Balanced accuracy, BM25 recall, MCC, and AUROC were also reported, so the analysis is not limited to raw accuracy.",
            "confidence": "STRONG",
        },
        {
            "failure_mode": "CDF normalization fails to preserve relative reliability",
            "evidence_for": f"G distribution shift diagnostics show KS values {[round(item['ks_G'], 6) for item in shift['pairwise_G_shift']]} across source stages.",
            "evidence_against": "CDFs are correctly fitted and right-inclusive; shift is observational and cannot establish that normalization caused failure.",
            "confidence": "MODERATE",
        },
        {
            "failure_mode": "Thresholding is insufficient",
            "evidence_for": "Validation preferred progressively lower BM25 routing as tau increased, while the frozen holdout still produced net negative switching.",
            "evidence_against": "The preregistered holdout cannot be used to select or compare unregistered thresholds; no tau beyond 0.20 was tested.",
            "confidence": "MODERATE",
        },
        {
            "failure_mode": "Hard selection is too costly under a strong Qwen baseline",
            "evidence_for": f"There were {harmful} harmful BM25 switches versus {beneficial} beneficial switches; harmful-switch loss exceeded beneficial-switch gain.",
            "evidence_against": "This is specific to the frozen Qwen baseline, signals, threshold, and Climate setting.",
            "confidence": "STRONG",
        },
        {
            "failure_mode": "Source distribution shift",
            "evidence_for": "Saved FIT, validation, and holdout G and raw-signal summaries differ; pairwise KS/Wasserstein diagnostics are reported.",
            "evidence_against": "All three are source splits from one benchmark and the analysis is not a causal shift test.",
            "confidence": shift_confidence,
        },
        {
            "failure_mode": "Complementarity exists but current signals cannot identify it",
            "evidence_for": "BM25 wins on 28/200 holdout queries and the oracle exceeds Qwen, but only 8 opportunities were captured and 60 BM25 switches were harmful.",
            "evidence_against": "The conclusion is limited to margin/dispersion and this frozen source setting; other observables were not tested.",
            "confidence": "STRONG",
        },
    ]


def future_hypotheses() -> list[dict[str, Any]]:
    return [
        {
            "id": "H1",
            "scientific_question": "Can an explicitly asymmetric selective-risk or abstention objective avoid harmful BM25 switches while retaining a measurable subset of BM25 opportunities?",
            "motivation": "The holdout had 60 harmful BM25 switches versus 8 beneficial switches under the frozen hard selector.",
            "difference_from_M2": "Changes the scientific target from winner classification to pre-registered risk control/utility with abstention; it is not another tau, k, or signal tweak.",
            "prior_art_threat": "Arabzadeh, QuDAR, and query-adaptive hybrid work already cover strategy selection and confidence/weighting mechanisms.",
            "novelty_risk": "HIGH",
            "fresh_evidence_required": "Fresh source-disjoint development groups and a separately held-out confirmatory resource with an externally specified cost matrix.",
            "clean_data_consequence": "The Climate Milestone 2 holdout is consumed and cannot serve as confirmatory evidence.",
        },
        {
            "id": "H2",
            "scientific_question": "Can observable retriever disagreement or query-document coverage identify relative BM25 advantage when independent top-k score shape does not?",
            "motivation": "Oracle headroom and 28 BM25-winning holdout queries show complementarity, while margin-based G was weak for identifying them.",
            "difference_from_M2": "Tests a preregistered new feature family and identifiability question rather than combining margin and dispersion or adding a post-hoc exception.",
            "prior_art_threat": "MoR, QuDAR, RouterRetriever, QPP, and complementarity-routing work make this a high-risk replication/transfer question.",
            "novelty_risk": "HIGH",
            "fresh_evidence_required": "New source-query groups, blinded feature freeze, multiple fixed retrievers, and a fresh target or benchmark.",
            "clean_data_consequence": "Current Climate FIT, validation, and holdout are exploratory history for this hypothesis.",
        },
        {
            "id": "H3",
            "scientific_question": "Is cross-resource calibration itself the limiting factor, such that relative-reliability signals need multi-source invariance before transfer can be tested?",
            "motivation": "G and raw-signal distributions vary across FIT, validation, and holdout, and ArguAna transfer was not authorized after source failure.",
            "difference_from_M2": "Studies pre-registered multi-source calibration and invariance; it does not retune the consumed holdout or recalibrate on the target after seeing outcomes.",
            "prior_art_threat": "Generic QPP, confidence, and query-adaptive routing literature directly threatens any calibration-method claim.",
            "novelty_risk": "HIGH",
            "fresh_evidence_required": "At least two genuinely new source resources plus a new confirmatory target, with all calibration boundaries fixed in advance.",
            "clean_data_consequence": "All Milestone 2 Climate data are exploratory history and cannot be used as clean confirmation.",
        },
    ]


def build_report(summary: Mapping[str, Any], tables: Mapping[str, Mapping[str, str]], figures: Mapping[str, Mapping[str, str]]) -> str:
    fit_rows = summary["fit_diagnostics"]["table_rows"]
    decomposition = summary["holdout_switch_diagnostics"]
    split_stats = summary["distribution_shift_diagnostics"]["split_statistics"]
    failure = summary["failure_mode_evidence"]
    publication = summary["negative_paper_assessment"]["criteria"]
    gain = summary["signal_gain_correlations"]
    source = summary["selector_vs_qwen"]
    table_sections = "\n".join(
        f"- {name}: `{bundle['csv']}`, `{bundle['markdown']}`, `{bundle['latex']}`"
        for name, bundle in tables.items()
    )
    figure_sections = "\n".join(
        f"- {name}: `{bundle['png']}`, `{bundle['pdf']}`, plot data `{bundle['plot_data_csv']}`"
        for name, bundle in figures.items()
    )
    balance_lines = "\n".join(
        f"- {name}: BM25={item['actual_bm25_winner_count']} ({item['actual_bm25_winner_rate']:.3%}), Qwen={item['actual_qwen_winner_count']} ({item['actual_qwen_winner_rate']:.3%}), always-Qwen accuracy={item['majority_baseline_accuracy']:.3%}"
        for name, item in summary["class_balance"].items()
    )
    shift_lines = "\n".join(
        f"- {name}: BM25 raw mean/median/std={item['raw_BM25']['mean']:.9f}/{item['raw_BM25']['median']:.9f}/{item['raw_BM25']['std_ddof0']:.9f}; Qwen raw mean/median/std={item['raw_Qwen']['mean']:.9f}/{item['raw_Qwen']['median']:.9f}/{item['raw_Qwen']['std_ddof0']:.9f}; G mean={item['G']['mean']:.9f}, median={item['G']['median']:.9f}, std={item['G']['std_ddof0']:.9f}, Q1={item['G']['q1']:.9f}, Q3={item['G']['q3']:.9f}, G < -tau={item['percentage_G_lt_negative_tau']:.3f}%"
        for name, item in split_stats.items()
    )
    confusion_lines = "\n".join(
        f"- {signal}: actual BM25→predicted BM25={item['confusion_matrix']['actual_BM25_predicted_BM25']}, actual BM25→Qwen={item['confusion_matrix']['actual_BM25_predicted_Qwen']}, actual Qwen→BM25={item['confusion_matrix']['actual_Qwen_predicted_BM25']}, actual Qwen→Qwen={item['confusion_matrix']['actual_Qwen_predicted_Qwen']}"
        for signal, item in (("margin", summary["fit_diagnostics"]["margin"]), ("dispersion", summary["fit_diagnostics"]["dispersion"]))
    )
    threshold_lines = "\n".join(
        f"- tau={row['tau']:.2f}: CS nDCG@10={row['code_switched_ndcg_at_10']:.9f}, BM25 route={row['bm25_choice_rate']:.3%}, Qwen route={row['qwen_choice_rate']:.3%}, selected={row['selected']}"
        for row in summary["validation_behavior"]
    )
    hypotheses = "\n".join(
        f"### {item['id']}\n\n**Question:** {item['scientific_question']}\n\n**Motivation:** {item['motivation']}\n\n**Difference from Milestone 2:** {item['difference_from_M2']}\n\n**Prior-art threat:** {item['prior_art_threat']} Novelty risk: **{item['novelty_risk']}**\n\n**Required evidence:** {item['fresh_evidence_required']}\n\n**Data boundary:** {item['clean_data_consequence']}"
        for item in summary["future_hypotheses_if_any"]
    )
    return f"""# Milestone 2.5 scientific postmortem

## 1. Executive conclusion

The immutable confirmatory result remains **MILESTONE 2 SOURCE GATE FAILED**. The most supported explanation is not that BM25 and Qwen lack complementarity. Rather, the frozen margin/dispersion signals did not identify the useful BM25 opportunities reliably enough, and false BM25 switches were much more costly than captured opportunities were beneficial. This conclusion is limited to the pre-specified signals, fixed retrievers, benchmark-provided Climate zh-en setting, and consumed post-exploratory holdout.

The primary recommendation is **{summary['recommended_path']}**.

## 2. Immutable Milestone 2 result

Saved headline values were independently verified from the original machine-readable record. Margin was selected at FIT accuracy {summary['fit_diagnostics']['margin_accuracy']:.9f} versus dispersion {summary['fit_diagnostics']['dispersion_accuracy']:.9f}; tau={summary['selected_tau']:.2f}. Climate holdout CS nDCG@10 was BM25={source['cs_metrics']['BM25']['ndcg@10']:.9f}, Qwen={source['cs_metrics']['Qwen']['ndcg@10']:.9f}, Selector={source['cs_metrics']['Selector']['ndcg@10']:.9f}. Selector-Qwen was {source['cs_difference']:.9f}, with 95% CI [{source['cs_ci_lower']:.9f}, {source['cs_ci_upper']:.9f}]. Original safety difference was {source['original_difference']:.9f}, with CI [{source['original_ci_lower']:.9f}, {source['original_ci_upper']:.9f}].

The original Milestone 2 output manifest remains intact; its SHA-256 is `{summary['milestone2_record']['output_manifest_sha256']}`. No original Milestone 2 result was overwritten.

## 3. What hypothesis was tested

Milestone 2 tested whether unlabeled normalized top-1/top-2 score margin or top-k score dispersion could predict the relative per-query winner between fixed BM25 and fixed Qwen under benchmark-provided zh-en code switching. It used candidate-specific Climate FIT empirical CDFs, one selected signal, a fixed threshold grid, and a hard Qwen-fallback selector. The oracle used outcome labels and was diagnostic only.

## 4. What failed

The selector routed 68/200 holdout queries to BM25 and 132/200 to Qwen. Actual BM25 wins occurred on 28/200 queries, but only 8 were captured; 60 BM25 switches were harmful. Thus the central failure was costly false positive BM25 routing, not absence of all per-query complementarity.

## 5. FIT signal diagnostics

The preregistered FIT objective remains winner accuracy. The following additional measures are explicitly **{ANALYSIS_STATUS}** and did not select the signal:

{table_markdown(fit_rows)}

FIT actual winners were BM25={summary['class_balance']['fit']['actual_bm25_winner_count']} and Qwen={summary['class_balance']['fit']['actual_qwen_winner_count']}; an always-Qwen predictor would score {summary['class_balance']['fit']['majority_baseline_accuracy']:.3%}. This makes the raw 52.167%/49.167% candidate accuracies poor evidence of useful BM25 identification despite margin winning the frozen comparison.

FIT confusion matrices:

{confusion_lines}

## 6. Class-imbalance analysis

{balance_lines}

Qwen was the majority winner in every analyzed split. The always-Qwen diagnostic baseline therefore exceeded both FIT candidate accuracies. This does not retroactively replace the preregistered selection criterion; it shows why raw winner accuracy alone was an incomplete proxy for deployment utility.

## 7. Validation behavior

The saved validation sweep was:

{threshold_lines}

Increasing tau monotonically reduced BM25 routing and increased Qwen fallback while validation nDCG@10 increased at every registered grid point. The data support the narrow interpretation that validation preferred increasingly conservative switching. No tau outside the frozen grid was tested or inferred.

## 8. Holdout failure decomposition

{table_markdown(decomposition['categories'])}

BM25 switch precision was {decomposition['bm25_switch_precision']:.3%}; BM25 opportunity recall was {decomposition['bm25_opportunity_recall']:.3%}; harmful-switch rate was {decomposition['harmful_switch_rate']:.3%}; missed-opportunity rate was {decomposition['missed_opportunity_rate']:.3%}. Correct BM25 switches contributed total nDCG@10 gain {decomposition['beneficial_gain_total']:.9f} (mean {decomposition['beneficial_gain_mean']:.9f}). Harmful switches incurred total loss {decomposition['harmful_loss_total']:.9f} (mean {decomposition['harmful_loss_mean']:.9f}). Missed BM25 opportunities left total gain {decomposition['missed_gain_total']:.9f} unrealized (mean {decomposition['missed_gain_mean']:.9f}). The net switch effect was negative because false switches dominated.

## 9. QPP confidence versus actual retriever advantage

For the selected holdout margin, Spearman correlation between G and Qwen-minus-BM25 nDCG@10 was {gain['holdout_spearman_G_vs_Qwen_minus_BM25']:.9f}; equivalently, correlation between -G and BM25-minus-Qwen advantage was {gain['holdout_spearman_minus_G_vs_BM25_minus_Qwen']:.9f}. The post-hoc AUROC for detecting BM25-winner queries from -G was {gain['holdout_auroc_BM25']:.9f}. These values support limited or weak identifiability, not a universal claim that QPP contains no information. Figure 2 is a **{ANALYSIS_STATUS}** visualization.

## 10. Complementarity versus identifiability

Complementarity remains observable: BM25 won on 28 holdout queries, and the outcome-defined oracle reached nDCG@10 {source['cs_metrics']['Oracle diagnostic']['ndcg@10']:.9f} versus Qwen {source['cs_metrics']['Qwen']['ndcg@10']:.9f}. Headroom was Oracle-Qwen={summary['oracle_headroom']['oracle_minus_qwen']:.9f}; Selector-Qwen={source['cs_difference']:.9f}; Oracle-Selector={summary['oracle_headroom']['oracle_minus_selector']:.9f}. The oracle is not deployable. The defensible distinction is therefore: complementarity exists, but these unlabeled score-shape signals did not identify it safely.

Fixed RRF reached {source['cs_metrics']['RRF']['ndcg@10']:.9f}; RRF-Qwen={summary['rrf_difference']['rrf_minus_qwen']:.9f} and RRF-Selector={summary['rrf_difference']['rrf_minus_selector']:.9f}. This descriptively suggests fixed fusion exploited some complementarity that hard QPP routing did not, but RRF remains an established baseline and is not promoted as the contribution.

## 11. Distribution-shift analysis

Saved selected-margin raw-signal and G summaries were:

{shift_lines}

Pairwise G shift diagnostics are reported in the machine-readable summary: KS and Wasserstein distances compare FIT/validation, FIT/holdout, and validation/holdout. Differences make distribution shift a plausible contributor, but all three splits come from one source benchmark; these are not causal or external-domain shift tests. No CDF was refit.

## 12. Failure-mode evidence matrix

{table_markdown(failure)}

## 13. What can and cannot be claimed

Supported wording: “Under the frozen ClimateFEVERHardNegatives zh-en code-switched setting, normalized score margin and top-k dispersion did not provide sufficient relative-reliability information to safely switch between BM25 and Qwen.”

This does not show that QPP fails universally, that QPP causes degradation, or that all code-switching QPP methods fail. The selector-minus-Qwen CS confidence interval includes zero, so the result is not a statistically established negative effect in the universal sense.

## 14. Negative-paper viability

{table_markdown(publication)}

The current evidence is valuable as a disciplined negative/diagnostic result, but insufficient by itself for a standalone main-paper contribution. Its strongest use is a secondary analysis, workshop/short-paper finding, or motivation for a genuinely new preregistered hypothesis.

## 15. Existing novelty risk

The frozen novelty documents identify QuDAR, Arabzadeh et al., MoR, Query-Adaptive Hybrid Search, confidence/QPP work, RouterRetriever, SETU-RAG, and FIRE/code-mixed hybrid systems as close threats. The overlap is high for confidence, QPP, relative selection, routing, fusion, and complementarity. The remaining distinction is the narrow empirical calibration/transfer question for fixed BM25 versus fixed Qwen on benchmark-provided zh-en variants. Novelty risk is **HIGH**. A **FRESH LITERATURE REVIEW REQUIRED** before publication, but none was performed in this postmortem.

## 16. Possible future hypotheses

The following are hypotheses only; no implementation or experiment was run:

{hypotheses}

## 17. Data-independence consequences

Milestone 1 aggregate observations, Milestone 2 Climate FIT, validation, and holdout outcomes, and every postmortem diagnostic derived from them are now exploratory history for any future branch. **Climate Milestone 2 holdout = CONSUMED FOR FUTURE HYPOTHESIS DESIGN.** It cannot serve as fresh confirmatory evidence. Future confirmation requires newly defined source groups and a fresh confirmatory target; this postmortem does not recommend using CSR-L to tune a new idea.

## 18. Recommended next step

Do not tune the failed selector. If the project continues, first write a new preregistration around one clearly differentiated hypothesis, a new data boundary, a fresh literature review, and an explicit cost/utility or identifiability target. Human review is required before any new protected evaluation.

## 19. Final GO/NO-GO decision

**{summary['recommended_path']}**

Concrete reasons:

1. The negative source result is preregistered, reproducible, and diagnostically informative.
2. The holdout shows strong asymmetric switching failure: 60 harmful versus 8 beneficial BM25 switches.
3. Complementarity and oracle headroom exist, so the scientific question is not vacuous.
4. The evidence is limited to one source benchmark because ArguAna was correctly not executed.
5. Prior-art overlap makes a standalone method or universal QPP claim indefensible.

## 20. Protected-boundary statement

No new protected evaluation or raw protected dataset access occurred. Previously saved Climate holdout outcomes were analyzed post hoc. ArguAna and CSR-L remained untouched. No BM25, Qwen, BGE, RRF retrieval, encoding, GPU work, tuning, signal addition, or selector implementation was run. The original Milestone 2 verdict remains **MILESTONE 2 SOURCE GATE FAILED**.

**NO RETUNING.** **NO NEW PROTECTED EXPERIMENT.** **ARGUANA UNTOUCHED.** **FINAL CSR-L TEST UNTOUCHED.**

## Postmortem artifacts

### Tables

{table_sections}

### Figures

{figure_sections}
"""


def run_postmortem() -> dict[str, Any]:
    record = verify_milestone2_record()
    m2 = record["summary"]
    fit_rows = read_csv(M2_ROOT / "calibration" / "fit_signal_selection.csv")
    validation_rows = read_csv(M2_ROOT / "validation" / "selected_tau_diagnostics.csv")
    validation_sweep = read_csv(M2_ROOT / "validation" / "tau_sweep.csv")
    holdout_rows = read_csv(M2_ROOT / "holdout" / "code_switched_selector_diagnostics.csv")
    original_rows = read_csv(M2_ROOT / "holdout" / "original_selector_diagnostics.csv")
    if len(fit_rows) != 600 or len(validation_rows) != 200 or len(holdout_rows) != 200 or len(original_rows) != 200:
        raise AssertionError("saved postmortem row counts do not match the frozen split")
    if any(row["setting"] != "code_switched" for row in fit_rows + validation_rows + holdout_rows):
        raise AssertionError("postmortem calibration/validation/holdout rows are not CS-only")
    if any(row["setting"] != "original" for row in original_rows):
        raise AssertionError("saved original safety rows have the wrong setting")

    fit_rows_table = fit_table_rows(fit_rows)
    fit_metrics = {
        "margin": signal_posthoc_metrics(fit_rows, "margin_gap", "margin_predicted_winner"),
        "dispersion": signal_posthoc_metrics(fit_rows, "dispersion_gap", "dispersion_predicted_winner"),
        "table_rows": fit_rows_table,
        "margin_accuracy": float(m2["fit_signal_accuracies"]["normalized_top1_minus_top2_score_margin"]),
        "dispersion_accuracy": float(m2["fit_signal_accuracies"]["top_k_score_dispersion"]),
        "diagnostic_status": ANALYSIS_STATUS,
    }
    balance = {
        "fit": classification_metrics(fit_rows, "margin_predicted_winner"),
        "validation": classification_metrics(validation_rows, "choice"),
        "holdout": classification_metrics(holdout_rows, "choice"),
    }
    decomposition = holdout_decomposition(holdout_rows)
    split_rows = {"FIT": fit_rows, "VALIDATION": validation_rows, "HOLDOUT": holdout_rows}
    split_statistics = {
        "FIT": split_signal_stats(fit_rows, raw_bm25="margin_bm25_raw", raw_qwen="margin_qwen_raw", gap="margin_gap"),
        "VALIDATION": split_signal_stats(validation_rows, raw_bm25="bm25_raw_signal", raw_qwen="qwen_raw_signal", gap="gap"),
        "HOLDOUT": split_signal_stats(holdout_rows, raw_bm25="bm25_raw_signal", raw_qwen="qwen_raw_signal", gap="gap"),
    }
    pairwise = []
    ordered_splits = ("FIT", "VALIDATION", "HOLDOUT")
    for index, first in enumerate(ordered_splits):
        for second in ordered_splits[index + 1 :]:
            first_g = [f(row["margin_gap"] if "margin_gap" in row else row["gap"]) for row in split_rows[first]]
            second_g = [f(row["margin_gap"] if "margin_gap" in row else row["gap"]) for row in split_rows[second]]
            pairwise.append(
                {
                    "first": first,
                    "second": second,
                    "ks_G": ks_statistic(first_g, second_g),
                    "wasserstein_G": wasserstein_1d(first_g, second_g),
                    "diagnostic_status": ANALYSIS_STATUS,
                }
            )
    distribution_shift = {
        "split_statistics": split_statistics,
        "pairwise_G_shift": pairwise,
        "interpretation": "Distribution shift is plausible if these source-split differences are material, but no causal or external-domain claim is made.",
        "diagnostic_status": ANALYSIS_STATUS,
    }

    holdout_gain = [f(row["bm25_ndcg_at_10"]) - f(row["qwen_ndcg_at_10"]) for row in holdout_rows]
    holdout_g = [f(row["gap"]) for row in holdout_rows]
    gain_correlations = {
        "fit_margin": {
            "auroc_BM25": fit_metrics["margin"]["auroc_for_BM25_winner_using_minus_G"],
            "spearman_G_vs_Qwen_minus_BM25": fit_metrics["margin"]["spearman_G_vs_Qwen_minus_BM25_ndcg_at_10"],
        },
        "fit_dispersion": {
            "auroc_BM25": fit_metrics["dispersion"]["auroc_for_BM25_winner_using_minus_G"],
            "spearman_G_vs_Qwen_minus_BM25": fit_metrics["dispersion"]["spearman_G_vs_Qwen_minus_BM25_ndcg_at_10"],
        },
        "holdout_auroc_BM25": auroc_positive([row["observed_winner"] == "BM25" for row in holdout_rows], [-value for value in holdout_g]),
        "holdout_spearman_G_vs_Qwen_minus_BM25": spearman(holdout_g, [-value for value in holdout_gain]),
        "holdout_spearman_minus_G_vs_BM25_minus_Qwen": spearman([-value for value in holdout_g], holdout_gain),
        "diagnostic_status": ANALYSIS_STATUS,
    }

    source_systems = m2["source_holdout_metrics"]["systems"]
    selector_vs_qwen = {
        "cs_metrics": {name: source_systems[name]["code_switched"] for name in ("BM25", "Qwen", "Selector", "RRF", "BGE-M3", "Oracle diagnostic")},
        "original_metrics": {name: source_systems[name]["original"] for name in ("BM25", "Qwen", "Selector", "RRF", "BGE-M3", "Oracle diagnostic")},
        "cs_difference": source_systems["Selector"]["code_switched"]["ndcg@10"] - source_systems["Qwen"]["code_switched"]["ndcg@10"],
        "cs_ci_lower": m2["source_gate"]["source_cs_ci_lower"],
        "cs_ci_upper": m2["source_gate"]["source_cs_ci_upper"],
        "original_difference": source_systems["Selector"]["original"]["ndcg@10"] - source_systems["Qwen"]["original"]["ndcg@10"],
        "original_ci_lower": m2["source_gate"]["source_original_ci_lower"],
        "original_ci_upper": m2["source_gate"]["source_original_ci_upper"],
        "diagnostic_status": ANALYSIS_STATUS,
    }
    oracle_headroom = {
        "oracle_minus_qwen": source_systems["Oracle diagnostic"]["code_switched"]["ndcg@10"] - source_systems["Qwen"]["code_switched"]["ndcg@10"],
        "selector_minus_qwen": selector_vs_qwen["cs_difference"],
        "oracle_minus_selector": source_systems["Oracle diagnostic"]["code_switched"]["ndcg@10"] - source_systems["Selector"]["code_switched"]["ndcg@10"],
        "diagnostic_status": ANALYSIS_STATUS,
    }
    rrf_difference = {
        "rrf_minus_qwen": source_systems["RRF"]["code_switched"]["ndcg@10"] - source_systems["Qwen"]["code_switched"]["ndcg@10"],
        "rrf_minus_selector": source_systems["RRF"]["code_switched"]["ndcg@10"] - source_systems["Selector"]["code_switched"]["ndcg@10"],
        "diagnostic_status": ANALYSIS_STATUS,
    }
    prior_hashes = {rel(path): sha256_file(path) for path in PRIOR_WORK_FILES}
    failure = failure_rows(fit_rows_table, decomposition, distribution_shift, gain_correlations)
    publication = publication_rows()
    hypotheses = future_hypotheses()

    table_b_rows = decomposition["categories"]
    tables = {
        "table_A_qpp_signal_diagnostic_quality": write_table_bundle("table_A_qpp_signal_diagnostic_quality", fit_rows_table),
        "table_B_holdout_switching_decomposition": write_table_bundle("table_B_holdout_switching_decomposition", table_b_rows),
        "table_C_failure_mode_evidence_matrix": write_table_bundle("table_C_failure_mode_evidence_matrix", failure),
        "table_D_publication_viability_assessment": write_table_bundle("table_D_publication_viability_assessment", publication),
    }
    summary: dict[str, Any] = {
        "postmortem_revision": "milestone_2_5_saved_data_only_v1",
        "created_utc": now_utc(),
        "milestone2_status": m2["final_milestone2_status"],
        "selected_signal": m2["selected_signal"],
        "selected_tau": m2["selected_tau"],
        "fit_diagnostics": fit_metrics,
        "class_balance": balance,
        "majority_baseline": {name: item["majority_baseline_accuracy"] for name, item in balance.items()},
        "validation_behavior": [
            {
                "tau": f(row["tau"]),
                "code_switched_ndcg_at_10": f(row["code_switched_ndcg_at_10"]),
                "bm25_choice_rate": f(row["bm25_choice_rate"]),
                "qwen_choice_rate": f(row["qwen_choice_rate"]),
                "selected": row["selected"] == "True",
                "diagnostic_status": ANALYSIS_STATUS,
            }
            for row in validation_sweep
        ],
        "holdout_switch_diagnostics": decomposition,
        "beneficial_switch_count": decomposition["beneficial_switch_count"],
        "harmful_switch_count": decomposition["harmful_switch_count"],
        "missed_opportunity_count": decomposition["missed_opportunity_count"],
        "selector_vs_qwen": selector_vs_qwen,
        "oracle_headroom": oracle_headroom,
        "rrf_difference": rrf_difference,
        "signal_gain_correlations": gain_correlations,
        "distribution_shift_diagnostics": distribution_shift,
        "failure_mode_evidence": failure,
        "negative_paper_assessment": {
            "standalone_main_paper": False,
            "best_fit": "secondary analysis, workshop/short-paper finding, or motivation for a new hypothesis",
            "criteria": publication,
            "reason": "One source benchmark, no authorized ArguAna transfer, selector CI including zero, and high novelty risk.",
        },
        "novelty_risk": "HIGH",
        "novelty_context": {
            "closest_prior_works": ["QuDAR", "Arabzadeh et al.", "MoR", "Query-Adaptive Hybrid Search", "QPP/coherence work", "RouterRetriever", "SETU-RAG", "FIRE/code-mixed hybrid systems"],
            "overlap": "Confidence/QPP, relative strategy selection, routing, fusion, and complementarity are established mechanisms.",
            "remaining_distinction": "A narrow saved-data empirical calibration/transfer question for fixed BM25 versus fixed Qwen on benchmark-provided zh-en variants.",
            "fresh_literature_review": "FRESH LITERATURE REVIEW REQUIRED before publication; none performed in Milestone 2.5.",
            "prior_work_file_hashes": prior_hashes,
        },
        "recommended_path": "CONDITIONAL GO — NEW HYPOTHESIS REQUIRED",
        "future_hypotheses_if_any": hypotheses,
        "climate_holdout_consumed_for_future_design": True,
        "arguana_executed": False,
        "csr_l_untouched": True,
        "new_experiment_executed": False,
        "no_retuning": True,
        "no_new_protected_experiment": True,
        "milestone2_record": record,
        "source_artifact_row_counts": {"fit": len(fit_rows), "validation": len(validation_rows), "holdout_cs": len(holdout_rows), "holdout_original": len(original_rows)},
        "tables": tables,
        "figures": {},
        "input_files": {
            "milestone2_summary": rel(M2_ROOT / "milestone2_summary.json"),
            "milestone2_summary_sha256": sha256_file(M2_ROOT / "milestone2_summary.json"),
            "milestone2_output_manifest": rel(M2_ROOT / "logs" / "output_manifest.json"),
            "milestone2_output_manifest_sha256": record["output_manifest_sha256"],
        },
        "environment": {"python": sys.version, "os": platform.platform(), "numpy": np.__version__},
    }
    figures = create_figures(holdout_rows, split_rows, decomposition)
    summary["figures"] = figures
    summary["report_path"] = rel(REPORT_PATH)
    write_json(SUMMARY_PATH, summary)
    report = build_report(summary, tables, figures)
    atomic_write_text(REPORT_PATH, report)
    summary["report_sha256"] = sha256_file(REPORT_PATH)
    summary["analysis_script_sha256"] = sha256_file(Path(__file__))
    write_json(SUMMARY_PATH, summary)
    write_json(
        OUT_ROOT / "logs" / "postmortem_validation.json",
        {
            "status": "PASS",
            "created_utc": now_utc(),
            "milestone2_record_verified": True,
            "original_milestone2_output_manifest_verified": True,
            "arguana_outcomes_read": False,
            "csr_l_read": False,
            "new_experiment_executed": False,
            "posthoc_diagnostics_labeled": True,
            "source_artifact_row_counts": summary["source_artifact_row_counts"],
        },
    )
    manifest_path = OUT_ROOT / "logs" / "output_manifest.json"
    manifest_files = sorted(
        path for path in OUT_ROOT.rglob("*") if path.is_file() and path != manifest_path
    )
    write_json(
        manifest_path,
        {
            "created_utc": now_utc(),
            "scope": "Milestone 2.5 postmortem outputs; manifest excludes itself",
            "files": [
                {"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
                for path in manifest_files
            ],
        },
    )
    return summary


def main() -> int:
    try:
        result = run_postmortem()
    except Exception as error:  # pragma: no cover - CLI boundary
        print(f"MILESTONE 2.5 EXECUTION BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "PASS", "recommended_path": result["recommended_path"], "summary": rel(SUMMARY_PATH), "report": rel(REPORT_PATH)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

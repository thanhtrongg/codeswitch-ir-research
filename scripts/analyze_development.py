"""Generate development-only RQ0, complementarity, and structure diagnostics."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable
import unicodedata

import numpy as np


RUN_ROOT = Path("results/runs")
OUTPUT_ROOT = Path("results/analysis/development_only")
DEV_DATASETS = {"ArguAna", "ClimateFEVERHardNegatives"}
DENSE_RETRIEVERS = {"Qwen3-Embedding-0.6B", "BGE-M3", "multilingual-e5-large"}
METRICS = ("official", "ndcg@10", "recall@10", "mrr")
TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def pearson(left: Iterable[float], right: Iterable[float]) -> float | None:
    x = np.asarray(list(left), dtype=float)
    y = np.asarray(list(right), dtype=float)
    if len(x) < 2 or np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def bootstrap_mean_ci(values: list[float], seed: int, repetitions: int = 2000) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    if len(array) < 2:
        return (float(array[0]) if len(array) else 0.0, float(array[0]) if len(array) else 0.0)
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(array), size=(repetitions, len(array)))
    means = array[samples].mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def structure_features(text: str) -> dict[str, float]:
    labels: list[str] = []
    latin = 0
    cjk = 0
    unknown = 0
    for char in text:
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        if "CJK UNIFIED IDEOGRAPH" in name or "HIRAGANA" in name or "KATAKANA" in name:
            labels.append("CJK")
            cjk += 1
        elif "LATIN" in name:
            labels.append("LATIN")
            latin += 1
        else:
            unknown += 1
    total = latin + cjk
    proportions = [value / total for value in (latin, cjk) if value]
    entropy = -sum(probability * math.log2(probability) for probability in proportions)
    switches = sum(left != right for left, right in zip(labels, labels[1:]))
    return {
        "query_length_tokens": float(len(TOKEN_RE.findall(text))),
        "known_letter_count": float(total),
        "unknown_letter_count": float(unknown),
        "latin_fraction": float(latin / total) if total else 0.0,
        "cjk_fraction": float(cjk / total) if total else 0.0,
        "switch_ratio": float(min(latin, cjk) / total) if total else 0.0,
        "language_entropy_bits": float(entropy),
        "switch_count": float(switches),
        "has_detected_switch": float(len(set(labels)) > 1),
    }


def load_compact_runs() -> dict[tuple[str, str], dict[tuple[str, str], dict[str, Any]]]:
    runs: dict[tuple[str, str], dict[tuple[str, str], dict[str, Any]]] = {}
    for path in RUN_ROOT.glob("**/per_query.jsonl"):
        config = json.loads((path.parent / "run_config.json").read_text(encoding="utf-8"))
        dataset = path.parent.parent.parent.name
        retriever = config["retriever"]
        if dataset not in DEV_DATASETS:
            raise AssertionError(f"non-development artifact encountered: {path}")
        condition: dict[tuple[str, str], dict[str, Any]] = {}
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                key = (row["source_query_id"], row["setting"])
                if key in condition:
                    raise AssertionError(f"duplicate compact row: {path} {key}")
                condition[key] = {
                    "source_query_id": row["source_query_id"],
                    "setting": row["setting"],
                    "query": row["query"],
                    "language_pair": row["language_pair"],
                    "metrics": {metric: float(value) for metric, value in row["metrics"].items()},
                }
        runs[(dataset, retriever)] = condition
    return runs


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else []
    header = "| " + " | ".join(fields) + " |\n"
    divider = "|" + "|".join("---" for _ in fields) + "|\n"
    body = "".join("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |\n" for row in rows)
    path.write_text(header + divider + body, encoding="utf-8")


def make_rq0(runs: dict[tuple[str, str], dict[tuple[str, str], dict[str, Any]]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for (dataset, retriever), rows in sorted(runs.items()):
        groups = sorted({source for source, setting in rows if setting == "original"})
        for metric in METRICS:
            originals = [rows[(source, "original")]["metrics"][metric] for source in groups]
            switched = [rows[(source, "code_switched")]["metrics"][metric] for source in groups]
            deltas = [cs - original for original, cs in zip(originals, switched)]
            original_mean = float(np.mean(originals))
            switched_mean = float(np.mean(switched))
            delta = switched_mean - original_mean
            seed_bytes = f"{dataset}|{retriever}|{metric}".encode("utf-8")
            seed = int.from_bytes(hashlib.sha256(seed_bytes).digest()[:4], "big")
            low, high = bootstrap_mean_ci(deltas, seed)
            output.append({
                "dataset": dataset,
                "retriever": retriever,
                "metric": metric,
                "language_pair": rows[(groups[0], "original")]["language_pair"],
                "query_count": len(groups),
                "original": original_mean,
                "code_switched": switched_mean,
                "delta_cs": delta,
                "relative_degradation": delta / abs(original_mean) if original_mean else None,
                "delta_bootstrap_ci_low": low,
                "delta_bootstrap_ci_high": high,
                "queries_with_negative_delta": sum(value < 0 for value in deltas),
                "queries_with_nonnegative_delta": sum(value >= 0 for value in deltas),
            })
    return output


def make_query_rows(runs: dict[tuple[str, str], dict[tuple[str, str], dict[str, Any]]]) -> list[dict[str, Any]]:
    by_dataset: dict[str, dict[str, dict[str, dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
    for (dataset, retriever), rows in runs.items():
        for (source, setting), row in rows.items():
            by_dataset[dataset][source].setdefault(retriever, {})[setting] = row
    output: list[dict[str, Any]] = []
    for dataset, sources in sorted(by_dataset.items()):
        for source, retrievers in sorted(sources.items()):
            source_row = next(iter(retrievers.values()))["code_switched"]
            record = {"dataset": dataset, "source_query_id": source, **structure_features(source_row["query"])}
            for retriever, pair in sorted(retrievers.items()):
                if "original" not in pair or "code_switched" not in pair:
                    continue
                for metric in ("official", "recall@10", "mrr"):
                    prefix = retriever.replace("-", "_").replace(".", "_")
                    record[f"{prefix}_original_{metric}"] = pair["original"]["metrics"][metric]
                    record[f"{prefix}_cs_{metric}"] = pair["code_switched"]["metrics"][metric]
                    record[f"{prefix}_delta_{metric}"] = pair["code_switched"]["metrics"][metric] - pair["original"]["metrics"][metric]
            output.append(record)
    return output


def make_complementarity(query_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for dataset in sorted({row["dataset"] for row in query_rows}):
        subset = [row for row in query_rows if row["dataset"] == dataset]
        bm_prefix = "BM25"
        dense_prefixes = {"Qwen3_Embedding_0_6B": "Qwen3-Embedding-0.6B", "BGE_M3": "BGE-M3", "multilingual_e5_large": "multilingual-e5-large"}
        for dense_prefix, dense in sorted((prefix, name) for prefix, name in dense_prefixes.items() if f"{prefix}_delta_official" in subset[0]):
            required = [f"{bm_prefix}_delta_official", f"{dense_prefix}_delta_official", f"{bm_prefix}_cs_official", f"{dense_prefix}_cs_official"]
            paired = [row for row in subset if all(key in row for key in required)]
            if not paired:
                continue
            bm_delta = np.asarray([row[f"{bm_prefix}_delta_official"] for row in paired])
            dense_delta = np.asarray([row[f"{dense_prefix}_delta_official"] for row in paired])
            categories = {
                "bm25_survives_dense_degrades": int(np.sum((bm_delta >= 0) & (dense_delta < 0))),
                "dense_survives_bm25_degrades": int(np.sum((bm_delta < 0) & (dense_delta >= 0))),
                "both_degrade": int(np.sum((bm_delta < 0) & (dense_delta < 0))),
                "neither_degrades": int(np.sum((bm_delta >= 0) & (dense_delta >= 0))),
            }
            bm_worst = set(np.where(bm_delta <= np.quantile(bm_delta, 0.25))[0])
            dense_worst = set(np.where(dense_delta <= np.quantile(dense_delta, 0.25))[0])
            union = bm_worst | dense_worst
            dense_cs = np.asarray([row[f"{dense_prefix}_cs_official"] for row in paired])
            bm_cs = np.asarray([row[f"{bm_prefix}_cs_official"] for row in paired])
            output.append({
                "dataset": dataset,
                "dense_retriever": dense,
                "query_count": len(paired),
                **categories,
                **{f"{key}_rate": value / len(paired) for key, value in categories.items()},
                "delta_pearson": pearson(bm_delta, dense_delta),
                "dense_wins_cs_score": int(np.sum(dense_cs > bm_cs)),
                "bm25_wins_cs_score": int(np.sum(bm_cs > dense_cs)),
                "cs_score_ties": int(np.sum(bm_cs == dense_cs)),
                "dense_wins_cs_score_rate": float(np.mean(dense_cs > bm_cs)),
                "oracle_mean_cs_score": float(np.mean(np.maximum(bm_cs, dense_cs))),
                "bm25_mean_cs_score": float(np.mean(bm_cs)),
                "dense_mean_cs_score": float(np.mean(dense_cs)),
                "worst_quartile_jaccard": len(bm_worst & dense_worst) / len(union) if union else 1.0,
                "mean_dense_minus_bm25_delta": float(np.mean(dense_delta - bm_delta)),
            })
    return output


def make_structure_summary(query_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary: list[dict[str, Any]] = []
    bins: list[dict[str, Any]] = []
    feature_names = ("query_length_tokens", "switch_ratio", "language_entropy_bits", "switch_count")
    for dataset in sorted({row["dataset"] for row in query_rows}):
        subset = [row for row in query_rows if row["dataset"] == dataset]
        retrievers = sorted({key.split("_delta_official")[0] for row in subset for key in row if key.endswith("_delta_official")})
        for retriever in retrievers:
            delta_key = f"{retriever}_delta_official"
            rows = [row for row in subset if delta_key in row]
            for feature in feature_names:
                summary.append({
                    "dataset": dataset,
                    "retriever": retriever,
                    "feature": feature,
                    "query_count": len(rows),
                    "pearson_with_delta_cs": pearson((row[feature] for row in rows), (row[delta_key] for row in rows)),
                    "mean_delta_cs": float(np.mean([row[delta_key] for row in rows])),
                })
            if rows:
                values = np.asarray([row["switch_ratio"] for row in rows])
                edges = np.quantile(values, [0.0, 0.25, 0.5, 0.75, 1.0])
                for index in range(4):
                    lower, upper = edges[index], edges[index + 1]
                    selected = [row for row in rows if (row["switch_ratio"] >= lower and (row["switch_ratio"] <= upper if index == 3 else row["switch_ratio"] < upper))]
                    if selected:
                        bins.append({
                            "dataset": dataset,
                            "retriever": retriever,
                            "feature": "switch_ratio_quartile",
                            "bin": index + 1,
                            "lower": float(lower),
                            "upper": float(upper),
                            "query_count": len(selected),
                            "mean_delta_cs": float(np.mean([row[delta_key] for row in selected])),
                        })
    return summary, bins


def make_figures(rq0: list[dict[str, Any]], query_rows: list[dict[str, Any]], output: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    output.mkdir(parents=True, exist_ok=True)
    official = [row for row in rq0 if row["metric"] == "official"]
    labels = [f"{row['dataset']}\n{row['retriever']}" for row in official]
    deltas = [row["delta_cs"] for row in official]
    colors = ["#2f6f9f" if value >= 0 else "#b84a4a" for value in deltas]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(labels, deltas, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Delta_CS (official score)")
    ax.set_title("Development code-switching score change")
    fig.tight_layout()
    fig.savefig(output / "delta_cs_by_condition.png", dpi=180)
    plt.close(fig)

    for x_name, filename, xlabel in (("switch_ratio", "delta_vs_switch_ratio.png", "Detected switch ratio"), ("query_length_tokens", "delta_vs_query_length.png", "Query length (tokens)")):
        fig, ax = plt.subplots(figsize=(8, 5))
        for dataset, retriever in sorted({(row["dataset"], key.split("_delta_official")[0]) for row in query_rows for key in row if key.endswith("_delta_official")}):
            key = f"{retriever}_delta_official"
            points = [row for row in query_rows if row["dataset"] == dataset and key in row]
            ax.scatter([row[x_name] for row in points], [row[key] for row in points], s=7, alpha=0.22, label=f"{dataset}/{retriever}")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Delta_CS (official score)")
        ax.set_title(f"Development Delta_CS vs {xlabel.lower()}")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(output / filename, dpi=180)
        plt.close(fig)

    dense = "BGE_M3"
    if any(f"{dense}_delta_official" in row for row in query_rows):
        fig, ax = plt.subplots(figsize=(7, 6))
        for dataset in sorted({row["dataset"] for row in query_rows}):
            points = [row for row in query_rows if row["dataset"] == dataset and f"{dense}_delta_official" in row and "BM25_delta_official" in row]
            ax.scatter([row["BM25_delta_official"] for row in points], [row[f"{dense}_delta_official"] for row in points], s=8, alpha=0.2, label=dataset)
        limits = ax.get_xlim()
        ax.plot(limits, limits, linestyle="--", color="black", linewidth=0.8)
        ax.axhline(0, color="grey", linewidth=0.6)
        ax.axvline(0, color="grey", linewidth=0.6)
        ax.set_xlabel("BM25 Delta_CS")
        ax.set_ylabel("BGE-M3 Delta_CS")
        ax.set_title("Per-query Delta_CS complementarity")
        ax.legend()
        fig.tight_layout()
        fig.savefig(output / "bm25_bge_delta_scatter.png", dpi=180)
        plt.close(fig)


def main() -> int:
    runs = load_compact_runs()
    expected_conditions = {(dataset, retriever) for dataset in DEV_DATASETS for retriever in ("BM25", "Qwen3-Embedding-0.6B", "BGE-M3")}
    missing = sorted(expected_conditions - set(runs))
    if missing:
        raise SystemExit(f"missing required development conditions: {missing}")
    rq0 = make_rq0(runs)
    query_rows = make_query_rows(runs)
    complementarity = make_complementarity(query_rows)
    structure, bins = make_structure_summary(query_rows)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(OUTPUT_ROOT / ".matplotlib"))
    for name, rows in (("rq0_summary", rq0), ("query_diagnostics", query_rows), ("complementarity_summary", complementarity), ("structure_summary", structure), ("structure_bins", bins)):
        write_csv(OUTPUT_ROOT / f"{name}.csv", rows)
        write_markdown(OUTPUT_ROOT / f"{name}.md", rows)
    make_figures(rq0, query_rows, OUTPUT_ROOT / "figures")
    (OUTPUT_ROOT / "analysis_config.json").write_text(json.dumps({
        "scope": "development_only",
        "datasets": sorted(DEV_DATASETS),
        "retrievers": ["BM25", "Qwen3-Embedding-0.6B", "BGE-M3"],
        "bootstrap_repetitions": 2000,
        "negative_delta_means_degradation": True,
        "structure_language_id": "Unicode-name heuristic: LATIN vs CJK/Hiragana/Katakana; punctuation/digits/other letters ignored",
        "switch_ratio": "min(Latin letters, CJK letters) / known Latin+CJK letters",
        "oracle_note": "oracle_cs_score is diagnostic only and is not a deployable fusion result",
    }, indent=2), encoding="utf-8")
    print(json.dumps({"rq0_rows": len(rq0), "query_rows": len(query_rows), "complementarity_rows": len(complementarity), "structure_rows": len(structure)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

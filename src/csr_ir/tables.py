from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


def _read_rows(run_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in run_root.glob("**/summary.jsonl"):
        with path.open("r", encoding="utf-8") as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _markdown(path: Path, title: str, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "| " + " | ".join(fields) + " |"
    divider = "|" + "|".join("---" for _ in fields) + "|"
    body = ["| " + " | ".join(str(row.get(field, "")) for field in fields) + " |" for row in rows]
    path.write_text(f"# {title}\n\n{header}\n{divider}\n" + "\n".join(body) + "\n", encoding="utf-8")


def _latex(path: Path, title: str, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = "l" * len(fields)
    line_end = " " + "\\" * 2
    lines = [
        f"\\begin{{table}}[ht]",
        "\\centering",
        f"\\caption{{{title}}}",
        f"\\begin{{tabular}}{{{cols}}}",
        "\\hline",
        " & ".join(fields) + line_end,
        "\\hline",
    ]
    lines.extend(" & ".join(str(row.get(field, "")).replace("_", "\\_") for field in fields) + line_end for row in rows)
    lines += ["\\hline", "\\end{tabular}", "\\end{table}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _table_a(audit_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    rows = []
    for item in payload["resources"]:
        rows.append({
            "Dataset": item["short_name"],
            "Benchmark": item["benchmark_family"],
            "Queries": item.get("query_count"),
            "Corpus": item.get("corpus_size"),
            "Languages": ",".join(item["languages"]),
            "Split": f"{item.get('qrels_config')}/{item.get('qrels_split')}",
            "Final role": item.get("role"),
        })
    return rows


def _table_b(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = defaultdict(dict)
    for row in rows:
        if row.get("setting") not in {"original", "code_switched"} or row.get("metric") != "official":
            continue
        key = (row["dataset"], row["language_pair"], row["retriever"], row["benchmark_family"])
        grouped[key].update(row)
        grouped[key][row["setting"]] = row["score"]
    output = []
    for key, row in grouped.items():
        original = row.get("original")
        switched = row.get("code_switched")
        output.append({
            "Dataset": key[0],
            "Language Pair": key[1],
            "Model": key[2],
            "Original": original,
            "Code-Switched": switched,
            "Delta": None if original is None or switched is None else switched - original,
        })
    return sorted(output, key=lambda item: (item["Dataset"], item["Language Pair"], item["Model"]))


def _table_c(
    rows: list[dict[str, Any]],
    audit_payload: dict[str, Any],
    candidate_names: list[str],
) -> list[dict[str, Any]]:
    expected = {
        item["short_name"]: int(item["query_count"])
        for item in audit_payload["resources"]
        if item.get("role") == "development"
    }
    grouped: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        if row.get("benchmark_family") != "CS-MTEB" or row.get("metric") != "official":
            continue
        if row.get("retriever") == "BM25":
            continue
        grouped[(row["retriever"], row["dataset"], row["setting"])] = row
    output = []
    complete_retrievers: list[str] = []
    for retriever in candidate_names:
        complete = all(
            (retriever, dataset, setting) in grouped
            and int(grouped[(retriever, dataset, setting)].get("query_count", -1)) == count
            for dataset, count in expected.items()
            for setting in ("original", "code_switched")
        )
        if not complete:
            output.append({
                "Retriever": retriever,
                "Dev nDCG@10": "",
                "CS Drop": "",
                "Runtime": "incomplete dev artifacts",
                "Memory": "-",
                "Selected": "NO",
            })
            continue
        original_values = [float(grouped[(retriever, dataset, "original")]["score"]) for dataset in expected]
        switched_values = [float(grouped[(retriever, dataset, "code_switched")]["score"]) for dataset in expected]
        original = sum(original_values) / len(original_values)
        switched = sum(switched_values) / len(switched_values)
        complete_retrievers.append(retriever)
        output.append({
            "Retriever": retriever,
            "Dev nDCG@10": switched,
            "CS Drop": switched - original,
            "Runtime": "see run_config.json",
            "Memory": "see run_config.json",
            "Selected": "NO",
        })
    if len(complete_retrievers) >= 2:
        # Selection is made only from the development artifacts. The final CSR-L
        # resources never enter this ranking.
        selected = max(
            (item for item in output if item["Retriever"] in complete_retrievers),
            key=lambda item: (item["Dev nDCG@10"], item["CS Drop"]),
        )["Retriever"]
        for item in output:
            item["Selected"] = "YES" if item["Retriever"] == selected else "NO"
    return output


def _figures(rows: list[dict[str, Any]], output_dir: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    points = [row for row in rows if row.get("metric") == "official" and row.get("setting") in {"original", "code_switched"}]
    if not points:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for row in points:
        grouped[(row["dataset"], row["retriever"])][row["setting"]] = float(row["score"])
    labels = [f"{dataset}\n{model}" for dataset, model in grouped]
    original = [grouped[key].get("original", 0.0) for key in grouped]
    switched = [grouped[key].get("code_switched", 0.0) for key in grouped]
    x = list(range(len(labels)))
    width = 0.38
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 0.7), 5))
    ax.bar([item - width / 2 for item in x], original, width, label="Original")
    ax.bar([item + width / 2 for item in x], switched, width, label="Code-switched")
    ax.set_xticks(x, labels, rotation=60, ha="right")
    ax.set_ylabel("Official score")
    ax.set_title("Original vs code-switched retrieval performance")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "original_vs_codeswitched.png", dpi=160)
    plt.close(fig)

    drop = [switched_value - original_value for original_value, switched_value in zip(original, switched)]
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 0.7), 5))
    ax.bar(x, drop)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x, labels, rotation=60, ha="right")
    ax.set_ylabel("Code-switched − original")
    ax.set_title("Code-switching performance drop")
    fig.tight_layout()
    fig.savefig(output_dir / "code_switching_drop.png", dpi=160)
    plt.close(fig)


def generate(run_root: str, audit_path: str, output_dir: str, config_path: str = "configs/benchmarks.yaml") -> None:
    root = Path(output_dir)
    rows = _read_rows(Path(run_root))
    audit_payload = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    catalog = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    candidate_names = [model["name"] for model in catalog["models"] if model.get("selection_role") == "candidate"]
    table_a = _table_a(Path(audit_path))
    table_b = _table_b(rows)
    table_c = _table_c(rows, audit_payload, candidate_names)
    specs = [
        ("table_a", "Table A — Benchmark audit", ["Dataset", "Benchmark", "Queries", "Corpus", "Languages", "Split", "Final role"], table_a),
        ("table_b", "Table B — Baseline performance", ["Dataset", "Language Pair", "Model", "Original", "Code-Switched", "Delta"], table_b),
        ("table_c", "Table C — Retriever selection", ["Retriever", "Dev nDCG@10", "CS Drop", "Runtime", "Memory", "Selected"], table_c),
    ]
    for stem, title, fields, data in specs:
        _write_csv(root / f"{stem}.csv", data, fields)
        _markdown(root / f"{stem}.md", title, fields, data)
        _latex(root / f"{stem}.tex", title, fields, data)
    _figures(rows, root / "figures")
    (root / "selection.json").write_text(json.dumps({"selected": next((row["Retriever"] for row in table_c if row["Selected"] == "YES"), None), "selection_source": "CS-MTEB development artifacts only"}, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate artifact-backed tables and diagnostics.")
    parser.add_argument("--run-root", default="results/runs")
    parser.add_argument("--audit", default="results/audit/dataset_overlap.json")
    parser.add_argument("--output-dir", default="results/tables")
    parser.add_argument("--config", default="configs/benchmarks.yaml")
    args = parser.parse_args(argv)
    generate(args.run_root, args.audit, args.output_dir, args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

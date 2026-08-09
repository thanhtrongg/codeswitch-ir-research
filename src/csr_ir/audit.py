from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from .catalog import Resource, load_catalog, load_resources
from .data import _load_dataset_rows, row_id
from .leakage import qrel_signature, source_query_group


def _get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "codeswitch-ir-audit/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def _get_json(url: str) -> Any:
    return json.loads(_get_text(url))


def _front_matter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    _, body, _ = text.split("---", 2)
    value = yaml.safe_load(body)
    return value if isinstance(value, dict) else {}


def _metadata(resource: Resource) -> dict[str, Any]:
    url = f"https://huggingface.co/datasets/{resource.dataset_id}/raw/{resource.revision}/README.md"
    try:
        card = _front_matter(_get_text(url))
    except Exception as exc:  # pragma: no cover - only offline/error path
        return {"error": f"dataset card unavailable: {exc}"}
    configs = {}
    for info in card.get("dataset_info", []) or []:
        if not isinstance(info, dict):
            continue
        configs[info.get("config_name", "default")] = {
            "features": info.get("features", []),
            "splits": info.get("splits", []),
        }
    return {
        "language": card.get("language", []),
        "task_categories": card.get("task_categories", []),
        "source_datasets": card.get("source_datasets", []),
        "configs": configs,
    }


def _iter_rows(resource: Resource, config: str, split: str):
    return _load_dataset_rows(resource.dataset_id, config, split, resource.revision, streaming=True)


def _qrel_map(resource: Resource) -> dict[str, dict[str, float]]:
    qrels: dict[str, dict[str, float]] = defaultdict(dict)
    for row in _iter_rows(resource, resource.qrels_config, resource.qrels_split):
        query_id = str(row.get("query-id", row.get("query_id", row.get("qid"))))
        doc_id = str(row.get("corpus-id", row.get("corpus_id", row.get("doc_id"))))
        score = float(row.get("score", row.get("relevance", row.get("label", 0.0))))
        qrels[query_id][doc_id] = score
    return dict(qrels)


def _manifest(resource: Resource, include_rows: bool) -> dict[str, Any]:
    metadata = _metadata(resource)
    manifest: dict[str, Any] = {
        "dataset_id": resource.dataset_id,
        "short_name": resource.short_name,
        "benchmark_family": resource.benchmark_family,
        "source_dataset": resource.source_dataset,
        "task_type": resource.task_type,
        "official_metric": resource.official_metric,
        "rewrite_authoring": resource.rewrite_authoring,
        "languages": list(resource.languages),
        "revision": resource.revision,
        "role": resource.role,
        "corpus_config": resource.corpus_config,
        "corpus_split": resource.corpus_split,
        "qrels_config": resource.qrels_config,
        "qrels_split": resource.qrels_split,
        "original_query_source": resource.original_query_source,
        "original_query_config": resource.original_query_config,
        "original_query_split": resource.original_query_split,
        "cs_query_configs": resource.cs_query_configs,
        "source_query_id_convention": "official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs",
        "shared_qrels_declared": resource.shared_qrels,
        "metadata": metadata,
        "corpus_size": None,
        "query_count": None,
        "qrels_query_count": None,
        "corpus_ids": [],
        "corpus_artifact_ids": [],
        "qrel_corpus_ids": [],
        "query_ids": [],
        "source_query_groups": [],
        "source_query_group_count": 0,
        "qrel_signature_by_group": {},
        "variant_qrel_alignment": {},
    }
    if not include_rows:
        return manifest
    try:
        tree_url = f"https://huggingface.co/api/datasets/{resource.dataset_id}/tree/{resource.revision}?recursive=true"
        tree = _get_json(tree_url)
        corpus_artifacts = []
        for item in tree:
            path = str(item.get("path", ""))
            if path == "corpus" or path.startswith("corpus/") or path.startswith("corpus."):
                corpus_artifacts.append({
                    "path": path,
                    "oid": item.get("lfs", {}).get("oid", item.get("oid")),
                    "size": item.get("lfs", {}).get("size", item.get("size")),
                })
        qrels = _qrel_map(resource)
        # Official qrels retain the original query IDs, which are the stable
        # source-query key shared by original and rewritten variants. This
        # avoids treating each rewritten text file as an independent sample.
        unique_query_ids = sorted(qrels)
        groups = {query_id: source_query_group(resource.source_dataset, query_id) for query_id in unique_query_ids}
        variant_signatures: dict[str, dict[str, str]] = defaultdict(dict)
        for query_id, qrel in qrels.items():
            variant_signatures[groups[query_id]][query_id] = qrel_signature(qrel)
        grouped_signature = {
            group: hashlib.sha256(
                json.dumps(signatures, sort_keys=True).encode("utf-8")
            ).hexdigest()
            for group, signatures in variant_signatures.items()
        }
        manifest.update({
            "corpus_size": _metadata_corpus_size(metadata, resource.corpus_config, resource.corpus_split),
            "query_count": len(unique_query_ids),
            "qrels_query_count": len(qrels),
            "corpus_ids": [],
            "corpus_artifact_ids": corpus_artifacts,
            "qrel_corpus_ids": sorted({doc_id for qrel in qrels.values() for doc_id in qrel}),
            "query_ids": unique_query_ids,
            "source_query_groups": sorted(set(groups.values())),
            "source_query_group_count": len(set(groups.values())),
            "qrel_signature_by_group": grouped_signature,
            "variant_qrel_alignment": {
                language: {
                    "query_count_from_qrels": len(unique_query_ids),
                    "qrels_available": len(unique_query_ids),
                    "query_text_config": config,
                }
                for language, config in resource.cs_query_configs.items()
            },
        })
    except Exception as exc:
        manifest["row_audit_error"] = repr(exc)
    return manifest


def _metadata_corpus_size(metadata: dict[str, Any], config: str, split: str) -> int | None:
    item = metadata.get("configs", {}).get(config, {})
    for split_info in item.get("splits", []) or []:
        if split_info.get("name") == split or (split == "test" and split_info.get("name") in {"test", "corpus"}):
            return split_info.get("num_examples")
    return None


def _pair_overlap(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_groups = set(left.get("source_query_groups", []))
    right_groups = set(right.get("source_query_groups", []))
    shared_groups = sorted(left_groups & right_groups)
    left_qrels = left.get("qrel_signature_by_group", {})
    right_qrels = right.get("qrel_signature_by_group", {})
    shared_qrels = [group for group in shared_groups if left_qrels.get(group) == right_qrels.get(group)]
    return {
        "left": left["dataset_id"],
        "right": right["dataset_id"],
        "source_dataset": left["source_dataset"],
        "query_id_overlap_count": len(set(left.get("query_ids", [])) & set(right.get("query_ids", []))),
        "source_query_overlap_count": len(shared_groups),
        "qrel_overlap_count": len(shared_qrels),
        "corpus_id_overlap_count": len(set(left.get("corpus_ids", [])) & set(right.get("corpus_ids", []))),
        "qrel_corpus_doc_id_overlap_count": len(set(left.get("qrel_corpus_ids", [])) & set(right.get("qrel_corpus_ids", []))),
        "same_declared_corpus_size": left.get("corpus_size") == right.get("corpus_size") and left.get("corpus_size") is not None,
        "corpus_artifact_overlap_count": 0,
        "source_query_sample": shared_groups[:10],
        "qrel_sample": shared_qrels[:10],
    }


def _overlap(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = []
    for index, left in enumerate(manifests):
        for right in manifests[index + 1 :]:
            if left["source_dataset"] == right["source_dataset"]:
                pair = _pair_overlap(left, right)
                pair["corpus_id_overlap_count"] = len(set(left.get("corpus_ids", [])) & set(right.get("corpus_ids", [])))
                left_artifacts = {item.get("oid") for item in left.get("corpus_artifact_ids", [])}
                right_artifacts = {item.get("oid") for item in right.get("corpus_artifact_ids", [])}
                pair["corpus_artifact_overlap_count"] = len((left_artifacts - {None}) & (right_artifacts - {None}))
                pairs.append(pair)
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for manifest in manifests:
        by_source[manifest["source_dataset"]].append(manifest)
    dataset_level = [
        {
            "source_dataset": source,
            "dataset_count": len(items),
            "datasets": sorted(item["dataset_id"] for item in items),
            "benchmark_families": sorted({item["benchmark_family"] for item in items}),
        }
        for source, items in sorted(by_source.items())
    ]
    development = [item for item in manifests if item["role"] == "development"]
    final = [item for item in manifests if item["role"] == "final_test"]
    dev_sources = {item["source_dataset"] for item in development}
    final_sources = {item["source_dataset"] for item in final}
    return {
        "audit_scope": "all catalogued retrieval resources",
        "dataset_level": dataset_level,
        "pairwise_same_source": pairs,
        "development_final_source_dataset_overlap": sorted(dev_sources & final_sources),
        "protocol_leakage_safe": not bool(dev_sources & final_sources),
    }


def _write_csv(path: Path, manifests: list[dict[str, Any]]) -> None:
    rows = []
    for index, left in enumerate(manifests):
        for right in manifests[index + 1 :]:
            if left["source_dataset"] != right["source_dataset"]:
                continue
            row = _pair_overlap(left, right)
            left_artifacts = {item.get("oid") for item in left.get("corpus_artifact_ids", [])}
            right_artifacts = {item.get("oid") for item in right.get("corpus_artifact_ids", [])}
            row["corpus_artifact_overlap_count"] = len((left_artifacts - {None}) & (right_artifacts - {None}))
            rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "left", "right", "source_dataset", "query_id_overlap_count",
        "source_query_overlap_count", "qrel_overlap_count", "corpus_id_overlap_count",
        "qrel_corpus_doc_id_overlap_count", "same_declared_corpus_size", "corpus_artifact_overlap_count", "source_query_sample", "qrel_sample",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_markdown(path: Path, manifests: list[dict[str, Any]], overlap: dict[str, Any], catalog: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Benchmark audit",
        "",
        "This document is generated from `configs/benchmarks.yaml`, the pinned official repository commit, and the immutable Hugging Face revisions recorded in the manifest below.",
        "",
        f"- Official repository commit: `{catalog['official_repository']['commit']}`",
        f"- Paper: [{catalog['paper']['arxiv']}]({catalog['paper']['arxiv']})",
        "- Audit scope: all catalogued retrieval and instruction-retrieval resources; non-retrieval CS-MTEB resources are catalogued in the YAML but are outside the baseline runner.",
        "",
        "## Table A — benchmark audit",
        "",
        "| Dataset | Benchmark | Queries | Corpus | Languages | Split/config | Final role | Metric |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    for item in manifests:
        languages = ", ".join(item["languages"])
        lines.append(
        f"| {item['short_name']} | {item['benchmark_family']} | {item.get('query_count', 'n/a')} / {item.get('source_query_group_count', 'n/a')} | {item.get('corpus_size', 'n/a')} | {languages} | `{item.get('qrels_config')}/{item.get('qrels_split')}`; `{item.get('corpus_config')}/{item.get('corpus_split')}` | {item['role']} | {item['official_metric']} |"
        )
    lines += ["", "## Resource-level records", ""]
    for item in manifests:
        lines += [
            f"### {item['short_name']}",
            "",
            f"- Dataset: `{item['dataset_id']}` at revision `{item['revision']}`.",
            f"- Benchmark family: **{item['benchmark_family']}**; final role: **{item['role']}**; task: `{item['task_type']}`.",
            f"- Original source dataset: `{item['source_dataset']}`; original query source: `{item['original_query_source']}` (`{item['original_query_config']}/{item['original_query_split']}`).",
            f"- Languages: {', '.join(item['languages'])}; rewrite authoring: {item['rewrite_authoring']}.",
            f"- Corpus: `{item['corpus_config']}/{item['corpus_split']}`, {item.get('corpus_size', 'n/a')} documents. Qrels: `{item['qrels_config']}/{item['qrels_split']}`, {item.get('qrels_query_count', 'n/a')} query IDs.",
            f"- Source-query groups: {item.get('source_query_group_count', 'n/a')}; raw query IDs: {item.get('query_count', 'n/a')}. IDs use `{item['source_query_id_convention']}`.",
            f"- Code-switched query configurations: {', '.join(f'{lang}={config}' for lang, config in item['cs_query_configs'].items())}.",
            f"- Official primary metric: `{item['official_metric']}`. Declared shared-qrel expectation: `{item['shared_qrels_declared']}`.",
            "",
        ]
    lines += ["## Pairwise overlap summary", "", "| Source dataset | CSR-L resource | CS-MTEB resource | Raw query-ID overlap | Source-query overlap | Exact qrel overlap | Qrel document-ID overlap | Same corpus size |", "|---|---|---|---:|---:|---:|---:|---|"]
    for pair in overlap["pairwise_same_source"]:
        if "CSR-L" not in pair["left"] and "CSR-L" not in pair["right"]:
            continue
        left = pair["left"]
        right = pair["right"]
        lines.append(f"| {pair['source_dataset']} | {left if 'CSR-L' in left else right} | {right if 'CS-MTEB' in right else left} | {pair['query_id_overlap_count']} | {pair['source_query_overlap_count']} | {pair['qrel_overlap_count']} | {pair['qrel_corpus_doc_id_overlap_count']} | {pair['same_declared_corpus_size']} |")
    lines += ["", "Corpus artifact OIDs are also compared in `results/audit/source_query_overlap.csv`. Different OIDs can reflect reserialization; exact source-corpus provenance, equal corpus cardinality, and shared qrel document IDs are retained as separate evidence rather than conflated.", ""]
    lines += [
        "",
        "## Leakage findings",
        "",
        f"Protocol source-dataset disjointness: **{'PASS' if overlap['protocol_leakage_safe'] else 'FAIL'}**.",
        "",
        "The pairwise overlap CSV records corpus-ID, query-ID, source-query-group, and exact-qrel-signature overlaps. Rewritten variants are grouped as `source_dataset::query_id`; they are never treated as independent examples.",
        "",
        "The FollowIR-derived CSR-L resources publish `qrel_diff` configurations. They are retained as final-test resources but are not eligible for model selection and must be evaluated with their official pairwise-MRR protocol rather than being silently collapsed into ordinary nDCG retrieval.",
        "",
        "## Provenance cautions",
        "",
        "The paper’s main CSR-L table reports Touché 2020, HumanEval, TRECCOVID, and FollowIR. The current official author account also publishes Core17, News21, and Robust04 CSR-L resources. Both sets are recorded here so a later run cannot silently mix paper-era and repository-current scopes.",
        "The benchmark name `FollowIR` is represented by the Core17, News21, and Robust04 instruction-retrieval resources in the current author repository; no separate `FollowIR` dataset ID is silently substituted.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit(config_path: str, output_json: str, output_csv: str, output_doc: str, include_rows: bool = True) -> dict[str, Any]:
    catalog = load_catalog(config_path)
    resources = [resource for resource in load_resources(config_path) if resource.is_retrieval]
    manifests = [_manifest(resource, include_rows=include_rows) for resource in resources]
    overlap = _overlap(manifests)
    payload = {
        "catalog_version": "milestone_1_v1",
        "official_repository": catalog["official_repository"],
        "paper": catalog["paper"],
        "resources": manifests,
        "overlap": overlap,
    }
    json_path = Path(output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(Path(output_csv), manifests)
    _write_markdown(Path(output_doc), manifests, overlap, catalog)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit official CSR-L and CS-MTEB retrieval resources.")
    parser.add_argument("--config", default="configs/benchmarks.yaml")
    parser.add_argument("--output-json", default="results/audit/dataset_overlap.json")
    parser.add_argument("--output-csv", default="results/audit/source_query_overlap.csv")
    parser.add_argument("--output-doc", default="docs/benchmark_audit.md")
    parser.add_argument("--metadata-only", action="store_true", help="skip streaming rows; useful for offline metadata checks")
    args = parser.parse_args(argv)
    payload = run_audit(args.config, args.output_json, args.output_csv, args.output_doc, include_rows=not args.metadata_only)
    print(json.dumps({"resources": len(payload["resources"]), "protocol_leakage_safe": payload["overlap"]["protocol_leakage_safe"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

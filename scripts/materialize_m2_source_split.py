"""Materialize the preregistered Climate source-query split from an existing run.

This utility reads only the provenance-qualified source_query_id field from the
completed Milestone 1 per-query artifact. It does not read scores, qrels,
rankings, or any final-test artifact, and it does not launch a retriever.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SOURCE_QUERY_RE = re.compile(r'"source_query_id":"([^"]+)"')


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_lines(values: list[str]) -> str:
    return hashlib.sha256(("\n".join(values) + "\n").encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()

    group_counts: dict[str, int] = {}
    with args.input.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            match = SOURCE_QUERY_RE.search(line)
            if not match:
                raise ValueError(f"line {line_number}: missing source_query_id")
            group = match.group(1)
            group_counts[group] = group_counts.get(group, 0) + 1

    groups = sorted(group_counts)
    if len(groups) != 1000:
        raise ValueError(f"expected 1000 Climate source-query groups, found {len(groups)}")
    if sorted(set(group_counts.values())) != [2]:
        raise ValueError(f"expected exactly two variants per group, found counts {sorted(set(group_counts.values()))}")

    keyed = sorted(
        groups,
        key=lambda group: hashlib.sha256(f"{args.seed}|{group}".encode("utf-8")).hexdigest(),
    )
    fit_count = int(len(keyed) * 0.60)
    validation_count = int(len(keyed) * 0.20)
    assignments = {
        group: (
            "fit"
            if index < fit_count
            else "validation"
            if index < fit_count + validation_count
            else "post_exploratory_frozen_holdout"
        )
        for index, group in enumerate(keyed)
    }
    ordered_assignments = [
        {"source_query_id": group, "assignment": assignments[group]}
        for group in sorted(groups)
    ]
    payload = {
        "protocol_id": "milestone_2_rq1_v1",
        "resource": "UTokyo-Yokoya-Lab/ClimateFEVER_hardnegatives_CS-MTEB",
        "short_name": "ClimateFEVERHardNegatives",
        "language_pair": "zh-en",
        "unit": "source_dataset::query_id",
        "seed": args.seed,
        "algorithm": "sort source_query_id by sha256(f'{seed}|{source_query_id}'), then assign contiguous 60/20/20 blocks",
        "fit_fraction": 0.60,
        "validation_fraction": 0.20,
        "post_exploratory_frozen_holdout_fraction": 0.20,
        "group_count": len(groups),
        "variant_count": sum(group_counts.values()),
        "group_variant_counts": {str(count): list(group_counts.values()).count(count) for count in sorted(set(group_counts.values()))},
        "source_query_groups_sha256": sha256_lines(groups),
        "assignment_sha256": hashlib.sha256(canonical_json(ordered_assignments)).hexdigest(),
        "assignments": ordered_assignments,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .catalog import load_resources


def load_protocol(path: str | Path = "configs/data_protocol.yaml") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_protocol(catalog_path: str | Path, protocol_path: str | Path) -> list[str]:
    catalog = {resource.dataset_id: resource for resource in load_resources(catalog_path)}
    protocol = load_protocol(protocol_path)
    errors: list[str] = []
    dev_ids = protocol["development"]["datasets"]
    final_ids = protocol["final_test"]["datasets"]
    missing = [dataset_id for dataset_id in dev_ids + final_ids if dataset_id not in catalog]
    if missing:
        errors.append(f"protocol datasets missing from catalog: {missing}")
    dev_sources = {catalog[dataset_id].source_dataset for dataset_id in dev_ids if dataset_id in catalog}
    final_sources = {catalog[dataset_id].source_dataset for dataset_id in final_ids if dataset_id in catalog}
    overlap = sorted(dev_sources & final_sources)
    if overlap:
        errors.append(f"development/final source-query leakage: {overlap}")
    if protocol["final_test"].get("untouched_after_freeze") is not True:
        errors.append("final test is not marked untouched_after_freeze")
    if protocol["final_test"].get("selection_allowed") is not False:
        errors.append("final test is marked selection_allowed")
    if protocol["selection_rule"] != "development_only":
        errors.append("model selection rule is not development_only")
    if protocol["internal_splits"]["enabled"] and protocol["internal_splits"]["method"] != "group_shuffle_split":
        errors.append("internal split is not source-query-group based")
    return errors


def assert_protocol(catalog_path: str | Path, protocol_path: str | Path) -> None:
    errors = validate_protocol(catalog_path, protocol_path)
    if errors:
        raise AssertionError("; ".join(errors))

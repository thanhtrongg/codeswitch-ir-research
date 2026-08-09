import json
from pathlib import Path

from csr_ir.catalog import resources_by_id
from csr_ir.data import load_corpus_and_qrels, load_pairs
from csr_ir.protocol import assert_protocol
from csr_ir.validate_artifacts import validate_run


if __name__ == "__main__":
    assert_protocol("configs/benchmarks.yaml", "configs/data_protocol.yaml")
    audit = json.loads(Path("results/audit/dataset_overlap.json").read_text(encoding="utf-8"))
    if not audit["overlap"]["protocol_leakage_safe"]:
        raise AssertionError("official audit found development/final source overlap")
    resources = resources_by_id("configs/benchmarks.yaml")
    for path in Path("results/runs").glob("**/per_query.jsonl"):
        config = json.loads((path.parent / "run_config.json").read_text(encoding="utf-8"))
        resource = resources[config["resource_id"]]
        pairs = load_pairs(resource, config["language"])
        corpus, _ = load_corpus_and_qrels(resource)
        expected_pairs = {pair.source_query_id: pair.qrels for pair in pairs}
        print(path, validate_run(path, expected_pairs=expected_pairs, corpus_ids=set(corpus), expected_depth=config.get("retrieval_depth", 1000)))
    print("audit/artifacts: PASS")

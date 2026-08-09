# GitHub repository setup

This report records the first private GitHub archive operation for the
repository.

- Date: 2026-08-09
- Repository: `thanhtrongg/codeswitch-ir-research`
- Remote URL: <https://github.com/thanhtrongg/codeswitch-ir-research>
- Visibility: **PRIVATE**
- Branch: `main`
- Initial archive commit: `7e661bd1dca051c43e4e3ebbf55a3c5bcbfb589c`
- Upstream: `origin/main`

## Archive policy

Excluded from Git:

- virtual environments and Python bytecode/cache directories;
- `.env` files, private credentials, tokens, and key/certificate files;
- downloaded raw datasets and local data/download directories;
- model weights, embeddings, vector indexes, and caches;
- large raw `results/runs/**/per_query.jsonl` outputs;
- temporary, backup, and local-agent metadata files.

Compact summaries, reports, protocol manifests, ledgers, tables, plot data,
and paper figures were retained. The largest tracked file is
`results/audit/dataset_overlap.json` at 4.04 MB.

## Validation

- `python -m pytest -q`: **33 passed**
- `python scripts/validate_protocol.py`: **PASS**
- JSON/YAML parsing: **28 JSON and 8 YAML files parsed successfully**
- Security scan: **no credential files or targeted secret assignments found**
- Largest-file audit: **no staged file exceeded 50 MB or 100 MB**

## Protected research boundaries

- No retrieval experiment, dense encoding job, or GPU run was launched.
- ClimateFEVER Milestone 2 holdout data/results remain historically consumed.
- ArguAna outcomes were not accessed during confirmatory transfer.
- The final CSR-L boundary remains untouched.
- No post-holdout retuning or Milestone 3 experiment was performed.
- No research result, metric, hash, protocol YAML, gate decision, or frozen
  report was changed.

# Reproducibility notes

## Environment

- Supported Python: `>=3.10`, as declared in `pyproject.toml`.
- Local validation environment: Python `3.11.0` in `.venv`.
- Dependencies: install from the existing `requirements.txt` or the project
  dependencies in `pyproject.toml`; do not replace them with a generated
  `pip freeze` file.
- GPU, model downloads, and benchmark downloads are not required for the
  lightweight validation commands.

## Cache policy

Set `CSR_IR_CACHE_ROOT` to a machine-local directory when running retrieval
code. The default is the ignored repository-local `.cache/csr_ir` directory.
The example variable is documented in [`.env.example`](.env.example); it does
not contain credentials.

## Seeds and protocol

- Frozen protocol seed: `20260809`.
- Milestone 2 source split: 600 fit, 200 validation, and 200 procedurally
  protected holdout source-query groups.
- The authoritative protocol and integrity records are in `configs/` and
  `results/protocol/`.
- Existing result artifacts, hashes, manifests, ledgers, and metrics are
  preserved as recorded.

## Lightweight validation

From the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
python scripts/validate_protocol.py
```

These checks validate infrastructure and frozen semantics. They do not rerun
retrieval, encode a corpus, download protected data, or access CSR-L.

## Baseline artifacts

Compact summaries, tables, plot data, figures, and manifests are retained.
Large raw per-query JSONL files, downloaded datasets, model weights,
embeddings, indexes, virtual environments, and caches are excluded from Git by
policy. Third-party data must be obtained from the official sources and under
their original licenses in any separately approved reproduction.

## Protected experiments

Do not casually rerun `scripts/run_milestone2.py` or
`scripts/run_milestone2_5.py`, launch a new dense encoder, access ArguAna
transfer outcomes, or open the CSR-L final boundary. Milestone 2 failed its
preregistered ClimateFEVER source gate, and Milestone 2.6 authorized no new
experiment. Any future work needs a new approved protocol and must preserve
the archived negative result.

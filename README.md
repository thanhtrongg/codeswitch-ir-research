# Code-Switching Information Retrieval — Robustness & Relative Retriever Reliability

This repository is the reproducible research record for an empirical study of
code-switched information retrieval. It documents benchmark auditing,
leakage-safe sparse and dense baselines, and a frozen test of whether
unlabeled retrieval-behavior signals could identify which fixed retriever should
be trusted per query.

> **Current status:** **NO-GO — NO DEFENSIBLE NEW HYPOTHESIS FOUND**

The repository archives a preregistered negative result and the subsequent
fresh novelty audit. It does not claim a successful proposed method,
state-of-the-art performance, a published paper, successful transfer, or a
final CSR-L result.

## Research motivation

Code-switching can degrade retrieval, and sparse BM25 and dense Qwen retrieval
can fail on different queries. This project investigated whether fixed,
unlabeled retrieval-behavior and query-performance-prediction (QPP) signals
could select the more reliable retriever per query without training a new
retriever, score fusion, or access to protected final data.

## Research progression

| Milestone | Scope and outcome |
| --- | --- |
| 1 | Audited candidate benchmarks, established leakage-safe baselines, and selected Qwen as the dense primary baseline. |
| 1.5–1.5d | Audited novelty, hardened semantic definitions, and froze the Milestone 2 protocol. |
| 2 | Executed the frozen QPP hard selector on the ClimateFEVER source holdout; the preregistered source gate failed. |
| 2.5 | Diagnosed weak identifiability, class imbalance, distribution shift, and costly false BM25 switches. |
| 2.6 | Performed a fresh literature/novelty audit; no defensible new hypothesis survived. |

See the [research navigation index](docs/RESEARCH_INDEX.md) for the complete
chronological record.

## Main empirical finding

BM25/Qwen complementarity exists in the development evidence, but the frozen
normalized score-margin/top-k-dispersion selector did not reliably identify
BM25-winning opportunities under the ClimateFEVER zh-en setting. The selector
failed the preregistered source gate:

| ClimateFEVER code-switched holdout metric | nDCG@10 |
| --- | ---: |
| Qwen fixed primary baseline | 0.196078718 |
| Frozen selector | 0.182517423 |
| Selector − Qwen | -0.013561295 |
| 95% paired-bootstrap CI | [-0.032543918, 0.004811338] |
| Oracle diagnostic-only upper bound | 0.245614707 |
| RRF fixed baseline-only comparator | 0.198827500 |

The postmortem counted 8 beneficial BM25 switches and 60 harmful BM25
switches. These are protected-holdout diagnostics, not evidence that QPP in
general does not work for code-switching. Oracle is diagnostic-only; RRF is a
baseline-only comparator.

## Final research status

**NO-GO — NO DEFENSIBLE NEW HYPOTHESIS FOUND**

The fresh Milestone 2.6 audit found substantial overlap with existing work on
QPP, retriever routing, adaptive retrieval, selective risk, and hybrid
retrieval. H1, H2, and H3 were rejected, H4 was not proposed, and no Milestone
3 experiment or preregistration was authorized.

## Reproducibility and protocol

The registered workflow was:

```text
TRAIN/FIT → VALIDATION → FREEZE → HOLDOUT
```

Protected boundaries were enforced at the source-query-group level. The
Milestone 2 holdout was procedurally protected after the earlier exploratory
Milestone 1 analysis; it is not described as historically untouched. The six
CSR-L resources remain the truly untouched final boundary.

The lightweight checks are:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
python scripts/validate_protocol.py
```

The [reproducibility notes](REPRODUCIBILITY.md) record environment assumptions,
seeds, cache policy, and protected-run restrictions. Do not casually rerun the
Milestone 2 or Milestone 2.5 execution scripts, access CSR-L, or attempt a new
dense encoding run; those actions require a separately approved protocol.

## Repository structure

| Path | Contents |
| --- | --- |
| `src/` | Baseline retrieval, benchmark catalog, leakage, metrics, and cache infrastructure. |
| `scripts/` | Audit, validation, analysis, and historical milestone runners. |
| `configs/` | Benchmark provenance, data boundaries, and frozen protocol YAML. |
| `docs/` | Milestone reports, preregistration, postmortem, novelty audits, and navigation. |
| `results/` | Compact metrics, tables, figures, plot data, manifests, ledgers, and milestone summaries. |
| `tests/` | Lightweight infrastructure and semantic-freeze tests. |

## Data and artifact boundary

Datasets, model weights, embeddings, indexes, caches, and other downloaded
artifacts are not redistributed here. Official benchmark identifiers,
revisions, provenance notes, and the frozen data boundary are recorded in
[`configs/benchmarks.yaml`](configs/benchmarks.yaml),
[`configs/data_protocol.yaml`](configs/data_protocol.yaml), and the linked
reports. Third-party datasets retain their original licenses.

Large raw per-query run outputs are intentionally excluded by `.gitignore`;
compact summaries and analysis outputs remain in the archive. This keeps the
repository reviewable without changing the research conclusions or the
historical local artifacts.

Research integrity boundaries:

- ClimateFEVER Milestone 2 holdout data/results were consumed historically.
- ArguAna transfer was not executed after the ClimateFEVER source gate failed.
- The final CSR-L test boundary remained untouched.
- No post-holdout retuning was performed.
- No Milestone 3 experiment was run.

## References

The complete verified bibliography is in
[`docs/milestone2_6_bibliography.md`](docs/milestone2_6_bibliography.md). The
central prior-work families include:

- [CSR-L / CS-MTEB](https://aclanthology.org/2026.findings-acl.636/)
- [ContrastiveMix](https://aclanthology.org/2024.naacl-short.17/)
- [Litschko et al., artificially code-switched training](https://aclanthology.org/2023.findings-acl.193/)
- [MoR](https://aclanthology.org/2025.emnlp-main.601/)
- [RouterRetriever](https://ojs.aaai.org/index.php/AAAI/article/view/33306)
- [QuDAR](https://aclanthology.org/2026.acl-long.1791/)
- [Query-Adaptive Hybrid Search](https://www.mdpi.com/2504-4990/8/4/91)
- [Dense query-performance prediction](https://eprints.gla.ac.uk/328868/)

## License and citation

Source code is released under the [MIT License](LICENSE). The repository does
not relicense third-party benchmarks or datasets. A minimal
[`CITATION.cff`](CITATION.cff) is provided; author identity fields were omitted
because no safe author metadata was available locally.

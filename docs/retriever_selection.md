# Retriever selection

## Frozen rule

Selection uses development data only: ArguAna and ClimateFEVERHardNegatives, Chinese-English queries, official nDCG@10 as the primary quality criterion, and absolute Delta_CS as the robustness tie-break. CSR-L was not run and cannot affect this decision.

The candidates are pinned in `configs/benchmarks.yaml`:

| Retriever | Model revision | Selection status |
|---|---|---|
| Qwen3-Embedding-0.6B | `Qwen/Qwen3-Embedding-0.6B@97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` | complete |
| BGE-M3 | `BAAI/bge-m3@5617a9f61b028005a4858fdac845db406aefb181` | complete |
| multilingual-e5-large | `intfloat/multilingual-e5-large@3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3` | not run; optional candidate |

## Development results

Official nDCG@10:

| Dataset | Retriever | Original | Code-switched | Delta_CS | Relative degradation |
|---|---|---:|---:|---:|---:|
| ArguAna | Qwen3-Embedding-0.6B | 0.440355 | 0.440685 | +0.000329 | +0.000748 |
| ArguAna | BGE-M3 | 0.378846 | 0.371870 | -0.006976 | -0.018415 |
| ClimateFEVERHardNegatives | Qwen3-Embedding-0.6B | 0.214748 | 0.185079 | -0.029669 | -0.138156 |
| ClimateFEVERHardNegatives | BGE-M3 | 0.094373 | 0.087955 | -0.006418 | -0.068011 |

The complete metric and per-query results are in `results/analysis/development_only/` and `results/tables/table_b.*`. Both candidates have complete 1,406-pair ArguAna and 1,000-pair ClimateFEVER artifacts. Strict artifact validation passed.

## Decision

Selected main dense retriever: **Qwen3-Embedding-0.6B**, revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`.

The selection is based on higher development code-switched nDCG@10 on both datasets (0.440685 vs 0.371870 on ArguAna; 0.185079 vs 0.087955 on ClimateFEVER). The equal-weight mean of the two development code-switched scores is 0.312882 for Qwen and 0.229912 for BGE. Qwen is also approximately unchanged on ArguAna, although BGE has the smaller absolute drop on ClimateFEVER. This is a transparent quality-first decision; no post-hoc fusion or tuning was used.

BGE is computationally more practical in the recorded runs: ArguAna indexing/query time was 181.63/105.38 seconds and ClimateFEVER was 1,045.43/76.99 seconds. Qwen ClimateFEVER indexing/query time was 2,261.27/318.64 seconds. The new persistent cache was validated and saved for BGE ClimateFEVER; completed Qwen runs were not rerun solely to backfill a cache.

All dense runs used CUDA FP16, `torch.inference_mode()`, mean masked last-hidden-state pooling, L2 normalization, max length 512, truncation, dynamic padding, and retrieval depth 1000. The cache fingerprints resource and revision, corpus content and document order, model and revision, embedding shape, pooling, normalization, prefix, tokenizer settings, dtype, and cache version.

This selection is development-only and does not imply that Qwen is universally more robust to code-switching. ClimateFEVER shows meaningful degradation for Qwen, and the per-query complementarity analysis remains relevant to the next human-reviewed milestone. No mitigation method was implemented.

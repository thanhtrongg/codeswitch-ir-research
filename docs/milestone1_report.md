# Milestone 1 report: benchmark audit, retriever selection, and leakage-safe baseline

Status: **CONDITIONAL GO** for a human-reviewed next milestone. Milestone 1 stops here: no final CSR-L evaluation, retriever training, score fusion, adaptive alpha, gating, or mitigation method was implemented.

## 1. Executive summary

The benchmark and leakage audit supports a clean development-only experiment. The two eligible development datasets are ArguAna and ClimateFEVERHardNegatives; the six CSR-L resources remain untouched final-test data. BM25 shows a clear code-switching degradation on both datasets. The two complete dense candidates show different behavior: Qwen3-Embedding-0.6B is strongest on development code-switched nDCG@10 and is nearly unchanged on ArguAna, but drops substantially on ClimateFEVER; BGE-M3 is weaker in absolute nDCG but has smaller drops.

Qwen3-Embedding-0.6B is selected as the single development-only dense backbone because it has the higher code-switched nDCG@10 on both datasets (0.440685 vs 0.371870 on ArguAna; 0.185079 vs 0.087955 on ClimateFEVER). BM25 and dense failures are not identical, especially for Qwen on ClimateFEVER, which motivates further reliability analysis. The structure-only diagnostics are weak and noisy, so they do not yet justify a structure-based method.

The recommendation is conditional rather than an unconditional GO: the empirical motivation is real, but the novelty space is crowded and the exact mechanism remains untested. Any next milestone requires a fresh, mechanism-specific prior-art review and a pre-registered evaluation plan.

## 2. Benchmark audit outcome

The audit is pinned to official repository commit `63e0c33826c7cb4f03e93a6819e49b92e6f33196` and immutable dataset revisions in `configs/benchmarks.yaml`. The catalog contains 14 retrieval resources: two development CS-MTEB resources and six CSR-L resources, with paired CSR-L/CS-MTEB counterparts recorded for provenance.

The primary metric is official nDCG@10 for the document-retrieval development resources. The final CSR-L instruction-retrieval resources retain their official pairwise-MRR protocol and are not collapsed into ordinary nDCG evaluation.

## 3. Leakage outcome

Protocol source-dataset disjointness passed at dataset, corpus, query-ID, source-query-group, and qrel-signature levels. Rewritten variants are grouped by source query and are not treated as independent examples. The CSR-L source-query groups are not eligible for selection. No final-test artifact was generated, and no final metric was used for selection or tuning.

The frozen protocol is recorded in `configs/data_protocol.yaml`; the detailed overlap evidence is in `results/audit/dataset_overlap.json` and `results/audit/source_query_overlap.csv`.

## 4. Frozen development/final protocol

Development consists of ArguAna (1,406 paired queries; 8,674 documents) and ClimateFEVERHardNegatives (1,000 paired queries; 47,416 documents), using Chinese-English (`zh`) query pairs. Each source query has an original and code-switched row, with shared qrels and retrieval depth 1,000. Delta is defined as:

`Delta_CS = metric(code-switched) - metric(original)`.

The final test is CSR-L only, remains untouched, and cannot influence model choice. There are no internal train/dev splits in this milestone, no retriever training, and no model tuning on final data.

## 5. BM25 baseline

| Dataset | Original nDCG@10 | Code-switched nDCG@10 | Delta_CS | Relative degradation |
|---|---:|---:|---:|---:|
| ArguAna | 0.278541 | 0.254198 | -0.024343 | -8.74% |
| ClimateFEVERHardNegatives | 0.138579 | 0.109299 | -0.029281 | -21.13% |

BM25 also loses recall@10 by 0.046942 and MRR by 0.016446 on ArguAna, and recall@10 by 0.037150 and MRR by 0.046121 on ClimateFEVER. The deterministic 2,000-replicate bootstrap intervals for official Delta_CS are [-0.02941, -0.01920] and [-0.03772, -0.02063], respectively.

## 6. Dense candidate results

| Dataset | Retriever | Original nDCG@10 | Code-switched nDCG@10 | Delta_CS | Relative degradation |
|---|---|---:|---:|---:|---:|
| ArguAna | Qwen3-Embedding-0.6B | 0.440355 | 0.440685 | +0.000329 | +0.07% |
| ArguAna | BGE-M3 | 0.378846 | 0.371870 | -0.006976 | -1.84% |
| ClimateFEVERHardNegatives | Qwen3-Embedding-0.6B | 0.214748 | 0.185079 | -0.029669 | -13.82% |
| ClimateFEVERHardNegatives | BGE-M3 | 0.094373 | 0.087955 | -0.006418 | -6.80% |

Both Qwen and BGE have complete, strictly validated artifacts for both development datasets. The optional multilingual-e5-large candidate was not run because two serious dense candidates were complete; no incomplete candidate was used in selection.

## 7. RQ0 results

RQ0 asks whether code-switching degrades retrieval under the frozen paired-query protocol. The answer is dataset- and retriever-dependent, but the degradation signal is clear for BM25 on both datasets and for both dense candidates on ClimateFEVER. Qwen's ArguAna nDCG interval includes zero ([-0.00353, 0.00458]), while its ClimateFEVER interval is entirely negative ([-0.03637, -0.02281]). BGE's official nDCG intervals are negative on both datasets.

The complete aggregate table, including recall@10, MRR, relative changes, bootstrap intervals, and per-query sign counts, is `results/analysis/development_only/rq0_summary.csv` and `.md`.

## 8. Per-query Delta analysis

Per-query paired rows were retained for all 2,406 source queries and three retrievers. Negative/nonnegative counts are computed from paired original/code-switched query scores, not from independently sampled queries. This supports uncertainty summaries and failure-overlap diagnostics without changing the benchmark protocol.

The evidence is heterogeneous: Qwen is stable on ArguAna but has 258 negative per-query nDCG deltas on ClimateFEVER; BM25 has 217 negative deltas on ClimateFEVER; BGE has 99. These counts are descriptive and do not establish causes.

## 9. BM25/dense complementarity

The analysis compares paired per-query Delta signs, score winners on the code-switched condition, Pearson correlation of Delta values, and an oracle diagnostic that chooses the better observed retriever per query. It does not fuse scores or propose a deployment policy.

| Dataset | Dense | BM25 survives / dense degrades | Dense survives / BM25 degrades | Both degrade | Neither degrades | Delta correlation | Dense wins CS score |
|---|---|---:|---:|---:|---:|---:|---:|
| ArguAna | Qwen | 11.8% | 14.4% | 2.9% | 70.9% | 0.072 | 63.4% |
| ArguAna | BGE | 12.9% | 14.4% | 2.9% | 69.8% | 0.025 | 49.6% |
| ClimateFEVERHardNegatives | Qwen | 16.4% | 12.3% | 9.4% | 61.9% | 0.144 | 35.9% |
| ClimateFEVERHardNegatives | BGE | 6.2% | 18.0% | 3.7% | 72.1% | 0.074 | 17.1% |

Qwen's ClimateFEVER worst-quartile failure-set Jaccard is 0.237, indicating materially different failures in that slice; its observed oracle mean CS score is 0.222170 versus 0.185079 for Qwen and 0.109299 for BM25. These are diagnostic upper bounds, not results of a method.

## 10. Structure diagnostics

A deterministic lightweight Unicode heuristic labels Latin and CJK/Hiragana/Katakana script characters and reports switch ratio, switch count, language entropy, and query length. This is an observational diagnostic only.

Most correlations between structure features and per-query Delta_CS are weak. The largest reported absolute values are BM25 on ArguAna for switch ratio (-0.173) and language entropy (-0.170), and Qwen on ClimateFEVER for switch ratio (-0.139) and entropy (-0.146). Quartile patterns are inconsistent across datasets and retrievers. Therefore the current evidence does not support a causal claim or a structure-only router. Full results are in `results/analysis/development_only/structure_summary.csv`, `structure_bins.csv`, and the corresponding Markdown files.

## 11. Selected dense backbone

The selected development-only dense retriever is **Qwen3-Embedding-0.6B**, pinned at revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`. The frozen selection rule uses development official nDCG@10 first and absolute Delta_CS as the robustness tie-break. Qwen's equal-weight mean code-switched nDCG@10 is 0.312882 versus 0.229912 for BGE-M3. BGE is faster and has smaller absolute drops, but its absolute development retrieval quality is lower on both datasets.

The selection record is `results/tables/selection.json`; the readable rationale is `docs/retriever_selection.md`.

## 12. Engineering, runtime, and cache notes

Dense inference ran on the existing CUDA environment and NVIDIA GeForce RTX 4060 Laptop GPU using FP16, `torch.inference_mode()`, mean masked last-hidden-state pooling, L2 normalization, batch size 16 for Qwen ArguAna, and batch size 32 for the other dense runs. Qwen ClimateFEVER indexing took 2,261.27 seconds and processed 47,416 documents; BGE ClimateFEVER indexing took 1,045.43 seconds. The completed Qwen ClimateFEVER run was not restarted or duplicated.

A persistent corpus embedding cache is implemented before further dense work. Its key fingerprints resource and revision, corpus content hash and document order, model and revision, embedding dimension, pooling, normalization, prefix, max length, truncation/padding settings, tokenizer settings, dtype, and cache version. Entries are validated for metadata, ordered IDs, shape, dtype, and finite values before atomic publication. A real BGE ClimateFEVER cache miss was saved and subsequently validated by the cache tests and metadata checks; completed Qwen outputs were not rerun solely to backfill the cache.

## 13. Limitations

The development evidence covers only two zh-en conditions and does not establish behavior on the untouched CSR-L final suite or on other language pairs. The structure heuristic is intentionally lightweight and not a language-identification gold standard. The complementarity oracle is descriptive and optimistic. Runtime comparisons are hardware- and batch-dependent, and some legacy run configurations predate cache wiring, although their artifacts pass strict integrity validation. No causal explanation for degradation has been established.

## 14. Novelty landscape

The focused audit finds direct or high-risk prior art for code-switched retrieval benchmarks, code-switched training, code-mixed BM25 plus semantic retrieval, and generic sparse/dense routing or adaptive weighting. Particularly important threats include CSR-L/CS-MTEB, ContrastiveMix, artificially code-switched training, MoR, RouterRetriever, Query-Adaptive Hybrid Search, and Decoding Benglish. See `docs/novelty_audit.md` for primary-source links and the exact-mechanism search record.

The audit did not identify a primary source matching the exact untested hypothesis of combining code-switch structure with observed per-query BM25-vs-Qwen reliability on CSR-L/CS-MTEB. This is not evidence of novelty; the next milestone would need a fresh mechanism-specific search before any contribution claim.

## 15. Recommendation

**CONDITIONAL GO.** Proceed only after human review confirms that the narrow research question remains worthwhile and after a fresh novelty check defines the mechanism, supervision, and deployment distinction from existing code-mixed hybrid retrieval and retriever-routing work. Milestone 1 provides a leakage-safe baseline, two validated dense candidates, a transparent selection, RQ0 evidence, and complementarity diagnostics. It does not justify implementing mitigation yet.

The final CSR-L suite remains untouched, and the repository should stop at this milestone until the next protocol is explicitly approved.

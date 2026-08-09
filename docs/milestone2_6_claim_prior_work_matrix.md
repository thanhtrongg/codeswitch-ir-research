# Milestone 2.6 claim-to-prior-work matrix

Audit date: 2026-08-09.  Statuses are deliberately conservative:
`CLEARLY COVERED`, `PARTIALLY COVERED`, `STRONGLY THREATENED`, `POSSIBLE GAP`,
and `NO SUPPORT`.  `POSSIBLE GAP` means that an exact combination was not found;
it is not evidence of novelty.

| Claim | Candidate claim | Closest prior work | Status | What is actually distinct | Defensibility consequence |
|---|---|---|---|---|---|
| C1 | Code-switching can degrade retrieval relative to monolingual/original queries. | ZENG2026; CONTRASTIVEMIX2024; LITSCHKO2023 | CLEARLY COVERED | A new resource-specific measurement could be descriptive only. | Do not make degradation a contribution. |
| C2 | Sparse and dense retrievers have complementary per-query strengths. | MOR2025; FIREOVERVIEW2025; FIREMF2025; FIRERRF2025 | CLEARLY COVERED | The exact BM25/Qwen pair and resource would be a new setting, not a new claim. | Oracle headroom and disagreement are diagnostics only. |
| C3 | Combining BM25 and dense retrieval improves code-mixed retrieval. | CONTRASTIVEMIX2024; FIRELEXISEM2025; FIRERRF2025; BENGLISH2025 | CLEARLY COVERED | A fixed baseline comparison could be useful, but not a method contribution. | No hybrid/fusion novelty claim. |
| C4 | Code-switch structure or mixing proportion can determine retrieval behavior. | MIXING2026; CODEMIXPROBES2024; SETURAG2026; MAIMAITI2025 | STRONGLY THREATENED | A different language pair or feature definition does not clear the mechanism collision. | Reject structure-only H4-style routing. |
| C5 | A query-specific sparse/dense alpha or weight is a new contribution. | QUDAR2026; QAHS2026; MOR2025; FIRERRF2025 | CLEARLY COVERED | Code-switch-specific calibration could be a setting distinction. | Alpha/fusion is not an original method claim. |
| C6 | A query-level router can choose among sparse, dense, hybrid, or expert retrieval. | ARABZADEH2021; ROUTER2025; QUDAR2026; LARMOR2024; RAGROUTER2025 | CLEARLY COVERED | Fixed BM25 versus fixed Qwen and no training narrow the setting only. | A router study must be framed as replication/transfer. |
| C7 | Unlabeled margin, score, coherence, entropy, or difficulty signals can select the better retriever. | VLACHOU2024; FAGGIOLI2023; MENG2025; CHIFU2025; QUDAR2026 | STRONGLY THREATENED | Relative BM25-versus-Qwen reliability under code-switching is not the same target as every prior QPP task. | Only a tightly registered transfer audit could be defensible; not a new signal. |
| C8 | Retriever disagreement or coverage can be converted into a useful reliability signal. | MOR2025; RARAG2025; QUDAR2026; ARABZADEH2021 | STRONGLY THREATENED | Code-switched queries and target-relative coverage might be an evaluation boundary. | Disagreement/coverage must not be presented as a new mechanism. |
| C9 | Asymmetric risk/abstention can prevent harmful switches while preserving coverage. | XIN2021; RECOVERR2024; RCRAG2024; SANTOSH2024; CDA2025 | PARTIALLY COVERED | Applying risk-coverage to sparse/dense choice under code-switching is narrower than the cited tasks. | Still crowded at the mechanism level; requires a clearly new scientific target. |
| C10 | A calibrated signal remains invariant when transferred across disjoint domains and preserves original-query performance. | CHIFU2025; LARMOR2024; ADAPTIVE2025; QAHS2026; RARAG2025 | STRONGLY THREATENED | The proposed invariance target is a stringent evaluation setting, not an unoccupied calibration idea. | Current literature does not support claiming a new invariance method. |

## Matrix interpretation

The only residual gap is a narrow combination of target, data boundary, and
evaluation protocol: unlabeled existing signals predicting *relative* fixed
BM25-versus-dense reliability on benchmark-provided code-switched variants,
with source-query-safe cross-domain transfer and an original-query safety check.
That combination is not an exact title match in the reviewed set, but the
mechanisms and scientific claims are already covered by QPP, model selection,
query-wise hybrid weighting, source reliability, mixture routing, and selective
risk work.  It is therefore insufficient to authorize Milestone 3.

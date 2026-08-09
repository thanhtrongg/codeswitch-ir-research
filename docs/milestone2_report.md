# Milestone 2 development-only QPP evaluation

## 1. Executive summary

**MILESTONE 2 SOURCE GATE FAILED**

The frozen development experiment selected **margin** and tau=0.20. No retrieval, encoding, model, or GPU worker was launched. No retuning occurred after holdout access, no target recalibration occurred, and the final CSR-L boundary remains untouched.

On the frozen Climate holdout, the preregistered QPP signals did not provide sufficient relative-reliability prediction: the selector underperformed fixed Qwen and failed both the code-switched source gate and original-query safety condition.

## 2. Frozen research question

Can a pre-specified unlabeled post-retrieval signal predict relative BM25-versus-Qwen reliability under benchmark-provided zh-en code switching, preserve original-query performance, and transfer unchanged from ClimateFEVERHardNegatives to ArguAna?

## 3. Protocol compliance

The authoritative revision was `milestone_1_5d`. Source and target were fixed to ClimateFEVERHardNegatives and ArguAna, with no reverse direction. Active signals were margin and top-k dispersion only; coherence remained removed. The selector used k=10, epsilon=1e-12, right-inclusive candidate-specific empirical CDFs, and Qwen fallback unless G < -tau.

## 4. Artifact and checksum verification

All 1.5d frozen-file hashes, source-split hashes, fixed BM25/Qwen/BGE artifact hashes, Qwen revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, depth-1000 ranking structure, row pairing, score order, and document-ID uniqueness checks passed before protected outcome access. Details are in `results/milestone2/logs/baseline_artifact_manifest.json` and the method-freeze manifest.

## 5. Source split

The grouped source split contained 600 FIT, 200 validation, and 200 post-exploratory frozen holdout groups. Group checksum: `49d53e935f3e9e54c252d9aa130107f0bff1e5e678d39d8aa325916f307dab5b`. Assignment checksum: `fb1514ce76470601464f51ade05877fe33b5850b5d1087a1f4dc52ddd0fcdf9b`. Original and code-switched variants remained grouped.

## 6. Signal definitions

Margin was `(s1-s2)/(|s1-s10|+epsilon)`. Dispersion was the population standard deviation (`ddof=0`) of the min-max-normalized top-10 scores. Both were converted using separate BM25 and Qwen empirical CDFs fitted on the 600 Climate FIT code-switched rows; ties were right-inclusive.

## 7. FIT signal-selection result

Margin winner accuracy was 0.521666667; dispersion winner accuracy was 0.491666667. The selected signal was **margin** because it had the higher FIT winner accuracy, with margin specified as the tie-break. Winner ties were assigned to Qwen. The unselected signal was discarded after FIT.

## 8. Validation tau-selection result

Only Climate validation code-switched outcomes entered threshold selection. The complete frozen sweep was:

- tau=0.00: CS nDCG@10=0.143756969, BM25 choice=49.500%, Qwen choice=50.500%
- tau=0.05: CS nDCG@10=0.146909004, BM25 choice=46.000%, Qwen choice=54.000%
- tau=0.10: CS nDCG@10=0.149767491, BM25 choice=41.500%, Qwen choice=58.500%
- tau=0.15: CS nDCG@10=0.150334021, BM25 choice=33.500%, Qwen choice=66.500%
- tau=0.20: CS nDCG@10=0.151968037, BM25 choice=29.500%, Qwen choice=70.500% (selected)

Selected tau: **0.20**, using highest CS nDCG@10, then smaller tau, then deterministic lexical serialization order. Original outcomes and Delta_CS did not enter selection.

## 9. Method freeze

The method-freeze manifest was written and hash-validated before holdout access: `results/milestone2/freeze/milestone2_method_freeze_manifest.yaml` with SHA-256 `CADC299EED07C5AE6DC37C926F7FCF8CCC4FEF72BAF9962010F1DC30CEC25D7F`. It freezes implementation hashes, CDF values and hashes, selected signal, tau, protocol/split hashes, fixed ranking hashes, bootstrap settings, and RRF k.

## 10. Climate holdout results

The frozen method was evaluated once on 200 post-exploratory protected groups. BM25 nDCG@10=0.121611699, Recall@10=0.144916667, MRR=0.178093452; Qwen nDCG@10=0.196078718, Recall@10=0.233000000, MRR=0.279249610; Selector nDCG@10=0.182517423, Recall@10=0.215500000, MRR=0.254439528.

Full fixed-system, RRF, BGE reference-only, and oracle-diagnostic metrics appear in Table 3. The oracle is not deployable.

## 11. Source bootstrap gate

The Selector-Qwen CS nDCG@10 difference was -0.013561295. The 2000-replicate paired-bootstrap 95% CI (seed 20260809) was [-0.032543918, 0.004811338]. The registered strict lower-bound > 0 source CS condition was **FAIL**.

## 12. Original-query safety

The same CS-derived calibration and tau were applied unchanged. BM25 nDCG@10=0.158279203, Recall@10=0.205333333, MRR=0.222498505; Qwen nDCG@10=0.219842514, Recall@10=0.250750000, MRR=0.323328026; Selector nDCG@10=0.204964629, Recall@10=0.233166667, MRR=0.295898640. The Selector-Qwen difference was -0.014877885, 95% CI [-0.040193461, 0.010080240]. The lower-bound >= 0 safety condition was **FAIL**. Overall source gate: **FAIL**.

## 13. ArguAna transfer result

ArguAna was not accessed because the complete registered Climate source gate failed. No target outcomes were decoded.

## 14. Transfer gate

Not evaluated because the source gate failed.

## 15. Comparator results

Fixed RRF used the union of existing depth-1000 BM25/Qwen rankings with 1-based ranks and k=60. BGE-M3 is reference-only, and the oracle is diagnostic-only. The Arabzadeh comparator is `NOT AVAILABLE`: no faithful existing implementation with the registered features and objective was present at freeze, and no substitute was invented.

## 16. Relative-reliability diagnostics

Climate holdout CS routed 34.000% to BM25 and 66.000% to Qwen; winner classification accuracy was 0.600000000. BM25 truly won 14.000% of cases, the selector captured 0.285714286 of those opportunities, and 88.235% of BM25 switches were harmful. Confusion matrices, G values, and deterministic |G| bins are saved as post-hoc diagnostics and did not affect tuning.

## 17. Delta_CS

Delta_CS is code-switched minus original; negative values indicate degradation. Exact nDCG@10, Recall@10, and MRR deltas for BM25, Qwen, Selector, RRF, BGE, and the diagnostic oracle are in Tables 3 and 4.

## 18. Figures and tables index

Tables are under `results/milestone2/tables/` as CSV, Markdown, and LaTeX. Figures 1-5 are under `results/milestone2/figures/` as 300-dpi PNG and vector PDF, each with plot-data CSV. The index is recorded in `results/milestone2/milestone2_summary.json`.

## 19. Limitations

This is a narrow development-only evaluation on benchmark-provided zh-en code-switched variants. It does not establish universal QPP reliability, natural human code-switching generalization, causality, routing novelty, or state of the art. The Climate holdout is post-exploratory and procedurally protected, not historically untouched.

## 20. Leakage statement

FIT and validation used source code-switched outcomes only. Holdout outcomes were inaccessible to tuning and decoded only after the freeze. ArguAna was inaccessible unless the complete source gate passed and was never used for recalibration. Dataset-backed validation retained its frozen `inconclusive_timeout` status; raw-artifact overlap validation remained PASS with zero source-qualified development/final overlap.

## 21. Exploratory-history disclosure

Earlier Milestone 1 exploration informed the decision to preregister this narrow follow-up. The current source holdout therefore carries the explicit `post_exploratory_frozen_holdout` label; no claim of historical blindness is made.

## 22. Final Milestone 2 verdict

**MILESTONE 2 SOURCE GATE FAILED**

The result was classified exactly by the frozen source, transfer, and original-safety rules. Negative or null gate outcomes were not rescued by retuning.

Accordingly, this development result is evidence that the two pre-specified signals were insufficient under the frozen source setting; it is not evidence for successful cross-resource transfer, which was not authorized for evaluation.

## 23. CSR-L boundary

**FINAL CSR-L TEST UNTOUCHED.** No CSR-L query, qrel, corpus, ranking, metric, or counterpart resource was loaded, encoded, retrieved, or inspected. Milestone 2 stops here pending human review.

## Reproducibility metadata

- Python: 3.11.0 (main, Oct 24 2022, 18:26:48) [MSC v.1933 64 bit (AMD64)]
- OS: Windows-10-10.0.26200-SP0
- Packages: `{"PyYAML": "6.0.3", "matplotlib": "3.11.1", "numpy": "2.4.6", "pytest": "9.1.1"}`
- Execution start: 2026-08-09T05:04:01.178708+00:00
- Execution end: 2026-08-09T05:05:29.871012+00:00
- Total runtime: 88.692 seconds
- CPU/GPU: CPU-only post-processing; GPU used=false; GPU worker launched=false
- Pre-holdout tests: .....................                                                    [100%]
21 passed in 0.24s

## Original-query target safety

Not evaluated because ArguAna was not authorized by the source gate.

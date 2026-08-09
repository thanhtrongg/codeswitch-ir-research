# Milestone 2.5 scientific postmortem

## 1. Executive conclusion

The immutable confirmatory result remains **MILESTONE 2 SOURCE GATE FAILED**. The most supported explanation is not that BM25 and Qwen lack complementarity. Rather, the frozen margin/dispersion signals did not identify the useful BM25 opportunities reliably enough, and false BM25 switches were much more costly than captured opportunities were beneficial. This conclusion is limited to the pre-specified signals, fixed retrievers, benchmark-provided Climate zh-en setting, and consumed post-exploratory holdout.

The primary recommendation is **CONDITIONAL GO — NEW HYPOTHESIS REQUIRED**.

## 2. Immutable Milestone 2 result

Saved headline values were independently verified from the original machine-readable record. Margin was selected at FIT accuracy 0.521666667 versus dispersion 0.491666667; tau=0.20. Climate holdout CS nDCG@10 was BM25=0.121611699, Qwen=0.196078718, Selector=0.182517423. Selector-Qwen was -0.013561295, with 95% CI [-0.032543918, 0.004811338]. Original safety difference was -0.014877885, with CI [-0.040193461, 0.010080240].

The original Milestone 2 output manifest remains intact; its SHA-256 is `0B9E51A2A9E8BF4FAE9E43A6BB9180D783D1CB20BA83DC0709C91F14A66633A9`. No original Milestone 2 result was overwritten.

## 3. What hypothesis was tested

Milestone 2 tested whether unlabeled normalized top-1/top-2 score margin or top-k score dispersion could predict the relative per-query winner between fixed BM25 and fixed Qwen under benchmark-provided zh-en code switching. It used candidate-specific Climate FIT empirical CDFs, one selected signal, a fixed threshold grid, and a hard Qwen-fallback selector. The oracle used outcome labels and was diagnostic only.

## 4. What failed

The selector routed 68/200 holdout queries to BM25 and 132/200 to Qwen. Actual BM25 wins occurred on 28/200 queries, but only 8 were captured; 60 BM25 switches were harmful. Thus the central failure was costly false positive BM25 routing, not absence of all per-query complementarity.

## 5. FIT signal diagnostics

The preregistered FIT objective remains winner accuracy. The following additional measures are explicitly **POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA** and did not select the signal:

| signal | winner_accuracy | majority_baseline | improvement_over_majority | balanced_accuracy | BM25_precision | BM25_recall | BM25_F1 | MCC | actual_BM25_count | actual_Qwen_count | POSTHOC_AUROC_BM25 | POSTHOC_Spearman_G_vs_Qwen_minus_BM25 | diagnostic_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| margin | 0.521666667 | 0.848333333 | -0.326666667 | 0.546611542 | 0.175496689 | 0.582417582 | 0.269720102 | 0.066879258 | 91 | 509 | 0.532913059 | 0.034891340 | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |
| dispersion | 0.491666667 | 0.848333333 | -0.356666667 | 0.501856689 | 0.152597403 | 0.516483516 | 0.235588972 | 0.002664907 | 91 | 509 | 0.508765301 | 0.035018759 | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |


FIT actual winners were BM25=91 and Qwen=509; an always-Qwen predictor would score 84.833%. This makes the raw 52.167%/49.167% candidate accuracies poor evidence of useful BM25 identification despite margin winning the frozen comparison.

FIT confusion matrices:

- margin: actual BM25→predicted BM25=53, actual BM25→Qwen=38, actual Qwen→BM25=249, actual Qwen→Qwen=260
- dispersion: actual BM25→predicted BM25=47, actual BM25→Qwen=44, actual Qwen→BM25=261, actual Qwen→Qwen=248

## 6. Class-imbalance analysis

- fit: BM25=91 (15.167%), Qwen=509 (84.833%), always-Qwen accuracy=84.833%
- validation: BM25=26 (13.000%), Qwen=174 (87.000%), always-Qwen accuracy=87.000%
- holdout: BM25=28 (14.000%), Qwen=172 (86.000%), always-Qwen accuracy=86.000%

Qwen was the majority winner in every analyzed split. The always-Qwen diagnostic baseline therefore exceeded both FIT candidate accuracies. This does not retroactively replace the preregistered selection criterion; it shows why raw winner accuracy alone was an incomplete proxy for deployment utility.

## 7. Validation behavior

The saved validation sweep was:

- tau=0.00: CS nDCG@10=0.143756969, BM25 route=49.500%, Qwen route=50.500%, selected=False
- tau=0.05: CS nDCG@10=0.146909004, BM25 route=46.000%, Qwen route=54.000%, selected=False
- tau=0.10: CS nDCG@10=0.149767491, BM25 route=41.500%, Qwen route=58.500%, selected=False
- tau=0.15: CS nDCG@10=0.150334021, BM25 route=33.500%, Qwen route=66.500%, selected=False
- tau=0.20: CS nDCG@10=0.151968037, BM25 route=29.500%, Qwen route=70.500%, selected=True

Increasing tau monotonically reduced BM25 routing and increased Qwen fallback while validation nDCG@10 increased at every registered grid point. The data support the narrow interpretation that validation preferred increasingly conservative switching. No tau outside the frozen grid was tested or inferred.

## 8. Holdout failure decomposition

| category | count | percentage_of_holdout | mean_signed_BM25_minus_Qwen_ndcg_at_10 | total_signed_BM25_minus_Qwen_ndcg_at_10 | mean_gain_or_loss_ndcg_at_10 | total_gain_or_loss_ndcg_at_10 | interpretation | diagnostic_label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| beneficial_BM25_switches | 8 | 4.000000000 | 0.365432449 | 2.923459589 | 0.365432449 | 2.923459589 | BM25-minus-Qwen gain from a beneficial switch | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |
| harmful_BM25_switches | 60 | 30.000000000 | -0.093928643 | -5.635718598 | 0.093928643 | 5.635718598 | Qwen-minus-BM25 loss from an incorrect BM25 switch | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |
| correct_Qwen_keeps | 112 | 56.000000000 | -0.171115027 | -19.164882979 | 0.171115027 | 19.164882979 | Qwen-minus-BM25 advantage retained by the Qwen fallback | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |
| missed_BM25_opportunities | 20 | 10.000000000 | 0.349186915 | 6.983738298 | 0.349186915 | 6.983738298 | BM25-minus-Qwen gain left unrealized by a missed opportunity | POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA |


BM25 switch precision was 11.765%; BM25 opportunity recall was 28.571%; harmful-switch rate was 88.235%; missed-opportunity rate was 71.429%. Correct BM25 switches contributed total nDCG@10 gain 2.923459589 (mean 0.365432449). Harmful switches incurred total loss 5.635718598 (mean 0.093928643). Missed BM25 opportunities left total gain 6.983738298 unrealized (mean 0.349186915). The net switch effect was negative because false switches dominated.

## 9. QPP confidence versus actual retriever advantage

For the selected holdout margin, Spearman correlation between G and Qwen-minus-BM25 nDCG@10 was 0.072268999; equivalently, correlation between -G and BM25-minus-Qwen advantage was 0.072268999. The post-hoc AUROC for detecting BM25-winner queries from -G was 0.474979236. These values support limited or weak identifiability, not a universal claim that QPP contains no information. Figure 2 is a **POST-HOC DIAGNOSTICS - NOT SELECTION CRITERIA** visualization.

## 10. Complementarity versus identifiability

Complementarity remains observable: BM25 won on 28 holdout queries, and the outcome-defined oracle reached nDCG@10 0.245614707 versus Qwen 0.196078718. Headroom was Oracle-Qwen=0.049535989; Selector-Qwen=-0.013561295; Oracle-Selector=0.063097284. The oracle is not deployable. The defensible distinction is therefore: complementarity exists, but these unlabeled score-shape signals did not identify it safely.

Fixed RRF reached 0.198827500; RRF-Qwen=0.002748782 and RRF-Selector=0.016310077. This descriptively suggests fixed fusion exploited some complementarity that hard QPP routing did not, but RRF remains an established baseline and is not promoted as the contribution.

## 11. Distribution-shift analysis

Saved selected-margin raw-signal and G summaries were:

- FIT: BM25 raw mean/median/std=0.302301791/0.289910305/0.193113631; Qwen raw mean/median/std=0.274646758/0.248530266/0.185101690; G mean=0.000000000, median=-0.003333333, std=0.408737510, Q1=-0.273750000, Q3=0.292500000, G < -tau=32.833%
- VALIDATION: BM25 raw mean/median/std=0.306218859/0.288617979/0.197147856; Qwen raw mean/median/std=0.295659932/0.286320540/0.181489160; G mean=0.033391667, median=0.003333333, std=0.398824919, Q1=-0.252083333, Q3=0.337916667, G < -tau=29.500%
- HOLDOUT: BM25 raw mean/median/std=0.303901023/0.288926224/0.210988795; Qwen raw mean/median/std=0.292164537/0.265940489/0.191255099; G mean=0.032258333, median=0.039166667, std=0.430741186, Q1=-0.302083333, Q3=0.352916667, G < -tau=34.000%

Pairwise G shift diagnostics are reported in the machine-readable summary: KS and Wasserstein distances compare FIT/validation, FIT/holdout, and validation/holdout. Differences make distribution shift a plausible contributor, but all three splits come from one source benchmark; these are not causal or external-domain shift tests. No CDF was refit.

## 12. Failure-mode evidence matrix

| failure_mode | evidence_for | evidence_against | confidence |
| --- | --- | --- | --- |
| Signal has almost no predictive information | FIT margin accuracy=0.521667; POST-HOC AUROC for BM25 winners=0.532913; holdout gain correlation=0.072269. | FIT is above chance and the diagnostic AUROC is not necessarily exactly 0.5; the result does not prove no information exists. | STRONG |
| Class imbalance makes winner accuracy misleading | Qwen is the majority winner in FIT, validation, and holdout; always-Qwen accuracy exceeds both candidate FIT accuracies. | Balanced accuracy, BM25 recall, MCC, and AUROC were also reported, so the analysis is not limited to raw accuracy. | STRONG |
| CDF normalization fails to preserve relative reliability | G distribution shift diagnostics show KS values [0.065, 0.08, 0.055] across source stages. | CDFs are correctly fitted and right-inclusive; shift is observational and cannot establish that normalization caused failure. | MODERATE |
| Thresholding is insufficient | Validation preferred progressively lower BM25 routing as tau increased, while the frozen holdout still produced net negative switching. | The preregistered holdout cannot be used to select or compare unregistered thresholds; no tau beyond 0.20 was tested. | MODERATE |
| Hard selection is too costly under a strong Qwen baseline | There were 60 harmful BM25 switches versus 8 beneficial switches; harmful-switch loss exceeded beneficial-switch gain. | This is specific to the frozen Qwen baseline, signals, threshold, and Climate setting. | STRONG |
| Source distribution shift | Saved FIT, validation, and holdout G and raw-signal summaries differ; pairwise KS/Wasserstein diagnostics are reported. | All three are source splits from one benchmark and the analysis is not a causal shift test. | WEAK |
| Complementarity exists but current signals cannot identify it | BM25 wins on 28/200 holdout queries and the oracle exceeds Qwen, but only 8 opportunities were captured and 60 BM25 switches were harmful. | The conclusion is limited to margin/dispersion and this frozen source setting; other observables were not tested. | STRONG |


## 13. What can and cannot be claimed

Supported wording: “Under the frozen ClimateFEVERHardNegatives zh-en code-switched setting, normalized score margin and top-k dispersion did not provide sufficient relative-reliability information to safely switch between BM25 and Qwen.”

This does not show that QPP fails universally, that QPP causes degradation, or that all code-switching QPP methods fail. The selector-minus-Qwen CS confidence interval includes zero, so the result is not a statistically established negative effect in the universal sense.

## 14. Negative-paper viability

| criterion | assessment | evidence | confidence |
| --- | --- | --- | --- |
| Novelty of exact empirical question | Narrow distinction remains, but it is high-risk rather than a method novelty claim. | Existing audit found no exact all-conditions match, while generic QPP, confidence, routing, and complementarity mechanisms are established. | MODERATE |
| Strength of evidence | Useful preregistered source failure; not a statistically proven universal negative. | One frozen 200-query Climate holdout; selector-Qwen CI includes zero. | STRONG |
| Benchmark breadth | Insufficient for a broad standalone claim. | One source benchmark; ArguAna was correctly not executed after the source gate failed. | STRONG |
| Explanatory value | Moderate postmortem value: complementarity exists, but false switches dominate. | 28 BM25 opportunities, 8 captured, 60 harmful switches, and oracle headroom above Qwen. | STRONG |
| Prior-work comparison | High novelty risk. | Novelty audit identifies QuDAR, Arabzadeh, MoR, Query-Adaptive Hybrid Search, QPP, and code-mixed hybrid precedents. | STRONG |
| Best publication form | Secondary analysis, workshop/short-paper finding, or motivation for a new preregistered hypothesis. | The negative is narrow, source-only, and transfer was not observed. | MODERATE |
| Standalone negative paper now | Insufficient by itself. | No ArguAna transfer result, one source benchmark, and high mechanism-overlap risk. | STRONG |


The current evidence is valuable as a disciplined negative/diagnostic result, but insufficient by itself for a standalone main-paper contribution. Its strongest use is a secondary analysis, workshop/short-paper finding, or motivation for a genuinely new preregistered hypothesis.

## 15. Existing novelty risk

The frozen novelty documents identify QuDAR, Arabzadeh et al., MoR, Query-Adaptive Hybrid Search, confidence/QPP work, RouterRetriever, SETU-RAG, and FIRE/code-mixed hybrid systems as close threats. The overlap is high for confidence, QPP, relative selection, routing, fusion, and complementarity. The remaining distinction is the narrow empirical calibration/transfer question for fixed BM25 versus fixed Qwen on benchmark-provided zh-en variants. Novelty risk is **HIGH**. A **FRESH LITERATURE REVIEW REQUIRED** before publication, but none was performed in this postmortem.

## 16. Possible future hypotheses

The following are hypotheses only; no implementation or experiment was run:

### H1

**Question:** Can an explicitly asymmetric selective-risk or abstention objective avoid harmful BM25 switches while retaining a measurable subset of BM25 opportunities?

**Motivation:** The holdout had 60 harmful BM25 switches versus 8 beneficial switches under the frozen hard selector.

**Difference from Milestone 2:** Changes the scientific target from winner classification to pre-registered risk control/utility with abstention; it is not another tau, k, or signal tweak.

**Prior-art threat:** Arabzadeh, QuDAR, and query-adaptive hybrid work already cover strategy selection and confidence/weighting mechanisms. Novelty risk: **HIGH**

**Required evidence:** Fresh source-disjoint development groups and a separately held-out confirmatory resource with an externally specified cost matrix.

**Data boundary:** The Climate Milestone 2 holdout is consumed and cannot serve as confirmatory evidence.
### H2

**Question:** Can observable retriever disagreement or query-document coverage identify relative BM25 advantage when independent top-k score shape does not?

**Motivation:** Oracle headroom and 28 BM25-winning holdout queries show complementarity, while margin-based G was weak for identifying them.

**Difference from Milestone 2:** Tests a preregistered new feature family and identifiability question rather than combining margin and dispersion or adding a post-hoc exception.

**Prior-art threat:** MoR, QuDAR, RouterRetriever, QPP, and complementarity-routing work make this a high-risk replication/transfer question. Novelty risk: **HIGH**

**Required evidence:** New source-query groups, blinded feature freeze, multiple fixed retrievers, and a fresh target or benchmark.

**Data boundary:** Current Climate FIT, validation, and holdout are exploratory history for this hypothesis.
### H3

**Question:** Is cross-resource calibration itself the limiting factor, such that relative-reliability signals need multi-source invariance before transfer can be tested?

**Motivation:** G and raw-signal distributions vary across FIT, validation, and holdout, and ArguAna transfer was not authorized after source failure.

**Difference from Milestone 2:** Studies pre-registered multi-source calibration and invariance; it does not retune the consumed holdout or recalibrate on the target after seeing outcomes.

**Prior-art threat:** Generic QPP, confidence, and query-adaptive routing literature directly threatens any calibration-method claim. Novelty risk: **HIGH**

**Required evidence:** At least two genuinely new source resources plus a new confirmatory target, with all calibration boundaries fixed in advance.

**Data boundary:** All Milestone 2 Climate data are exploratory history and cannot be used as clean confirmation.

## 17. Data-independence consequences

Milestone 1 aggregate observations, Milestone 2 Climate FIT, validation, and holdout outcomes, and every postmortem diagnostic derived from them are now exploratory history for any future branch. **Climate Milestone 2 holdout = CONSUMED FOR FUTURE HYPOTHESIS DESIGN.** It cannot serve as fresh confirmatory evidence. Future confirmation requires newly defined source groups and a fresh confirmatory target; this postmortem does not recommend using CSR-L to tune a new idea.

## 18. Recommended next step

Do not tune the failed selector. If the project continues, first write a new preregistration around one clearly differentiated hypothesis, a new data boundary, a fresh literature review, and an explicit cost/utility or identifiability target. Human review is required before any new protected evaluation.

## 19. Final GO/NO-GO decision

**CONDITIONAL GO — NEW HYPOTHESIS REQUIRED**

Concrete reasons:

1. The negative source result is preregistered, reproducible, and diagnostically informative.
2. The holdout shows strong asymmetric switching failure: 60 harmful versus 8 beneficial BM25 switches.
3. Complementarity and oracle headroom exist, so the scientific question is not vacuous.
4. The evidence is limited to one source benchmark because ArguAna was correctly not executed.
5. Prior-art overlap makes a standalone method or universal QPP claim indefensible.

## 20. Protected-boundary statement

No new protected evaluation or raw protected dataset access occurred. Previously saved Climate holdout outcomes were analyzed post hoc. ArguAna and CSR-L remained untouched. No BM25, Qwen, BGE, RRF retrieval, encoding, GPU work, tuning, signal addition, or selector implementation was run. The original Milestone 2 verdict remains **MILESTONE 2 SOURCE GATE FAILED**.

**NO RETUNING.** **NO NEW PROTECTED EXPERIMENT.** **ARGUANA UNTOUCHED.** **FINAL CSR-L TEST UNTOUCHED.**

## Postmortem artifacts

### Tables

- table_A_qpp_signal_diagnostic_quality: `results/milestone2_5/tables/table_A_qpp_signal_diagnostic_quality.csv`, `results/milestone2_5/tables/table_A_qpp_signal_diagnostic_quality.md`, `results/milestone2_5/tables/table_A_qpp_signal_diagnostic_quality.tex`
- table_B_holdout_switching_decomposition: `results/milestone2_5/tables/table_B_holdout_switching_decomposition.csv`, `results/milestone2_5/tables/table_B_holdout_switching_decomposition.md`, `results/milestone2_5/tables/table_B_holdout_switching_decomposition.tex`
- table_C_failure_mode_evidence_matrix: `results/milestone2_5/tables/table_C_failure_mode_evidence_matrix.csv`, `results/milestone2_5/tables/table_C_failure_mode_evidence_matrix.md`, `results/milestone2_5/tables/table_C_failure_mode_evidence_matrix.tex`
- table_D_publication_viability_assessment: `results/milestone2_5/tables/table_D_publication_viability_assessment.csv`, `results/milestone2_5/tables/table_D_publication_viability_assessment.md`, `results/milestone2_5/tables/table_D_publication_viability_assessment.tex`

### Figures

- figure1_holdout_confusion: `results/milestone2_5/figures/figure1_holdout_confusion.png`, `results/milestone2_5/figures/figure1_holdout_confusion.pdf`, plot data `results/milestone2_5/figures/figure1_holdout_confusion_plot_data.csv`
- figure2_G_vs_actual_gain: `results/milestone2_5/figures/figure2_G_vs_actual_gain.png`, `results/milestone2_5/figures/figure2_G_vs_actual_gain.pdf`, plot data `results/milestone2_5/figures/figure2_G_vs_actual_gain_plot_data.csv`
- figure3_G_distributions: `results/milestone2_5/figures/figure3_G_distributions.png`, `results/milestone2_5/figures/figure3_G_distributions.pdf`, plot data `results/milestone2_5/figures/figure3_G_distributions_plot_data.csv`
- figure4_opportunity_capture: `results/milestone2_5/figures/figure4_opportunity_capture.png`, `results/milestone2_5/figures/figure4_opportunity_capture.pdf`, plot data `results/milestone2_5/figures/figure4_opportunity_capture_plot_data.csv`

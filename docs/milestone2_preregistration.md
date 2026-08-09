# Milestone 2 preregistration — hardened and frozen

Status: **PREREGISTERED_NOT_EXECUTED**  
Protocol: `configs/milestone2_protocol.yaml`  
Freeze revision: `milestone_1_5d`  
Date: 2026-08-09

This is a protocol record, not an execution request. No selector, retrieval
run, fusion, RRF run, GPU encoding, or final CSR-L evaluation is authorized by
this document.

## 1. Scope and research question

**RQ1.** On benchmark-provided Chinese-English (`zh-en`) code-switched
variants, do pre-specified unlabeled post-retrieval behavior signals predict
which of fixed BM25 and fixed Qwen3-Embedding-0.6B will have higher per-query
retrieval quality, and does a ClimateFEVERHardNegatives calibration transfer
unchanged to ArguAna without score fusion, RRF, retriever training,
structure-only routing, or adaptive alpha?

The development variants are benchmark-provided and reported by the benchmark
audit as LLM-generated. This protocol therefore makes no claim that the
development queries are naturally occurring or human-authored. The CSR-L
resources remain a separate, truly untouched final boundary where the audit
declares human-authored/human-validated provenance where applicable.

Milestone 1 analyzed all 2,406 available development query groups
exploratorily. The holdout below is consequently a post-exploratory
procedurally protected holdout, not a historically untouched or fully unseen
estimate.

The primary direction is fixed before execution:

`ClimateFEVERHardNegatives` source → `ArguAna` target.

ClimateFEVERHardNegatives was chosen because Milestone 1 showed the larger
BM25/Qwen disagreement and oracle headroom. ArguAna cannot affect signal
selection, CDF construction, threshold selection, tuning, or exceptions. The
reverse direction is not registered.

## 2. Data and leakage boundary

The development resources are:

- `UTokyo-Yokoya-Lab/ClimateFEVER_hardnegatives_CS-MTEB` (primary source)
- `UTokyo-Yokoya-Lab/arguana_CS-MTEB` (fixed transfer target)

The identity of a split unit is `source_dataset::query_id`. Original and
code-switched variants, shared qrels, and all derived rows for a source query
remain in the same assignment. The exact Climate assignment is already
materialized at
`results/protocol/milestone2_climate_source_split.json`:

- seed: `20260809`
- 1,000 source-query groups and 2,000 variants
- 600 fit groups, 200 validation groups, 200 post-exploratory frozen-holdout groups
- source-group checksum:
  `49d53e935f3e9e54c252d9aa130107f0bff1e5e678d39d8aa325916f307dab5b`
- assignment checksum:
  `fb1514ce76470601464f51ade05877fe33b5850b5d1087a1f4dc52ddd0fcdf9b`

The assignment sorts `source_query_id` by
`sha256(f'{seed}|{source_query_id}')` and assigns contiguous 60/20/20 blocks.
It must not be regenerated. ArguAna is a transfer-only target: its outcomes
are reported after the source method is frozen and cannot influence any choice.

All source-fit calibration and signal-family selection use only the
code-switched `zh-en` variant from each Climate fit group. Original English
variants are excluded from CDF fitting, signal-family selection, winner-label
construction, and threshold tuning. Original-query evaluation is a later
safety analysis using the already frozen CS-derived calibration.

Leakage validation has two deliberately separate statuses:

- raw-artifact revalidation: **PASS**, with zero source-qualified
  development/final overlap; evidence is
  `results/audit/dataset_overlap.json` and
  `results/audit/source_query_overlap.csv`;
- dataset-backed validator: **INCONCLUSIVE_TIMEOUT** after 180 seconds during
  metadata resolution. This operational timeout neither indicates leakage nor
  supersedes the raw-artifact PASS.

The six CSR-L resources and their registered `zh`/`ja` languages remain
untouched until a later human-approved execution. No final query, qrel, corpus,
or metric is read before the method and development artifacts are frozen.

## 3. Fixed retrievers and existing inference configuration

- BM25: fixed secondary sparse baseline.
- Qwen3-Embedding-0.6B: fixed primary baseline at revision
  `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`.
- BGE-M3: reference-only; it cannot replace Qwen or enter candidate selection.

The existing Qwen development artifacts record the following configuration:

- effective maximum sequence length: `512`
- tokenizer truncation: `true`
- padding: dynamic to the longest sequence in each batch
- inference dtype: `torch.float16`
- pooling: masked mean of the last hidden state
- normalized embeddings: `true`
- Climate source batch size: `32`
- ArguAna transfer-target batch size: `16`

The selector consumes the existing BM25/Qwen rankings and scores. This freeze
does not authorize re-encoding or changing batch size. New dense encoding is
prohibited before Milestone 2 execution; final encoding is allowed only after
the registered development gate, checksum freeze, and human approval.

## 4. Candidate method and prohibited alternatives

There is one candidate: `unlabeled_relative_qpp_hard_selector_v1`. It chooses
exactly one retriever per query. It does not combine scores, use RRF, train a
router, use CMI or switch-ratio features, inspect script/language structure,
expand queries, invoke an LLM judge, or add exceptions.

The selector is restricted to two active signal families. Retrieved-set
embedding coherence is removed before Milestone 2 because no validated Qwen
Climate corpus embedding cache exists: the existing cache is BGE-M3 only, and
the Qwen run recorded `cache_path: null` and `embeddings_persisted: false`. No
new Qwen encoding is authorized to restore that signal.

All signals use `k=10` and `epsilon=1e-12`. For retriever `r`, with top-k scores
`s_r,1 >= ... >= s_r,k`:

1. Margin: `M_r(q) = (s_r,1 - s_r,2) /
   (abs(s_r,1 - s_r,k) + epsilon)`. If the denominator is `<= epsilon`, set
   `M_r(q)=0`.

2. Dispersion: `z_r,i = (s_r,i - s_r,k) /
   (s_r,1 - s_r,k + epsilon)`. If the score range is `<= epsilon`, set all
   `z_r,i` to zero. Otherwise, `D_r(q)` is the population standard deviation
   of the `k` values, with `ddof=0`.

The removed coherence definition would have been the symmetric retrieved-set
quantity `2/(k(k-1)) * sum_{i<j} cosine(e(d_i),e(d_j))`, measured in the fixed
normalized Qwen document-embedding space for both retrievers. It is not
computed in this protocol.

## 5. Signal selection, normalization, and hard decision

Signal-family selection is non-circular and is performed independently for
each active candidate using Climate **source-fit code-switched variants only**.
For each candidate `c` (margin and dispersion), do all of the following on
source fit:

1. Compute the candidate's raw signal separately for BM25 and Qwen.
2. Construct candidate-specific empirical CDFs
   `F_c,BM25` and `F_c,Qwen` from those raw CS-fit values, with ties included.
3. Convert to percentiles
   `P_c,r(q)=F_c,r(S_c,r(q))`.
4. Define `G_c(q)=P_c,Qwen(q)-P_c,BM25(q)`.
5. At `tau=0`, predict Qwen when `G_c>=0` and BM25 when `G_c<0`.
6. Compare with the observed CS winner label.

The observed label is BM25 only when per-query code-switched nDCG@10(BM25) is
strictly greater than nDCG@10(Qwen); ties are Qwen. This relevance-derived
label is used only for source-fit signal-family selection and is unavailable at
inference. The selection objective is mean per-query winner classification
accuracy, with deterministic tie order margin before dispersion.

After selecting exactly one signal family, discard the unselected signal. Only
the selected signal definition and its two source-fit CS empirical CDFs proceed
to Climate validation, the Climate holdout, and ArguAna transfer. The signals
are not combined, averaged, or passed to a classifier.

The selected signal's source-fit CDFs are therefore:

`F_r(x) = (1/N_fit) * sum_{q in Climate_source_fit_CS} indicator(S_r(q) <= x)`

with ties included, followed by `P_r(q)=F_r(S_r(q))` and
`G(q)=P_Qwen(q)-P_BM25(q)`. These CDFs are frozen and transferred unchanged;
there is no target recalibration or per-resource CDF refitting.

The hard decision is:

- if `abs(G) <= tau`: Qwen;
- if `G > tau`: Qwen;
- if `G < -tau`: BM25.

Thus BM25 is selected only when `G < -tau`; all ties and abstentions fall back
to Qwen. Fusion, RRF, alpha weighting, confidence exceptions, and additional
thresholds are prohibited.

Only Climate source validation **code-switched variants** select `tau` from
`{0.00, 0.05, 0.10, 0.15, 0.20}`. The objective is highest code-switched
nDCG@10. Ties are broken only by smaller `tau`, then deterministic lexical
serialization order. The grid cannot be expanded or continuously optimized.
Original-query performance and `Delta_CS` are not used for threshold selection
or tie-breaking.

For original English safety reporting on Climate holdout and ArguAna, use the
same selected signal, the same BM25/Qwen CDFs fitted on Climate fit CS variants,
and the same validation-selected `tau`. Do not fit another CDF, recalibrate on
original-query distributions, select another threshold, or use original-query
relevance outcomes for signal selection, threshold selection, tie-breaking, or
any implementation choice. Original queries are used only after method freeze
for safety reporting, `Delta_CS` reporting, and analysis.

## 6. Registered comparators

The report includes BM25-only, Qwen-only, BGE-M3 reference-only, fixed RRF,
and the observed per-query oracle as a diagnostic upper bound.

RRF is baseline-only and fixed as follows. For the union of the existing
depth-1000 BM25 and Qwen candidate rankings, ranks are 1-based and missing
ranks contribute zero:

`RRF_score(d) = sum_r 1/(60 + rank_r(d))`.

The RRF parameter is `60`; it is not tuned.

The Arabzadeh strategy selector is **NOT AVAILABLE unless faithfully
reproducible**. The registered reference is Arabzadeh, Yan, and Clarke,
“Predicting Efficiency/Effectiveness Trade-offs for Dense vs. Sparse Retrieval
Strategy Selection,” CIKM 2021,
[DOI](https://doi.org/10.1145/3459637.3482159). No faithful implementation
with its exact features, objective, and documented deviations has been
identified at freeze. Do not invent or report an “Arabzadeh-like” substitute;
if this remains unresolved, report `NOT AVAILABLE`.

## 7. Metrics and gates

The primary metric is official code-switched nDCG@10. Secondary reporting
includes original-query nDCG@10, `Delta_CS`, recall@10, MRR, and per-query
winner accuracy. Paired uncertainty uses 2,000 bootstrap replicates of complete
source-query groups with seed `20260809`; the 95% lower bound is the 2.5th
percentile of selector-minus-Qwen replicates.

The source gate requires the selector-minus-fixed-Qwen code-switched nDCG@10
paired-bootstrap 95% lower bound to be strictly greater than zero on the
Climate post-exploratory frozen holdout. The transfer gate requires the
unchanged selector-minus-fixed-Qwen code-switched nDCG@10 point estimate to be
at least zero on ArguAna. Positive source evidence with a failed target gate is
a failed transfer.

For both source holdout and transfer, report selector/Qwen/BM25 nDCG@10,
`Delta_CS`, selector-versus-Qwen paired confidence intervals, and secondary
winner accuracy. The frozen safety rule permits no negative 95% lower bound for
selector-minus-Qwen original-query nDCG@10.

A failed gate is a null/negative calibration or transfer result. It permits no
retuning, second selector, threshold change, corpus reduction, final-test
exception, or mitigation claim.

## 8. Execution order and stop rules

The exact primary flow is: Climate fit CS variants → compute raw margin and
dispersion independently → construct candidate-specific BM25/Qwen empirical
CDFs → select one signal using Climate fit CS winner labels → discard the
unselected signal → freeze the selected signal and its source-fit CDFs →
Climate validation CS variants → select `tau` from the fixed grid → freeze
implementation → evaluate Climate holdout once → human review and registered
gate → apply the identical selected signal, CDFs, `tau`, and implementation to
ArguAna transfer → no target recalibration. Original-query safety reporting
uses the same CS-derived calibration and `tau`.

Before any future execution, verify the protocol, data-protocol, benchmark,
split, baseline-artifact, dependency, and implementation checksums. CSR-L
execution is permitted only if the registered gates pass and a human approves.

Stop before execution for any source-qualified overlap, unexpected final
artifact, split/checksum mismatch, changed retriever revision/configuration,
missing or altered baseline artifact, or changed signal/CDF/threshold/RRF rule.
After any gate failure, stop without rerunning, retuning, reversing direction,
reducing the corpus, or inspecting final results for selection.

## 9. Leakage validation status

The independent raw-artifact revalidation is **PASS**, with zero
source-qualified development/final overlap, based on
`results/audit/dataset_overlap.json` and
`results/audit/source_query_overlap.csv`.

The later dataset-backed `scripts/validate_audit.py` attempt is
**INCONCLUSIVE_TIMEOUT** after 180 seconds during cached Hugging Face metadata
resolution. It did not launch retrieval or GPU work. This operational timeout
does not indicate leakage, does not indicate validator failure, and does not
supersede the raw-artifact PASS.

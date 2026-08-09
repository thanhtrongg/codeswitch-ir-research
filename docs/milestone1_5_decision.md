# Milestone 1.5 decision

Date: 2026-08-09  
Scope: protocol clarification, leakage revalidation, novelty threat audit,
complementarity interpretation, and preregistration only.

## 1. Executive verdict

**CONDITIONAL GO for one narrow empirical question; NO-GO for a new
adaptive-alpha, fusion, structure-only, or generic routing method.**

Milestone 1.5 stops here. No mitigation was implemented, no new dense encoding
job was launched, and the final CSR-L suite remains untouched.

## 2. Protocol correction

Milestone 1 actually ran only Chinese-English (`zh-en`) query pairs on ArguAna and
ClimateFEVERHardNegatives. The earlier development language list described
available CS-MTEB variants and could be misread as an execution record. The frozen
protocol now records `languages_evaluated_milestone1: [zh]`, separately lists
available-but-not-evaluated `ja`, `de`, `es`, `ko`, `fr`, `it`, `pt`, and `nl`, and
records the two resources and `source_query_group` rule.

This is a transparency amendment, not a new experiment: no metric, artifact,
selection decision, model revision, or final boundary changed. See
`configs/data_protocol.yaml` and `docs/protocol_amendment_m1_5.md`.

## 3. Leakage revalidation

**PASS.** The raw `results/audit/dataset_overlap.json` and
`results/audit/source_query_overlap.csv` were re-inspected. Development/final
intersections are empty at source-dataset, source-qualified source-query-group,
qrel-signature, qrel-document, and corpus-artifact levels. Source corpus IDs are
not treated as globally meaningful when the manifests do not provide them.

There are 11 raw numeric query-ID collisions between ClimateFEVER and the
unrelated Touche resource; they disappear under source-qualified identity. The
six CSR-L/CS-MTEB counterpart pairs share source provenance and qrel documents,
remain on the final side, and were excluded from development. No final retrieval,
metric, selection, tuning, or artifact was created. Full evidence is in
`docs/leakage_revalidation_m1_5.md`.

## 4. What Milestone 1 actually established

Independent reads of the existing metric artifacts give these official nDCG@10
Delta_CS values:

| Resource | BM25 | Qwen3-Embedding-0.6B | BGE-M3 |
|---|---:|---:|---:|
| ArguAna | -0.0243428 | +0.0003294 | -0.0069764 |
| ClimateFEVERHardNegatives | -0.0292806 | -0.0296689 | -0.0064184 |

Qwen is the selected development-only dense backbone by code-switched nDCG, but
it is not uniformly robust. Fixed BM25 and Qwen have different per-query outcomes
on both development resources. ClimateFEVER supplies larger diagnostic oracle
headroom; ArguAna supplies a smaller, noisier cross-resource check.

## 5. What Milestone 1 did not establish

Milestone 1 did not establish:

- a causal explanation in CMI, switch ratio, entropy, switch count, or query length;
- a deployable selector, router, gate, confidence estimator, fusion rule, or alpha;
- that an oracle diagnostic is achievable by an unlabeled query-time signal;
- generality beyond the two `zh-en` development resources;
- performance on any CSR-L final resource or language; or
- a new code-switched hybrid-retrieval mechanism.

The existing structure correlations are exploratory, weak, and inconsistent.

## 6. Code-switch structure verdict

**NO-GO for structure-only mitigation.** Simple switch ratio, switch count,
language entropy, and query length do not provide stable evidence for an
`alpha(q)` or gate. Structure measurements and structure-driven routing are also
already represented in prior work, including [SETU-RAG](https://digitalcommons.isical.ac.in/masters-dissertations/458/)
and [When Does Mixing Help?](https://aclanthology.org/2026.acl-long.1455/).

Milestone 1.5 therefore does not run new structure experiments or implement a
CMI/switch-ratio router.

## 7. Sparse/dense complementarity verdict

Complementarity is a valid diagnostic, not a contribution. On ClimateFEVER,
BM25 survives while Qwen degrades on 164/1000 queries (16.4%), Qwen survives
while BM25 degrades on 123/1000 (12.3%), both degrade on 94/1000 (9.4%), and
neither degrades on 619/1000 (61.9%). Delta correlation is 0.14383.

Qwen CS nDCG is 0.1850795, BM25 CS nDCG is 0.1092986, and the observed
per-query oracle is 0.2221703. On ArguAna, the corresponding one-sided counts are
166 (11.8%), 202 (14.4%), 41 (2.9%), and 997 (70.9%), with correlation 0.07195.
The oracle means are 0.4600284 for ArguAna and 0.2221703 for ClimateFEVER.

The oracle uses observed outcomes and is therefore an upper bound, not a
realizable method. See `docs/complementarity_interpretation_m1_5.md`.

## 8. Updated novelty landscape

The fresh primary-source search covered code-switched IR, sparse+dense code-mixed
retrieval, query-adaptive hybrid search, confidence/QPP, mixture/routing,
code-switch structure, FIRE CMIR, mixing-ratio analysis, and all named threats.

The landscape is crowded: code-switching degradation and benchmark analysis are
covered by [CSR-L/CS-MTEB](https://aclanthology.org/2026.findings-acl.636/);
code-mixed BM25+dense, RRF, and reranking appear in [ContrastiveMix](https://aclanthology.org/2024.naacl-short.17/)
and [FIRE CMIR](https://ceur-ws.org/Vol-4173/); generic routing is established;
and confidence, adaptive weighting, and QPP are established adjacent mechanisms.

## 9. Critical prior-art threats

The strongest threats are:

- [QuDAR](https://aclanthology.org/2026.acl-long.1791/): query-wise sparse/dense
  adaptation and margin/confidence signals;
- [Query-Adaptive Hybrid Search](https://www.mdpi.com/2504-4990/8/4/91): learned
  query-specific sparse/dense alpha with complementarity-aware training;
- [Arabzadeh et al.](https://doi.org/10.1145/3459637.3482159): query-level sparse,
  dense, and hybrid strategy selection;
- [MoR](https://aclanthology.org/2025.emnlp-main.601/): per-query mixture,
  comparative advantage, weighting, and oracle routing;
- FIRE systems such as [dense-sparse RRF](https://ceur-ws.org/Vol-4173/T3-7.pdf)
  and [Decoding Benglish](https://ceur-ws.org/Vol-4173/T3-9.pdf): direct
  code-mixed hybrid/reranking precedents; and
- [SETU-RAG](https://digitalcommons.isical.ac.in/masters-dissertations/458/):
  thesis-level CMI/matrix-language routing prior art.

The complete 22-entry matrix and mechanism distinctions are in
`docs/novelty_audit_m1_5.md`.

## 10. Claim novelty matrix summary

The claim-level status is:

- C1 code-switching hurts retrieval: **CLEARLY COVERED**;
- C2 BM25/dense complementarity: **CLEARLY COVERED**;
- C3 code-mixed BM25+dense improvement: **CLEARLY COVERED**;
- C4 structure-driven adaptation: **STRONGLY THREATENED**;
- C5 query-specific sparse/dense alpha: **CLEARLY COVERED**;
- C6 sparse/dense query routing: **CLEARLY COVERED**;
- C7 confidence/margin selection: **STRONGLY THREATENED**;
- C8 structure plus behavior for relative reliability: **POSSIBLE GAP, HIGH RISK**;
- C9 code-switch mitigation by choosing the more reliable retriever:
  **PARTIALLY COVERED, HIGH RISK**.

Details and defensibility conditions are in `docs/claim_novelty_matrix.md`.

## 11. Candidate research questions

At most three candidates were considered:

1. **RQ1 — KEEP, conditional:** Under benchmark-provided Chinese-English
   code-switched variants (reported by the audit as LLM-generated), do existing
   unlabeled post-retrieval/query-performance signals predict relative fixed
   BM25-versus-Qwen reliability and transfer across disjoint domains better than
   fixed single-retriever baselines, without score fusion, CMI features, or
   retriever training?
2. **RQ2 — REJECT:** Can switch ratio, CMI, entropy, or matrix-language structure
   determine an adaptive alpha or gate?
3. **RQ3 — REJECT:** Can a new BM25+Qwen fusion/RRF/adaptive weighting method
   improve code-mixed retrieval?

## 12. Rejected candidate ideas and reasons

RQ2 is rejected because the development evidence does not support it and the
structure/mixing idea is already threatened by direct and adjacent prior art.
RQ3 is rejected because code-mixed hybrid, RRF, reranking, adaptive alpha, and
mixture weighting are already demonstrated by FIRE, ContrastiveMix, QuDAR, Query-
Adaptive Hybrid Search, and MoR.

These are not rescued by combining known features: a feature soup or an exact
unpublished combination would be combinatorial novelty, not a defensible gap.

## 13. Surviving research question

RQ1 survives only as a high-risk empirical calibration/transfer study. It does not
claim to invent routing, confidence, QPP, fusion, CMI, or complementarity.

## 14. Exact distinction from closest prior work

The closest generic selector is Arabzadeh et al.; the closest confidence/weighting
threats are QuDAR and Query-Adaptive Hybrid Search; MoR is the closest
complementarity/oracle analysis; and FIRE supplies direct code-mixed hybrid
precedents. None of the inspected primary sources matched all of these conditions
simultaneously: benchmark-provided Chinese-English code-switched variants (not
claimed to be naturally occurring or human-authored), fixed BM25 and fixed Qwen-like
dense retrieval, an unlabeled predictor of *relative* retriever reliability,
source-query-safe cross-resource transfer, and original-versus-code-switched
Delta_CS.

That non-match is not proof of novelty. The only potentially meaningful
distinction is the scientific question of whether existing unlabeled behavior/QPP
signals remain calibrated for this relative-reliability target under
benchmark-provided code-switching and domain transfer. It must be evaluated as a transfer/calibration
study, not presented as a new feature combination or routing mechanism.

## 15. Proposed Milestone 2 protocol

Because RQ1 survives conditionally, a future protocol was written but not run:

- `configs/milestone2_protocol.yaml`
- `docs/milestone2_preregistration.md`

It specifies source-query-group splits with deterministic seed `20260809`,
fit/validation/frozen-holdout order, one hard-selection candidate, a finite
threshold grid, registered comparisons, paired bootstrap analysis, transfer
reporting, freeze/checksum requirements, and CSR-L access only after approval and
freeze. It acknowledges that Milestone 1 informed the hypothesis. It prohibits
fusion, adaptive alpha, CMI features, query expansion, LLM judging, retriever
training, corpus reduction, and post-final retuning.

## 16. Remaining novelty risks

Novelty remains high-risk because generic query selection, QPP, confidence,
mixture routing, adaptive weighting, and code-mixed hybrid retrieval are all
established. The two development resources are limited to `zh-en`, and the
Milestone 1 exploration means they cannot be described as independent
confirmatory data. A positive result may be a useful benchmarked transfer finding
without supporting a new-method claim; a failed transfer is also a valid negative
result. Human review must decide whether that contribution is sufficient before
any implementation.

## 17. GO / CONDITIONAL GO / NO-GO

**CONDITIONAL GO.** The narrow RQ1 is empirically motivated and methodologically
testable, but its distinction from generic selectors and QPP is not strong enough
for an unconditional novelty claim. RQ2 and RQ3 are NO-GO. Milestone 1.5 ends
with the preregistration only; Milestone 2 implementation and all CSR-L retrieval
remain blocked pending explicit human approval.

**FINAL TEST UNTOUCHED.** No mitigation method was implemented, no new final-test
result was created, and no unnecessary dense GPU job was launched.

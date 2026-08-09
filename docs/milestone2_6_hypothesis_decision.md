# Milestone 2.6 hypothesis decision

Audit date: 2026-08-09  
Decision: **NO-GO — NO DEFENSIBLE NEW HYPOTHESIS FOUND**

Milestone 2.6 was a literature and design audit only. It did not authorize a
retrieval run, encoder, GPU worker, evaluation, tuning, or protected-data
access.

## Candidate definitions

### H1 — asymmetric selective risk / abstention

For a fixed BM25-versus-Qwen choice, an unlabeled confidence signal could
abstain from or defer potentially harmful switches under an asymmetric
risk/coverage objective, while preserving original-query performance.

### H2 — retriever disagreement / coverage

Unlabeled disagreement, score behavior, or candidate coverage could predict
when BM25 adds useful evidence over Qwen and support hard retriever selection.

### H3 — multi-source calibration / invariance

Calibrating heterogeneous retriever/source signals on clean development data
could make relative reliability transfer across disjoint domains and language
conditions without target recalibration.

### H4

No H4 was generated. A structure-only or structure-plus-behavior H4 would be a
crowded recombination of CMI/mixing-ratio analysis, code-mixed probes, query-wise
weighting, and routing. It fails the “not crowded” condition before experiment.

## Verdicts

| Hypothesis | Verdict | Decisive reason |
|---|---|---|
| H1 | REJECT — crowded/high risk | Selective prediction and risk-coverage are established; risk-aware RAG, source reliability, and training-free source choice directly cover selective knowledge access. The exact sparse/dense code-switch target is only an evaluation distinction. |
| H2 | REJECT — strongly threatened | MoR, Arabzadeh et al., RouterRetriever, LARMOR, QuDAR, and FIRE systems cover per-query selection, disagreement/complementarity, oracle headroom, and hybrid retrieval. |
| H3 | REJECT — no mechanism-level gap | QPP transfer failures, LARMOR, Query-Adaptive Hybrid Search, QuDAR, RA-RAG, and adaptive-retrieval work cover calibration, uncertainty, source reliability, and cross-domain variation. |
| H4 | NOT PROPOSED | Any obvious code-switch-structure variant is already crowded and is unsupported by the prior milestone’s exploratory evidence. |

## Scoring screen

Scores are 1 (poor) to 5 (strong). They are a structured aid, not a mechanical
decision rule. The critical novelty-collision veto overrides aggregate scores.

| Candidate | Problem importance | Empirical motivation | Novelty | Distinction from closest work | Collision resistance | Scientific falsifiability | Data-boundary fit | Expected feasibility | Transfer value | Reviewer defensibility | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 4 | 4 | 2 | 2 | 1 | 4 | 4 | 4 | 3 | 2 | 30 |
| H2 | 4 | 4 | 1 | 1 | 1 | 4 | 4 | 3 | 3 | 1 | 26 |
| H3 | 4 | 3 | 2 | 2 | 1 | 3 | 4 | 3 | 4 | 2 | 28 |

H1 has the best scientific motivation, but its mechanism remains generic
selective prediction/risk control. H3 has possible transfer value, but the
claimed invariance is not operationally distinct from established calibration
and domain-generalization questions. None clears the novelty collision veto.

## Novelty boundary that remains unresolved

The narrowest non-colliding formulation found was:

> Do existing unlabeled QPP/behavior signals transfer to relative fixed
> BM25-versus-dense reliability under benchmark-provided code-switched variants
> and source-query-safe cross-domain evaluation, while preserving original-query
> performance?

This is a potentially useful empirical audit, but it is an evaluation setting
for existing mechanisms. It does not justify claiming a new selector, routing
algorithm, confidence signal, abstention method, fusion rule, or code-switch
feature. The current literature is too close for a defensible Milestone 3
hypothesis without a materially sharper research question.

## Data decision

No fresh data were opened. ClimateFEVER remains consumed; ArguAna remains a
historically known, outcome-unseen target for this audit; CSR-L remains the
strong untouched final boundary. A future project would require a new written
data ledger, clean split, frozen signal set, and human approval before any CSR-L
access.

## Authorization

Milestone 3 is not authorized and no preregistration draft is created. The
absence of `docs/milestone3_preregistration_draft.md` is intentional: no
hypothesis survived the novelty audit. No implementation or experiment may be
inferred from this document.

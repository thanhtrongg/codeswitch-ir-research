# Research index

This page is the chronological map of the archived Code-Switching IR research
record. Machine-readable outputs are linked where they are small and suitable
for repository distribution.

## 1. Milestone 1

- Purpose: benchmark audit, leakage-safe baselines, dense retriever selection,
  and initial complementarity analysis.
- Verdict: established code-switching degradation and sparse/dense
  complementarity; selected Qwen as the dense primary baseline.
- Key report: [Milestone 1 report](milestone1_report.md)
- Key outputs: [benchmark overlap audit](../results/audit/dataset_overlap.json),
  [retriever selection](../results/tables/selection.json)

## 2. Milestone 1.5

- Purpose: interpret complementarity, revalidate leakage, and audit novelty
  before proposing a follow-up experiment.
- Verdict: a narrowly scoped QPP transfer question remained conditionally
  testable, subject to a hardened freeze.
- Key report: [Milestone 1.5 decision](milestone1_5_decision.md)
- Key outputs: [novelty audit](novelty_audit_m1_5.md),
  [claim novelty matrix](claim_novelty_matrix.md)

## 3. Milestone 1.5b

- Purpose: harden and freeze the preregistration candidate.
- Verdict: candidate selector and data boundary specified for Milestone 2.
- Key report: [Milestone 1.5b freeze report](milestone1_5b_freeze_report.md)
- Key output: [Milestone 2 freeze manifest](../results/protocol/milestone2_freeze_manifest.yaml)

## 4. Milestone 1.5c

- Purpose: resolve semantic ambiguities in normalization, calibration scope,
  and leakage labels.
- Verdict: candidate-specific CDFs and code-switched-only calibration frozen;
  prior decisions unchanged.
- Key report: [Milestone 1.5c semantic freeze report](milestone1_5c_semantic_freeze_report.md)
- Key output: [Milestone 1.5c manifest](../results/protocol/milestone2_freeze_manifest_1_5c.yaml)

## 5. Milestone 1.5d

- Purpose: apply the final protocol correction and establish the stop rule.
- Verdict: final protocol freeze completed; no result or boundary changed.
- Key report: [Milestone 1.5d protocol fix](milestone1_5d_final_protocol_fix.md)
- Key output: [Milestone 1.5d manifest](../results/protocol/milestone2_freeze_manifest_1_5d.yaml)

## 6. Milestone 2

- Purpose: execute the frozen QPP hard-selector experiment.
- Verdict: the ClimateFEVER source gate failed; ArguAna transfer was not
  executed after source failure; CSR-L was not accessed.
- Key report: [Milestone 2 report](milestone2_report.md) and
  [preregistration](milestone2_preregistration.md)
- Key outputs: [Milestone 2 summary](../results/milestone2/milestone2_summary.json),
  [holdout results](../results/milestone2/holdout/holdout_results.json),
  [source gate](../results/milestone2/gates/climate_source_gate.json),
  [final status](../results/milestone2/gates/final_status.json)

## 7. Milestone 2.5

- Purpose: perform a scientific postmortem of the failed source-gated
  experiment.
- Verdict: weak identifiability, class imbalance, distribution shift, and
  costly false BM25 switches explain the failure; no retuning was performed.
- Key report: [Milestone 2.5 postmortem](milestone2_5_scientific_postmortem.md)
- Key output: [Milestone 2.5 summary](../results/milestone2_5/milestone2_5_summary.json)

## 8. Milestone 2.6

- Purpose: conduct a fresh literature and novelty audit before any new
  experiment.
- Verdict: H1/H2/H3 rejected, H4 not proposed, and no new hypothesis survived
  the audit. No experiment or new data access occurred.
- Key reports: [fresh novelty audit](milestone2_6_fresh_novelty_audit.md),
  [hypothesis decision](milestone2_6_hypothesis_decision.md),
  [reviewer attack](milestone2_6_reviewer_attack.md)
- Key outputs: [Milestone 2.6 summary](../results/milestone2_6/milestone2_6_summary.json),
  [prior-work matrix](milestone2_6_claim_prior_work_matrix.md),
  [literature CSV](../results/milestone2_6/literature/prior_work.csv)

Current branch status:

**NO-GO — NO DEFENSIBLE NEW HYPOTHESIS FOUND.**

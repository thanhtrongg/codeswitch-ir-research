# Milestone 1.5d final protocol fix

Date: 2026-08-09  
Supersedes: `milestone_1_5c`  
Status: **READY FOR MILESTONE 2 IMPLEMENTATION**

This is a single protocol correction. No Milestone 2 experiment or outcome
inspection was performed.

## Threshold-selection correction

Threshold selection is now fully restricted to Climate source validation
code-switched variants. The objective remains highest code-switched nDCG@10.
The only tie-breaks are, in order:

1. smaller `tau`;
2. deterministic lexical serialization order.

Original-query nDCG@10 and `Delta_CS` have been removed from threshold
selection and tie-breaking. The threshold grid remains exactly
`{0.00, 0.05, 0.10, 0.15, 0.20}`.

Original English queries are used only after the method is frozen for safety
reporting, `Delta_CS` reporting, and analysis. They do not influence signal
selection, CDF fitting, threshold selection, tie-breaking, or implementation
choices.

## Preserved decisions

The research question, ClimateFEVERHardNegatives → ArguAna direction,
600/200/200 split, source split checksums, margin/dispersion signals, removed
coherence signal, equations, `k=10`, `epsilon=1e-12`, Qwen primary baseline,
BM25 secondary baseline, RRF `k=60` baseline-only comparator, leakage boundary,
and untouched CSR-L final test are unchanged.

The source split file was not regenerated or modified. The raw-artifact leakage
status remains **PASS** with zero source-qualified overlap. The dataset-backed
validator remains **INCONCLUSIVE_TIMEOUT** after 180 seconds.

The 1.5d versioned freeze manifest is
`results/protocol/milestone2_freeze_manifest_1_5d.yaml` and supersedes, without
erasing, the 1.5c freeze history.

## Stop condition

Static YAML parsing, protocol validation, tests, and checksum verification are
required and were run without retrieval or experimental outcome inspection.
Human approval remains required before Milestone 2.

**READY FOR MILESTONE 2 IMPLEMENTATION**

STOP after Milestone 1.5d. Do not start Milestone 2 in this task.

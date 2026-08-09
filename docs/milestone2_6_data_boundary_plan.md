# Milestone 2.6 data boundary plan

This is a future-only boundary plan.  It authorizes no data access and no
experiment in Milestone 2.6.

## Historical state

- ClimateFEVERHardNegatives has been consumed by the completed Milestone 2
  development/holdout process.  Its saved outcomes are historical evidence and
  must not be treated as fresh confirmatory data.
- ArguAna is historically known from the completed development record, but its
  outcome files are not a new target and were not read during this audit.
- CSR-L and its stronger final evaluation boundary remain untouched.
- CSR-L outcomes, ranking files, qrels, and final metrics must not be accessed
  for the literature decision or used to tune any candidate.

## If a future milestone is separately approved

The future protocol would require a new clean source-query-group split and a
written access ledger before any protected data are opened.  The order would be:

1. Fit any already-registered calibration only on clean development groups.
2. Use a separate development validation portion for model/threshold decisions.
3. Freeze checksums and the decision rule before any protected target access.
4. Use ArguAna only as a historically specified transfer check or a newly
   approved clean split; never silently reinterpret its old results as fresh.
5. Reserve CSR-L for the final untouched evaluation, with no target
   recalibration, feature selection, threshold search, or post-final retuning.

## Required exclusions

No future implementation may silently turn a research question into a new
fusion or adaptive-alpha method.  The following are outside the current
boundary: new dense encoding; retrieval reruns; corpus reduction; new model
instances; score fusion; learned alpha; CMI-only routing; query expansion;
LLM judging; target-derived calibration; and any access to CSR-L before a
human-approved preregistration and freeze.

## Interpretive boundary

Even if a future clean test showed that an existing signal transfers, the
claim would be an empirical calibration/transfer result for the fixed retriever
pair and data construction.  It would not be evidence that QPP, abstention,
routing, disagreement, or code-switch structure was invented in the project.

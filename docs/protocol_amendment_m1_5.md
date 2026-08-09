# Protocol amendment for Milestone 1.5

Date: 2026-08-09

## Amendment

The completed Milestone 1 runs evaluated only the Chinese-English (`zh-en`) query pairs on:

- `ArguAna`
- `ClimateFEVERHardNegatives`

The published CS-MTEB resources make additional language variants available (`ja`, `de`, `es`, `ko`, `fr`, `it`, `pt`, `nl`), but those variants were not evaluated in Milestone 1. `configs/data_protocol.yaml` previously listed the available resource languages in the development `languages` field without distinguishing availability from execution history.

The development protocol now records:

- `languages_evaluated_milestone1: [zh]`
- `languages_available_not_evaluated: [ja, de, es, ko, fr, it, pt, nl]`
- `execution_history.evaluated_query_pairs: zh-en`
- the two development resources actually used: `ArguAna` and
  `ClimateFEVERHardNegatives`;
- `source_query_group` as the grouping identity, so original and rewritten
  variants of one source query are never treated as independent observations; and
- the six CSR-L resources as final-test-only resources with selection disabled.

## Reason and methodological impact

This is a transparency clarification, not a new experiment. It corrects the possible interpretation that all published development language pairs had been run. It does not change any existing metric, artifact, model selection decision, source-query grouping rule, or final-test boundary. Milestone 1 remains a two-dataset, zh-en development study.

The final CSR-L resources and their available language variants remain final-test-only. No retrieval or evaluation was performed on them.

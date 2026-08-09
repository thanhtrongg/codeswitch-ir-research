# Milestone 1.5c semantic freeze report

Date: 2026-08-09  
Supersedes: `milestone_1_5b`  
Status: **READY FOR MILESTONE 2 IMPLEMENTATION**

This is a tiny protocol-correction milestone. Milestone 2 was not executed,
and human approval is still required before implementation or execution.

## Corrections made

### 1. Candidate-specific CDFs remove the circularity

For each active candidate independently—normalized margin and top-k
dispersion—the protocol now requires, on Climate source-fit code-switched
variants only:

1. compute the candidate's raw BM25 and Qwen signals;
2. construct that candidate's separate BM25 and Qwen empirical CDFs;
3. convert the raw values to candidate-specific percentiles;
4. compute candidate-specific `G = P_Qwen - P_BM25`;
5. predict Qwen at `tau=0` when `G>=0`, otherwise BM25; and
6. compare with the observed code-switched BM25-vs-Qwen winner label.

The highest mean per-query winner classification accuracy selects exactly one
signal, with margin before dispersion as the deterministic tie-break. The
unselected signal is then discarded. Only the selected definition and its two
Climate-fit CDFs proceed to validation, holdout, transfer, and original-query
safety reporting.

No signal combination, averaging, classifier, or third signal was added.

### 2. Calibration scope is Climate fit code-switched variants only

CDF fitting, signal-family selection, and winner-label construction are now
explicitly restricted to Climate source-fit `zh-en` code-switched variants.
Original English variants are excluded from those procedures. The winner label
is BM25 only when per-query CS nDCG@10(BM25) strictly exceeds CS nDCG@10(Qwen);
ties are Qwen, and the label is unavailable at inference.

Threshold selection remains Climate validation CS-only on the unchanged grid
`{0.00, 0.05, 0.10, 0.15, 0.20}`. The pre-registered original-query tie-break
remains unchanged, but original queries never receive a new CDF or threshold.
Original-query safety uses the selected signal, Climate-fit CS CDFs, and the
validation-selected `tau` unchanged.

### 3. Leakage statuses are separated

The independent raw-artifact revalidation is recorded as:

- **PASS**;
- source-qualified development/final overlap: `0`; and
- evidence: `results/audit/dataset_overlap.json` and
  `results/audit/source_query_overlap.csv`.

The later dataset-backed validator is separately recorded as
**INCONCLUSIVE_TIMEOUT** after 180 seconds during metadata resolution. The
timeout does not indicate leakage, does not indicate validator failure, and
does not supersede the raw-artifact PASS.

## Unchanged frozen decisions

The research question, ClimateFEVERHardNegatives → ArguAna direction, Qwen
revision, BM25/Qwen/BGE roles, margin and dispersion equations, removed
coherence signal, `k=10`, `epsilon=1e-12`, threshold grid, RRF `k=60`, CSR-L
boundary, and no-new-dense-encoding policy are unchanged.

The exact source split was not regenerated or modified: 600 fit, 200
validation, and 200 post-exploratory frozen-holdout groups, seed `20260809`.
The source-group checksum remains
`49d53e935f3e9e54c252d9aa130107f0bff1e5e678d39d8aa325916f307dab5b`; the
assignment checksum remains
`fb1514ce76470601464f51ade05877fe33b5850b5d1087a1f4dc52ddd0fcdf9b`.

Milestone 1's use of all 2,406 development groups remains exploratory. The
Climate holdout is post-exploratory and procedurally protected, not historically
untouched; ArguAna also appeared in earlier exploratory analysis. CSR-L remains
the only truly untouched final evaluation boundary.

## Verification and stop condition

The final 1.5c manifest is
`results/protocol/milestone2_freeze_manifest_1_5c.yaml`. It records the required
SHA-256 hashes and supersession of the 1.5b freeze. Static semantic checks,
YAML parsing, protocol validation, compilation, and tests must pass before this
milestone is handed off.

No new experimental outcome was inspected or used. No retrieval, BM25, Qwen,
RRF, selector, GPU work, corpus encoding, or CSR-L access occurred.

**READY FOR MILESTONE 2 IMPLEMENTATION**

STOP after Milestone 1.5c. Do not start Milestone 2 in this task.

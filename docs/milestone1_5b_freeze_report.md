# Milestone 1.5b freeze report

Date: 2026-08-09  
Status: **COMPLETE — Milestone 2 preregistered, hardened, frozen, and not executed**

## Outcome

Milestone 1.5 remains **CONDITIONAL GO** for one narrow empirical calibration/
transfer question only:

`ClimateFEVERHardNegatives source → ArguAna target`.

It remains **NO-GO** for structure-only alpha, CMI/switch-ratio routing,
BM25+dense fusion, RRF as a proposed method, generic routing, adaptive alpha,
or confidence routing as a claimed method.

The hardened protocol is in
`configs/milestone2_protocol.yaml` and
`docs/milestone2_preregistration.md`. The immutable file/checksum record is in
`results/protocol/milestone2_freeze_manifest.yaml`.

## Freeze decisions

- Development variants are described as benchmark-provided zh-en variants,
  reported by the audit as LLM-generated. No naturally occurring or
  human-authored development evidence is claimed.
- Milestone 1 used all 2,406 development groups exploratorily. The new holdout
  is procedurally protected after exploration, not historically untouched.
  CSR-L remains the only truly untouched final boundary.
- Climate is the sole source resource because it showed larger Milestone 1
  BM25/Qwen disagreement and oracle headroom. ArguAna is target-transfer only;
  the reverse direction is not registered.
- The exact Climate split is materialized before selector implementation: 1,000
  source-query groups, 600 fit, 200 validation, 200 post-exploratory frozen
  holdout, with 2,000 variants kept together. The group and assignment checksums
  are recorded in the protocol and manifest.
- Qwen3-Embedding-0.6B is the fixed primary baseline; BM25 is secondary; BGE-M3
  is reference-only.

## Candidate specification

Two active signals are frozen at `k=10`, `epsilon=1e-12`:

1. normalized top-1 minus top-2 score margin; and
2. top-k score dispersion using population standard deviation (`ddof=0`) of the
   registered normalized score values.

Retrieved-set embedding coherence is explicitly removed before selection. The
only validated cache found was a BGE-M3 Climate cache; the Qwen run recorded no
cache path and did not persist embeddings. No new Qwen corpus encoding is
authorized to restore this signal.

The selected signal uses only Climate source-fit outcomes. Raw signal values
are converted with source-fit empirical CDFs separately for BM25 and Qwen;
those CDFs are frozen and transferred unchanged. The hard rule is Qwen when
`G >= -tau` and BM25 only when `G < -tau`, where
`G=P_Qwen-P_BM25`; the validation-only threshold grid is
`{0.00, 0.05, 0.10, 0.15, 0.20}`.

The primary success comparison is always selector minus fixed Qwen, not the
stronger baseline. Source success requires a positive paired-bootstrap 95%
lower bound on Climate holdout code-switched nDCG@10. Transfer requires a
nonnegative selector-minus-Qwen point estimate on ArguAna. Original-query
selector-versus-Qwen paired safety intervals are reported for both.

RRF is a fixed baseline-only comparator with
`RRF_score(d)=sum_r 1/(60+rank_r(d))`; its parameter is not tuned. The
Arabzadeh comparator is `NOT AVAILABLE` unless a faithful implementation with
exact features/objective/deviations is identified; no “Arabzadeh-like”
substitute is permitted.

## Operational checks and limitations

The existing development Qwen artifacts record max length 512, tokenizer
truncation enabled, dynamic longest-in-batch padding, `torch.float16`, source
batch size 32, and target batch size 16. The selector consumes existing
rankings/scores; this freeze did not launch encoding, retrieval, GPU work, or a
second model instance.

Raw Milestone 1.5 manifest revalidation passed. The later audit validator was
inconclusive because it timed out after 180 seconds during cached Hugging Face
dataset metadata resolution. It did not launch retrieval or GPU work. The
timeout is not treated as evidence of either pass or failure; the independent
raw overlap artifacts remain the recorded leakage evidence.

No Milestone 2 method, selector, fusion, RRF run, final encoding, or CSR-L
evaluation was performed in this freeze.

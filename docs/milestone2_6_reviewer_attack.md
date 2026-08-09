# Milestone 2.6 reviewer attack

This document treats the most skeptical reasonable reviewer as the decision
maker.  No experiment is proposed here to answer the objections.

## Attack 1: “The project is rediscovering code-switching degradation.”

Valid. CSR-L/CS-MTEB (ZENG2026) directly benchmarks degradation, embedding
divergence, and multiple retriever families.  Any current project result on
ClimateFEVER or future CSR-L must be described as characterization or
replication.

## Attack 2: “The project is rediscovering BM25/dense complementarity.”

Valid. MoR, the FIRE CMIR overview, FIRE RRF, LexiSemIR, and Decoding Benglish
already report complementary lexical and semantic systems, oracle comparisons,
fusion, or reranking.  Per-query disagreement is not itself a contribution.

## Attack 3: “The proposed margin selector is QuDAR in a smaller costume.”

Valid and decisive. QuDAR explicitly uses top-1/top-2 score margins and dynamic
sparse/dense query-wise weighting, and is a 2026 ACL paper.  Restricting the
method to hard selection or removing query expansion changes the implementation
but not the mechanism-level collision.

## Attack 4: “Adaptive alpha is already a published method.”

Valid and decisive. Query-Adaptive Hybrid Search predicts a query-specific alpha
with a learned predictor, uses BM25 plus dense retrieval, and trains against
antagonistic sparse failures.  It also evaluates multilingual and cross-domain
settings.  An exact code-switched dataset would be a new evaluation setting,
not sufficient method novelty.

## Attack 5: “QPP and model selection already solve the problem.”

Partly valid. Arabzadeh et al. select sparse/dense/hybrid strategies; LARMOR and
Khramtsova et al. study unsupervised dense-retriever selection; QPP work studies
unlabeled score/coherence/LLM relevance predictors.  The literature also shows
that these predictors can be unstable across rankers and collections.  This
both threatens novelty and makes an untested positive hypothesis scientifically
uncertain.

## Attack 6: “Abstention is not a retrieval contribution.”

Valid. H1 borrows its evaluation language from selective prediction and risk-
coverage work.  Risk-aware RAG and source-reliability work show closely related
selective knowledge-access decisions, but they do not prove that a sparse/dense
selector will transfer.  This is a distinction in target and data, not a new
abstention mechanism.

## Attack 7: “The apparent gap is a feature-soup/combinatorial novelty claim.”

Valid. Combining CMI, score margin, overlap, and calibration after seeing
Milestone 2.5 outcomes would be post hoc and would not become novel merely
because no paper uses the exact tuple.  A defensible future study would have to
freeze a minimal, literature-derived signal set before target access and call
the result a transfer/calibration evaluation.

## Attack 8: “The data are already contaminated by milestone history.”

Valid. ClimateFEVER has been consumed; the previous development exploration
informed the candidate; ArguAna is historically known; and CSR-L is the only
strong untouched final boundary.  This makes any positive result on the old
resources non-confirmatory and makes target-safe data governance central.

## Attack 9: “A negative result is not a contribution.”

Not necessarily, but it changes the contribution type.  A careful negative
transfer/calibration study could be publishable as a benchmarked failure
analysis if preregistered and compared to strong baselines.  That possibility
does not justify claiming a new hypothesis mechanism now, and the current
review did not find a sufficiently sharp research question to authorize it.

## Attack 10: “The work is too close to current papers to be worth Milestone 3.”

Sustained. The exact evaluation boundary is a possible gap, but H1–H3 all have
direct mechanism collisions and H4 would be a structure-only variant already
threatened by code-mixed probing, mixing-ratio analysis, and CMI routing.  The
correct scientific action is NO-GO until a materially different question is
found, not to run an experiment hoping the result creates novelty.

## Reviewer conclusion

The review can support a transparent account of why Milestone 2 failed and why
the next project should not claim a new selector, fusion, QPP, abstention, or
structure router.  It cannot support a defensible Milestone 3 mechanism.

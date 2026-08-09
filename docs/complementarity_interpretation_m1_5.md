# Interpreting complementarity for Milestone 1.5

## Scope

The complementarity artifacts are diagnostics from the frozen development-only
runs. They compare the per-query code-switched nDCG outcomes of fixed BM25 and
fixed Qwen3-Embedding-0.6B. They do not train a selector, define an alpha, fuse
scores, or access CSR-L.

## A. Is the disagreement real?

Yes, but it is not by itself a contribution. On ClimateFEVERHardNegatives,
BM25 survives while Qwen degrades on 164/1000 queries (16.4%), while Qwen survives
and BM25 degrades on 123/1000 (12.3%). Both degrade on 94/1000 (9.4%), and neither
degrades on 619/1000 (61.9%). The corresponding Delta correlation is positive but
small (Pearson r = 0.14383), so the systems are not identical but are also not
independent complementary experts in a strong statistical sense.

On ArguAna, BM25 survives while Qwen degrades on 166/1406 queries (11.8%), Qwen
survives while BM25 degrades on 202/1406 (14.4%), both degrade on 41/1406 (2.9%),
and neither degrades on 997/1406 (70.9%). The correlation is weaker (r = 0.07195).

## B. Is it enough motivation for a research question?

Yes, conditionally. The one-sided cases establish that a per-query choice could
have headroom in principle. They do not establish that a cheap observable signal
can identify the better retriever before relevance labels are known. The observed
oracle is an upper-bound diagnostic, not a realizable method: it uses the query's
outcome to choose the winner after evaluation.

This distinction matters because generic per-query routing, mixture weighting,
confidence, and oracle analyses already exist. The defensible question is whether
existing unlabeled signals predict *relative* fixed-retriever reliability under
natural code-switching and transfer across source-disjoint domains.

## C. ClimateFEVER one-sided and joint failure pattern

ClimateFEVER supplies the stronger motivation for that question. The BM25-only
and Qwen-only systems have different failure events, but the majority of queries
are in the neither-degrades cell. The 9.4% both-degrade cell also shows that a
router cannot be treated as a universal cure for code-switching degradation.

The Qwen CS nDCG is 0.1850794991, BM25 CS nDCG is 0.1092985646, and the mean
dense-minus-BM25 Delta is -0.0003882915. The issue is therefore not simply that
one globally dominates: relative behavior varies by query even though Qwen is
the stronger aggregate baseline on this resource.

## D. Oracle headroom

The observed per-query oracle mean nDCG is 0.2221703200 on ClimateFEVER and
0.4600284288 on ArguAna. For comparison:

| Resource | Qwen CS nDCG | BM25 CS nDCG | Observed oracle mean | Oracle minus Qwen |
|---|---:|---:|---:|---:|
| ArguAna | 0.4406845468 | 0.2541979268 | 0.4600284288 | +0.0193438820 |
| ClimateFEVERHardNegatives | 0.1850794991 | 0.1092985646 | 0.2221703200 | +0.0370908209 |

The oracle headroom is about 4.4% relative to Qwen on ArguAna and about 20.0%
relative to Qwen on ClimateFEVER. Those ratios are descriptive only; the oracle
has access to the answer and cannot be used as a deployable estimate. The Climate
oracle is also 0.1128719 nDCG above BM25, which illustrates diagnostic headroom
but not a guaranteed achievable gain.

## E. Does complementarity occur in both datasets?

Yes. The one-sided cells occur in both ArguAna and ClimateFEVER, and the oracle
mean is above both single-retriever means in both resources. ClimateFEVER has the
larger absolute Qwen-to-oracle headroom, while ArguAna has the larger Qwen
aggregate advantage over BM25. This is enough to motivate cross-dataset testing,
not enough to establish generality beyond these two development resources.

## F. What ArguAna adds

ArguAna is a smaller and noisier motivation: Qwen wins more often in aggregate,
the oracle gain over Qwen is smaller, the Delta correlation is weak, and the
worst-quartile overlap is high (Jaccard 0.80952). It therefore prevents the
ClimateFEVER pattern from being treated as a universal or easily separable
structure effect. A future signal must be evaluated for transfer rather than
validated only where oracle headroom is largest.

## G. Does structure explain the complementarity?

No causal or sufficiently stable explanation is available. Existing Milestone 1
diagnostics show weak/inconsistent associations between switch ratio, query
length, entropy, and relative outcomes. Examples include ClimateFEVER Qwen
switch-ratio correlation -0.13909 and entropy correlation -0.14640, with weaker
or inconsistent values for BGE and BM25; ArguAna Qwen switch-ratio correlation
is -0.07468. These are exploratory correlations, not validated predictors, and
they do not justify a structure-only gate.

## H. Methodological conclusion

The evidence supports the following limited conclusion:

> Fixed BM25 and fixed Qwen exhibit query-level outcome differences on both
> development resources, creating a diagnostic opportunity to test whether
> existing unlabeled query-performance/behavior signals can predict relative
> reliability under natural code-switching.

It does not support a CMI/switch-ratio alpha, adaptive fusion, structure-only
router, or claim that complementarity itself is novel. Milestone 1.5 implements
none of these mitigations. Any follow-up must be preregistered, source-query
group-safe, and evaluated first on held-out development data.

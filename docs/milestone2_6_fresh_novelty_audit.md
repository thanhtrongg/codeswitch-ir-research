# Milestone 2.6 fresh novelty audit

Date: 2026-08-09  
Final decision: **NO-GO — NO DEFENSIBLE NEW HYPOTHESIS FOUND**

This audit was conducted after the frozen Milestone 2 source-gate failure and
the Milestone 2.5 conditional verdict. It is deliberately literature-only.
No retrieval, dense encoding, model or GPU worker, evaluation, hyperparameter
search, protected-data access, or new experiment was performed.

## Review size and quality

The fresh inventory contains 36 unique works in
`results/milestone2_6/literature/prior_work.csv`, with 36 bibliography entries
including one adjacent code-switching translation paper listed for context.
The review deeply categorized 30+ works across:

- code-switched/code-mixed IR and benchmark analysis;
- BM25 plus dense retrieval, reranking, RRF, and hybrid selection;
- query-wise alpha/weight prediction and expert routing;
- dense-retriever selection and QPP;
- selective prediction, abstention, risk/coverage, and source reliability;
- cross-domain calibration, uncertainty, and transfer.

The closest mechanisms were checked against official abstracts and method/setup
text. The exact source list, queries, inclusion rules, duplicate handling, and
access limitations are in
`results/milestone2_6/literature/search_log.md`.

## Decisive 2024–2026 findings

1. **CSR-L/CS-MTEB (Zeng et al., ACL Findings 2026)** directly establishes
   code-switching IR degradation, evaluates sparse/dense/late-interaction
   families, and analyzes embedding divergence. Code-switching robustness is
   not a new problem claim.
2. **QuDAR (Kim et al., ACL 2026)** directly uses query-wise sparse/dense
   adaptation, top-1/top-2 score margins, and dynamic weighting across original
   and expanded queries. This is a critical collision for margin selection,
   adaptive alpha, and confidence-guided routing.
3. **Query-Adaptive Hybrid Search (Posokhov et al., 2026)** predicts a query-
   specific alpha for BM25 plus a dense encoder and trains against sparse
   failures. This is a direct collision for learned adaptive hybrid weighting.
4. **MoR (Kalra et al., EMNLP 2025)** studies per-query mixtures of sparse,
   dense, and human retrievers, including comparative advantage and oracle
   routing. Per-query complementarity is not a new claim.
5. **RouterRetriever (Lee et al., AAAI 2025)** establishes query-specific
   routing over domain-specific embedding experts. Generic “choose the best
   retriever/model per query” is already a named problem.
6. **RA-RAG (Hwang et al., EMNLP 2025)** estimates source reliability, performs
   selective retrieval, and aggregates with weighted majority voting. It is a
   direct adjacent threat to multi-source reliability and selective coverage.
7. **QPP and model-selection work** (Faggioli et al.; Vlachou and Macdonald;
   Meng et al.; Chifu et al.; Khramtsova et al.) already studies unlabeled
   score/coherence/query-difficulty signals, dense model selection, and their
   poor transfer across collections.
8. **Selective-risk and abstention work** (Xin et al.; Chen et al.; Kim et al.;
   Santosh et al.; Vasisht et al.) establishes risk-coverage, confidence,
   abstention, overconfidence, and generalization-specificity trade-offs.
9. **FIRE CMIR 2025 systems** provide direct code-mixed BM25+dense reranking,
   dense-sparse RRF, fixed fusion, and hybrid complementarity precedents.
10. **Mixing and structure work** (Zhu et al.; Code-Mixed Probes; SETU-RAG;
    Maimaiti et al.) makes CMI, mixing ratio, script structure, and structure-
    aware routing poor candidates for a new mechanism.

## Closest-work audit: H1

| Work | Exact method overlap | Setting | Key difference | Threat |
|---|---|---|---|---|
| Xin et al. 2021 | Selective prediction, confidence threshold, risk/coverage | NLP classification | Not retrieval or code-switching | HIGH |
| Chen et al. 2024 | RAG risk control and abstention based on retrieval quality/use | QA/RAG | Output risk rather than retriever-choice risk | HIGH |
| Kim et al. 2025 CDA | Training-free adaptive prioritization of knowledge sources plus abstention | LLM generation | Parametric/contextual sources, not BM25/Qwen | HIGH |
| Santosh et al. 2024 | Confidence estimators, calibration, risk-coverage and overconfidence analysis | Legal classification | Different prediction object and data | MEDIUM-HIGH |
| Srinivasan et al. 2024 | Reduces over-abstention while preserving accuracy | VLM reasoning | Evidence recovery is modality-specific | MEDIUM |
| Vasisht et al. 2025 | Abstention evaluation and generalization-specificity trade-off | Safety/knowledge concepts | Not retrieval selection | MEDIUM |
| Hwang et al. 2025 RA-RAG | Reliability-aware selective source retrieval | Multi-source RAG | Source reliability rather than sparse/dense rank choice | CRITICAL-ADJACENT |
| QuDAR 2026 | Confidence margin drives query-wise retrieval weighting | Sparse/dense RAG retrieval | Uses weighting/fusion rather than abstention | CRITICAL |

H1 therefore has a meaningful risk-oriented question but no clean mechanism
novelty. Its only remaining distinction is the code-switched, fixed-retriever,
asymmetric target; that is an evaluation boundary.

## Closest-work audit: H2

| Work | Exact method overlap | Setting | Key difference | Threat |
|---|---|---|---|---|
| Arabzadeh et al. 2021 | Query-level sparse/dense/hybrid strategy selection | MS MARCO | Cost/effectiveness classifier target | CRITICAL |
| Khramtsova et al. 2023 | Unsupervised dense-retriever selection | New collection, no labels | Corpus/model rather than per-query BM25/Qwen | HIGH |
| LARMOR 2024 | Unsupervised retriever ranking using pseudo-relevance | Target corpus | Corpus-level and LLM-assisted | HIGH |
| MoR 2025 | Per-query mixture, comparative advantage and oracle routing | Heterogeneous retrievers | No code-switching and weighted mixture | CRITICAL |
| RouterRetriever 2025 | Query-specific expert routing | Domain experts on BEIR | Experts are dense LoRA models | HIGH |
| QuDAR 2026 | Margin/confidence-guided sparse/dense adaptation | Hybrid retrieval | More elaborate dual-perspective fusion | CRITICAL |
| Query-Adaptive Hybrid Search 2026 | Query-specific hybrid weight and complementarity training | MLDR/MIRACL | Learned alpha and dense retraining | CRITICAL |
| RA-RAG 2025 | Source reliability and selective retrieval | Heterogeneous sources | Reliability is source-level and multi-source | CRITICAL-ADJACENT |
| FIRE RRF/LexiSemIR/Benglish 2025 | Code-mixed lexical/semantic combination | Bengali-English social media | Fixed hybrid/reranking, not hard selector | CRITICAL-ADJACENT |

H2 is the most directly crowded candidate. Even if a no-training hard selector
were evaluated, the mechanism is already covered and the novel part would be
only the target/data transfer setting.

## Closest-work audit: H3

| Work | Exact method overlap | Setting | Key difference | Threat |
|---|---|---|---|---|
| Faggioli et al. 2023 | QPP across sparse and neural rankers | ECIR collections | Predicts performance rather than transfer-invariant relative choice | HIGH |
| Vlachou and Macdonald 2024 | Dense score/coherence predictors and query-type instability | TREC DL | No sparse/dense relative target | HIGH |
| Meng et al. 2025 | Metric-specific QPP via generated relevance judgments | TREC DL/CAsT | Uses LLM relevance judgments and ranker metric prediction | HIGH |
| Chifu et al. 2025 | Cross-collection QPP robustness and selective processing | ROBUST/GOV2/WT10G/MS MARCO | Finds generalization limitations | CRITICAL |
| LARMOR 2024 | Unsupervised model ranking under domain shift | Dense retriever pool | Corpus-level selection | HIGH |
| Query-Adaptive Hybrid Search 2026 | Query-specific alpha and cross-lingual/domain hybrid evaluation | MLDR/MIRACL | Learns alpha and antagonist training | CRITICAL |
| QuDAR 2026 | Query/corpus variation handled by confidence-aware dynamic weights | Sparse/dense RAG | Does not present invariance as the sole target | CRITICAL |
| RA-RAG 2025 | Reliability estimation across heterogeneous sources | Multi-source RAG | Source-level reliability and voting | HIGH |

H3 could be a useful transfer study but not a defensible new calibration
mechanism. The review found no primary source with the exact BM25/Qwen,
code-switched, Delta-CS, source-safe target, but that non-match is not enough
to authorize execution.

## Candidate decision

The full candidate score and the final rejection are in
`docs/milestone2_6_hypothesis_decision.md`. All H1–H3 fail the critical
mechanism-collision veto. H4 was not generated because a structure-based
variant is even more crowded and lacks a stable empirical basis.

## Final novelty boundary

The only defensible future contribution type identified is a preregistered
negative-or-positive *calibration/transfer evaluation* of existing signals for
relative fixed-retriever reliability under code-switching. It must not be
described as a new router, alpha, confidence estimator, fusion method,
abstention mechanism, disagreement feature, or CMI method. That boundary is
too narrow and too exposed to current prior art for a positive Milestone 3 go.

## Data and execution status

ClimateFEVER remains consumed. ArguAna outcomes were not read during this
audit and remain an historically known target. CSR-L remains untouched as the
stronger final boundary. No implementation, experiment, retuning, or
preregistration draft was authorized.

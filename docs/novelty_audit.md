# Focused novelty and prior-work audit

This is a focused threat audit for the development evidence, not a claim of exhaustive literature coverage. It was performed after the RQ0, complementarity, and structure analyses. The project does not claim that code-switching degradation or hybrid retrieval is new.

## Evidence-supported direction

Development results show meaningful but dataset-dependent behavior:

- BM25 loses official nDCG@10 on ArguAna by 0.02434 and on ClimateFEVERHardNegatives by 0.02928.
- Qwen3-Embedding-0.6B is essentially unchanged on ArguAna (+0.00033) but loses 0.02967 on ClimateFEVERHardNegatives.
- BM25 and dense Delta_CS values are only weakly correlated in the current development evidence (Qwen: 0.072 on ArguAna and 0.144 on ClimateFEVER; BGE: 0.025 and 0.074).
- Qwen has substantial per-query disagreement with BM25 on ClimateFEVER: BM25 survives while Qwen degrades on 16.4% of paired queries, Qwen survives while BM25 degrades on 12.3%, and both degrade on 9.4%.

These observations justify studying whether a lightweight reliability-aware method is useful. They do not establish novelty, causality, or that a particular switch-ratio router will work.

## Prior work and threat assessment

| Work | Year / venue | Task and mechanism | Relation to this project | Threat |
|---|---|---|---|---|
| Zeng et al., [Code-Switching Information Retrieval: Benchmarks, Analysis, and the Limits of Current Retrievers](https://aclanthology.org/2026.findings-acl.636/) | 2026, Findings of ACL | CSR-L and CS-MTEB; evaluates sparse, dense, and late-interaction retrieval under code-switching and analyzes embedding-space divergence | Directly establishes the problem and benchmark setting. Our RQ0 is a controlled replication/characterization, not a discovery claim. | Critical |
| Do, Lee, and Hwang, [ContrastiveMix](https://aclanthology.org/2024.naacl-short.17/) | 2024, NAACL | Code-mixed IR transfer with an additional contrastive objective aligning English and code-mixed query representations | Direct prior work on code-mixing-aware IR training. It threatens any claim that code-switched representation adaptation is new, although it is not the same as our untrained inference-time diagnostic. | High |
| Litschko, Artemova, and Plank, [Boosting Zero-shot Cross-lingual Retrieval by Training on Artificially Code-Switched Data](https://arxiv.org/abs/2305.05295) | 2023, Findings of ACL / arXiv | Artificial code-switched data generated with bilingual lexicons to train zero-shot rankers across 36 language pairs | Directly covers code-switched training as a retrieval adaptation strategy and motivates treating training-based mitigation as prior art. | High |
| Maimaiti et al., [Improving Cross-lingual Representation for Semantic Retrieval with Code-switching](https://arxiv.org/abs/2403.01364) | 2024, arXiv; later journal publication | Code-switched continual pretraining with language-modeling and similarity losses for semantic retrieval | Direct threat to code-switch-aware representation learning and continual pretraining. It is not an inference-only sparse/dense reliability method. | High |
| [Retrievability of code mixed microblogs](https://doras.dcu.ie/23399/) | 2015, research paper / institutional repository | Compares single, separate, and clustered indexing statistics for mixed and monolingual document collections | Earlier lexical/indexing work shows code-mixed retrieval has been studied beyond recent neural benchmarks. | Medium |
| Kalra et al., [MoR: Better Handling Diverse Queries with a Mixture of Sparse, Dense, and Human Retrievers](https://aclanthology.org/2025.emnlp-main.601/) | 2025, EMNLP | Zero-shot mixture and query routing across BM25 and dense retrievers, with complementary retriever analysis | Direct threat to claims about sparse/dense complementarity, mixture-of-retrievers analysis, or generic query-adaptive combination. | Critical |
| Lee et al., [RouterRetriever: Routing over a Mixture of Expert Embedding Models](https://ojs.aaai.org/index.php/AAAI/article/view/33306) | 2025, AAAI | Query-specific routing over domain-specific embedding experts | Direct threat to generic “route each query to the best retriever/model” novelty, though not code-switch-specific. | High |
| [Query-Adaptive Hybrid Search](https://www.mdpi.com/2504-4990/8/4/91) | 2026, peer-reviewed journal article | Predicts query-dependent sparse/dense interpolation weights | Direct threat to fixed-alpha or adaptive-alpha hybrid retrieval as a contribution. Such a method is explicitly outside Milestone 1. | Critical |
| [Decoding Benglish: Scalable Information Retrieval for Code-Mixed Queries](https://ceur-ws.org/Vol-4173/T3-9.pdf) | 2026, FIRE 2025 proceedings | Code-mixed Bengali-English IR using BM25 plus SBERT semantic reranking and a dedicated collection | Especially relevant direct code-mixed hybrid retrieval prior art. It makes a generic “BM25 + dense helps code-mixed IR” claim untenable. | Critical |
| [Code-Mixed Probes Show How Pre-Trained Models Generalise on Code-Switched Text](https://aclanthology.org/2024.lrec-main.307/) | 2024, LREC-COLING | Probes language detection, structural cues, and representation consistency in code-switched text | Threat to claims that lightweight script/mixing structure diagnostics are unexplored; it is not an IR router. | Medium-High |

## Exact mechanism search

The focused searches covered code-switching IR, artificially code-switched training, ContrastiveMix, BM25+dense code-mixed retrieval, query-adaptive hybrid weighting, mixture-of-retrievers routing, CMI/switch-ratio routing, and language-entropy routing. The search found strong adjacent and direct threats, including code-mixed BM25+SBERT retrieval and generic sparse/dense routing. It did not identify a primary source that exactly matches the current evidence-conditioned hypothesis of using code-switch structure together with observed per-query sparse-vs-Qwen reliability on CSR-L/CS-MTEB.

That non-match is not evidence of novelty. The exact hypothesis remains untested here, and any next-milestone proposal would need a fresh search using its precise feature definition, target, training supervision, and deployment mechanism. A CMI-only or switch-ratio-only router would face a particularly strong novelty and adequacy challenge because code-mixing-rate-aware training and routing ideas already exist.

## Decision implication

The plausible contribution space is narrow and conditional: a lightweight method would need to demonstrate a specific, reproducible advantage tied to code-switching-aware relative retriever reliability, while clearly distinguishing itself from ContrastiveMix, code-switched training, generic mixture/routing, adaptive alpha prediction, and existing code-mixed hybrid retrieval. Milestone 1 supplies motivation and failure evidence only; it does not implement or validate that method.

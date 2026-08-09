# Milestone 1.5 novelty threat audit

Audit date: 2026-08-09  
Scope: code-switching robustness in information retrieval, with a narrow interest in lightweight mitigation only if justified.  
Boundary: no CSR-L retrieval/evaluation, no new dense run, and no mitigation implementation.

This is a focused, claim-level threat audit rather than a claim of exhaustive literature coverage. Primary publisher, proceedings, ACL Anthology, arXiv, institutional-repository, and official FIRE/CEUR pages were searched. Method sections were inspected for the closest papers instead of relying only on search-result snippets.

## Search coverage

The fresh search included the following conceptual families:

1. code-switched and code-mixed information retrieval;
2. BM25 plus dense, SBERT, bi-encoder, reranking, RRF, and ensemble systems for code-mixed queries;
3. query-adaptive hybrid retrieval, dynamic alpha, and query-dependent interpolation;
4. retriever confidence, score margins, query difficulty, QPP, and sparse/dense strategy selection;
5. mixtures of retrievers, expert routing, disagreement, and complementarity;
6. CMI, switch ratio, language entropy, matrix-language, and mixing-intensity methods;
7. FIRE CMIR and mixed-script IR proceedings;
8. mixing-proportion and query-embedding interpolation studies.

The search explicitly checked the named threats: CSR-L/CS-MTEB, ContrastiveMix, Litschko et al., Maimaiti et al., MoR, RouterRetriever, Query-Adaptive Hybrid Search, QuDAR, Decoding Benglish, FIRE CMIR systems, When Does Mixing Help?, SETU-RAG, query-difficulty prediction, confidence/margin selection, and disagreement/complementarity routing.

## Prior-art matrix

### Cross-paper mechanism index

The index makes the required mechanism distinctions auditable across every entry.
`Struct` means an explicit code-switch/mixing-structure feature or control; `Conf`
means a confidence/QPP/score-behavior signal; `Comp` means disagreement,
complementarity, comparative advantage, or an oracle; `Router` means a learned
or explicitly trained routing predictor; `alpha` distinguishes a learned or
predicted continuous weight from a hard route or fixed fusion. `Varied` means the
shared-task volume contains multiple systems rather than one common mechanism.

| Entry | Query-adaptive? | Struct | Conf | Comp | Router | alpha | Main operation |
|---|---|---|---|---|---|---|---|
| PA1 CSR-L/CS-MTEB | No | No | No | Analysis | No | No | Benchmark comparison/diagnosis |
| PA2 ContrastiveMix | No | Code-mixed training data | No | No | No | Fixed linear weight baseline | Dense training plus fixed hybrid baseline |
| PA3 Litschko et al. | No | Mixing ratio in training analysis | No | No | No | No | Supervised cross-encoder reranking |
| PA4 Maimaiti et al. | No | Code-switched pretraining data | No | No | No | No | Dense representation training |
| PA5 Retrievability microblogs | No | Mixed collection/query analysis | No | No | No | No | Lexical/indexing analysis |
| PA6 MoR | Yes | No | Geometry/interaction | Explicit | No additional routing training | Continuous/query weights | Run all retrievers, weight and aggregate |
| PA7 RouterRetriever | Yes | No | Pilot similarity | Implicit expert comparison | No additional routing training | No | Hard expert routing |
| PA8 QuDAR | Yes | No | Margin/LLM relevance | Implicit dual-view comparison | Predictor variants | Dynamic weights | Query-wise weighting/fusion |
| PA9 Query-Adaptive Hybrid Search | Yes | No | Query representation | Explicit antagonist/complementarity | Predictor | Discrete alpha bins | Learned alpha prediction and fusion |
| PA10 Arabzadeh et al. | Yes | No | Query features, outcome-derived labels | No | Yes, classifier | No | Hard sparse/dense/hybrid strategy selection |
| PA11 Dense retriever zero-shot selection | Yes | No | Similarity/entropy | Model comparison | No | No | Label-free model selection |
| PA12 Dense QPP | Yes | No | Coherence/score behavior | No | No | No | Unsupervised QPP |
| PA13 When Does Mixing Help? | Query interpolation, not routing | Mixing proportion | No | No | No | No | Embedding interpolation/control study |
| PA14 Code-Mixed Probes | No | Explicit structural probes | Representation analysis | No | No | No | Representation probing |
| PA15 FIRE CMIR findings | Varied | Some systems | Some systems | Complementarity in hybrid systems | Some systems | Varied | Fusion, reranking, RRF, meta-learning |
| PA16 FIRE classical fusion | No | No | No | Explicit motivation | No | No | Fixed RRF |
| PA17 FIRE LexiSemIR | No | No | No | No | No | No | BM25 candidate retrieval plus dense reranking |
| PA18 FIRE dense-sparse RRF | No | No | No | Explicit motivation | No | No | Dense training plus static RRF |
| PA19 Decoding Benglish | No | Transliteration setting | No | No | No | No | BM25 candidate retrieval plus SBERT reranking |
| PA20 SETU-RAG | Yes | CMI/matrix language | No | No | Not established in repository record | No | Structure-triggered RAG routing/fan-out |
| PA21 FIRE/mixed-script lineage | Varied | Script/language labeling | No generic signal | Varied | Varied | Varied | Preprocessing, lexical retrieval, and hybrid lineage |
| PA22 Tasks, queries, and rankers | Query/QPP analysis | No | Query difficulty/QPP | Ranker comparison | No | No | Pre-retrieval performance prediction |

The fields below are deliberately explicit. “No” means that the inspected paper does not use that mechanism for its reported method; it does not mean that the paper is unrelated in every respect.

### PA1 — CSR-L / CS-MTEB

- Citation/status: Qingcheng Zeng, Yuheng Lu, Zeqi Zhou, Heli Qi, Puxuan Yu, Fuheng Zhao, Hitomi Yanaka, Weihao Xuan, and Naoto Yokoya, [Code-Switching Information Retrieval: Benchmarks, Analysis, and the Limits of Current Retrievers](https://aclanthology.org/2026.findings-acl.636/), 2026, Findings of ACL; peer-reviewed conference paper.
- Task/setting/datasets: natural code-switched document retrieval; CSR-L human-annotated benchmark and CS-MTEB broader benchmark; multiple language pairs and tasks.
- Components: evaluates statistical/sparse, dense, cross-encoder, and late-interaction retrievers; no proposed sparse/dense fusion or learned router.
- Query-adaptive/structure/confidence/disagreement: no adaptive alpha, structure-driven router, confidence selector, or learned disagreement selector; it analyzes performance and representation divergence.
- Supervision/training/inference: benchmark annotations and existing retrievers; no mitigation training as the paper’s central method; ordinary retrieval inference.
- Relation and exact threat: directly establishes the code-switching robustness problem and benchmark setting. The project’s RQ0 is characterization on disjoint development resources, not a new-problem claim. **Threat: CRITICAL** for C1 and any claim that code-switching degradation itself is novel.

### PA2 — ContrastiveMix

- Citation/status: Junggeun Do, Jaeseong Lee, and Seung-won Hwang, [ContrastiveMix: Overcoming Code-Mixing Dilemma in Cross-Lingual Transfer for Information Retrieval](https://aclanthology.org/2024.naacl-short.17/), 2024, NAACL-HLT short paper; peer-reviewed conference paper.
- Task/setting/datasets: zero-shot cross-lingual IR with English and code-mixed query data; experiments include mDPR-style retrieval and MIRACL-related multilingual settings.
- Components: dense mDPR-style retrieval; the paper also describes a sparse–dense hybrid baseline with BM25 and a tuned linear weight.
- Query-adaptive/structure/confidence/disagreement: fixed validation-tuned fusion baseline; no query-adaptive alpha, CMI feature, confidence selector, or disagreement router.
- Supervision/training/inference: supervised/contrastive training using English and code-mixed data; an additional query-encoder contrastive loss aligns English and code-mixed representations while preserving query–passage matching.
- Relation and exact threat: code-mixing-aware retrieval adaptation and sparse–dense hybrid use are already demonstrated. It is not an inference-only reliability selector, but it blocks claims that code-mixed IR adaptation or code-mix-aware training is new. **Threat: HIGH** for C3 and training-based mitigation claims.

### PA3 — Artificially code-switched retrieval training

- Citation/status: Robert Litschko, Ekaterina Artemova, and Barbara Plank, [Boosting Zero-shot Cross-lingual Retrieval by Training on Artificially Code-Switched Data](https://aclanthology.org/2023.findings-acl.193/), 2023, Findings of ACL; peer-reviewed conference paper.
- Task/setting/datasets: zero-shot MoIR, CLIR, and MLIR; mMARCO; 36 language pairs.
- Components: trained cross-encoder rankers; no sparse component or dense/sparse fusion in the proposed mechanism.
- Query-adaptive/structure/confidence/disagreement: no query-wise router or confidence signal; code-switch ratio is analyzed as a training-data factor.
- Supervision/training/inference: artificial code-switched training examples generated using bilingual lexicons; relevance-ranking supervision; standard reranking inference.
- Relation and exact threat: establishes code-switched training as a retrieval adaptation strategy and reports gains that vary with language distance and mixing ratio. **Threat: HIGH** for any code-switched training mitigation claim; lower for an inference-only relative-reliability study.

### PA4 — Code-switched continual pretraining for semantic retrieval

- Citation/status: Mieradilijiang Maimaiti, Yuanhang Zheng, Ji Zhang, Yue Zhang, Wenpei Luo, and Kaiyu Huang, [Improving Cross-lingual Representation for Semantic Retrieval with Code-switching](https://www.sciencedirect.com/science/article/pii/S0950705125009645), 2025, Knowledge-Based Systems 325, article 113919; peer-reviewed journal article. The earlier [arXiv record](https://arxiv.org/abs/2403.01364) is also available.
- Task/setting/datasets: sentence-level cross-lingual semantic retrieval for task-oriented FAQ/customer-service data; three business corpora and four open datasets in 20+ languages.
- Components: cross-lingual semantic encoder; no BM25 component, hybrid score, or router.
- Query-adaptive/structure/confidence/disagreement: no per-query selection; code-switching is used in data construction and pretraining rather than as a runtime feature.
- Supervision/training/inference: bilingual-dictionary-generated code-switched data; weighted XMLM plus similarity loss; downstream fine-tuning and dense inference.
- Relation and exact threat: direct prior art for code-switch-aware representation learning, but not for choosing between already-trained sparse and dense retrievers. **Threat: HIGH** for training/representation novelty; MEDIUM for inference-only reliability questions.

### PA5 — Retrievability of Code Mixed Microblogs

- Citation/status: Debasis Ganguly, Ayan Bandyopadhyay, Mandar Mitra, and Gareth J. F. Jones, [Retrievability of Code Mixed Microblogs](https://doras.dcu.ie/23399/), 2016, SIGIR ’16; peer-reviewed conference paper.
- Task/setting/datasets: retrievability and indexing strategies for collections containing code-mixed and monolingual microblogs.
- Components: lexical/indexing and collection-statistics analysis; no modern dense component or learned router.
- Query-adaptive/structure/confidence/disagreement: no query-adaptive mechanism; mixing is a collection/query phenomenon rather than a learned reliability feature.
- Supervision/training/inference: analytical retrieval study; no learned training target or runtime gate.
- Relation and exact threat: shows that code-mixed retrieval and mixed-collection indexing have long-standing IR prior art. **Threat: MEDIUM** for C1 and lexical novelty, LOW for a modern relative-reliability question.

### PA6 — MoR: Mixture of Retrievers

- Citation/status: Jushaan Singh Kalra, Xinran Zhao, To Eun Kim, Fengyu Cai, Fernando Diaz, and Tongshuang Wu, [MoR: Better Handling Diverse Queries with a Mixture of Sparse, Dense, and Human Retrievers](https://aclanthology.org/2025.emnlp-main.601/), 2025, EMNLP; peer-reviewed main-conference paper.
- Task/setting/datasets: zero-shot multi-retriever retrieval and RAG-oriented evidence collection; NFCorpus, SciDocs, SciFact, SciQ, and a simulated-human analysis.
- Components: BM25 plus multiple dense retrievers and human-like ranked sources; query routing and weighted score/rank aggregation.
- Query-adaptive/structure/confidence/disagreement: query-adaptive retriever weights from zero-shot geometry and retriever/query/document interactions; no code-switch structure feature; explicitly studies comparative advantage and oracle routing.
- Supervision/training/inference: no ground-truth routing labels for the central zero-shot weighting mechanism; all retrievers are run, scores are normalized, weights are assigned, and adjusted rankings are produced.
- Relation and exact threat: directly covers sparse/dense complementarity, per-query comparative wins, oracle headroom, and generic mixture weighting. **Threat: CRITICAL** for C2, C3, generic C6, and any claim that observed disagreement/oracle headroom alone is a novel contribution.

### PA7 — RouterRetriever

- Citation/status: Hyunji Lee, Luca Soldaini, Arman Cohan, Minjoon Seo, and Kyle Lo, [RouterRetriever: Routing over a Mixture of Expert Embedding Models](https://ojs.aaai.org/index.php/AAAI/article/view/33306), 2025, AAAI-25; peer-reviewed conference paper.
- Task/setting/datasets: domain-specific expert dense retrieval on BEIR and related out-of-domain evaluation.
- Components: shared base dense encoder with domain-specific LoRA experts; no BM25 component in the core method.
- Query-adaptive/structure/confidence/disagreement: query-specific expert routing based on similarity to pilot embeddings; no code-switch structure or explicit sparse/dense reliability signal.
- Supervision/training/inference: domain-specific expert training; at inference, select one expert without additional routing training.
- Relation and exact threat: generic “route each query to the best retrieval model” is already covered, although the expert type and domain-routing setting differ from BM25-versus-Qwen code-switch robustness. **Threat: HIGH** for generic C6 and C9.

### PA8 — QuDAR

- Citation/status: Joeun Kim, Seunghyouk Yoon, Xuan-Bach Le, Youngeun Nam, Doyoung Kim, Hwanjun Song, and Jae-Gil Lee, [QuDAR: Query-Wise Dual-Perspective Adaptive Retrieval](https://aclanthology.org/2026.acl-long.1791/), 2026, ACL long paper; peer-reviewed conference paper.
- Task/setting/datasets: query-wise adaptive retrieval for sparse/dense and original/expanded query views; broad retrieval/RAG-style evaluation.
- Components: sparse and dense retrievers plus original/expanded query representations; query-specific score weighting.
- Query-adaptive/structure/confidence/disagreement: explicitly query-adaptive; uses margin-derived confidence such as top-1 minus top-2 gaps and blind LLM-based relevance scoring; no CMI or explicit code-switch feature; confidence is used to weight/fuse retrievers.
- Supervision/training/inference: lightweight/full predictor configurations and relevance-score signals; query-time inference produces dynamic weights rather than a fixed alpha.
- Relation and exact threat: directly threatens confidence-based sparse/dense selection, margin-based routing, and query-specific alpha ideas. It is not code-switch-specific and adds query expansion/LLM signals, leaving only a narrow domain-specific calibration question. **Threat: CRITICAL** for C5 and C7; HIGH for C8/C9.

### PA9 — Query-Adaptive Hybrid Search

- Citation/status: Pavel Posokhov, Stepan Skrylnikov, Sergei Masliukhin, Alina Zavgorodniaia, Olesia Koroteeva, and Yuri Matveev, [Query-Adaptive Hybrid Search](https://www.mdpi.com/2504-4990/8/4/91), 2026, Machine Learning and Knowledge Extraction 8(4), article 91; peer-reviewed journal article.
- Task/setting/datasets: multilingual hybrid retrieval on MLDR and MIRACL.
- Components: fixed BM25 plus dense encoder; rank-based or min–max fusion; antagonist-aware dense training.
- Query-adaptive/structure/confidence/disagreement: QDAP predicts a discrete query-specific alpha from query representations; no code-switch structure feature, but the dense training explicitly targets sparse-retriever failures and complementarity.
- Supervision/training/inference: trained query predictor with 101 alpha bins and composite cross-entropy/Wasserstein objective; antagonist negative sampling; query-time alpha prediction and fusion.
- Relation and exact threat: an exact direct precedent for learned query-specific sparse/dense weighting plus complementarity-aware training. **Threat: CRITICAL** for C3, C5, C8, and C9.

### PA10 — Sparse/dense/hybrid strategy selection

- Citation/status: Negar Arabzadeh, Xinyi Yan, and Charles L. A. Clarke, [Predicting Efficiency/Effectiveness Trade-offs for Dense vs. Sparse Retrieval Strategy Selection](https://doi.org/10.1145/3459637.3482159), 2021, CIKM ’21, pp. 2862–2866; peer-reviewed conference paper.
- Task/setting/datasets: query-level selection among sparse, dense, and hybrid strategies on MS MARCO passage retrieval.
- Components: sparse, dense, and hybrid retrieval options; a classifier selects a strategy for each query.
- Query-adaptive/structure/confidence/disagreement: query-adaptive selection from query features; no code-switch structure and no explicit reliability calibration target.
- Supervision/training/inference: classifier labels are derived from relevance/rank outcomes at thresholds; BERT classifier is trained; inference chooses a retrieval strategy under a budget.
- Relation and exact threat: directly covers query-level sparse/dense/hybrid routing, even though the objective emphasizes cost/effectiveness trade-offs rather than code-switch robustness. **Threat: CRITICAL** for C6 and HIGH for C7/C9.

### PA11 — Dense-retriever model selection in zero-shot search

- Citation/status: Ekaterina Khramtsova, Shengyao Zhuang, Mahsa Baktashmotlagh, Xi Wang, and Guido Zuccon, [Selecting which Dense Retriever to use for Zero-Shot Search](https://arxiv.org/abs/2309.09403), 2023, SIGIR-AP ’23; peer-reviewed conference paper, with the accessible arXiv record.
- Task/setting/datasets: selecting among dense retrievers on unseen collections; BEIR datasets.
- Components: multiple dense retrievers; no sparse component or code-switch feature.
- Query-adaptive/structure/confidence/disagreement: evaluates query similarity, corpus similarity, extracted-document similarity, and entropy as unsupervised selection signals; no direct code-switch structure or BM25-vs-dense target.
- Supervision/training/inference: selection is label-free at target time; the paper evaluates whether unsupervised predictors recover the true model ranking.
- Relation and exact threat: shows model selection itself is an established IR problem and that naive unsupervised signals can fail under domain shift. **Threat: HIGH** for generic model-selection novelty; it motivates a narrowly code-switch-specific transfer question rather than a generic selector claim.

### PA12 — Dense query-performance prediction

- Citation/status: Maria Vlachou and Craig Macdonald, [Coherence-based Query Performance Measures for Dense Retrieval](https://eprints.gla.ac.uk/328868/), 2024, ACM SIGIR/ICTIR 2024, pp. 15–24; refereed conference paper.
- Task/setting/datasets: unsupervised QPP for dense rankings on TREC Deep Learning Track datasets.
- Components: dense retrieval rankings and embedding-based coherence predictors; no sparse/dense fusion.
- Query-adaptive/structure/confidence/disagreement: predicts query performance from score/coherence/embedding signals and studies query-type effects; no code-switch structure or relative retriever winner target.
- Supervision/training/inference: unsupervised post-retrieval predictors, no relevance labels at prediction time.
- Relation and exact threat: blocks claims that confidence/QPP signals for dense retrieval are unexplored; a relative sparse-vs-dense, code-switched transfer target remains distinct only if tested explicitly. **Threat: HIGH** for C7/C8.

### PA13 — When Does Mixing Help?

- Citation/status: Tongyao Zhu, Chao-Ming Huang, and Min-Yen Kan, [When Does Mixing Help? Analyzing Query Embedding Interpolation in Multilingual Dense Retrieval](https://aclanthology.org/2026.acl-long.1455/), 2026, ACL long paper; peer-reviewed conference paper.
- Task/setting/datasets: multilingual dense passage retrieval on mMARCO; 35 language pairs and three document-language settings.
- Components: BGE-M3 and other dense retrievers; no sparse component, router, or fusion.
- Query-adaptive/structure/confidence/disagreement: controls mixing proportion and analyzes language-pair/document-language effects; no per-query sparse/dense reliability selector.
- Supervision/training/inference: no new retriever training in the main diagnostic; embeddings of parallel monolingual queries are interpolated at test time; word-level mixing is a validation comparison.
- Relation and exact threat: establishes that mixing proportion and document-language composition can systematically change dense retrieval, weakening any claim that mix ratio is an unexplored explanatory variable. **Threat: HIGH** for C4 and structure-only claims; MEDIUM for relative sparse/dense routing.

### PA14 — Code-mixed structural probing

- Citation/status: Frances Adriana Laureano De Leon, Harish Tayyar Madabushi, and Mark Lee, [Code-Mixed Probes Show How Pre-Trained Models Generalise on Code-Switched Text](https://aclanthology.org/2024.lrec-main.307/), 2024, LREC-COLING; peer-reviewed conference paper.
- Task/setting/datasets: controlled naturalistic code-switched text with parallel monolingual translations; probes code-switch detection, structural information, and representation consistency.
- Components: pretrained language models; no IR sparse/dense component or router.
- Query-adaptive/structure/confidence/disagreement: explicitly studies structural signals, but not retrieval reliability or fusion.
- Supervision/training/inference: probing and controlled evaluation; no retrieval mitigation training.
- Relation and exact threat: structure-only features are not an empty research space. It does not answer relative retriever reliability, so it is an adjacent rather than direct routing precedent. **Threat: MEDIUM-HIGH** for C4 and any claim that structural diagnostics alone are unexplored.

### PA15 — FIRE CMIR shared-task findings

- Citation/status: Supriya Chanda, Krishna Tewari, and Sukomal Pal, [Findings of the Code-Mixed Information Retrieval from Social Media Data (CMIR) Shared Task at FIRE 2025](https://ceur-ws.org/Vol-4173/T3-1.pdf), 2025/2026 volume publication, FIRE 2025 Working Notes; workshop proceedings paper.
- Task/setting/datasets: mixed-script Bengali–English social-media retrieval; 20 training queries and 30 test queries over 107,900 documents.
- Components: lexical, neural reranking, and fusion-based submissions; reports that fusion/hybrid systems outperform standalone systems in the shared task.
- Late interaction: no inspected CMIR-2025 submission uses a late-interaction
  retriever as its central submitted pipeline; ColBERT-X is discussed as related
  context in [Decoding Benglish](https://ceur-ws.org/Vol-4173/T3-9.pdf), not used
  as that paper's reported BM25+SBERT system.
- Query-adaptive/structure/confidence/disagreement: participant systems include static fusion, reranking, RRF, phonetic normalization, and one dynamic XGBoost meta-learner; no unified code-switch reliability selector.
- Supervision/training/inference: shared-task training qrels; varied participant-specific supervision; held-out test evaluation.
- Relation and exact threat: code-mixed hybrid, reranking, fusion, normalization, and complementarity are directly present in a current benchmark community. **Threat: CRITICAL** for generic C2/C3 and HIGH for C9.

### PA16 — FIRE CMIR classical fusion

- Citation/status: Rachana Nagaraju and Hosahalli Lakshmaiah Shashirekha, [Model Fusion for Bridging Linguistic Variability in Bengali-English Code-Mixed Information Retrieval](https://ceur-ws.org/Vol-4173/T3-2.pdf), FIRE 2025 Working Notes; workshop proceedings paper.
- Task/setting/datasets: CMIR-2025 Bengali-English Roman/mixed-script social-media retrieval; training qrels and held-out test queries.
- Components: BM25, DirichletLM, HiemstraLM, and Reciprocal Rank Fusion; no dense component in the main fusion.
- Query-adaptive/structure/confidence/disagreement: fixed RRF; no query-adaptive alpha or code-switch structure selector; complementarity is the stated motivation.
- Supervision/training/inference: indexing/preprocessing configuration and training qrels; RRF inference.
- Relation and exact threat: directly establishes that exploiting complementary retrieval functions for code-mixed IR is an existing contribution. **Threat: CRITICAL** for C2/C3.

### PA17 — FIRE CMIR lexical + neural reranking

- Citation/status: Swati Gupta, Tanusree Nath, Vedika Gupta, and Manjari Gupta, [LexiSemIR: A Two-Stage Re-ranking Framework with BM25 and Zero-Shot Bi-Encoder](https://ceur-ws.org/Vol-4173/T3-4.pdf), FIRE 2025 Working Notes; workshop proceedings paper.
- Task/setting/datasets: CMIR-2025 Bengali-English code-mixed social-media retrieval; 20 labeled training queries and test queries.
- Components: BM25 top-100 followed by all-mpnet-base-v2 bi-encoder reranking; dense-only is not the main pipeline.
- Query-adaptive/structure/confidence/disagreement: fixed two-stage reranking; no code-switch structure, confidence, or disagreement selector.
- Supervision/training/inference: BM25 hyperparameters tuned on training qrels; zero-shot bi-encoder; lexical retrieval then semantic reranking.
- Relation and exact threat: generic BM25+dense reranking on code-mixed data is directly covered. **Threat: CRITICAL** for C3.

### PA18 — FIRE CMIR RRF dense–sparse hybrid

- Citation/status: Burhanuddin Merchant, Ashwaq Khazi, and Sheetal S. Sonawane, [Reciprocal Rank Fusion Based Hybrid Dense–Sparse Information Retrieval on Code-Mixed Banglish Social Media Text](https://ceur-ws.org/Vol-4173/T3-7.pdf), FIRE 2025 Working Notes; workshop proceedings paper.
- Task/setting/datasets: CMIR-2025 Bengali-English/Banglish social media; 20 training queries and 30 test queries.
- Components: BM25 plus fine-tuned multilingual Sentence Transformer; RRF with a weighted-fusion comparison.
- Query-adaptive/structure/confidence/disagreement: static RRF; no query-adaptive mechanism, but explicitly argues that sparse/dense signals are complementary.
- Supervision/training/inference: triplet-loss fine-tuning of the dense model and Bengali-to-Banglish preprocessing; RRF inference.
- Relation and exact threat: an especially direct code-mixed BM25+dense+RRF precedent. **Threat: CRITICAL** for C2/C3/C9.

### PA19 — Decoding Benglish

- Citation/status: Harsh Mishra, Ramya Sharma, and Naina Yadav, [Decoding Benglish: Scalable Information Retrieval for Transliterated Code-Mixed Conversations](https://ceur-ws.org/Vol-4173/T3-9.pdf), FIRE 2025 Working Notes; workshop proceedings paper.
- Task/setting/datasets: Bengali-English transliterated conversational/social-media retrieval; 107,900 documents, 20 queries, and 5,409 qrel judgments.
- Components: BM25 top-100 candidate generation followed by SBERT reranking; compares dense-only, BM25+SBERT reranking, and hybrid configurations.
- Query-adaptive/structure/confidence/disagreement: fixed pipeline; no learned router, confidence target, or CMI feature.
- Supervision/training/inference: reported SBERT/cross-encoder configurations and held-out FIRE evaluation; hybrid inference is lexical recall then semantic reranking.
- Relation and exact threat: direct evidence that a generic BM25+dense code-mixed retrieval claim is not defensible. **Threat: CRITICAL** for C3.

### PA20 — SETU-RAG CMI-Adaptive Retrieval Router

- Citation/status: Ashutosh Juvale, [Design and Evaluation of a Code-Switching-Aware Multilingual Conversational AI System using Advanced RAG Architectures](https://digitalcommons.isical.ac.in/masters-dissertations/458/), awarded 2026, Indian Statistical Institute; Master’s dissertation.
- Task/setting/datasets: code-switching-aware multilingual RAG/customer-support corpus; the repository record describes a CMI-adaptive router and matrix-language routing.
- Components: CMI and matrix-language routing, multi-view query expansion, and RAG gates; not a peer-reviewed IR benchmark paper.
- Query-adaptive/structure/confidence/disagreement: explicitly query-adaptive through CMI/matrix language; no sparse/dense relative-performance target is reported in the repository abstract.
- Supervision/training/inference: end-to-end system with strong open models and fallbacks; runtime router uses linguistic profile; exact training details require the dissertation text.
- Relation and exact threat: direct thesis-level prior art against “CMI-based retrieval routing” and structure-triggered retrieval fan-out. **Threat: HIGH** for C4/C6/C8; MEDIUM for a rigorously different no-generation IR calibration study.

### PA21 — FIRE and earlier mixed-script IR lineage

- Citation/status: the [FIRE 2025 CMIR volume index](https://ceur-ws.org/Vol-4173/) links the CMIR overview and multiple systems; Abhinav Mukherjee, Anirudh Ravi, and Kaustav Datta, [Mixed-Script Query Labeling Using Supervised Learning and Ad Hoc Retrieval Using Sub-Word Indexing](https://ceur-ws.org/Vol-1331/), FIRE 2014, pp. 86–90, is an earlier workshop/proceedings precedent. The lineage summary also covers the current FIRE systems individually listed above.
- Task/setting/datasets: mixed-script and code-mixed Indic queries, social-media comments, transliteration and script variation.
- Components: BM25/TF-IDF/DFR, subword indexing, phonetic normalization, CRF/LID, RRF, dense reranking, and ensembles across the lineage.
- Query-adaptive/structure/confidence/disagreement: language labeling and script-aware preprocessing occur; generic reliability confidence is not the common unifying mechanism.
- Supervision/training/inference: varies from supervised query labeling to fixed lexical/phonetic preprocessing and hybrid retrieval.
- Relation and exact threat: CMI/script structure, transliteration handling, and code-mixed IR are established problem components. **Threat: HIGH** for “structure-aware code-mixed retrieval is unexplored.”

### PA22 - Query difficulty and pre-retrieval performance prediction

- Citation/status: Paul Thomas, Falk Scholer, Peter Bailey, and Alistair Moffat,
  [Tasks, Queries, and Rankers in Pre-Retrieval Performance Prediction](https://www.microsoft.com/en-us/research/publication/tasks-queries-and-rankers-in-pre-retrieval-performance-prediction/),
  2017, Australasian Document Computing Symposium proceedings; ACM conference
  paper.
- Task/setting/datasets: pre-retrieval query-performance prediction across five
  rankers, 100 tasks, and 28,869 queries; it separates task, query, and ranker
  effects rather than studying code-switching.
- Components: generic rankers and pre-retrieval predictors; no fixed BM25/Qwen
  pair and no sparse/dense hybrid mechanism.
- Query-adaptive/structure/confidence/disagreement: query difficulty/QPP is the
  target; no code-switch structure, confidence margin, sparse/dense disagreement
  router, or adaptive alpha.
- Supervision/training/inference: evaluates pre-retrieval predictors without
  relevance judgments at prediction time; no learned retriever router.
- Relation and exact threat: establishes that difficulty prediction and choosing
  special processing based on predicted query performance are longstanding IR
  problems, while also warning that task effects can be mistaken for query
  difficulty. **Threat: MEDIUM-HIGH** for generic C7/C8; lower for the narrow
  natural-code-switching relative-reliability transfer question.

## Distinguishing the three levels

The audit separates three concepts that are often conflated:

| Level | Examples | Prior-art status | Milestone 1 evidence |
|---|---|---|---|
| Code-switch structure | CMI, switch ratio, language entropy, switch count, matrix language, script boundaries | Established measurements and structure probes; SETU-RAG explicitly routes on CMI/matrix language; When Does Mixing Help? studies mixing proportion | Weak/inconsistent correlations with Delta_CS; no support for structure-only alpha |
| Retriever behavior/confidence | score margins, score distributions, coherence, top-k overlap, query difficulty | QuDAR, QPP, Arabzadeh et al., and MoR use behavior/confidence/geometry signals | Existing artifacts provide per-query outcomes, but not a pre-registered unlabeled confidence predictor |
| Relative retriever reliability | which retriever will be better for this query | Generic routing/selection/oracle work is established; code-switch-specific natural-query transfer remains less directly documented | ClimateFEVER shows non-identical BM25/Qwen failures and diagnostic oracle headroom |

The only potentially defensible gap is therefore not “use CMI,” “use alpha,” or “use a router.” It is the narrower empirical question of whether existing, unlabeled QPP/behavior signals remain calibrated for *relative* BM25-versus-dense reliability under natural code-switching and transfer across disjoint development datasets. That remains high-risk and is not established by the current data.

## Exact-mechanism result

The search found direct code-mixed hybrid systems, CMI routing, generic sparse/dense selection, confidence-based adaptive weighting, QPP, and oracle/complementarity analyses. It did not find a primary source that exactly matches all of the following simultaneously:

1. naturally occurring code-switched queries;
2. a fixed sparse BM25 and fixed Qwen-like dense retriever;
3. an unlabeled query-time predictor of *relative* retriever reliability;
4. cross-dataset transfer evaluation under source-query-safe splits; and
5. robustness measured by original-versus-code-switched Delta_CS.

This non-match is only an unresolved search result, not evidence of novelty. QuDAR, MoR, Arabzadeh et al., QPP work, SETU-RAG, and FIRE systems make the mechanism high-risk. Any claim must be framed as a narrowly scoped empirical study of calibration and transfer, not as the invention of routing, fusion, confidence, CMI, or complementarity.

## Decision implication

The following claims are not defensible as standalone contributions:

- code-switching harms retrieval;
- BM25 and dense retrieval are complementary;
- BM25 plus dense improves code-mixed retrieval;
- CMI/switch ratio controls retrieval;
- query-specific alpha or sparse/dense routing is new;
- oracle selection reveals a novel method.

A possible next question survives only if it tests a scientifically meaningful distinction—relative-reliability calibration under natural code-switching and cross-dataset transfer—against the established generic selectors and QPP baselines. The candidate remains conditional, not a novelty claim.

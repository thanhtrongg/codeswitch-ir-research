# Benchmark audit

This document is generated from `configs/benchmarks.yaml`, the pinned official repository commit, and the immutable Hugging Face revisions recorded in the manifest below.

- Official repository commit: `63e0c33826c7cb4f03e93a6819e49b92e6f33196`
- Paper: [https://arxiv.org/abs/2604.17632](https://arxiv.org/abs/2604.17632)
- Audit scope: all catalogued retrieval and instruction-retrieval resources; non-retrieval CS-MTEB resources are catalogued in the YAML but are outside the baseline runner.

## Table A — benchmark audit

| Dataset | Benchmark | Queries | Corpus | Languages | Split/config | Final role | Metric |
|---|---|---:|---:|---|---|---|---|
| Touche2020 | CSR-L | 49 / 49 | 303732 | en, zh, ja | `default/test`; `corpus/corpus` | final_test | ndcg_at_10 |
| HumanEvalRetrieval | CSR-L | 158 / 158 | 158 | en, zh, ja | `qrels/test`; `corpus/test` | final_test | ndcg_at_10 |
| TRECCOVID | CSR-L | 50 / 50 | 171332 | en, zh, ja | `default/test`; `corpus/test` | final_test | ndcg_at_10 |
| Core17InstructionRetrieval | CSR-L | 40 / 20 | 19899 | en, zh, ja | `default/test`; `corpus/corpus` | final_test | pairwise_mrr |
| News21InstructionRetrieval | CSR-L | 64 / 32 | 30921 | en, zh, ja | `default/test`; `corpus/corpus` | final_test | pairwise_mrr |
| Robust04InstructionRetrieval | CSR-L | 104 / 52 | 47492 | en, zh, ja | `default/test`; `corpus/corpus` | final_test | pairwise_mrr |
| ArguAna | CS-MTEB | 1406 / 1406 | 8674 | en, zh, ja, de, es, ko, fr, it, pt, nl | `default/test`; `corpus/corpus` | development | ndcg_at_10 |
| ClimateFEVERHardNegatives | CS-MTEB | 1000 / 1000 | 47416 | en, zh, ja, de, es, ko, fr, it, pt, nl | `default/test`; `corpus/test` | development | ndcg_at_10 |
| HumanEvalRetrieval-CS-MTEB | CS-MTEB | 158 / 158 | 158 | en, zh, ja, de, es, ko, fr, it, pt, nl | `qrels/test`; `corpus/test` | final_test | ndcg_at_10 |
| TRECCOVID-CS-MTEB | CS-MTEB | 50 / 50 | 171332 | en, zh, ja, de, es, ko, fr, it, pt, nl | `default/test`; `corpus/test` | final_test | ndcg_at_10 |
| Touche2020-CS-MTEB | CS-MTEB | 49 / 49 | 303732 | en, zh, ja, de, es, ko, fr, it, pt, nl | `default/test`; `corpus/test` | final_test | ndcg_at_10 |
| Core17InstructionRetrieval-CS-MTEB | CS-MTEB | 40 / 20 | 19899 | en, zh, ja, de, es, ko, fr, it, pt, nl | `default/test`; `corpus/corpus` | final_test | pairwise_mrr |
| News21InstructionRetrieval-CS-MTEB | CS-MTEB | 64 / 32 | 30921 | en, zh, ja, de, es, ko, fr, it, pt, nl | `default/test`; `corpus/corpus` | final_test | pairwise_mrr |
| Robust04InstructionRetrieval-CS-MTEB | CS-MTEB | 104 / 52 | 47492 | en, zh, ja, de, es, ko, fr, it, pt, nl | `default/test`; `corpus/corpus` | final_test | pairwise_mrr |

## Resource-level records

### Touche2020

- Dataset: `UTokyo-Yokoya-Lab/webis-touche2020-v3-CSR-L` at revision `45ca9a97c0ce8d247bda9986040d8e2b549bbe5b`.
- Benchmark family: **CSR-L**; final role: **final_test**; task: `document_retrieval`.
- Original source dataset: `mteb/webis-touche2020-v3`; original query source: `mteb/webis-touche2020-v3` (`queries/train`).
- Languages: en, zh, ja; rewrite authoring: human-authored and human-validated (paper CSR-L).
- Corpus: `corpus/corpus`, 303732 documents. Qrels: `default/test`, 49 query IDs.
- Source-query groups: 49; raw query IDs: 49. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en.
- Official primary metric: `ndcg_at_10`. Declared shared-qrel expectation: `True`.

### HumanEvalRetrieval

- Dataset: `UTokyo-Yokoya-Lab/HumanEvalRetrieval-CSR-L` at revision `d7634f8e08cf9249cdb2169fb153b0de85d705c8`.
- Benchmark family: **CSR-L**; final role: **final_test**; task: `document_retrieval`.
- Original source dataset: `mteb/HumanEvalRetrieval`; original query source: `mteb/HumanEvalRetrieval` (`queries/test`).
- Languages: en, zh, ja; rewrite authoring: human-authored and human-validated (paper CSR-L).
- Corpus: `corpus/test`, 158 documents. Qrels: `qrels/test`, 158 query IDs.
- Source-query groups: 158; raw query IDs: 158. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en.
- Official primary metric: `ndcg_at_10`. Declared shared-qrel expectation: `True`.

### TRECCOVID

- Dataset: `UTokyo-Yokoya-Lab/trec-covid-CSR-L` at revision `a5013e0563346911767949a4f249119d60cb7654`.
- Benchmark family: **CSR-L**; final role: **final_test**; task: `document_retrieval`.
- Original source dataset: `mteb/trec-covid`; original query source: `mteb/trec-covid` (`queries/test`).
- Languages: en, zh, ja; rewrite authoring: human-authored and human-validated (paper CSR-L).
- Corpus: `corpus/test`, 171332 documents. Qrels: `default/test`, 50 query IDs.
- Source-query groups: 50; raw query IDs: 50. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en.
- Official primary metric: `ndcg_at_10`. Declared shared-qrel expectation: `True`.

### Core17InstructionRetrieval

- Dataset: `UTokyo-Yokoya-Lab/core17-instructions-mteb-CSR-L` at revision `8b89cba7cc29a70cf70b9ec49f6b80f045afe4ff`.
- Benchmark family: **CSR-L**; final role: **final_test**; task: `instruction_retrieval`.
- Original source dataset: `jhu-clsp/core17-instructions-mteb`; original query source: `jhu-clsp/core17-instructions-mteb` (`queries/test`).
- Languages: en, zh, ja; rewrite authoring: not declared in dataset card; retain as provenance risk.
- Corpus: `corpus/corpus`, 19899 documents. Qrels: `default/test`, 40 query IDs.
- Source-query groups: 20; raw query IDs: 40. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en.
- Official primary metric: `pairwise_mrr`. Declared shared-qrel expectation: `False`.

### News21InstructionRetrieval

- Dataset: `UTokyo-Yokoya-Lab/news21-instructions-mteb-CSR-L` at revision `b165f4edfbbf211e6824dbd7a46b964c375e6132`.
- Benchmark family: **CSR-L**; final role: **final_test**; task: `instruction_retrieval`.
- Original source dataset: `jhu-clsp/news21-instructions-mteb`; original query source: `jhu-clsp/news21-instructions-mteb` (`queries/test`).
- Languages: en, zh, ja; rewrite authoring: not declared in dataset card; retain as provenance risk.
- Corpus: `corpus/corpus`, 30921 documents. Qrels: `default/test`, 64 query IDs.
- Source-query groups: 32; raw query IDs: 64. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en.
- Official primary metric: `pairwise_mrr`. Declared shared-qrel expectation: `False`.

### Robust04InstructionRetrieval

- Dataset: `UTokyo-Yokoya-Lab/robust04-instructions-mteb-CSR-L` at revision `98419b934cc562f458d4a3e3c2f4038fa423cf6d`.
- Benchmark family: **CSR-L**; final role: **final_test**; task: `instruction_retrieval`.
- Original source dataset: `jhu-clsp/robust04-instructions-mteb`; original query source: `jhu-clsp/robust04-instructions-mteb` (`queries/test`).
- Languages: en, zh, ja; rewrite authoring: not declared in dataset card; retain as provenance risk.
- Corpus: `corpus/corpus`, 47492 documents. Qrels: `default/test`, 104 query IDs.
- Source-query groups: 52; raw query IDs: 104. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en.
- Official primary metric: `pairwise_mrr`. Declared shared-qrel expectation: `False`.

### ArguAna

- Dataset: `UTokyo-Yokoya-Lab/arguana_CS-MTEB` at revision `b11f59a0d2e3d2636928608a73cf485bd31a7ac2`.
- Benchmark family: **CS-MTEB**; final role: **development**; task: `document_retrieval`.
- Original source dataset: `mteb/arguana`; original query source: `mteb/arguana` (`queries/test`).
- Languages: en, zh, ja, de, es, ko, fr, it, pt, nl; rewrite authoring: LLM-generated; author card declares code-switched variants.
- Corpus: `corpus/corpus`, 8674 documents. Qrels: `default/test`, 1406 query IDs.
- Source-query groups: 1406; raw query IDs: 1406. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en, de=queries_de_en, es=queries_es_en, ko=queries_ko_en, fr=queries_fr_en, it=queries_it_en, pt=queries_pt_en, nl=queries_nl_en.
- Official primary metric: `ndcg_at_10`. Declared shared-qrel expectation: `True`.

### ClimateFEVERHardNegatives

- Dataset: `UTokyo-Yokoya-Lab/ClimateFEVER_hardnegatives_CS-MTEB` at revision `742d2689e13422963b6e15a36362ac5315167974`.
- Benchmark family: **CS-MTEB**; final role: **development**; task: `document_retrieval`.
- Original source dataset: `mteb/ClimateFEVER_test_top_250_only_w_correct-v2`; original query source: `mteb/ClimateFEVER_test_top_250_only_w_correct-v2` (`queries/test`).
- Languages: en, zh, ja, de, es, ko, fr, it, pt, nl; rewrite authoring: LLM-generated; author card declares code-switched variants.
- Corpus: `corpus/test`, 47416 documents. Qrels: `default/test`, 1000 query IDs.
- Source-query groups: 1000; raw query IDs: 1000. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en, de=queries_de_en, es=queries_es_en, ko=queries_ko_en, fr=queries_fr_en, it=queries_it_en, pt=queries_pt_en, nl=queries_nl_en.
- Official primary metric: `ndcg_at_10`. Declared shared-qrel expectation: `True`.

### HumanEvalRetrieval-CS-MTEB

- Dataset: `UTokyo-Yokoya-Lab/HumanEvalRetrieval_CS-MTEB` at revision `c3351f576b53e848f760285ef4d77cb466f91225`.
- Benchmark family: **CS-MTEB**; final role: **final_test**; task: `document_retrieval`.
- Original source dataset: `mteb/HumanEvalRetrieval`; original query source: `mteb/HumanEvalRetrieval` (`queries/test`).
- Languages: en, zh, ja, de, es, ko, fr, it, pt, nl; rewrite authoring: LLM-generated; author card declares code-switched variants.
- Corpus: `corpus/test`, 158 documents. Qrels: `qrels/test`, 158 query IDs.
- Source-query groups: 158; raw query IDs: 158. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en, de=queries_de_en, es=queries_es_en, ko=queries_ko_en, fr=queries_fr_en, it=queries_it_en, pt=queries_pt_en, nl=queries_nl_en.
- Official primary metric: `ndcg_at_10`. Declared shared-qrel expectation: `True`.

### TRECCOVID-CS-MTEB

- Dataset: `UTokyo-Yokoya-Lab/trec-covid_CS-MTEB` at revision `0d5311e79dbfbe822968bbdc2343c4bd08057c81`.
- Benchmark family: **CS-MTEB**; final role: **final_test**; task: `document_retrieval`.
- Original source dataset: `mteb/trec-covid`; original query source: `mteb/trec-covid` (`queries/test`).
- Languages: en, zh, ja, de, es, ko, fr, it, pt, nl; rewrite authoring: LLM-generated; author card declares code-switched variants.
- Corpus: `corpus/test`, 171332 documents. Qrels: `default/test`, 50 query IDs.
- Source-query groups: 50; raw query IDs: 50. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en, de=queries_de_en, es=queries_es_en, ko=queries_ko_en, fr=queries_fr_en, it=queries_it_en, pt=queries_pt_en, nl=queries_nl_en.
- Official primary metric: `ndcg_at_10`. Declared shared-qrel expectation: `True`.

### Touche2020-CS-MTEB

- Dataset: `UTokyo-Yokoya-Lab/webis-touche2020-v3_CS-MTEB` at revision `c823b1fcb70ee44f4178aacce3fe624775ca77e4`.
- Benchmark family: **CS-MTEB**; final role: **final_test**; task: `document_retrieval`.
- Original source dataset: `mteb/webis-touche2020-v3`; original query source: `mteb/webis-touche2020-v3` (`queries/test`).
- Languages: en, zh, ja, de, es, ko, fr, it, pt, nl; rewrite authoring: LLM-generated; author card declares code-switched variants.
- Corpus: `corpus/test`, 303732 documents. Qrels: `default/test`, 49 query IDs.
- Source-query groups: 49; raw query IDs: 49. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en, de=queries_de_en, es=queries_es_en, ko=queries_ko_en, fr=queries_fr_en, it=queries_it_en, pt=queries_pt_en, nl=queries_nl_en.
- Official primary metric: `ndcg_at_10`. Declared shared-qrel expectation: `True`.

### Core17InstructionRetrieval-CS-MTEB

- Dataset: `UTokyo-Yokoya-Lab/core17-instructions-mteb_CS-MTEB` at revision `6875544dcc2b71baa5b4799968e2d28e12c272d6`.
- Benchmark family: **CS-MTEB**; final role: **final_test**; task: `instruction_retrieval`.
- Original source dataset: `jhu-clsp/core17-instructions-mteb`; original query source: `jhu-clsp/core17-instructions-mteb` (`queries/test`).
- Languages: en, zh, ja, de, es, ko, fr, it, pt, nl; rewrite authoring: LLM-generated; author card declares code-switched variants.
- Corpus: `corpus/corpus`, 19899 documents. Qrels: `default/test`, 40 query IDs.
- Source-query groups: 20; raw query IDs: 40. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en, de=queries_de_en, es=queries_es_en, ko=queries_ko_en, fr=queries_fr_en, it=queries_it_en, pt=queries_pt_en, nl=queries_nl_en.
- Official primary metric: `pairwise_mrr`. Declared shared-qrel expectation: `True`.

### News21InstructionRetrieval-CS-MTEB

- Dataset: `UTokyo-Yokoya-Lab/news21-instructions-mteb_CS-MTEB` at revision `239895ad8290d9e68e51bafeca7add63befa2050`.
- Benchmark family: **CS-MTEB**; final role: **final_test**; task: `instruction_retrieval`.
- Original source dataset: `jhu-clsp/news21-instructions-mteb`; original query source: `jhu-clsp/news21-instructions-mteb` (`queries/test`).
- Languages: en, zh, ja, de, es, ko, fr, it, pt, nl; rewrite authoring: LLM-generated; author card declares code-switched variants.
- Corpus: `corpus/corpus`, 30921 documents. Qrels: `default/test`, 64 query IDs.
- Source-query groups: 32; raw query IDs: 64. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en, de=queries_de_en, es=queries_es_en, ko=queries_ko_en, fr=queries_fr_en, it=queries_it_en, pt=queries_pt_en, nl=queries_nl_en.
- Official primary metric: `pairwise_mrr`. Declared shared-qrel expectation: `True`.

### Robust04InstructionRetrieval-CS-MTEB

- Dataset: `UTokyo-Yokoya-Lab/robust04-instructions-mteb_CS-MTEB` at revision `5038ae297de84d03e60911819a4c93bc3936d9e5`.
- Benchmark family: **CS-MTEB**; final role: **final_test**; task: `instruction_retrieval`.
- Original source dataset: `jhu-clsp/robust04-instructions-mteb`; original query source: `jhu-clsp/robust04-instructions-mteb` (`queries/test`).
- Languages: en, zh, ja, de, es, ko, fr, it, pt, nl; rewrite authoring: LLM-generated; author card declares code-switched variants.
- Corpus: `corpus/corpus`, 47492 documents. Qrels: `default/test`, 104 query IDs.
- Source-query groups: 52; raw query IDs: 104. IDs use `official qrel query IDs, canonicalized only for -og/-changed FollowIR pairs`.
- Code-switched query configurations: zh=queries_zh_en, ja=queries_ja_en, de=queries_de_en, es=queries_es_en, ko=queries_ko_en, fr=queries_fr_en, it=queries_it_en, pt=queries_pt_en, nl=queries_nl_en.
- Official primary metric: `pairwise_mrr`. Declared shared-qrel expectation: `True`.

## Pairwise overlap summary

| Source dataset | CSR-L resource | CS-MTEB resource | Raw query-ID overlap | Source-query overlap | Exact qrel overlap | Qrel document-ID overlap | Same corpus size |
|---|---|---|---:|---:|---:|---:|---|
| mteb/webis-touche2020-v3 | UTokyo-Yokoya-Lab/webis-touche2020-v3-CSR-L | UTokyo-Yokoya-Lab/webis-touche2020-v3_CS-MTEB | 49 | 49 | 49 | 2732 | True |
| mteb/HumanEvalRetrieval | UTokyo-Yokoya-Lab/HumanEvalRetrieval-CSR-L | UTokyo-Yokoya-Lab/HumanEvalRetrieval_CS-MTEB | 158 | 158 | 158 | 158 | True |
| mteb/trec-covid | UTokyo-Yokoya-Lab/trec-covid-CSR-L | UTokyo-Yokoya-Lab/trec-covid_CS-MTEB | 50 | 50 | 50 | 35480 | True |
| jhu-clsp/core17-instructions-mteb | UTokyo-Yokoya-Lab/core17-instructions-mteb-CSR-L | UTokyo-Yokoya-Lab/core17-instructions-mteb_CS-MTEB | 40 | 20 | 20 | 4739 | True |
| jhu-clsp/news21-instructions-mteb | UTokyo-Yokoya-Lab/news21-instructions-mteb-CSR-L | UTokyo-Yokoya-Lab/news21-instructions-mteb_CS-MTEB | 64 | 32 | 32 | 4248 | True |
| jhu-clsp/robust04-instructions-mteb | UTokyo-Yokoya-Lab/robust04-instructions-mteb-CSR-L | UTokyo-Yokoya-Lab/robust04-instructions-mteb_CS-MTEB | 104 | 52 | 52 | 17643 | True |

Corpus artifact OIDs are also compared in `results/audit/source_query_overlap.csv`. Different OIDs can reflect reserialization; exact source-corpus provenance, equal corpus cardinality, and shared qrel document IDs are retained as separate evidence rather than conflated.


## Leakage findings

Protocol source-dataset disjointness: **PASS**.

The pairwise overlap CSV records corpus-ID, query-ID, source-query-group, and exact-qrel-signature overlaps. Rewritten variants are grouped as `source_dataset::query_id`; they are never treated as independent examples.

The FollowIR-derived CSR-L resources publish `qrel_diff` configurations. They are retained as final-test resources but are not eligible for model selection and must be evaluated with their official pairwise-MRR protocol rather than being silently collapsed into ordinary nDCG retrieval.

## Provenance cautions

The paper’s main CSR-L table reports Touché 2020, HumanEval, TRECCOVID, and FollowIR. The current official author account also publishes Core17, News21, and Robust04 CSR-L resources. Both sets are recorded here so a later run cannot silently mix paper-era and repository-current scopes.
The benchmark name `FollowIR` is represented by the Core17, News21, and Robust04 instruction-retrieval resources in the current author repository; no separate `FollowIR` dataset ID is silently substituted.

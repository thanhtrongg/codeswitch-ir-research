# Leakage revalidation for Milestone 1.5

Revalidation date: 2026-08-09

## Evidence inspected

The revalidation read the raw manifests in `results/audit/dataset_overlap.json` and `results/audit/source_query_overlap.csv`, rather than relying only on the prose report. The manifest contains 14 resources: two development resources and twelve final-test resources, including CSR-L/CS-MTEB counterparts.

## Development/final separation

The two development source datasets are:

- `mteb/arguana`
- `mteb/ClimateFEVER_test_top_250_only_w_correct-v2`

The six distinct final source datasets are the Touche2020, HumanEvalRetrieval, TRECCOVID, Core17, News21, and Robust04 source datasets. The raw manifest reports zero development/final source-dataset overlap, and the independently computed source-dataset intersection is empty.

Source-qualified identity and ancestry checks were also empty for:

- source-query groups (`source_dataset::query_id`);
- qrel signatures by source-query group;
- qrel document IDs;
- corpus document IDs and declared corpus provenance;
- corpus artifact identifiers; and
- rewritten-query ancestry represented by the source-query grouping and variant
  qrel alignment fields in the raw manifest.

The raw manifest's `protocol_leakage_safe` flag is `true`, and `development_final_source_dataset_overlap` is an empty list.

## Query-ID nuance

There are 11 overlaps if raw numeric query IDs are compared without a dataset namespace. Each is a ClimateFEVER numeric ID reused by the unrelated `Touche2020-CS-MTEB` resource. These are identifier collisions, not shared query ancestry: the source-qualified query groups have zero intersection. Therefore raw query IDs are not treated as globally unique; the protocol identity is the source-qualified source-query group.

## Counterpart handling

The six CSR-L/CS-MTEB counterpart pairs share underlying source datasets and, in several cases, qrel document IDs. They are all retained on the final side of the boundary and excluded from development. The two development resources have different source datasets and are not counterparts of the final suite.

Different serialized corpus artifact identifiers are not interpreted as proof of semantic disjointness. The decision uses source provenance, source-qualified query ancestry, qrel signatures, document IDs, and the explicit counterpart policy together.

## Verdict

**PASS.** The frozen final-test boundary is valid under the source-qualified protocol. No final CSR-L retrieval, metric computation, selection, tuning, or result artifact was created. **FINAL TEST UNTOUCHED.**

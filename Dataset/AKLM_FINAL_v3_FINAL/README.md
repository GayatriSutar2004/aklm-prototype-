# AKLM-FINAL-v3

Research-quality synthetic benchmark for Adaptive Knowledge Lifecycle Management.

Use `rag/chunks.csv` and the versioned corpus as the RAG knowledge source. Keep evaluation labels outside the index.

The benchmark is specifically designed around:
- knowledge freshness
- document/version changes
- selective re-indexing
- adaptive retrieval
- stale-answer detection
- conflict handling
- retrieval-needed vs retrieval-not-needed decisions

The dataset is synthetic and should be complemented by a separately authorized real-website validation set for external validity.

## Artifacts (new in this extension)

All derived artifacts are built from the canonical corpus, `rag/chunks.csv`, `lifecycle/changes.csv` and the original evaluation tables. Nothing in the corpus structure was modified.

| Path | Contents |
|---|---|
| `lifecycle/page_hashes.csv` | 20,000 rows; raw + normalized SHA-256 per document version |
| `lifecycle/version_timestamps.csv` | 10 rows; synthetic release schedule (V01 = 2026-01-01, +7 days/version) |
| `lifecycle/chunk_changes.csv` | 36,000 rows (2 per change event); per-chunk diff status (unchanged/modified/added/removed), text similarity, `embedding_affected` (deterministic text-equality rule) |
| `lifecycle/changes.csv` | extended with `pct_content_changed`, `min_chunk_text_similarity`, `embedding_affected`, `change_event_timestamp`, `split` |
| `evaluation/stale_cases.csv` | 2,000 rows (was 1,200); full website x version-pair coverage incl. V01->V02, V08->V10, V09->V10 |
| `evaluation/conflict_cases.csv` | 200 rows (was 150); every website covered; new `resolved_version`, `snapshot_is_newer`, `resolution_rule` |
| `evaluation/questions.csv` | extended with `gold_answer`, `supporting_chunk_ids`, `citation_required_document_ids`, `gold_available`, `gold_derivation`, version/snapshot columns, `stale_case_id`, `conflict_id` |
| `lifecycle/stale_replacements/index_snapshots.csv` | 1,800 immutable snapshot registry rows (W x V01..V09) |
| `lifecycle/stale_replacements/stale_replacements.csv` | 20,000 selective-replacement plans (per stale case x page) with per-chunk embedding update flags |

## Gold-answer semantics

- `comparison` — entity diff of the policy page between the question's two versions (identical pair → "No change").
- `change_detection` — `change_type` of the support page pair from `changes.csv`; V01 questions resolve to "initial release, no predecessor".
- `stale` — snapshot vs required version decision; `a == b` rows are fresh-index safe cases (no stale_case row by design).
- `historical` — pricing page content at the requested version plus diff vs V10.
- `conflict` — authoritative source = current release (target_version); older snapshot superseded.
- `policy` / `freshness` / `requirement` — deterministic render of the target page's template-parsed entities.
- `multi_document` — combined render of services (P09) + support (P04) at the target version.
- `retrieval_control` — arithmetic answer, no retrieval, no citations.

## Integrity

`quality/FINAL_AUDIT.md` documents the full audit gate; every check passes (hashes reproducible, chunk diffs consistent with `changes.csv`, 100% stale/conflict question linkage, all supporting chunk ids resolving to `rag/chunks.csv`, one-split-per-website 160/20/20).

See `quality/FINAL_AUDIT.md` and `quality/CORRECTION_LOG.txt`.
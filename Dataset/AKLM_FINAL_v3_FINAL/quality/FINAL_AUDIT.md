# AKLM-FINAL-v3 — Final Corrected Audit (v3.1 derived-label extension)

## Final status
**PASS — corrected dataset is internally consistent under the existing P01-P10 corpus design, after the v3.1 derived-label extension.**

## What was corrected (recent extension)

1. **Stale-case coverage gaps closed**
   - `stale_cases.csv` extended 1,200 -> 2,000 rows to the full website x version-pair cross-product under the canonical version space, including the previously missing V01->V02, V08->V10 and V09->V10 pairs.
   - Every original row preserved; additions flagged `added_cover_gap=yes`.
   - 100% of stale questions with stale < required link 1:1 to a stale_case row (460); the 60 fresh-index cases (V01->V01) intentionally have no case.

2. **Conflict-case coverage closed**
   - `conflict_cases.csv` extended 150 -> 200 rows so every website has a record; `resolved_version = max(version_a, version_b)`, `snapshot_is_newer`, `resolution_rule` added.
   - 100% of conflict questions link to their website's conflict record.

3. **Deterministic gold answers added**
   - `questions.csv` gold_answer/supporting_chunk_ids/citation_required_document_ids/gold_available/gold_derivation appended for all 5,200 rows (5,200 gold_available=yes, 4,680 with supporting chunks, 520 retrieval_control with none by design).
   - Golds derive only from the canonical corpus (template-parsed entities) and `changes.csv`; nothing fabricated.

4. **Chunk-level change tracking added**
   - `lifecycle/chunk_changes.csv` (36,000 rows) from `rag/chunks.csv` text equality; all 36,000 consecutive-version chunks are text-modified, consistent with the 100% content-change rate.
   - `embedding_affected` deterministic from text equality; `requires_reembedding='conditional'` (reordering) retained as original signal.

5. **Version timestamps + derived change timestamps added**
   - `version_timestamps.csv` (10 rows, +7 days from V01=2026-01-01); `changes.csv` gains `change_event_timestamp`, `pct_content_changed`, `min_chunk_text_similarity`, `embedding_affected`, `split`.

6. **Snapshot + replacement artifacts added**
   - `lifecycle/stale_replacements/index_snapshots.csv` (1,800 rows; W x V01..V09).
   - `lifecycle/stale_replacements/stale_replacements.csv` (20,000 rows; stale case x page) with per-chunk embedding-update plans; all unresolved chunk ids fail the audit if they do not exist in `rag/chunks.csv`.

## Final inventory
- Websites: 200 (train 160 / validation 20 / test 20)
- Versions: 10
- Corpus records: 20000
- Pages per website/version: 10
- RAG chunks: 40000
- Page hashes: 20000
- Lifecycle change records: 18000
- Chunk change records: 36000
- Version lineage records: 18000
- Version timestamps: 10
- Evaluation questions: 5200 (all gold-available)
- Conflict cases: 200 (all websites)
- Stale cases: 2000 (full version-pair coverage)
- Index snapshots: 1800
- Stale replacement plans: 20000

## Integrity checks (all PASS)
- Duplicate corpus content: 0; duplicate question text: 0; duplicate chunk ids: 0
- Page hashes reproducible on sample: 0 mismatches
- Chunk diffs consistent with changes.csv (change_ids match 1:1, 2 chunks/event, statuses/embedding flags valid)
- pct_content_changed in (0, 100], min_chunk_text_similarity in [0, 1]
- change_event_timestamp == release date of to_version; timestamps strictly +7 days
- Stale question -> case linkage: 460/460; conflict question -> case linkage: 520/520
- change_detection golds resolve from changes.csv (V02..V10) or initial-release rule (V01): 520/520
- comparison pairs valid within V01..V10 and target docs exist: 520/520
- Train/validation question overlap: 0; train/test: 0; validation/test: 0
- One split per website; per-type split balance 416/52/52
- Conflict cases with observable version differences: 200/200
- Remaining conflict REVIEW cases: 0
- Supporting chunk ids resolve to rag/chunks.csv; citations resolve to corpus document ids: 0 failures

## Methodological note
The 300 unsupported page-inventory claims were **not converted into fake page additions/deletions**.
The 100% consecutive-version change rate is retained as a dataset characteristic and was not artificially changed.
All v3.1 extension content (gold answers, chunk diffs, timestamps, replacement plans) is derived from the
existing canonical artifacts and is not fabricated. Conflict case files document worked example pairs;
question-level conflict golds resolve from each question's own target (latest) version.
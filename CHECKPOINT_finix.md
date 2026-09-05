# CHECKPOINT: finix

**Purpose:** This checkpoint freezes the exact, fully-working state of the
AKLM prototype project *before* the next phase of work (live-site refresh
loop, collection splitting, real-website validation).

**Created:** 2026-09-05
**Status at checkpoint:** ALL GREEN — dataset audit PASS, index built,
models trained, evaluation runs, no known breakage.

---

## What worked at this exact point

| Component | State |
|---|---|
| Dataset `Dataset/AKLM_FINAL_v3_FINAL` | Complete + audited (62/62 checks PASS). 5,200 gold questions, 2,000 stale cases, 200 conflicts, lifecycle metadata, stale-replacement plans, no duplicate columns |
| Qdrant index (`qdrant_storage`, collection `aklm_knowledge`) | 36,044 points = 36,000 synthetic benchmark + 44 production ADCET |
| `build_index.py` | Idempotent, PASS; production + replacement steps verified |
| Models | `models/aklm_retrieval_model.joblib` (100% val/test), `models/aklm_stale_detection_model.joblib`, `models/aklm_chunk_replacement_model.joblib` |
| Evaluation | `evaluate_retrieval.py` runs; Recall@5 0.045 site-wide / 0.066 same-site / MRR 0.025 (honest low-recall finding) |
| Full RAG | `generate_answer.py` works end-to-end (real Gemini call) — NOTE: currently polluted by synthetic chunks in the same collection |
| Cache | `apply_cache.json` holds all 36,000 benchmark vectors (reruns are fast) |

## To restore to this point

1. **Restore files:** if files were modified/deleted, re-copy the backup zip
   contents into `D:\practicceProjects\ResearchPrj\Prototype-AKLM`.
2. **Rebuild index if `qdrant_storage` is missing:** `python build_index.py`
   (cached, fast if `apply_cache.json` is present).
3. **Re-verify:**
   - `python C:\Users\gayat\AppData\Local\Temp\opencode\aklm_final_audit.py`
     → expect `ALL AUDIT CHECKS PASSED`.
   - `python evaluate_retrieval.py` → should reproduce the numbers above.
   - Qdrant points should read 36,044.

## Known issues carried into this checkpoint (NOT bugs to fix here)

1. Production + benchmark vectors share one Qdrant collection → ADCET Q&A is
   polluted by synthetic chunks (planned fix: split collections).
2. No query-time version routing in `retrieve.py` yet.
3. Embedding labels in synthetic data are 100% `yes` → stale-detection model
   accuracy (100%) is not proof of real signal; real-website validation not done.
4. Crawler scripts hit Firecrawl credits and `testCrawler.py` deletes
   `scraped_data/` before refetching.
5. `portalocker/msvcrt` deallocator traceback at exit under Python 3.14
   (cosmetic). Local Qdrant warns for collections >20k points.

## Secrets note

`.env` / `.env.bak` contain FIRECRAWL_API_KEY and GEMINI_API_KEY. They are
git-ignored. Never print their values.
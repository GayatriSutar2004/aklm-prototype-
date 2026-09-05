# AKLM — Adaptive Knowledge Lifecycle Management for College Portals

**Live AI bot (deployed):** https://adcetportal.vercel.app → *Ask ADCET AI*
**API:** `POST https://adcetportal.vercel.app/api/ask` `{ "question": "..." }`
**Frontend repo:** https://github.com/GayatriSutar2004/adcetportal
**Dataset/code repo (research):** Prototype-AKLM (this package)

## What it is
A system that keeps a website's RAG knowledge index correct as the site changes.
When a deployed college portal updates its content, AKLM detects *which* pages
actually changed (vs UI-only tweaks), decides whether embeddings must be
refreshed, and **selectively replaces only the stale parts** of the vector index —
instead of re-embedding everything.

The deployed bot runs fully on the live site: Gemini embeddings + a
Numpy-in-the-tiny-serverless-function cosine retriever + grounded Gemini
answer generation using ONLY retrieved website content.

## Architecture (runtime — deployed today)
```
User question
   -> AKLM decision: is retrieval needed? (trained classifier)
   -> retrieve current knowledge (top-5 similarity)
   -> Gemini grounded answer (rules: no outside knowledge, no invented facts)
```

## Dataset (harden-tested, audit PASS 62/62)
- 5,200 gold Q&A pairs, 2,000 stale-change cases, 200 conflict cases
- 36,000 synthetic chunks across 200 simulated websites (ADKLM benchmark v3)
- Full lifecycle metadata: page hashes, chunk diffs, selective replacement plans
- Deterministic gold answers with resolvable citations

## Machine Learning (trained & saved)
- Retrieval-needed classifier — 100% val/test (synthetic): `models/aklm_retrieval_model.joblib`
- Freshness / stale-detection models: `aklm_stale_detection_model.joblib`,
  `aklm_chunk_replacement_model.joblib`

## Local index (Qdrant, embedded mode) — 36,044 points
36,000 refreshed benchmark chunks + 44 real ADCET production chunks.
`build_index.py` = idempotent one-command rebuild (create -> store -> replace).
`evaluate_retrieval.py` = read-only Recall/MRR evaluation.

## Reproducibility
```
python build_index.py        # rebuild Qdrant index (cached, idempotent)
python train_aklm_model.py   # train stale detection models
python train_retrieval_model.py
python evaluate_retrieval.py # evaluation report
```
Restore point: `CHECKPOINT_finix.md` documents the exact verified baseline.
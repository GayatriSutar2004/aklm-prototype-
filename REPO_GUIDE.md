# AKLM — Complete Repository Guide

> **Purpose of this document:** Give another AI (or a person) 100% understanding of the
> `Prototype-AKLM` repository: what the project is, what every file does, how the pieces
> connect, and how to run/verify everything.

---

## 1. What the project is (one paragraph)

**AKLM = Adaptive Knowledge Lifecycle Manager.** It is a research prototype for keeping a
RAG (Retrieval-Augmented Generation) chatbot's knowledge current without retraining. Given a
company website (here: the ADCET admission portal at `https://adcetportal.vercel.app`), AKLM:

1. **Crawls** the site and converts each page into plain text markdown.
2. **Chunks** the text and **embeds** it (two trackings: an offline local index and the live
   production index).
3. Stores vectors in **Qdrant** (`aklm_knowledge` collection).
4. **Answers queries** by retrieving the top-K chunks and letting **Gemini** generate a
   grounded answer with source citations.
5. **Learns the knowledge lifecycle** (AKLM's core novelty): it trains 3 small sklearn models —
   a *stale-detection* model, a *retrieval* model, and a *selective-replacement* model — that
   detect when a website's content changes, find which stored chunks are now outdated, and
   replace only those chunks in the index instead of re-indexing everything.

The **live demo bot** is a Node.js (Vercel) serverless function that embeds queries with
Google Gemini embeddings and answers from a precomputed 44-chunk index (`api/vectors.json`).

---

## 2. Where things live

| Item | Location |
|---|---|
| This prototype repo | `D:\practicceProjects\ResearchPrj\Prototype-AKLM` / GitHub `GayatriSutar2004/aklm-prototype-` (PUBLIC) |
| Live bot repo | `GayatriSutar2004/adcetportal` (currently PRIVATE — set Public before submitting this URL) |
| Live demo site | `https://adcetportal.vercel.app` |
| Live bot endpoint | `POST https://adcetportal.vercel.app/api/ask` `{ "query": "..." }` |
| Obsolete backend | `GayatriSutar2004/backend-ai` (Render-free-tier backend that OOM'd; can be deleted) |

---

## 3. High-level architecture

```
 [1] CRAWL            testCrawler.py / testAllPages.py / testFirecrawl.py (Firecrawl API)
        |  -> scraped_data/page_*.md
 [2] CHUNK            chunk_data.py  -> chunks.json
 [3] EMBED            create_embeddings.py (BAAI/bge-small-en-v1.5) -> embedded_chunks.json
 [4] STORE            store_embeddings.py / build_index.py -> qdrant_storage/ (Qdrant)
 [5] RETRIEVE         retrieve.py  (cosine top-k over Qdrant, bge embeddings)
 [6] ANSWER           generate_answer.py  (Gemini gemini-3.6-flash, grounded w/ sources)
 [7] EVALUATE         evaluate_retrieval.py   (benchmark vs gold questions.csv)
 [8] LIFECYCLE        train_aklm_model.py + train_retrieval_model.py
                      + apply_replacements.py (detect stale -> selectively replace)

 LIVE BOT (separate repo adcetportal):
      api/ask.js  (Node)  -- reads api/vectors.json, embeds query w/ Gemini
                             models/gemini-embedding-001 (3072-dim), cosine top-4,
                             passes context to Gemini for the grounded answer.
```

---

## 4. Full file inventory

### Root files & folders

| Path | What it is |
|---|---|
| `Dataset/` | The generated benchmark dataset (see §6) |
| `docs/decision_specification.md` | Design/decisions spec for the AKLM approach |
| `INFO_LOG/` | Run logs (`Day1.txt`, `steps.txt` — crawl/experiment notes) |
| `models/` | 3 trained `.joblib` models (force-added to git) |
| `qdrant_storage/` | Local Qdrant data dir with `aklm_knowledge` collection (36,044 points) — gitignored |
| `scraped_data/` | Raw Firecrawl page text (`page_1.md` … `page_8.md`) |
| `__pycache__/` | Python bytecode cache — gitignored |
| `.env` / `.env.bak` | API keys (GEMINI_API_KEY, FIRECRAWL_API_KEY) — gitignored, never commit |
| `.env.example` | Template of required env vars |
| `.gitignore` | Excludes `.env*`, `qdrant_storage/`, caches, `scraped_data/`, `models/*.joblib`, datasets status |
| `requirements.txt` | Python deps (fastapi, uvicorn, sentence-transformers, numpy, python-dotenv, google-genai, qdrant-client, pydantic, httpx) |
| `PROJECT_SUMMARY.md` | Contest submission summary (README-level) |
| `REPO_GUIDE.md` | This document |
| `CHECKPOINT_finix.md` | Verified baseline snapshot / restore point of the working pipeline |

### Core pipeline scripts (ordered)

| File | Role |
|---|---|
| `testCrawler.py` | Raw Firecrawl scrape test of a single page |
| `testAllPages.py` | Batch-scrapes all site pages into `scraped_data/page_*.md` |
| `testFirecrawl.py` | Small Firecrawl connectivity smoke test |
| `chunk_data.py` | LangChain `RecursiveCharacterTextSplitter` (chunk 1000, overlap 200) over scraped text → `chunks.json` |
| `create_embeddings.py` | SentenceTransformer `BAAI/bge-small-en-v1.5` embeds chunks → `embedded_chunks.json` |
| `store_embeddings.py` | Writes embeddings to local Qdrant collection `aklm_knowledge` |
| `build_index.py` | Orchestrates dataset checks + index build (subprocess wrapper around the embedding/store steps) |
| `retrieve.py` | Query → bge embedding → top-k cosine search in Qdrant |
| `generate_answer.py` | Builds context prompt from retrieved chunks, calls Gemini `gemini-3.6-flash`, returns grounded answer + source URLs |
| `evaluate_retrieval.py` | Benchmarks retrieval against `evaluation/questions.csv` + `stale_cases.csv`, reports accuracy/precision |
| `api.py` | Local FastAPI server wrapping `generate_answer.py` (old local demo backend; the deployed live bot uses the Node version instead) |
| `train_retrieval_model.py` | Trains `models/aklm_retrieval_model.joblib` (TF-IDF + LogisticRegression pipeline over Qdrant history) |
| `train_aklm_model.py` | Trains the core AKLM models from `lifecycle/changes.csv` + `chunk_changes.csv`: RandomForest stale-detection + selective-replacement classifiers → `models/aklm_stale_detection_model.joblib` and `models/aklm_chunk_replacement_model.joblib` |
| `apply_replacements.py` | Runtime updater: uses the trained models to decide which chunks are stale, then **selectively replaces** them in the index (measured: ~36,000 upserts + ~4,000 removes on the benchmark — orders of magnitude cheaper than full re-index) |

### Test/utility scripts

| File | Role |
|---|---|
| `inspect_dataset.py` | DataFrame inspector over the benchmark CSV files (schema sanity checks) |

### Root working artifacts (gitignored, regenerated)

| File | What it is |
|---|---|
| `chunks.json` | Output of `chunk_data.py` |
| `embedded_chunks.json` | Output of `create_embeddings.py` (chunk id/text/metadata + bge 384-dim embedding) |
| `apply_cache.json`, `apply_log.txt`, `apply_err.txt` | Selective-replacement runs cache/audit trail |

---

## 5. The three trained models (`models/`)

| File | Trained by | Job |
|---|---|---|
| `aklm_retrieval_model.joblib` | `train_retrieval_model.py` | TF-IDF + LogisticRegression; scores/ranks historical query→chunk relevance |
| `aklm_stale_detection_model.joblib` | `train_aklm_model.py` | RandomForest; given an old chunk + observed site change, predicts STALE vs CURRENT |
| `aklm_chunk_replacement_model.joblib` | `train_aklm_model.py` | RandomForest; decides whether to UPSERT, REMOVE, or KEEP each chunk on a detected site change |

Pipeline: new site snapshot → diff old/new text → **stale model** flags affected chunks →
**replacement model** picks per-chunk action → `apply_replacements.py` executes only those
untouched operations (≈36k upsert / 4k remove). This is AKLM's research contribution.

---

## 6. `Dataset/AKLM_FINAL_v3_FINAL` — the benchmark dataset

| Subfolder / file | Content |
|---|---|
| `rag/chunks.csv` | 44 real ADCET site chunks (the bot's knowledge) |
| `splits/` | Train/val/test splits |
| `evaluation/questions.csv` | Gold Q&A pairs used by `evaluate_retrieval.py` |
| `evaluation/stale_cases.csv` | Gold cases where content went stale (detection benchmark) |
| `lifecycle/changes.csv`, `chunk_changes.csv` | Labeled website-change → chunk-impact records (training data for the two AKLM models) |
| `lifecycle/stale_replacements/stale_replacements.csv` | Ground-truth replacement actions |
| `quality/` + `dataset_manifest.json` | Quality checks + dataset manifest/metadata |
| Plus `W###_V##.jsonl` corpus files | Versioned website-snapshot corpus used to synthesize lifecycle changes |

---

## 7. The live production bot (`adcetportal` repo) — how it works

Files (in the `adcetportal` clone used for deploys):
- `api/ask.js` — serverless function:
  1. Reads `api/vectors.json` (44 chunks, 3072-dim Gemini embeddings).
  2. Embeds the user query → Gemini REST `/v1beta/models/gemini-embedding-001:embedContent`
     (body field is `content` { parts:[{text}] }, `taskType: RETRIEVAL_QUERY`).
  3. Cosine-similarity over the stored vectors, takes top-4.
  4. Builds a grounded-answer prompt and calls Gemini `gemini-3.6-flash`.
  5. Returns JSON: answer + source chunk IDs/URLs (falls back to a friendly message if
     `GEMINI_API_KEY` missing).
- `api/vectors.json` — the frozen production index (currently the "60 seats" snapshot).
- `vercel.json` — rewrites: `/api/:path*` → `/api/:path*`, everything else → `/index.html`
  (single stock Next.js/Vercel page, no functions block).
- `src/pages/*.jsx` — the ADCET site pages people browse.

**How to check it live:** `POST https://adcetportal.vercel.app/api/ask` with
`{ "query": "How many intake seats are there for BBA?" }` → currently answers "60"
(snapshot is stale; site now says **65** — that gap is exactly what AKLM's auto-refresh fixes).

---

## 8. Why two embeddings / two models

- **Offline research track:** bge-small-en-v1.5 (384-dim) inside Qdrant — used for the
  dataset benchmarks, model training, and experimentation.
- **Live production track:** Gemini `gemini-embedding-001` (3072-dim) in `vectors.json` —
  used by the deployed bot for quality. (Render's Python free tier OOM'd at 512MB and Python
  3.14 shipped no onnx/onnxruntime wheels, so production is Node.)

---

## 9. Running / verifying the project

```bash
# offline pipeline
python chunk_data.py            # scraped_data -> chunks.json
python create_embeddings.py     # chunks.json -> embedded_chunks.json
python store_embeddings.py      # embedded_chunks.json -> qdrant_storage (aklm_knowledge)
python retrieve.py              # CLI: query -> top-k chunks
python generate_answer.py       # CLI: grounded answer via Gemini
python evaluate_retrieval.py    # benchmark vs gold questions

# lifecycle models
python train_retrieval_model.py # -> models/aklm_retrieval_model.joblib
python train_aklm_model.py      # -> stale_detection + chunk_replacement models
python apply_replacements.py    # selective index refresh (36k upsert / 4k remove)

# local demo server
python api.py                   # FastAPI on :8000
```

**Live bot health check:** `POST https://adcetportal.vercel.app/api/ask` (see §7).

---

## 10. Known limitations / current state (IMPORTANT honesty notes)

1. **The bot is a snapshot.** Editing `src/pages/*.jsx` does NOT auto-refresh
   `api/vectors.json`. Right now site says **65 intake seats**, bot still answers **60**.
2. **Fix (planned/optional):** a GitHub Action in `adcetportal` that extracts text from the
   jsx pages, embeds via Gemini, regenerates `api/vectors.json`, and commits only if changed
   (needs repo secret `GEMINI_API_KEY`). Files to add:
   - `.github/workflows/refresh-bot.yml`
   - `script/refresh_vectors.mjs`
   If that lands, the bot will track the site automatically (~next deploy).
3. **Secrets:** `GEMINI_API_KEY` has leaked into chat logs and a now-deleted Vercel project.
   Rotate it later.
4. `models/*.joblib` are gitignored but were force-committed, so they ARE present in the repo.
5. `qdrant_storage/`, `scraped_data/`, caches are local-only (gitignored).

---

## 11. Contest deliverables map

| Deliverable | Location |
|---|---|
| Source + dataset + models + docs | this `Prototype-AKLM` repo (public), + submission zip |
| Live AI bot | `https://adcetportal.vercel.app/api/ask` (bot repo `adcetportal`) |
| Summary README | `PROJECT_SUMMARY.md` |
| Video (7-min script given, user records with Win+Alt+R) | — |
| Robot must "know 100%" | this `REPO_GUIDE.md` |
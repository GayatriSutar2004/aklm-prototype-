# AKLM — Adaptive Knowledge Lifecycle Management for College Portals

An AI system that keeps a college website's knowledge base correct as the site
changes over time. When content updates, AKLM detects what actually changed and
selectively refreshes only the stale knowledge instead of re-embedding
everything.

## Live Demo (Deployed & Working)

**Website + AI bot:** https://adcetportal.vercel.app

Click **"Ask ADCET AI"** (bottom-right widget) and ask a question — the bot
answers grounded in the site's actual current content.

**Backend API:** `POST https://adcetportal.vercel.app/api/ask`

```json
{ "question": "How many intake seats are offered for the BBA program?" }
```

Returns the answer plus the retrieved source chunk IDs:

```json
{
  "answer": "There are 60 intake seats offered for the Bachelor of Business Administration (BBA) program.",
  "sources": [ { "chunk_id": "page_3_chunk_1", "source_url": "https://adcetportal.vercel.app/courses", "score": 0.70 } ]
}
```

## Repositories

- **Research project (code + dataset + models + pipeline):**
  https://github.com/GayatriSutar2004/aklm-prototype-
- **Frontend + live bot (React/Vite + Vercel serverless function):**
  https://github.com/GayatriSutar2004/adcetportal

## How to Check Whether It Works

### 1. Check the bot answers from the live site (fastest)

1. Open https://adcetportal.vercel.app
2. Click **Ask ADCET AI**.
3. Ask: `How many intake seats are offered for the BBA program?`
   - Expected: an answer like *"60 intake seats"*, *not* a canned response.
4. Ask a second question: `What is the full name of the college?`
   - Expected: the college's real full name from the site.

### 2. Check the API directly

```shell
curl -X POST https://adcetportal.vercel.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"How many intake seats are offered for the BBA program?"}'
```

A valid response contains an `answer` field and a non-empty `sources` array.
If `answer` is *"Sorry, the AI service is temporarily unavailable."*, the
`GEMINI_API_KEY` environment variable is not set on the Vercel project.

### 3. Check answers are grounded (no outside knowledge)

Ask: `Where is the college located and what are the contact details?`
The bot must answer only from `adcetportal.vercel.app` content and say
"I couldn't find that information on the website." for anything not present.

## How the AKLM Lifecycle Works (and How to See It)

The core idea: when a site changes, update only the stale knowledge.

1. **Crawl** the live site → page content.
2. **Chunk + hash** → detect which pages actually changed vs UI-only tweaks.
3. **Decide** whether embeddings must be refreshed (`chunk_changes.csv`).
4. **Selectively replace** only the stale chunks — never a full re-embed.

See it running locally:

```shell
# Build / refresh the Qdrant index (idempotent)
python build_index.py

# Selective replacement on the benchmark (upsert refreshed, remove obsolete)
python apply_replacements.py --website W001 --plan-limit 3

# Evaluation report + before/after retrieval demo
python evaluate_retrieval.py
```

On the full benchmark: **36,000 chunks refreshed, only 4,000 obsolete removed** —
the index self-updates without rebuilding everything.

## Dataset (in `aklm-prototype-`)

- 5,200 gold Q&A pairs
- 2,000 stale-change cases
- 200 conflict cases
- 36,000 transformed chunks across 200 simulated websites (versioned)
- Full lifecycle metadata: page hashes, chunk diffs, selective replacement plans
- Audit report: PASS (62/62 checks)

## Models & Trainers

- Retrieval-gating classifier — `train_retrieval_model.py` → `models/aklm_retrieval_model.joblib`
- Stale-detection models — `train_aklm_model.py` → `models/aklm_stale_detection_model.joblib`, `models/aklm_chunk_replacement_model.joblib`

## Tech

- Frontend: React + Vite (Vercel)
- Bot backend: Node serverless function + Gemini embeddings + Gemini grounded
  answer generation (no heavy ML runtime on the server)
- Vector index: Qdrant (local embedded mode, 36,044 points)
- Evaluations: Recall/MRR + same-website filtering

## Notes

- Answers are generated strictly from retrieved website content by design —
  never invented facts.
- Ask ADCET AI needs the `GEMINI_API_KEY` environment variable on the Vercel
  project.
- After a site content change, the knowledge snapshot is refreshed through the
  pipeline above (crawl → chunk → embed → redeploy).

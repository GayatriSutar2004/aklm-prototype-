import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from generate_answer import MODEL_NAME, generate_answer

# ==========================================
# 1. Configuration
# ==========================================

ROOT = Path(__file__).resolve().parent
EMBEDDED_CHUNKS = ROOT / "embedded_chunks.json"
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
TOP_K = 5
PORT = int(os.getenv("PORT", "8000"))

load_dotenv(ROOT / ".env")


# ==========================================
# 2. Load production index at startup
# ==========================================

def load_index():
    data = json.loads(
        EMBEDDED_CHUNKS.read_text(encoding="utf-8")
    )

    chunks = data if isinstance(data, list) else data.get("chunks", [])

    matrix = np.array(
        [c["embedding"] for c in chunks],
        dtype=np.float32,
    )

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0

    index = {
        "embeddings": matrix / norms,
        "rows": [
            {
                "chunk_id": c["id"],
                "text": c["text"],
                "source_url": c.get("metadata", {}).get(
                    "source_url",
                    "unknown",
                ),
                "page_id": c.get("metadata", {}).get(
                    "page_id",
                    "unknown",
                ),
            }
            for c in chunks
        ],
    }

    return index


@asynccontextmanager
async def lifespan(app):
    app.state.index = load_index()
    app.state.embedder = SentenceTransformer(EMBED_MODEL_NAME)
    app.state.chunk_count = len(app.state.index["rows"])
    print(
        f"[startup] production index ready: "
        f"{app.state.chunk_count} chunks, "
        f"model={EMBED_MODEL_NAME}, answerer={MODEL_NAME}"
    )
    yield


app = FastAPI(title="ADCET AI Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 3. Retrieval (in-process, production only)
# ==========================================

def retrieve(question, top_k=TOP_K):
    query = app.state.embedder.encode(
        [question],
        normalize_embeddings=True,
    )[0]

    scores = app.state.index["embeddings"] @ query
    order = np.argsort(scores)[::-1][:top_k]

    results = []
    rows = app.state.index["rows"]

    for i in order:
        row = rows[int(i)]
        results.append(
            {
                "chunk_id": row["chunk_id"],
                "text": row["text"],
                "source_url": row["source_url"],
                "page_id": row["page_id"],
                "score": float(scores[int(i)]),
            }
        )

    return results


# ==========================================
# 4. API endpoints
# ==========================================

class AskRequest(BaseModel):
    question: str


class SourceInfo(BaseModel):
    chunk_id: str
    source_url: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "chunks": app.state.chunk_count,
        "embedder": EMBED_MODEL_NAME,
        "answerer": MODEL_NAME,
    }


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    question = req.question.strip()

    if not question:
        return AskResponse(
            answer="Please ask a question about ADCET.",
            sources=[],
        )

    results = retrieve(question, top_k=TOP_K)
    answer = generate_answer(question, results)

    sources = [
        SourceInfo(
            chunk_id=r["chunk_id"],
            source_url=r["source_url"],
            score=r["score"],
        )
        for r in results
    ]

    return AskResponse(answer=answer, sources=sources)


# ==========================================
# 5. Entry point
# ==========================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
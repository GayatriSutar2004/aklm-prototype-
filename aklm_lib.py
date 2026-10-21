"""
AKLM shared core library.

Single source of truth for the crawl -> chunk -> embed -> store -> retrieve
workflow. Both the step scripts and run_pipeline.py import from here so there
is exactly one implementation of each step.

Embeddings are unified on Gemini (gemini-embedding-001, 3072-dim) so that the
local operational index (Qdrant collection "aklm_live") and the live bot's
api/vectors.json are always compatible.

The research collection "aklm_knowledge" (384-dim, bge) is intentionally NOT
touched by this module.
"""

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from dotenv import load_dotenv


# ==========================================
# Configuration
# ==========================================

PROJECT_DIR = Path(__file__).parent

ENV_PATH = PROJECT_DIR / ".env"

load_dotenv(ENV_PATH)

SCRAPED_DIR = PROJECT_DIR / "scraped_data"

CHUNKS_FILE = PROJECT_DIR / "chunks.json"

EMBEDDED_FILE = PROJECT_DIR / "embedded_chunks.json"

QDRANT_PATH = str(PROJECT_DIR / "qdrant_storage")

COLLECTION_NAME = "aklm_live"

SITE_URL = os.getenv("SITE_URL", "https://adcetportal.vercel.app/")

EMBED_MODEL = "gemini-embedding-001"

VECTOR_SIZE = 3072

GEN_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
]

DEFAULT_ADCETPORTAL_REPO = os.getenv(
    "ADCETPORTAL_REPO",
    r"C:\Users\gayat\AppData\Local\Temp\opencode\adcetportal"
)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


# ==========================================
# API key
# ==========================================

def get_api_key():

    key = os.getenv("GEMINI_API_KEY")

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not found in .env"
        )

    return key


# ==========================================
# Low-level HTTP
# ==========================================

def _post_json(url, payload, timeout=120, retries=3):

    data = json.dumps(payload).encode("utf-8")

    last_error = None

    for attempt in range(retries):

        try:

            request = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(
                request,
                timeout=timeout
            ) as response:

                return json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as e:

            last_error = e

            # Retry only on transient server-side errors.
            if e.code in (429, 500, 503):

                wait = 2 ** attempt

                print(
                    f"   [retry] HTTP {e.code}, "
                    f"waiting {wait}s "
                    f"({attempt + 1}/{retries})"
                )

                time.sleep(wait)

                continue

            raise

        except urllib.error.URLError as e:

            last_error = e

            wait = 2 ** attempt

            print(
                f"   [retry] network error, waiting {wait}s "
                f"({attempt + 1}/{retries})"
            )

            time.sleep(wait)

    raise RuntimeError(f"Request failed after {retries} attempts: {last_error}")


# ==========================================
# Gemini embeddings (3072-dim)
# ==========================================

def embed_texts(texts, task_type="RETRIEVAL_DOCUMENT", batch_size=20):

    if not texts:
        return []

    key = get_api_key()

    url = (
        f"{GEMINI_BASE}/{EMBED_MODEL}:batchEmbedContents"
        f"?key={key}"
    )

    embeddings = []

    total_batches = (len(texts) + batch_size - 1) // batch_size

    for index in range(0, len(texts), batch_size):

        batch = texts[index:index + batch_size]

        body = {
            "requests": [
                {
                    "model": f"models/{EMBED_MODEL}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": task_type,
                }
                for text in batch
            ]
        }

        batch_no = index // batch_size + 1

        print(
            f"   Embedding batch {batch_no}/{total_batches} "
            f"({len(batch)} texts)"
        )

        result = _post_json(url, body)

        batch_embeddings = result.get("embeddings", [])

        if len(batch_embeddings) != len(batch):
            raise RuntimeError(
                "Embedding count mismatch: "
                f"sent {len(batch)}, received {len(batch_embeddings)}"
            )

        for item in batch_embeddings:
            embeddings.append(item["values"])

    return embeddings


def embed_query(text):

    embeddings = embed_texts(
        [text],
        task_type="RETRIEVAL_QUERY"
    )

    return embeddings[0]


# ==========================================
# Gemini answer generation (with model fallback)
# ==========================================

ANSWER_PROMPT = """
You are the AI answer engine for an Adaptive Knowledge
Lifecycle Management (AKLM) system.

Your job is to answer the user's question using ONLY the
retrieved website information provided below.

==================================================
USER QUESTION
==================================================

{question}


==================================================
RETRIEVED WEBSITE INFORMATION
==================================================

{context}


==================================================
ANSWERING RULES
==================================================

RULE 1 - USE ONLY THE RETRIEVED INFORMATION
Do not use outside knowledge. Do not invent facts. Do not
assume information that is not supported by the retrieved
website content.

RULE 2 - DIRECT FACTS
If the answer is explicitly stated, answer it directly.

RULE 3 - COUNTING INFORMATION
If the user asks how many items are listed and the retrieved
content contains a clear list, count the items.

RULE 4 - REASONABLE INFERENCE
If the answer is not explicitly stated but can be reasonably
calculated or inferred, you MAY make the inference. Clearly
distinguish the inference from an explicit website statement.

RULE 5 - DO NOT OVER-INFER
Do NOT convert an inference into a confirmed fact.

RULE 6 - CALCULATIONS
You may perform simple calculations from the retrieved content.
Be careful with "+" values.

RULE 7 - MISSING INFORMATION
If the retrieved information does not contain enough evidence,
say: "I couldn't find that information on the website."

RULE 8 - PARTIAL INFORMATION
If the information partially answers the question, provide the
available information and clearly state what is missing.

RULE 9 - SOURCE TRANSPARENCY
When useful, mention the answer is based on the retrieved
website information. Do not fabricate citations or URLs.

RULE 10 - BE CONCISE
Give a clear, natural answer. Do not explain the RAG process.
Do not mention embeddings, vector databases, similarity scores,
or internal implementation details.

==================================================
FINAL ANSWER
==================================================
"""


def build_context(results):

    if not results:
        return "No relevant website information was retrieved."

    parts = []

    for i, result in enumerate(results, start=1):

        parts.append(
            f"""
--- Retrieved Source {i} ---

Chunk ID:
{result.get("chunk_id", "unknown")}

Similarity score:
{result.get("score", 0):.4f}

Source URL:
{result.get("source_url", "unknown")}

Website content:
{result.get("text", "")}

--- End Source {i} ---
"""
        )

    return "\n".join(parts)


def _generate_once(model, prompt, timeout=25):

    key = get_api_key()

    url = f"{GEMINI_BASE}/{model}:generateContent?key={key}"

    body = {"contents": [{"parts": [{"text": prompt}]}]}

    result = _post_json(url, body, timeout=timeout, retries=1)

    candidates = result.get("candidates", [])

    if not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])

    return "".join(part.get("text", "") for part in parts).strip()


def answer_question(question, results):

    context = build_context(results)

    prompt = ANSWER_PROMPT.replace(
        "{question}",
        question
    ).replace(
        "{context}",
        context
    )

    last_error = None

    for model in GEN_MODELS:

        try:

            print(f"   Generating answer with {model}...")

            text = _generate_once(model, prompt)

            if text:
                return text

            last_error = RuntimeError(f"{model} returned empty text")

        except Exception as e:

            last_error = e

            print(f"   [fallback] {model} failed: {e}")

    raise RuntimeError(
        f"All models failed. Last error: {last_error}"
    )


# ==========================================
# Crawl (Firecrawl, rendered site)
# ==========================================

def crawl_site(url=SITE_URL, output_dir=None):

    from firecrawl import Firecrawl

    output_dir = Path(output_dir or SCRAPED_DIR)

    api_key = os.getenv("FIRECRAWL_API_KEY")

    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY not found in .env")

    app = Firecrawl(api_key=api_key)

    print(f"   Crawling {url} ...")

    try:

        result = app.crawl(url=url, max_age=0)

    except Exception as e:

        message = str(e).lower()

        if any(word in message for word in ("credit", "quota", "limit")):
            raise RuntimeError(
                "Firecrawl free credits exceeded. "
                "Wait for reset or upgrade the plan."
            )

        raise

    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True)

    for i, document in enumerate(result.data or []):

        page_url = document.metadata.url

        markdown = document.markdown or ""

        filename = output_dir / f"page_{i + 1}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"URL: {page_url}\n\n")
            f.write(markdown)

    count = len(result.data or [])

    print(f"   Crawled {count} page(s) into {output_dir}")

    return count


# ==========================================
# Chunk (LangChain recursive splitter)
# ==========================================

def content_hash(text):

    normalized = " ".join(text.split())

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def build_chunks(scraped_dir=None, output_file=None):

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    scraped_dir = Path(scraped_dir or SCRAPED_DIR)

    output_file = Path(output_file or CHUNKS_FILE)

    if not scraped_dir.exists():
        raise RuntimeError(
            f"{scraped_dir} not found. Run the crawl step first."
        )

    files = sorted(
        scraped_dir.glob("*.md"),
        key=lambda p: int(p.stem.split("_")[-1])
        if p.stem.split("_")[-1].isdigit() else 0
    )

    if not files:
        raise RuntimeError("No Markdown files found in scraped_data.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    all_chunks = []

    valid_pages = 0

    rejected_pages = 0

    for file in files:

        content = file.read_text(encoding="utf-8")

        lines = content.splitlines()

        if lines and lines[0].startswith("URL:"):
            source_url = lines[0].replace("URL:", "", 1).strip()
            actual_content = "\n".join(lines[2:])
        else:
            source_url = "unknown"
            actual_content = content

        normalized = actual_content.lower().strip()

        is_404 = (
            normalized.startswith("# page not found")
            or normalized.startswith("**404**")
            or "**404**: not_found" in normalized
            or "404: not_found" in normalized
            or "code: `not_found`" in normalized
            or "looks like you've followed a broken link" in normalized
            or "error: not found" in normalized
        )

        if is_404 or not actual_content.strip():
            rejected_pages += 1
            print(f"   [skip] {file.name} ({source_url})")
            continue

        valid_pages += 1

        page_id = file.stem

        chunks = splitter.split_text(actual_content)

        print(f"   [ok] {file.name} -> {len(chunks)} chunk(s)")

        for i, chunk_text in enumerate(chunks):

            all_chunks.append({
                "id": f"{page_id}_chunk_{i}",
                "text": chunk_text,
                "metadata": {
                    "source_url": source_url,
                    "page_id": page_id,
                    "chunk_index": i,
                    "total_chunks_in_page": len(chunks),
                },
            })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(
        f"   Pages: {valid_pages} valid, {rejected_pages} rejected | "
        f"Chunks: {len(all_chunks)} -> {output_file.name}"
    )

    return all_chunks


# ==========================================
# Qdrant storage (collection: aklm_live, 3072-dim)
# ==========================================

def get_qdrant():

    from qdrant_client import QdrantClient

    return QdrantClient(path=QDRANT_PATH)


def ensure_collection(client, recreate=False):

    from qdrant_client.models import Distance, VectorParams

    existing = [
        c.name
        for c in client.get_collections().collections
    ]

    if COLLECTION_NAME in existing and recreate:
        client.delete_collection(COLLECTION_NAME)
        existing.remove(COLLECTION_NAME)
        print(f"   Recreated collection: {COLLECTION_NAME}")

    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
        print(f"   Created collection: {COLLECTION_NAME} ({VECTOR_SIZE}-dim)")

    return client


def _chunk_to_point(chunk, embedding):

    from qdrant_client.models import PointStruct

    chunk_hash = content_hash(chunk["text"])

    metadata = chunk.get("metadata", {})

    payload = {
        "text": chunk["text"],
        "source_url": metadata.get("source_url", "unknown"),
        "page_id": metadata.get("page_id", "unknown"),
        "chunk_index": metadata.get("chunk_index", 0),
        "total_chunks_in_page": metadata.get("total_chunks_in_page", 1),
        "chunk_id": chunk["id"],
        "content_hash": chunk_hash,
    }

    qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_hash))

    return PointStruct(
        id=qdrant_id,
        vector=embedding,
        payload=payload
    )


def _scroll_all(client):

    records = []

    offset = None

    while True:

        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )

        records.extend(points)

        if offset is None:
            break

    return records


def store_full(chunks, embeddings=None):

    if embeddings is None:
        embeddings = embed_texts(
            [chunk["text"] for chunk in chunks],
            task_type="RETRIEVAL_DOCUMENT"
        )

    client = get_qdrant()

    try:

        ensure_collection(client, recreate=True)

        points = [
            _chunk_to_point(chunk, embedding)
            for chunk, embedding in zip(chunks, embeddings)
        ]

        client.upsert(collection_name=COLLECTION_NAME, points=points)

        count = client.get_collection(COLLECTION_NAME).points_count

        print(f"   Stored {len(points)} vectors | collection now {count} points")

        return {"stored": len(points), "total": count}

    finally:

        _safe_close(client)


def store_update(chunks):

    client = get_qdrant()

    try:

        ensure_collection(client, recreate=False)

        existing = {
            point.payload.get("content_hash"): str(point.id)
            for point in _scroll_all(client)
            if point.payload
        }

        new_hashes = set()

        to_embed = []

        for chunk in chunks:

            chunk_hash = content_hash(chunk["text"])

            new_hashes.add(chunk_hash)

            if chunk_hash not in existing:
                to_embed.append(chunk)

        if to_embed:

            embeddings = embed_texts(
                [chunk["text"] for chunk in to_embed],
                task_type="RETRIEVAL_DOCUMENT"
            )

            points = [
                _chunk_to_point(chunk, embedding)
                for chunk, embedding in zip(to_embed, embeddings)
            ]

            client.upsert(collection_name=COLLECTION_NAME, points=points)

        else:

            points = []

        stale_ids = [
            qdrant_id
            for chunk_hash, qdrant_id in existing.items()
            if chunk_hash not in new_hashes
        ]

        if stale_ids:
            from qdrant_client.models import PointIdsList
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=PointIdsList(points=stale_ids)
            )

        count = client.get_collection(COLLECTION_NAME).points_count

        stats = {
            "unchanged": len(chunks) - len(to_embed),
            "added_or_changed": len(to_embed),
            "removed": len(stale_ids),
            "total": count,
        }

        print(
            f"   Update: +{stats['added_or_changed']} "
            f"(new/changed), {stats['unchanged']} unchanged, "
            f"-{stats['removed']} removed | collection now {count} points"
        )

        return stats

    finally:

        _safe_close(client)


def _safe_close(client):

    try:
        client.close()
    except Exception:
        pass


# ==========================================
# Retrieval
# ==========================================

def retrieve(query, top_k=5):

    if not query or not query.strip():
        return []

    client = get_qdrant()

    try:

        query_vector = embed_query(query)

        search_result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k
        )

        results = []

        for point in search_result.points:

            payload = point.payload or {}

            results.append({
                "score": float(point.score),
                "chunk_id": payload.get("chunk_id", "unknown"),
                "source_url": payload.get("source_url", "unknown"),
                "text": payload.get("text", ""),
                "page_id": payload.get("page_id", "unknown"),
                "chunk_index": payload.get("chunk_index", 0),
            })

        return results

    finally:

        _safe_close(client)


# ==========================================
# Sync live bot (rebuild api/vectors.json + push)
# ==========================================

def sync_live(chunks, repo_path=None):

    repo_path = Path(
        repo_path
        or os.getenv("ADCETPORTAL_REPO")
        or DEFAULT_ADCETPORTAL_REPO
    )

    vectors_file = repo_path / "api" / "vectors.json"

    git_dir = repo_path / ".git"

    if not git_dir.exists() or not (git_dir / "HEAD").exists():
        raise RuntimeError(
            f"{repo_path} is not a valid git clone (missing/broken .git). "
            "This usually means the clone was deleted or corrupted. "
            "Re-clone it first, e.g.:  "
            f'git clone <repo-url> "{repo_path}"'
        )

    embeddings = embed_texts(
        [chunk["text"] for chunk in chunks],
        task_type="RETRIEVAL_DOCUMENT"
    )

    entries = []

    for chunk, embedding in zip(chunks, embeddings):

        metadata = chunk.get("metadata", {})

        entries.append({
            "id": chunk["id"],
            "text": chunk["text"],
            "source_url": metadata.get("source_url", "unknown"),
            "embedding": embedding,
        })

    with open(vectors_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False)

    print(f"   Wrote {len(entries)} vectors -> {vectors_file}")

    def git(*args):
        return subprocess.run(
            ["git", *args],
            cwd=str(repo_path),
            capture_output=True,
            text=True
        )

    # Safety: make sure git really treats repo_path as the repo root. If its
    # ".git" is broken, git would silently walk up to a parent repo (e.g. an
    # accidental repo in the user's home folder).
    toplevel = git("rev-parse", "--show-toplevel")

    if (
        toplevel.returncode != 0
        or Path(toplevel.stdout.strip()).resolve() != repo_path.resolve()
    ):
        raise RuntimeError(
            f"Refusing to sync: git resolved '{repo_path}' to "
            f"'{toplevel.stdout.strip()}'. Re-clone {repo_path} first."
        )

    git("add", "api/vectors.json")

    status = git("status", "--porcelain")

    if not status.stdout.strip():
        print("   No changes to commit; live index already up to date.")
        return {"entries": len(entries), "committed": False}

    commit = git(
        "commit",
        "-m",
        f"Refresh knowledge index ({len(entries)} chunks)"
    )

    if commit.returncode != 0:
        raise RuntimeError(f"git commit failed: {commit.stderr.strip()}")

    # Integrate any remote commits that landed while we were working, then push.
    # Retry a few times in case the remote moves again mid-push.
    push = None

    for attempt in range(1, 4):

        branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"

        git("fetch", "origin")

        pull = git("pull", "--rebase", "origin", branch)

        if pull.returncode != 0:
            raise RuntimeError(
                "git pull --rebase failed (possible conflict): "
                + (pull.stderr.strip() or pull.stdout.strip())
            )

        push = git("push", "origin", branch)

        if push.returncode == 0:
            break

        print(f"   [retry] push rejected, retrying ({attempt}/3)...")

        time.sleep(2)

    else:

        raise RuntimeError(f"git push failed: {push.stderr.strip()}")

    print("   Committed and pushed -> Vercel will redeploy.")

    return {"entries": len(entries), "committed": True}

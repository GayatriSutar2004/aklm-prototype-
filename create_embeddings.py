"""
Step 3a - Embed (standalone).

Embeds chunks.json with Gemini (gemini-embedding-001, 3072-dim) via the shared
aklm_lib and writes embedded_chunks.json.

Note: run_pipeline.py embeds and stores in one go; this script exists so the
embedding step can still be inspected on its own.
"""

import json

import aklm_lib


print("=" * 40)
print("AKLM STEP 3a: EMBED (Gemini 3072-dim)")
print("=" * 40)

with open(aklm_lib.CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Loaded {len(chunks)} chunks from {aklm_lib.CHUNKS_FILE.name}")

embeddings = aklm_lib.embed_texts(
    [chunk["text"] for chunk in chunks],
    task_type="RETRIEVAL_DOCUMENT"
)

for chunk, embedding in zip(chunks, embeddings):
    chunk["embedding"] = embedding

with open(aklm_lib.EMBEDDED_FILE, "w", encoding="utf-8") as f:
    json.dump(chunks, f, indent=2, ensure_ascii=False)

print(f"\nEmbedded {len(chunks)} chunks.")
print(f"Dimensions: {len(chunks[0]['embedding'])}")
print(f"Saved to: {aklm_lib.EMBEDDED_FILE.name}")

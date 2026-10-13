"""
Step 3b - Store (standalone).

Stores embedded_chunks.json into the Gemini collection (aklm_live, 3072-dim)
via the shared aklm_lib. Recreates the collection first (full load).

The research collection aklm_knowledge (384-dim, bge) is not touched.
"""

import json

import aklm_lib


print("=" * 40)
print("AKLM STEP 3b: STORE -> Qdrant (aklm_live)")
print("=" * 40)

with open(aklm_lib.EMBEDDED_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

if not chunks:
    raise SystemExit("embedded_chunks.json contains no chunks.")

embeddings = [chunk["embedding"] for chunk in chunks]

dims = len(embeddings[0])

if dims != aklm_lib.VECTOR_SIZE:
    raise SystemExit(
        f"Embedding dimension mismatch: got {dims}, "
        f"expected {aklm_lib.VECTOR_SIZE}."
    )

print(f"Loaded {len(chunks)} embedded chunks ({dims}-dim).")

aklm_lib.store_full(chunks, embeddings=embeddings)

print(f"\nCollection: {aklm_lib.COLLECTION_NAME}")
print(f"Storage   : {aklm_lib.QDRANT_PATH}")

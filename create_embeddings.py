import json
from sentence_transformers import SentenceTransformer


# ---------------------------------------
# 1. Load chunks
# ---------------------------------------

with open("chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)


print(f"Loaded {len(chunks)} chunks.")


# ---------------------------------------
# 2. Load embedding model
# ---------------------------------------

print("Loading embedding model...")

model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

print("Embedding model loaded.")


# ---------------------------------------
# 3. Generate embeddings
# ---------------------------------------

texts = [
    chunk["text"]
    for chunk in chunks
]

print("Generating embeddings...")

embeddings = model.encode(
    texts,
    normalize_embeddings=True
)


# ---------------------------------------
# 4. Add embeddings to chunks
# ---------------------------------------

for chunk, embedding in zip(chunks, embeddings):

    chunk["embedding"] = embedding.tolist()


# ---------------------------------------
# 5. Save result
# ---------------------------------------

with open(
    "embedded_chunks.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        chunks,
        f,
        indent=2,
        ensure_ascii=False
    )


print("\n======================================")
print("EMBEDDING COMPLETE")
print("======================================")

print(f"Chunks embedded: {len(chunks)}")

print(
    f"Embedding dimensions: "
    f"{len(chunks[0]['embedding'])}"
)

print(
    "\nOutput saved to: embedded_chunks.json"
)

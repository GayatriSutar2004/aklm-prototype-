from pathlib import Path
import json
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


# ==========================================
# 1. Configuration
# ==========================================

INPUT_FILE = Path("embedded_chunks.json")

QDRANT_PATH = "qdrant_storage"

COLLECTION_NAME = "aklm_knowledge"

EXPECTED_VECTOR_SIZE = 384


# ==========================================
# 2. Check input file
# ==========================================

if not INPUT_FILE.exists():
    raise RuntimeError(
        f"{INPUT_FILE} not found.\n"
        "Run embed_data.py first."
    )


# ==========================================
# 3. Load embedded chunks
# ==========================================

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)


if not chunks:
    raise RuntimeError(
        "embedded_chunks.json contains no chunks."
    )


print("========================================")
print("AKLM QDRANT STORAGE")
print("========================================")

print(f"Input file       : {INPUT_FILE}")
print(f"Chunks received  : {len(chunks)}")


# ==========================================
# 4. Validate embeddings
# ==========================================

for i, chunk in enumerate(chunks):

    if "id" not in chunk:
        raise ValueError(
            f"Chunk {i} is missing 'id'."
        )

    if "embedding" not in chunk:
        raise ValueError(
            f"Chunk {chunk['id']} is missing 'embedding'."
        )

    vector_size = len(chunk["embedding"])

    if vector_size != EXPECTED_VECTOR_SIZE:
        raise ValueError(
            "\nEmbedding dimension mismatch!\n"
            f"Chunk ID : {chunk['id']}\n"
            f"Expected : {EXPECTED_VECTOR_SIZE}\n"
            f"Received : {vector_size}\n"
            "\nMake sure you are using "
            "BAAI/bge-small-en-v1.5."
        )


print(f"Vector dimension: {EXPECTED_VECTOR_SIZE}")


# ==========================================
# 5. Connect to local Qdrant
# ==========================================

print("\nConnecting to Qdrant...")

client = QdrantClient(
    path=QDRANT_PATH
)

print("✅ Qdrant connected")


# ==========================================
# 6. Create collection if necessary
# ==========================================

existing_collections = [
    collection.name
    for collection in client.get_collections().collections
]


if COLLECTION_NAME not in existing_collections:

    print(f"\nCreating collection: {COLLECTION_NAME}")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EXPECTED_VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )

    print("✅ Collection created")

else:

    print(
        f"\nCollection already exists: "
        f"{COLLECTION_NAME}"
    )


# ==========================================
# 7. Prepare Qdrant points
# ==========================================

points = []

for chunk in chunks:

    metadata = chunk.get("metadata", {})

    payload = {
        "text": chunk.get("text", ""),

        "source_url": metadata.get(
            "source_url",
            "unknown"
        ),

        "page_id": metadata.get(
            "page_id",
            "unknown"
        ),

        "chunk_index": metadata.get(
            "chunk_index",
            0
        ),

        "total_chunks_in_page": metadata.get(
            "total_chunks_in_page",
            1
        )
    }

    # Create a deterministic UUID from the AKLM chunk ID
    qdrant_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            chunk["id"]
        )
    )

    # Preserve the original readable chunk ID
    payload["chunk_id"] = chunk["id"]

    point = PointStruct(
        id=qdrant_id,
        vector=chunk["embedding"],
        payload=payload
    )

    points.append(point)


# ==========================================
# 8. Upload vectors
# ==========================================

print(
    f"\nUploading {len(points)} vectors..."
)

client.upsert(
    collection_name=COLLECTION_NAME,
    points=points
)

print("✅ Vectors uploaded")


# ==========================================
# 9. Verify storage
# ==========================================

collection_info = client.get_collection(
    collection_name=COLLECTION_NAME
)

points_count = collection_info.points_count


# ==========================================
# 10. Final report
# ==========================================

print("\n========================================")
print("QDRANT STORAGE COMPLETE")
print("========================================")

print(f"Collection       : {COLLECTION_NAME}")
print(f"Chunks received  : {len(chunks)}")
print(f"Vectors uploaded : {len(points)}")
print(f"Vector dimension : {EXPECTED_VECTOR_SIZE}")
print(f"Points in Qdrant : {points_count}")

print(f"\nStorage location : {QDRANT_PATH}")

print("\nStatus: ✅ SUCCESS")

print("========================================")

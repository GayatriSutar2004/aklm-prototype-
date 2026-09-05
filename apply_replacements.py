import argparse
import json
import os
import uuid
from pathlib import Path

try:

    import torch

    torch.set_num_threads(os.cpu_count() or 8)

except Exception:
    pass

import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer


# ==================================================
# CONFIGURATION
# ==================================================

ROOT = Path(
    "Dataset/AKLM_FINAL_v3_FINAL"
)

PLANS_PATH = ROOT / (
    "lifecycle/stale_replacements/stale_replacements.csv"
)

CHUNKS_PATH = ROOT / "rag/chunks.csv"

QDRANT_PATH = "qdrant_storage"

COLLECTION_NAME = "aklm_knowledge"

MODEL_NAME = "BAAI/bge-small-en-v1.5"

VECTOR_SIZE = 384

DATASET_VERSION_TAG = "benchmark-v3"


# ==================================================
# COMMAND-LINE OPTIONS
# ==================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--plan-limit",
    type=int,
    default=None,
    help="Apply only the first N replacement plans (default: all)."
)

parser.add_argument(
    "--website",
    default=None,
    help="Only apply plans for this website id, e.g. W001."
)

parser.add_argument(
    "--recreate",
    action="store_true",
    help="Recreate the collection before applying plans."
)

args = parser.parse_args()


# ==================================================
# LOAD DATA
# ==================================================

print("=" * 60)
print("AKLM SELECTIVE REPLACEMENT")
print("=" * 60)

print("\nLoading replacement plans...")

plans_df = pd.read_csv(
    PLANS_PATH,
    dtype=str
)

if args.website:

    plans_df = plans_df[
        plans_df["website_id"] == args.website
    ]

if args.plan_limit:

    plans_df = plans_df.head(args.plan_limit)

print(
    f"Plans to apply: {len(plans_df)}"
)

print("\nLoading chunk corpus...")

chunks_df = pd.read_csv(
    CHUNKS_PATH,
    dtype=str
)

chunk_text = dict(
    zip(
        chunks_df["chunk_id"],
        chunks_df["text"]
    )
)

chunk_source = dict(
    zip(
        chunks_df["chunk_id"],
        chunks_df["source_path"]
    )
)

chunk_version = dict(
    zip(
        chunks_df["chunk_id"],
        chunks_df["version"]
    )
)

chunk_page_type = dict(
    zip(
        chunks_df["chunk_id"],
        chunks_df["page_type"]
    )
)


# ==================================================
# GATHER REQUIRED (LATEST) CHUNKS
# ==================================================

required_chunk_ids = set()

pair_rows = []

for _, row in plans_df.iterrows():

    plan = json.loads(
        row["chunk_replacement_plan_json"]
    )

    for pair in plan:

        pair_rows.append(
            {
                "replacement_id": row["replacement_id"],
                "stale_test_id": row["stale_test_id"],
                "website_id": row["website_id"],
                "page_id": row["page_id"],
                "from_chunk_id": pair["from_chunk_id"],
                "to_chunk_id": pair["to_chunk_id"],
                "embedding_update_required": pair[
                    "embedding_update_required"
                ]
            }
        )

        if pair["embedding_update_required"] == "yes":

            required_chunk_ids.add(
                pair["to_chunk_id"]
            )

pair_df = pd.DataFrame(pair_rows)

print(
    f"Chunk pairs to process: {len(pair_df)}"
)

print(
    f"Unique chunks needing a fresh embedding: "
    f"{len(required_chunk_ids)}"
)


# ==================================================
# EMBED ONLY THE STALE CHUNKS
# ==================================================

def flush_print(message):

    print(message)

    import sys

    sys.stdout.flush()


flush_print("\nLoading embedding model...")

model = SentenceTransformer(MODEL_NAME)

required_chunk_ids = sorted(required_chunk_ids)

cache_path = Path("apply_cache.json")

cached = {}

if cache_path.exists():

    cached = json.loads(cache_path.read_text(encoding="utf-8"))

missing_ids = [
    chunk_id
    for chunk_id in required_chunk_ids
    if chunk_id not in cached
]

flush_print(
    f"Embedding {len(missing_ids)} locked chunk texts "
    f"(cached {len(cached)})..."
)

batch_size = 512

new_vectors = {}

for start in range(0, len(missing_ids), batch_size):

    batch_ids = missing_ids[start:start + batch_size]

    batch_embeddings = model.encode(
        [
            chunk_text[chunk_id]
            for chunk_id in batch_ids
        ],
        normalize_embeddings=True
    )

    for chunk_id, embedding in zip(
        batch_ids,
        batch_embeddings
    ):

        cached[chunk_id] = embedding.tolist()

    batch_number = start // batch_size

    is_last_batch = (
        start + batch_size
    ) >= len(missing_ids)

    if is_last_batch or batch_number % 8 == 7:

        cache_path.write_text(
            json.dumps(cached),
            encoding="utf-8"
        )

    flush_print(
        f"  embedded {min(start + batch_size, len(missing_ids))}"
        f"/{len(missing_ids)}"
    )

new_vectors = cached

flush_print("Embedding complete")


# ==================================================
# CONNECT TO QDRANT
# ==================================================

print("\nConnecting to Qdrant...")

client = QdrantClient(
    path=QDRANT_PATH
)

if args.recreate or COLLECTION_NAME not in [
    c.name for c in client.get_collections().collections
]:

    if args.recreate:

        client.delete_collection(
            COLLECTION_NAME
        )

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )

print("Qdrant ready")


# ==================================================
# APPLY SELECTIVE REPLACEMENT (TWO PHASES)
# ==================================================

def point_for(chunk_id):

    payload = {
        "chunk_id": chunk_id,
        "website_id": chunk_id.split("_")[0],
        "version": chunk_version[chunk_id],
        "page_id": chunk_id.split("_")[2],
        "page_type": chunk_page_type[chunk_id],
        "source_url": chunk_source[chunk_id],
        "text": chunk_text[chunk_id],
        "dataset": DATASET_VERSION_TAG
    }

    return PointStruct(
        id=str(
            uuid.uuid5(uuid.NAMESPACE_URL, chunk_id)
        ),
        vector=new_vectors[chunk_id],
        payload=payload
    )


update_rows = pair_df[
    pair_df["embedding_update_required"] == "yes"
]

required_ids = set(update_rows["to_chunk_id"])

obsolete_ids = sorted(
    set(update_rows["from_chunk_id"]) - required_ids
)

flush_print(
    f"\nPhase 1: upserting {len(required_ids)} refreshed chunks..."
)

points = [
    point_for(chunk_id)
    for chunk_id in sorted(required_ids)
]

for start in range(0, len(points), 500):

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points[start:start + 500]
    )

flush_print(
    f"Phase 2: removing {len(obsolete_ids)} obsolete chunks..."
)

for start in range(0, len(obsolete_ids), 500):

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=[
            str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))
            for chunk_id in obsolete_ids[start:start + 500]
        ]
    )

replaced = len(required_ids)

removed = len(obsolete_ids)

kept = len(pair_df) - len(update_rows)


# ==================================================
# SUMMARY
# ==================================================

print("\n" + "=" * 60)
print("REPLACEMENT COMPLETE")
print("=" * 60)

print(
    f"Plans applied        : {len(plans_df)}"
)

print(
    f"Chunks replaced      : {replaced}"
)

print(
    f"Chunks kept unchanged: {kept}"
)

print(
    f"Old vectors removed  : {removed}"
)

collection_info = client.get_collection(
    collection_name=COLLECTION_NAME
)

print(
    f"Points now in Qdrant : "
    f"{collection_info.points_count}"
)

print(
    f"\nCollection           : {COLLECTION_NAME}"
)

print(
    f"Storage location     : {QDRANT_PATH}"
)

print(
    "\nStatus: SELECTIVE REPLACEMENT APPLIED"
)

client.close()

print("=" * 60)
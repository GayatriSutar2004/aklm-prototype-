import json
import sys
from pathlib import Path

import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import MatchValue, FieldCondition, Filter
from sentence_transformers import SentenceTransformer


# ==================================================
# CONFIGURATION
# ==================================================

ROOT = Path(__file__).resolve().parent

QUESTIONS_PATH = ROOT / (
    "Dataset/AKLM_FINAL_v3_FINAL/evaluation/questions.csv"
)

STALE_CASES_PATH = ROOT / (
    "Dataset/AKLM_FINAL_v3_FINAL/evaluation/stale_cases.csv"
)

PLANS_PATH = ROOT / (
    "Dataset/AKLM_FINAL_v3_FINAL"
    "/lifecycle/stale_replacements/stale_replacements.csv"
)

CHUNKS_PATH = ROOT / (
    "Dataset/AKLM_FINAL_v3_FINAL/rag/chunks.csv"
)

QDRANT_PATH = ROOT / "qdrant_storage"

COLLECTION_NAME = "aklm_knowledge"

MODEL_NAME = "BAAI/bge-small-en-v1.5"

TOP_K = 5


# ==================================================
# HELPERS
# ==================================================

def parse_gold_ids(raw):

    if not raw or not str(raw).strip():
        return set()

    text = str(raw).strip()

    if text.startswith("["):

        return set(json.loads(text))

    return {
        part.strip()
        for part in text.split(",")
        if part.strip()
    }


def relative_best(scores):

    return max(scores) if scores else 0.0


# ==================================================
# LOAD DATA
# ==================================================

print("=" * 60)

print("AKLM RETRIEVAL EVALUATION")

print("=" * 60)

questions_df = pd.read_csv(
    QUESTIONS_PATH,
    dtype=str
)

test_df = questions_df[
    (questions_df["split"] == "test")
    & (questions_df["retrieval_needed"] == "yes")
].copy()

test_df["gold_ids"] = test_df[
    "supporting_chunk_ids"
].apply(parse_gold_ids)

test_df = test_df[
    test_df["gold_ids"].map(len) > 0
]

print(
    f"\nQuestions evaluated: {len(test_df)} "
    f"(test split, retrieval needed, gold chunks)"
)

print("\nLoading Qdrant index...")

client = QdrantClient(path=str(QDRANT_PATH))

db_chunk_ids = set()

offset = None

while True:

    points, offset = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=10000,
        with_payload=True,
        offset=offset
    )

    for point in points:

        chunk_id = (point.payload or {}).get("chunk_id")

        if chunk_id:

            db_chunk_ids.add(chunk_id)

    if offset is None:

        break

print(
    f"Chunks present in index: {len(db_chunk_ids)}"
)

covered = test_df["gold_ids"].map(
    lambda ids: ids.issubset(db_chunk_ids)
)

print(
    f"Questions whose gold chunks are all in the index: "
    f"{int(covered.sum())}/{len(test_df)}"
)

print("\nLoading embedding model...")

model = SentenceTransformer(MODEL_NAME)


# ==================================================
# RETRIEVE AND SCORE
# ==================================================

def retrieve(query, top_k=TOP_K, website_id=None):

    vector = model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    query_filter = None

    if website_id:

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="website_id",
                    match=MatchValue(value=website_id)
                )
            ]
        )

    result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=top_k,
        with_payload=True,
        query_filter=query_filter
    )

    return [
        (point.payload or {}).get(
            "chunk_id",
            "unknown"
        )
        for point in result.points
    ]


def reciprocal_rank(gold_ids, retrieved):

    for rank, chunk_id in enumerate(retrieved, start=1):

        if chunk_id in gold_ids:

            return 1.0 / rank

    return 0.0


records = []

for _, row in test_df.iterrows():

    gold_ids = row["gold_ids"]

    website_id = row["website_id"]

    retrieved = retrieve(row["question"])

    retrieved_same_site = retrieve(
        row["question"],
        website_id=website_id
    )

    hits = {
        chunk_id
        for chunk_id in retrieved
        if chunk_id in gold_ids
    }

    hits_same_site = {
        chunk_id
        for chunk_id in retrieved_same_site
        if chunk_id in gold_ids
    }

    records.append(
        {
            "question_id": row["question_id"],
            "question_type": row["question_type"],
            "retrieved": retrieved,
            "hits": sorted(hits),
            "recall_at_1": 1.0 if hits and retrieved[0] in gold_ids else 0.0,
            "recall_at_k": 1.0 if hits else 0.0,
            "mrr": reciprocal_rank(gold_ids, retrieved),
            "recall_at_k_same_site": (
                1.0 if hits_same_site else 0.0
            )
        }
    )

eval_df = pd.DataFrame(records)

overall_r1 = eval_df["recall_at_1"].mean()

overall_rk = eval_df["recall_at_k"].mean()

overall_mrr = eval_df["mrr"].mean()

print("\n" + "=" * 60)

print("OVERALL (question-level, top-5)")

print("=" * 60)

print(
    f"Recall@1 : {overall_r1:.4f}"
)

print(
    f"Recall@5 : {overall_rk:.4f}"
)

print(
    f"MRR      : {overall_mrr:.4f}"
)

overall_same_site = eval_df["recall_at_k_same_site"].mean()

print(
    f"\nRecall@5 (same-website search): "
    f"{overall_same_site:.4f}"
)

print("\n" + "=" * 60)

print("BY QUESTION TYPE")

print("=" * 60)

per_type = eval_df.groupby("question_type")[
    ["recall_at_k", "recall_at_k_same_site"]
].agg(["mean", "count"])

for question_type, row in per_type.iterrows():

    print(
        f"{question_type:<20} site-wide={row[('recall_at_k', 'mean')]:.4f} "
        f"same-site={row[('recall_at_k_same_site', 'mean')]:.4f} "
        f"(n={int(row[('recall_at_k', 'count')])})"
    )

print("\n" + "=" * 60)

print("GOLD AVAILABILITY BY TYPE")

print("=" * 60)

test_df["gold_covered"] = test_df["gold_ids"].map(
    lambda ids: ids.issubset(db_chunk_ids)
)

coverage = test_df.groupby("question_type")[
    "gold_covered"
].agg("mean")

for question_type, rate in coverage.items():

    print(
        f"{question_type:<20} {rate:.3f}"
    )


# ==================================================
# BEFORE / AFTER DEMO
# ==================================================

print("\n" + "=" * 60)

print("BEFORE / AFTER SELECTIVE REPLACEMENT")

print("=" * 60)

questions_by_id = dict(
    zip(
        test_df["question_id"],
        test_df
    )
)

demo_row = None

for _, row in test_df.iterrows():

    if row["question_type"] != "stale":
        continue

    if not row["gold_ids"].issubset(db_chunk_ids):
        continue

    demo_row = row

    break

if demo_row is None:

    print("\nNo eligible stale question for demo.")

    sys.exit(0)

gold_ids = demo_row["gold_ids"]

demo_gold_id = sorted(gold_ids)[0]

website_id, version_to, page_id = demo_gold_id.split("_")[:3]

chunks_df = pd.read_csv(CHUNKS_PATH, dtype=str)

page_chunks = chunks_df[
    (chunks_df["website_id"] == website_id)
    & (chunks_df["page_id"] == page_id)
]

snapshot_chunk_ids = sorted(
    page_chunks[
        page_chunks["version"] == version_to
    ]["chunk_id"]
)

plans_df = pd.read_csv(PLANS_PATH, dtype=str)

matching_plan = plans_df[
    (plans_df["website_id"] == website_id)
    & (plans_df["page_id"] == page_id)
    & (plans_df["required_version"] == version_to)
]

if len(matching_plan) == 0:

    print("\nNo matching replacement plan for demo.")

    sys.exit(0)

snapshot_version = matching_plan.iloc[0][
    "snapshot_version"
]

snapshot_chunk_ids = sorted(
    page_chunks[
        page_chunks["version"] == snapshot_version
    ]["chunk_id"]
)

print(
    f"\nDemo question: {demo_row['question']}"
)

print(
    "\nGold (correct) chunks target version "
    f"{version_to}."
)

print(
    "\nIndex BEFORE refresh only had version "
    f"{snapshot_version} chunks."
)

print(
    "Index AFTER refresh has version "
    f"{version_to} chunks."
)

question_embedding = model.encode(
    demo_row["question"],
    normalize_embeddings=True
)

snapshot_embeddings = model.encode(
    [
        page_chunks[
            page_chunks["chunk_id"] == chunk_id
        ].iloc[0]["text"]
        for chunk_id in snapshot_chunk_ids
    ],
    normalize_embeddings=True
)

snapshot_scores = [
    float(question_embedding @ embedding)
    for embedding in snapshot_embeddings
]

required_ids = sorted(set(gold_ids))

required_embeddings = model.encode(
    [
        page_chunks[
            page_chunks["chunk_id"] == chunk_id
        ].iloc[0]["text"]
        for chunk_id in required_ids
    ],
    normalize_embeddings=True
)

required_scores = [
    float(question_embedding @ embedding)
    for embedding in required_embeddings
]

print("\nResults BEFORE refresh (snapshot chunks only):")

for chunk_id, score in sorted(
    zip(snapshot_chunk_ids, snapshot_scores),
    key=lambda item: item[1],
    reverse=True
)[:3]:

    mark = " *GOLD*" if chunk_id in gold_ids else ""

    print(f"  {chunk_id:<22} sim={score:.4f}{mark}")

print("\nResults AFTER refresh (refreshed chunks only):")

for chunk_id, score in sorted(
    zip(required_ids, required_scores),
    key=lambda item: item[1],
    reverse=True
)[:3]:

    mark = " *GOLD*" if chunk_id in gold_ids else ""

    print(f"  {chunk_id:<22} sim={score:.4f}{mark}")

print("\n" + "=" * 60)

print("EVALUATION COMPLETE")

print("=" * 60)
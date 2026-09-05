from pathlib import Path

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


# ==========================================
# Configuration
# ==========================================

QDRANT_PATH = "qdrant_storage"

COLLECTION_NAME = "aklm_knowledge"

MODEL_NAME = "BAAI/bge-small-en-v1.5"


# ==========================================
# Load embedding model once
# ==========================================

print("\nLoading embedding model...")

model = SentenceTransformer(
    MODEL_NAME
)

print("✅ Embedding model loaded")


# ==========================================
# Retrieval function
# ==========================================

def retrieve(query, top_k=5):

    if not query or not query.strip():
        return []

    client = None

    try:

        # ----------------------------------
        # Connect to Qdrant
        # ----------------------------------

        client = QdrantClient(
            path=QDRANT_PATH
        )

        # ----------------------------------
        # Create query embedding
        # ----------------------------------

        query_embedding = model.encode(
            query,
            normalize_embeddings=True
        ).tolist()

        # ----------------------------------
        # Search Qdrant
        # ----------------------------------

        search_result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=top_k
        )

        results = search_result.points

        # ----------------------------------
        # Convert results into dictionaries
        # ----------------------------------

        formatted_results = []

        for result in results:

            payload = result.payload or {}

            formatted_results.append({
                "score": float(result.score),

                "chunk_id": payload.get(
                    "chunk_id",
                    "unknown"
                ),

                "source_url": payload.get(
                    "source_url",
                    "unknown"
                ),

                "text": payload.get(
                    "text",
                    ""
                ),

                "page_id": payload.get(
                    "page_id",
                    "unknown"
                ),

                "chunk_index": payload.get(
                    "chunk_index",
                    0
                )
            })

        return formatted_results

    finally:

        # ----------------------------------
        # IMPORTANT:
        # Explicitly close Qdrant
        # ----------------------------------

        if client is not None:

            try:
                client.close()

            except Exception:
                pass


# ==========================================
# Standalone testing
# ==========================================

if __name__ == "__main__":

    print("========================================")
    print("AKLM RETRIEVAL SYSTEM")
    print("========================================")

    question = input(
        "\nAsk a question about the website:\n> "
    ).strip()

    if not question:

        print(
            "\n❌ Query cannot be empty."
        )

        raise SystemExit


    print(
        "\n🔎 Retrieving relevant information..."
    )

    results = retrieve(
        question,
        top_k=5
    )

    print(
        f"✅ Retrieved {len(results)} result(s)"
    )


    print("\n========================================")
    print("RETRIEVAL RESULTS")
    print("========================================")


    if not results:

        print(
            "\n❌ No relevant information found."
        )

    else:

        for i, result in enumerate(
            results,
            start=1
        ):

            print(
                f"\nResult #{i}"
            )

            print("----------------------------------------")

            print(
                "Similarity Score:",
                round(
                    result["score"],
                    4
                )
            )

            print(
                "Chunk ID:",
                result["chunk_id"]
            )

            print(
                "Source:",
                result["source_url"]
            )

            print("\nRetrieved Text:\n")

            print(
                result["text"]
            )

    print("\n========================================")

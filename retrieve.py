"""
Retrieval.

Thin wrapper around aklm_lib.retrieve (Gemini query embedding, collection
aklm_live). The actual implementation lives in aklm_lib.
"""

import aklm_lib


def retrieve(query, top_k=5):
    return aklm_lib.retrieve(query, top_k=top_k)


if __name__ == "__main__":

    print("=" * 40)
    print("AKLM RETRIEVAL SYSTEM")
    print("=" * 40)

    question = input("\nAsk a question about the website:\n> ").strip()

    if not question:
        print("\nQuery cannot be empty.")
        raise SystemExit

    print("\nRetrieving relevant information...")

    results = retrieve(question, top_k=5)

    print(f"Retrieved {len(results)} result(s)")

    if not results:
        print("\nNo relevant information found.")
    else:
        for i, result in enumerate(results, start=1):
            print(f"\nResult #{i}")
            print("-" * 40)
            print("Similarity Score:", round(result["score"], 4))
            print("Chunk ID:", result["chunk_id"])
            print("Source:", result["source_url"])
            print("\nRetrieved Text:\n")
            print(result["text"])

"""
Grounded answer generation.

Thin wrapper around aklm_lib.answer_question (Gemini, with model fallback).
Kept as a module because api.py imports MODEL_NAME and generate_answer from it.
"""

import aklm_lib


MODEL_NAME = aklm_lib.GEN_MODELS[0]

build_context = aklm_lib.build_context


def generate_answer(question, results):
    return aklm_lib.answer_question(question, results)


if __name__ == "__main__":

    from retrieve import retrieve

    print("=" * 40)
    print("AKLM AI ANSWER GENERATION")
    print("=" * 40)

    question = input("\nAsk a question about the website:\n> ").strip()

    if not question:
        print("\nQuestion cannot be empty.")
        raise SystemExit

    print("\nRetrieving relevant information...")

    results = retrieve(question, top_k=5)

    print(f"Retrieved {len(results)} result(s)")

    for i, result in enumerate(results, start=1):
        print(f"   Result {i}: {result['score']:.4f}")

    print("\nGenerating AI answer...")

    answer = generate_answer(question, results)

    print("\n" + "=" * 40)
    print("AKLM FINAL ANSWER")
    print("=" * 40)
    print(answer)
    print("=" * 40)

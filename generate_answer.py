from pathlib import Path
import os

from dotenv import load_dotenv
from google import genai


# ==========================================
# 1. Configuration
# ==========================================

QDRANT_PATH = "qdrant_storage"
MODEL_NAME = "gemini-3.6-flash"

TOP_K = 5


# ==========================================
# 2. Load environment variables
# ==========================================

env_path = Path(__file__).parent / ".env"

load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env"
    )


# ==========================================
# 3. Initialize Gemini
# ==========================================

client = genai.Client(
    api_key=api_key
)


# ==========================================
# 4. Build context from retrieved results
# ==========================================

def build_context(results):

    if not results:
        return "No relevant website information was retrieved."

    context_parts = []

    for i, result in enumerate(results, start=1):

        score = result.get("score", 0)

        text = result.get(
            "text",
            ""
        )

        source = result.get(
            "source_url",
            "unknown"
        )

        chunk_id = result.get(
            "chunk_id",
            "unknown"
        )

        context_parts.append(
            f"""
--- Retrieved Source {i} ---

Chunk ID:
{chunk_id}

Similarity score:
{score:.4f}

Source URL:
{source}

Website content:
{text}

--- End Source {i} ---
"""
        )

    return "\n".join(context_parts)


# ==========================================
# 5. Generate grounded answer
# ==========================================

def generate_answer(question, results):

    context = build_context(results)

    prompt = f"""
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

RULE 1 — USE ONLY THE RETRIEVED INFORMATION

Do not use outside knowledge.

Do not invent facts.

Do not assume information that is not supported by
the retrieved website content.


RULE 2 — DIRECT FACTS

If the answer is explicitly stated in the website
information, answer it directly.

Example:

Website:
"Infosys - 160+ Offers"

Question:
"How many offers did Infosys provide?"

Answer:
"Infosys provided 160+ offers."


RULE 3 — COUNTING INFORMATION

If the user asks how many items are listed and the
retrieved content contains a clear list, count the items.

Example:

Website lists:

Infosys
Capgemini
KPIT
Tech Mahindra

Question:
"How many recruiters are listed?"

Answer:
"The website lists 4 recruiters."


RULE 4 — REASONABLE INFERENCE

If the answer is not explicitly stated but can be
reasonably calculated or inferred from the retrieved
information, you MAY make the inference.

However, clearly distinguish the inference from an
explicit website statement.

Example:

Question:
"How many companies are listed for placements?"

Website:
The "Our Top Recruiters" section lists 8 companies.

Good answer:

"Based on the website, 8 companies are listed under
'Our Top Recruiters.' This suggests that 8 recruiting
companies are currently listed on the website.

However, the website does not explicitly state that
all 8 are confirmed for the upcoming campus placement."


RULE 5 — DO NOT OVER-INFER

Do NOT convert an inference into a confirmed fact.

For example, if the website lists companies under
"Top Recruiters", do NOT automatically say:

"8 companies are confirmed to visit ADCET."

Instead say:

"The website lists 8 companies under its Top Recruiters
section, but it does not explicitly state that these
companies are confirmed for the upcoming placement."


RULE 6 — CALCULATIONS

You may perform simple calculations using information
contained in the retrieved website content.

For example:

If the website says:

Infosys: 160+
Capgemini: 130+

Question:
"What is the total?"

You may calculate:

"At least 290 offers based on the listed figures."

Be careful with "+" values. Do not treat "160+" as exactly
160 when calculating a total.


RULE 7 — MISSING INFORMATION

If the retrieved information does not contain enough
evidence to answer the question, say:

"I couldn't find that information on the website."

You may briefly explain what related information WAS found
if it is useful.


RULE 8 — PARTIAL INFORMATION

If the retrieved information partially answers the question,
provide the available information and clearly state what
is missing.

Example:

"The website lists 8 top recruiters, but it does not provide
a confirmed count of companies participating in the upcoming
campus placement."


RULE 9 — SOURCE TRANSPARENCY

When useful, mention that the answer is based on the retrieved
website information.

Do not fabricate citations, URLs, dates, or page numbers.


RULE 10 — BE CONCISE

Give a clear, natural answer.

Do not explain the entire RAG process to the user.

Do not mention embeddings, vector databases, Qdrant,
similarity scores, or internal implementation details
unless explicitly asked.


==================================================
IMPORTANT
==================================================

The distinction between these statements is critical:

"Website explicitly says X."

versus

"Based on the website information, we can infer X."

Never present an inference as an explicit website fact.


==================================================
FINAL ANSWER
==================================================
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    if not response.text:
        return "I couldn't generate an answer from the available website information."

    return response.text.strip()


# ==========================================
# 6. Interactive application
# ==========================================

if __name__ == "__main__":

    from retrieve import retrieve

    print("========================================")
    print("AKLM AI ANSWER GENERATION")
    print("========================================")

    question = input(
        "\nAsk a question about the website:\n> "
    ).strip()

    if not question:

        print(
            "\n❌ Question cannot be empty."
        )

        raise SystemExit


    # ======================================
    # Retrieval
    # ======================================

    print(
        "\n🔎 Retrieving relevant information..."
    )

    try:

        results = retrieve(
            question,
            top_k=TOP_K
        )

    except Exception as e:

        print(
            "\n❌ Retrieval failed:"
        )

        print(e)

        raise SystemExit(1)


    print(
        f"✅ Retrieved {len(results)} result(s)"
    )


    # ======================================
    # Show retrieval scores
    # ======================================

    for i, result in enumerate(
        results,
        start=1
    ):

        print(
            f"   Result {i}: "
            f"{result['score']:.4f}"
        )


    # ======================================
    # Generate answer
    # ======================================

    print(
        "\n🤖 Generating AI answer..."
    )

    try:

        answer = generate_answer(
            question,
            results
        )

    except Exception as e:

        print(
            "\n❌ Answer generation failed:"
        )

        print(e)

        raise SystemExit(1)


    # ======================================
    # Display final answer
    # ======================================

    print("\n========================================")
    print("AKLM FINAL ANSWER")
    print("========================================")

    print(answer)

    print("\n========================================")

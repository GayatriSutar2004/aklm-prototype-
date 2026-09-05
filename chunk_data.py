from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json


# =======================================
# 1. Configure chunking
# =======================================

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=[
        "\n\n",
        "\n",
        ". ",
        " ",
        ""
    ]
)


# =======================================
# 2. Find scraped Markdown files
# =======================================

scraped_dir = Path("scraped_data")

if not scraped_dir.exists():
    raise RuntimeError(
        "scraped_data folder not found. Run testCrawler.py first."
    )

files = list(scraped_dir.glob("*.md"))

if not files:
    raise RuntimeError(
        "No Markdown files found inside scraped_data."
    )

print(f"Found {len(files)} scraped pages.")


# =======================================
# 3. Create chunks
# =======================================

all_chunks = []

valid_pages = 0
rejected_pages = 0


for file in files:

    print(f"\nProcessing: {file.name}")

    # -----------------------------------
    # Read Markdown
    # -----------------------------------

    content = file.read_text(encoding="utf-8")

    # -----------------------------------
    # Extract URL
    # -----------------------------------

    lines = content.splitlines()

    if lines and lines[0].startswith("URL:"):
        source_url = lines[0].replace("URL:", "", 1).strip()
        actual_content = "\n".join(lines[2:])
    else:
        source_url = "unknown"
        actual_content = content

    # -----------------------------------
    # Check for 404 page
    # -----------------------------------

    normalized_content = actual_content.lower().strip()

    is_404 = (
        normalized_content.startswith("# page not found")
        or normalized_content.startswith("**404**")
        or "**404**: not_found" in normalized_content
        or "404: not_found" in normalized_content
        or "code: `not_found`" in normalized_content
        or "looks like you’ve followed a broken link" in normalized_content
        or "looks like you've followed a broken link" in normalized_content
        or "error: not found" in normalized_content
    )

    if is_404:

        print("❌ REJECTED - 404 page")
        print(f"   URL: {source_url}")

        rejected_pages += 1
        continue

    # -----------------------------------
    # Ignore empty pages
    # -----------------------------------

    if not actual_content.strip():

        print("❌ REJECTED - empty page")
        print(f"   URL: {source_url}")

        rejected_pages += 1
        continue

    valid_pages += 1

    # -----------------------------------
    # Generate page ID
    # -----------------------------------

    page_id = file.stem

    # -----------------------------------
    # Split into chunks
    # -----------------------------------

    chunks = text_splitter.split_text(actual_content)

    print(f"✅ Valid page")
    print(f"   URL: {source_url}")
    print(f"   Created {len(chunks)} chunks.")

    # -----------------------------------
    # Add metadata
    # -----------------------------------

    for i, chunk_text in enumerate(chunks):

        chunk_id = f"{page_id}_chunk_{i}"

        all_chunks.append({
            "id": chunk_id,

            "text": chunk_text,

            "metadata": {
                "source_url": source_url,
                "page_id": page_id,
                "chunk_index": i,
                "total_chunks_in_page": len(chunks)
            }
        })


# =======================================
# 4. Save chunks
# =======================================

output_file = Path("chunks.json")

with open(output_file, "w", encoding="utf-8") as f:

    json.dump(
        all_chunks,
        f,
        indent=2,
        ensure_ascii=False
    )


# =======================================
# 5. Print summary
# =======================================

print("\n======================================")
print("CHUNKING COMPLETE")
print("======================================")

print(f"Pages found     : {len(files)}")
print(f"Valid pages     : {valid_pages}")
print(f"Rejected pages  : {rejected_pages}")
print(f"Total chunks    : {len(all_chunks)}")
print(f"Output file     : {output_file}")

print("\n======================================")
print("FIRST CHUNK")
print("======================================")

if all_chunks:

    print("ID:")
    print(all_chunks[0]["id"])

    print("\nSource:")
    print(all_chunks[0]["metadata"]["source_url"])

    print("\nText:")
    print("--------------------------------------")
    print(all_chunks[0]["text"])
    print("--------------------------------------")

else:

    print("No valid chunks were created.")

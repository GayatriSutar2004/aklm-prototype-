"""
AKLM single-entry pipeline.

One command for the whole crawl -> chunk -> embed -> store workflow, replacing
the need to run testCrawler.py / chunk_data.py / create_embeddings.py /
store_embeddings.py by hand.

Modes
-----
  --mode full     Rebuild the whole index (recreate collection, store everything).
  --mode update   AKLM lifecycle update: only re-embed new/changed chunks and
                  remove stale ones (content-hash diff against Qdrant).

Extras
------
  --sync-live     Rebuild the live bot's api/vectors.json and push to adcetportal.
  --no-crawl      Reuse existing scraped_data/ (skip Firecrawl).
  --query "..."   Retrieve + answer a question after the pipeline runs.

Examples
--------
  python run_pipeline.py --mode full
  python run_pipeline.py --mode update
  python run_pipeline.py --mode update --sync-live
  python run_pipeline.py --mode update --no-crawl --query "How many intake seats?"
"""

import argparse
import sys

import aklm_lib


def parse_args():

    parser = argparse.ArgumentParser(
        description="AKLM crawl -> chunk -> embed -> store pipeline"
    )

    parser.add_argument(
        "--mode",
        choices=["full", "update"],
        required=True,
        help="full = rebuild everything; update = selective lifecycle update"
    )

    parser.add_argument(
        "--no-crawl",
        action="store_true",
        help="Reuse existing scraped_data instead of crawling the site"
    )

    parser.add_argument(
        "--sync-live",
        action="store_true",
        help="Rebuild api/vectors.json and push to the adcetportal repo"
    )

    parser.add_argument(
        "--repo",
        default=None,
        help="Path to the adcetportal clone (overrides ADCETPORTAL_REPO)"
    )

    parser.add_argument(
        "--url",
        default=aklm_lib.SITE_URL,
        help="Site URL to crawl (default: the live ADCET portal)"
    )

    parser.add_argument(
        "--query",
        default=None,
        help="After the pipeline, run this question through retrieve + answer"
    )

    return parser.parse_args()


def step(number, title):

    print("\n" + "=" * 44)
    print(f"STEP {number}: {title}")
    print("=" * 44)


def main():

    args = parse_args()

    print("=" * 44)
    print(f"AKLM PIPELINE  (mode: {args.mode})")
    print("=" * 44)

    # --------------------------------------
    # 1. Acquire pages
    # --------------------------------------

    if args.no_crawl:

        print("\n[1/4] Skipping crawl (--no-crawl).")

        if not aklm_lib.SCRAPED_DIR.exists():
            print("ERROR: scraped_data/ does not exist; cannot skip crawl.")
            return 1

    else:

        step(1, "CRAWL")

        aklm_lib.crawl_site(url=args.url)

    # --------------------------------------
    # 2. Chunk
    # --------------------------------------

    step(2, "CHUNK")

    chunks = aklm_lib.build_chunks()

    if not chunks:
        print("ERROR: no chunks produced; aborting.")
        return 1

    # --------------------------------------
    # 3. Embed + store
    # --------------------------------------

    step(3, f"EMBED + STORE ({args.mode})")

    if args.mode == "full":
        aklm_lib.store_full(chunks)
    else:
        aklm_lib.store_update(chunks)

    # --------------------------------------
    # 4. Sync live (optional)
    # --------------------------------------

    if args.sync_live:

        step(4, "SYNC LIVE BOT")

        aklm_lib.sync_live(chunks, repo_path=args.repo)

    # --------------------------------------
    # Optional query test
    # --------------------------------------

    if args.query:

        print("\n" + "=" * 44)
        print("QUERY TEST")
        print("=" * 44)

        print(f"\nQ: {args.query}")

        results = aklm_lib.retrieve(args.query, top_k=5)

        print(f"\nRetrieved {len(results)} result(s):")

        for i, result in enumerate(results, start=1):
            print(
                f"   {i}. score={result['score']:.4f} "
                f"[{result['chunk_id']}]"
            )

        if results:

            print("\nAnswer:")

            try:
                print(aklm_lib.answer_question(args.query, results))
            except Exception as e:
                print(f"(answer generation failed: {e})")

    print("\n" + "=" * 44)
    print("PIPELINE COMPLETE")
    print("=" * 44)

    return 0


if __name__ == "__main__":
    sys.exit(main())

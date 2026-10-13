"""
Step 1 - Crawl.

Thin wrapper around aklm_lib.crawl_site so the crawl step can still be run on
its own. The actual implementation lives in aklm_lib (shared with
run_pipeline.py).
"""

import aklm_lib


print("=" * 40)
print("AKLM STEP 1: CRAWL")
print("=" * 40)

count = aklm_lib.crawl_site()

print(f"\nCrawl finished: {count} page(s) saved to scraped_data/.")

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
from firecrawl import Firecrawl

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("FIRECRAWL_API_KEY")

if not api_key:
    raise RuntimeError("FIRECRAWL_API_KEY not found")

# Initialize Firecrawl
app = Firecrawl(api_key=api_key)

print("Starting website crawl...")

# ---------------------------------------
# Crawl website
# ---------------------------------------

try:

    result = app.crawl(
        url="https://adcetportal.vercel.app/",
        max_age=0
    )

except Exception as e:

    error_message = str(e).lower()

    if (
        "credit" in error_message
        or "credits" in error_message
        or "quota" in error_message
        or "limit" in error_message
    ):
        print("\n======================================")
        print("LIMITS OF FREE CREDITS EXCEEDED")
        print("Your Firecrawl account has run out of")
        print("available credits.")
        print("Please wait for your credits to reset")
        print("or upgrade your Firecrawl plan.")
        print("======================================\n")

    else:
        print("\nFirecrawl error:")
        print(e)

    raise SystemExit


print("Status:", result.status)
print("Pages found:", result.total)
print("Pages completed:", result.completed)

# ---------------------------------------
# Save scraped pages
# ---------------------------------------

output_dir = Path("scraped_data")

# Remove old scraped data
if output_dir.exists():
    shutil.rmtree(output_dir)

# Create fresh folder
output_dir.mkdir()

for i, document in enumerate(result.data):

    url = document.metadata.url
    markdown = document.markdown

    filename = output_dir / f"page_{i+1}.md"

    with open(filename, "w", encoding="utf-8") as f:

        f.write(f"URL: {url}\n\n")
        f.write(markdown or "")

    print(f"Saved: {filename}")


print("\nCrawling finished!")
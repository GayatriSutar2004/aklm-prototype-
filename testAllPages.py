import os
from pathlib import Path
from dotenv import load_dotenv

from firecrawl import FirecrawlApp

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("FIRECRAWL_API_KEY")

if not api_key:
    raise RuntimeError("FIRECRAWL_API_KEY not found")

# Initialize client
app = FirecrawlApp(api_key=api_key)

base_url = "https://adcetportal.vercel.app"

pages = [
    "/",
    "/about",
    "/courses",
    "/faculty",
    "/admissions",
    "/notices",
    "/faq",
    "/contact"
]

for path in pages:
    url = base_url + path

    print("\n========================================")
    print("Testing:", url)
    print("========================================")

    try:
        # Pass formats directly as a list keyword argument
        result = app.scrape_url(
            url,
            formats=["markdown"]
        )

        # Handle object response or dictionary response safely
        if isinstance(result, dict):
            metadata = result.get("metadata", {})
            status = metadata.get("statusCode") or metadata.get("status_code")
            cache = metadata.get("cacheState", "N/A")
            title = metadata.get("title") or metadata.get("pageTitle", "N/A")
            markdown = result.get("markdown", "")
        else:
            metadata = getattr(result, "metadata", None)
            status = getattr(metadata, "status_code", getattr(metadata, "statusCode", None)) if metadata else None
            cache = getattr(metadata, "cache_state", "N/A") if metadata else "N/A"
            title = getattr(metadata, "title", "N/A") if metadata else "N/A"
            markdown = getattr(result, "markdown", "") or ""

        print("Status :", status)
        print("Cache  :", cache)
        print("Title  :", title)

        if status == 200 or markdown:
            print("SUCCESS")
            print("Characters:", len(markdown))
            print("Preview:")
            print(markdown[:300])
        else:
            print("FAILED")

    except Exception as e:
        print("ERROR:", type(e).__name__)
        print(e)
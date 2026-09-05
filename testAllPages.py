import os
from pathlib import Path
from dotenv import load_dotenv

from firecrawl import Firecrawl
from firecrawl.types import ScrapeOptions


env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("FIRECRAWL_API_KEY")

if not api_key:
    raise RuntimeError("FIRECRAWL_API_KEY not found")


app = Firecrawl(api_key=api_key)

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


options = ScrapeOptions(
    formats=["markdown"],
    max_age=0
)


for path in pages:

    url = base_url + path

    print("\n========================================")
    print("Testing:", url)
    print("========================================")

    try:

        result = app.scrape(
            url,
            scrape_options=options
        )

        status = result.metadata.status_code
        cache = result.metadata.cache_state
        title = result.metadata.title

        print("Status :", status)
        print("Cache  :", cache)
        print("Title  :", title)

        if status == 200:
            print("SUCCESS")

            text = result.markdown or ""

            print("Characters:", len(text))
            print("Preview:")
            print(text[:300])

        else:
            print("FAILED")
            print(result.markdown)

    except Exception as e:

        print("ERROR:", type(e).__name__)
        print(e)
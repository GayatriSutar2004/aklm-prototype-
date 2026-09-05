import os
from pathlib import Path
from dotenv import load_dotenv
from firecrawl import Firecrawl

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("FIRECRAWL_API_KEY")

if not api_key:
    raise RuntimeError("FIRECRAWL_API_KEY not found")

app = Firecrawl(api_key=api_key)

url = "https://adcetportal.vercel.app/about"

print("Testing direct Firecrawl scrape...")
print("URL:", url)
print("------------------------------------")

try:

    result = app.scrape(
        url,
        formats=["markdown"],
        max_age=0
    )

    print("\nRESULT OBJECT:")
    print(result)

    print("\n------------------------------------")

    print("STATUS:")
    print(result.metadata.status_code)

    print("\nCACHE:")
    print(result.metadata.cache_state)

    print("\nMARKDOWN:")
    print(result.markdown or "NO MARKDOWN")

except Exception as e:

    print("\nFIRECRAWL ERROR:")
    print(type(e).__name__)
    print(e)
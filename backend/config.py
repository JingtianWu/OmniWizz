import os
from dotenv import load_dotenv

load_dotenv()  # Ensure .env is loaded before using os.getenv

TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"  # default to production mode
print("🚦 TEST_MODE =", TEST_MODE)

# API keys for hosted services used when TEST_MODE is disabled
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")        # GPT-4.1-mini
PIAPI_KEY = os.getenv("PIAPI_KEY", "")                  # DiffRhythm cloud inference
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")      # SerpAPI for image search
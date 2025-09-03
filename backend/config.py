import os
from dotenv import load_dotenv

load_dotenv()  # Ensure .env is loaded before using os.getenv

TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"  # default to production mode
print("🚦 TEST_MODE =", TEST_MODE)

# API keys for hosted services used when TEST_MODE is disabled
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")        # GPT-4.1-mini
# Support both common casings for the Beatoven key to avoid auth issues
BEATOVEN_API_KEY = os.getenv("BEATOVEN_API_KEY") or os.getenv("Beatoven_API_KEY", "")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")      # SerpAPI for image search
MUSIC_AI_API_KEY = os.getenv("MUSIC_AI_API_KEY", "")    # Music AI chord transcription
MUSICAI_CHORD_WORKFLOW = os.getenv("MUSICAI_CHORD_WORKFLOW", "untitled-workflow-1fe2713")

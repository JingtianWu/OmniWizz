import os
from dotenv import load_dotenv

load_dotenv()  # Ensure .env is loaded before using os.getenv

TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"  # default to production mode
print("🚦 TEST_MODE =", TEST_MODE)

# API keys for hosted services used when TEST_MODE is disabled
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")        # GPT-4.1-mini
PIAPI_KEY = os.getenv("PIAPI_KEY", "")                  # Ace Step cloud inference
NANO_BANANA_API_KEY = os.getenv("NANO_BANANA_API_KEY", "")  # Nano Banana image generation
MUSIC_AI_API_KEY = os.getenv("MUSIC_AI_API_KEY", "")    # Music AI chord transcription
MUSICAI_CHORD_WORKFLOW = os.getenv("MUSICAI_CHORD_WORKFLOW", "untitled-workflow-1fe2713")


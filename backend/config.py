import os
from dotenv import load_dotenv

load_dotenv()

TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"
print("TEST_MODE =", TEST_MODE)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PIAPI_KEY = os.getenv("PIAPI_KEY", "")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
MUSIC_AI_API_KEY = os.getenv("MUSIC_AI_API_KEY", "")

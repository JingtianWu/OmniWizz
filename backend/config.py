import os

TEST_MODE = os.getenv("TEST_MODE", "True").lower() == "true"  # set to False for full production

# API keys for hosted services used when TEST_MODE is disabled
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")        # GPT-4.1-nano
PIAPI_KEY = os.getenv("PIAPI_KEY", "")   # DiffRhythm cloud inference


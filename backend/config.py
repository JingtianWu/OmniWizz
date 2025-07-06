import os

TEST_MODE = True  # set to False for full production

# API keys for hosted services used when TEST_MODE is disabled
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")        # GPT-4.1-nano
DIFFRHYTHM_API_KEY = os.getenv("DIFFRHYTHM_API_KEY", "")   # DiffRhythm cloud inference


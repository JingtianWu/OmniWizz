import sys
import types
from pathlib import Path

# Ensure repository root and backend package are on sys.path for absolute imports
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Provide a lightweight stub for google.genai to avoid import errors during tests
google = types.ModuleType("google")
genai = types.ModuleType("genai")


class DummyClient:
    def __init__(self, api_key=None):
        pass


genai.Client = DummyClient
google.genai = genai
sys.modules.setdefault("google", google)
sys.modules.setdefault("google.genai", genai)

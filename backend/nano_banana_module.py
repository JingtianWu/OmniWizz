import os
import base64
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from google import genai

API_KEY = os.getenv("NANO_BANANA_API_KEY")
MODEL_NAME = "gemini-2.5-flash-image-preview"

client = genai.Client(api_key=API_KEY) if API_KEY else None


def slugify(text: str) -> str:
    """Return a filesystem-safe version of ``text``."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return slug or "image"


def _generate_single(prompt: str, idx: int, out_dir: Path) -> str | None:
    response = client.models.generate_content(model=MODEL_NAME, contents=[prompt])
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None and str(getattr(part.inline_data, "mime_type", "")).startswith("image/"):
            data = part.inline_data.data
            if isinstance(data, str):
                try:
                    data = base64.b64decode(data)
                except Exception:
                    continue
            try:
                image = Image.open(BytesIO(data))
                path = out_dir / f"{slugify(prompt)}_{idx}.png"
                image.save(path)
                return str(path)
            except UnidentifiedImageError:
                return None
    return None

def generate_images_for_entity(entity: str, num: int = 1, out_dir: Path | None = None, parallel: int = 8):
    """Generate `num` images for the text `entity` using the Nano Banana API."""
    if client is None:
        raise RuntimeError("NANO_BANANA_API_KEY not set in environment")
    out_dir = out_dir or Path(".")
    paths: list[str] = []

    with ThreadPoolExecutor(max_workers=min(num, parallel)) as ex:
        futures = [ex.submit(_generate_single, entity, i, out_dir) for i in range(num)]
        for future in as_completed(futures):
            try:
                path = future.result()
            except Exception:
                continue
            if path:
                paths.append(path)
    return paths


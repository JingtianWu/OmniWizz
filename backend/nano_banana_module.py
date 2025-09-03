import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

from PIL import Image
from google import genai

API_KEY = os.getenv("NANO_BANANA_API_KEY")
MODEL_NAME = "gemini-2.5-flash-image-preview"

client = genai.Client(api_key=API_KEY) if API_KEY else None

def _generate_single(prompt: str, idx: int, out_dir: Path) -> str | None:
    response = client.models.generate_content(model=MODEL_NAME, contents=[prompt])
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            path = out_dir / f"{prompt.replace(' ', '_')}_{idx}.png"
            image.save(path)
            return str(path)
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
            path = future.result()
            if path:
                paths.append(path)
    return paths


import os
from pathlib import Path
from io import BytesIO
from PIL import Image
from google import genai

API_KEY = os.getenv("NANO_BANANA_API_KEY")
MODEL = "gemini-2.5-flash-image-preview"

def fetch_images_for_entity(entity: str, num: int = 1, out_dir: Path = None):
    """Generate images for `entity` using Gemini and save to `out_dir`.

    Args:
        entity: Text prompt describing the desired image.
        num: Number of images to generate.
        out_dir: Directory to save generated images. Defaults to current directory.

    Returns:
        List of file paths to generated images.
    """
    if not API_KEY:
        raise RuntimeError("NANO_BANANA_API_KEY not set in environment")
    out_dir = out_dir or Path('.')
    out_dir.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=API_KEY)
    paths = []
    prompt = entity
    for idx in range(num):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=[prompt],
            )
            parts = response.candidates[0].content.parts
            for part in parts:
                if getattr(part, "inline_data", None):
                    image = Image.open(BytesIO(part.inline_data.data))
                    fname = f"{entity.replace(' ', '_')}_{idx}.png"
                    image.save(out_dir / fname)
                    paths.append(str(out_dir / fname))
                    break
        except Exception:
            continue
    return paths

import base64
from pathlib import Path
import requests

from config import OPENAI_API_KEY

GEN_ENDPOINT = "https://api.openai.com/v1/images/generations"


def generate_images_for_entity(entity: str, num: int = 1, out_dir: Path | None = None):
    """Generate images using OpenAI based on `entity` and save them locally.

    Args:
        entity: Text prompt used for image generation.
        num: Number of images to generate.
        out_dir: Directory to save generated images. Defaults to current directory.

    Returns:
        List of file paths for the generated images.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set in environment")

    out_dir = out_dir or Path(".")
    payload = {"model": "gpt-image-1", "prompt": entity, "n": num, "size": "1024x1024"}
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

    res = requests.post(GEN_ENDPOINT, headers=headers, json=payload, timeout=60)
    res.raise_for_status()
    data = res.json().get("data", [])
    paths: list[str] = []
    for idx, item in enumerate(data):
        b64 = item.get("b64_json")
        if not b64:
            continue
        image_bytes = base64.b64decode(b64)
        fname = f"{entity.replace(' ', '_')}_{idx}.png"
        local = out_dir / fname
        local.write_bytes(image_bytes)
        paths.append(str(local))

    return paths

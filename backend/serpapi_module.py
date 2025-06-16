import os, requests, io
from pathlib import Path
from PIL import Image

API_KEY = os.getenv("SERPAPI_API_KEY")
SEARCH_URL = "https://serpapi.com/search.json"
ALLOWED_FORMATS = {"jpg", "jpeg", "png", "gif"}

def fetch_images_for_entity(entity: str, num: int = 1, out_dir: Path = None):
    """
    Query SerpAPI for `entity`, download top `num` images into out_dir,
    verify validity, return list of local file paths.
    """
    if not API_KEY:
        raise RuntimeError("SERPAPI_API_KEY not set in environment")
    params = {
        "engine": "google_images",
        "q": entity,
        "api_key": API_KEY,
        "tbm": "isch",
        "ijn": "0"
    }
    res = requests.get(SEARCH_URL, params=params, timeout=10)
    data = res.json().get("images_results", [])[:num]
    paths = []
    for idx, img in enumerate(data):
        img_url = img.get("original") or img.get("thumbnail")
        if not img_url: continue

        # Parse extension
        ext = img_url.split(".")[-1].split("?")[0].lower()
        if ext not in ALLOWED_FORMATS:
            continue

        # Download image content
        try:
            img_data = requests.get(img_url, timeout=10).content

            # Verify valid image
            Image.open(io.BytesIO(img_data)).verify()

            fname = f"{entity.replace(' ', '_')}_{idx}.{ext}"
            local = out_dir / fname
            local.write_bytes(img_data)
            paths.append(str(local))
        except Exception:
            continue

        # Stop after collecting enough valid images
        if len(paths) >= num:
            break

    return paths
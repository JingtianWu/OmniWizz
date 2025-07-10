import requests, io
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36"
}

ALLOWED_FORMATS = {"jpg", "jpeg", "png", "gif"}


def fetch_images_for_entity(entity: str, num: int = 1, out_dir: Path = None):
    """Scrape Google Images for `entity` and download top `num` images."""
    out_dir = out_dir or Path.cwd()
    query = entity.replace(" ", "+")
    url = f"https://www.google.com/search?tbm=isch&q={query}"
    res = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    paths = []
    for img in soup.select("img"):
        img_url = img.get("data-iurl") or img.get("src")
        if not img_url or img_url.startswith("data:"):
            continue

        ext = img_url.split(".")[-1].split("?")[0].lower()
        if ext not in ALLOWED_FORMATS:
            continue

        try:
            img_data = requests.get(img_url, headers=HEADERS, timeout=10).content
            Image.open(io.BytesIO(img_data)).verify()
            fname = f"{entity.replace(' ', '_')}_{len(paths)}.{ext}"
            local = out_dir / fname
            local.write_bytes(img_data)
            paths.append(str(local))
        except Exception:
            continue

        if len(paths) >= num:
            break

    return paths

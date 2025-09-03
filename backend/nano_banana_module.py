# backend/nano_banana_module.py

import os
import re
import base64
import binascii
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import Optional, Union, List

from PIL import Image, UnidentifiedImageError
from google import genai

API_KEY = os.getenv("NANO_BANANA_API_KEY")
MODEL_NAME = "gemini-2.5-flash-image-preview"

client = genai.Client(api_key=API_KEY) if API_KEY else None


def slugify(text: str) -> str:
    """Return a filesystem-safe version of ``text``."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return slug or "image"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, data: bytes) -> None:
    """Write bytes atomically to avoid partial reads by the server/UI."""
    tmp = path.with_suffix(path.suffix + ".part")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _decode_inline_data(raw: Union[str, bytes, bytearray, None]) -> Optional[bytes]:
    """
    Return real image bytes from inline_data.data. Handles:
      - str base64 (optionally data: URIs)
      - ASCII bytes of base64
      - already-binary image bytes
    """
    if raw is None:
        return None

    # Already bytes? Try as real image first; if not, try as ASCII base64.
    if isinstance(raw, (bytes, bytearray)):
        b = bytes(raw)
        try:
            Image.open(BytesIO(b)).verify()
            return b
        except Exception:
            # Might be ASCII base64
            try:
                s = b.decode("ascii")
            except UnicodeDecodeError:
                return None
            try:
                return base64.b64decode(s, validate=True)
            except binascii.Error:
                return None

    # String case (possibly data URI)
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("data:"):
            # Strip data URI prefix: data:<mime>;base64,<payload>
            parts = s.split(",", 1)
            s = parts[1] if len(parts) == 2 else s
        try:
            return base64.b64decode(s, validate=True)
        except binascii.Error:
            return None

    return None


def _generate_single(prompt: str, idx: int, out_dir: Path) -> Optional[str]:
    if client is None:
        raise RuntimeError("NANO_BANANA_API_KEY not set in environment")

    resp = client.models.generate_content(model=MODEL_NAME, contents=[prompt])

    for cidx, cand in enumerate(getattr(resp, "candidates", []) or []):
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", []) or []
        for pidx, part in enumerate(parts):
            inline = getattr(part, "inline_data", None)
            mime: str = (getattr(inline, "mime_type", "") or "").lower()
            raw = getattr(inline, "data", None)

            # Must be an image part with data
            if not (mime.startswith("image/") and raw):
                continue

            img_bytes = _decode_inline_data(raw)
            if not img_bytes:
                print(f"[genai] could not decode inline_data (c={cidx} p={pidx}); skipping")
                continue

            # Choose extension from mime (jpg/webp/png…)
            ext = mime.split("/", 1)[1].split(";")[0].replace("jpeg", "jpg")
            ext = re.sub(r"[^a-z0-9]+", "", ext) or "bin"

            slug = slugify(prompt)
            out_file = out_dir / f"{slug}_{idx}.{ext}"
            _atomic_write(out_file, img_bytes)

            # Optional verification (non-fatal)
            try:
                Image.open(BytesIO(img_bytes)).verify()
            except UnidentifiedImageError as e:
                print(f"[genai] PIL verify failed for {out_file}: {e}")

            print(f"[genai] saved -> {out_file} (mime={mime}, bytes={len(img_bytes)})")
            return str(out_file)

    return None


def generate_images_for_entity(
    entity: str,
    num: int = 1,
    out_dir: Optional[Path] = None,
    parallel: int = 8,
) -> List[str]:
    """Generate `num` images for the text `entity` using the Gemini API."""
    if client is None:
        raise RuntimeError("NANO_BANANA_API_KEY not set in environment")

    out_dir = out_dir or Path(".")
    _ensure_dir(out_dir)

    results: List[str] = []
    with ThreadPoolExecutor(max_workers=min(max(1, num), parallel)) as ex:
        futures = [ex.submit(_generate_single, entity, i, out_dir) for i in range(num)]
        for fut in as_completed(futures):
            try:
                p = fut.result()
            except Exception as e:
                print(f"[genai] generation task failed: {e}")
                continue
            if p:
                results.append(p)
    return results

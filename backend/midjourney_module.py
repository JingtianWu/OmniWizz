import time
import requests
from pathlib import Path
from config import TEST_MODE, PIAPI_KEY


def generate_images(prompt: str, out_dir: Path, *, aspect_ratio: str = "1:1", process_mode: str = "turbo") -> list[str]:
    """Call PiAPI Midjourney endpoint to generate an image grid and save it."""
    if TEST_MODE:
        # In test mode just return an empty list; pipeline will copy mock images.
        return []

    payload = {
        "model": "midjourney",
        "task_type": "imagine",
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "process_mode": process_mode,
            "skip_prompt_check": False,
        },
    }
    headers = {"X-API-Key": PIAPI_KEY}

    res = requests.post(
        "https://api.piapi.ai/api/v1/task",
        json=payload,
        headers=headers,
        timeout=60,
    )
    res.raise_for_status()
    resp = res.json()
    task_id = resp.get("data", {}).get("task_id") or resp.get("task_id")
    if not task_id:
        raise RuntimeError("No task_id returned from Midjourney API")

    for _ in range(60):
        stat_res = requests.get(
            f"https://api.piapi.ai/api/v1/task/{task_id}",
            headers=headers,
            timeout=60,
        )
        stat_res.raise_for_status()
        stat = stat_res.json()
        status = stat.get("data", {}).get("status") or stat.get("status")
        if status and status.lower() == "completed":
            output = stat.get("data", {}).get("output", {}) or stat.get("output", {})
            image_urls = output.get("image_urls") or []
            if not image_urls and output.get("image_url"):
                image_urls = [output.get("image_url")]
            if not image_urls:
                works = stat.get("data", {}).get("works") or stat.get("works")
                if works:
                    url = works[0].get("resource", {}).get("resource")
                    if url:
                        image_urls = [url]
            paths = []
            for idx, url in enumerate(image_urls):
                img_res = requests.get(url, timeout=60)
                img_res.raise_for_status()
                ext = url.split(".")[-1].split("?")[0]
                fname = f"midjourney_{idx}.{ext}"
                fp = out_dir / fname
                fp.write_bytes(img_res.content)
                paths.append(str(fp))
            return paths
        if status and status.lower() in {"failed", "error"}:
            raise RuntimeError(f"Midjourney task failed: {status}")
        time.sleep(5)
    raise TimeoutError("Midjourney API timed out")

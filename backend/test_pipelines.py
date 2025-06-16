# test_pipelines.py  – SAFE VERSION (uses test-output/)

import os, json, shutil
from pathlib import Path
from pipeline import generate_music_from_image, generate_tags_from_image

# ---------- configuration ----------
TEST_IMAGE      = Path(__file__).parent / "uploads" / "example.jpg"
TEST_OUT_ROOT   = Path(__file__).parent.parent / "test-output"
IMG_NAME        = TEST_IMAGE.name            # usually "example.jpg"
# ------------------------------------

def clean_test_output():
    if TEST_OUT_ROOT.exists():
        shutil.rmtree(TEST_OUT_ROOT)
    TEST_OUT_ROOT.mkdir(parents=True, exist_ok=True)

def move_run_folder(src_folder: Path):
    dest = TEST_OUT_ROOT / src_folder.name
    shutil.move(str(src_folder), str(dest))
    return dest

def test_generate_tags():
    tags, src_folder = generate_tags_from_image(str(TEST_IMAGE))
    dest = move_run_folder(Path(src_folder))

    print("✅ Tags:", tags)
    assert (dest / IMG_NAME).exists(),    f"Missing {IMG_NAME}"
    assert (dest / "tags.json").exists(), "Missing tags.json"

    with open(dest / "tags.json", "r", encoding="utf-8") as f:
        assert json.load(f) == tags, "tags.json content mismatch"
    print("✅ tags pipeline test passed")

def test_generate_music():
    audio_path = generate_music_from_image(str(TEST_IMAGE))
    dest = move_run_folder(Path(audio_path).parent)

    assert (dest / "audio.wav").exists(),  "Missing audio.wav"
    assert (dest / "lyrics.lrc").exists(), "Missing lyrics.lrc"
    assert (dest / IMG_NAME).exists(),     f"Missing {IMG_NAME}"
    print("✅ music pipeline test passed")

if __name__ == "__main__":
    print("🔎 Cleaning test-output …")
    clean_test_output()

    print("🔬 Running image → tags test …")
    test_generate_tags()

    print("🔬 Running image → music test …")
    test_generate_music()

    print(f"\n🎉 All safe tests passed. Artifacts stored in: {TEST_OUT_ROOT}")
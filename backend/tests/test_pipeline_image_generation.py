from io import BytesIO

from PIL import Image

import backend.pipeline as pipeline


def test_generate_images_processes_all_entities(tmp_path, monkeypatch):
    img = Image.new("RGB", (1, 1), color="blue")
    img_path = tmp_path / "input.png"
    img.save(img_path)
    run_dir = tmp_path / "out"
    run_dir.mkdir()

    entities = ["alpha", "beta", "gamma"]

    class DummyProcessor:
        def __init__(self, *args, **kwargs):
            pass

        def process(self):
            return entities

    monkeypatch.setattr(pipeline, "ImageToVisualEntitiesProcessor", lambda *a, **k: DummyProcessor())
    monkeypatch.setattr(pipeline, "TEST_MODE", False)

    calls = []

    def fake_generate(entity, num, out_dir):
        calls.append((entity, num))
        p = out_dir / f"{entity}.png"
        p.write_bytes(b"")
        return [str(p)]

    monkeypatch.setattr(pipeline, "generate_images_for_entity", fake_generate)

    ents, out_dir, paths = pipeline.generate_images_from_image(str(img_path), run_dir=run_dir)

    assert sorted(calls) == sorted((e, 1) for e in entities)
    expected_paths = {str(run_dir / "images" / f"{e}.png") for e in entities}
    assert set(paths) == expected_paths
    assert ents == entities

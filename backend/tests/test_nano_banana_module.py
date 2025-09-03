import base64
from io import BytesIO
from pathlib import Path

from PIL import Image

import backend.nano_banana_module as nb


class DummyModel:
    def __init__(self, parts):
        self._parts = parts

    def generate_content(self, model, contents):
        class Resp:
            def __init__(self, parts):
                self.candidates = [self.Candidate(parts)]

            class Candidate:
                def __init__(self, parts):
                    self.content = self.Content(parts)

                class Content:
                    def __init__(self, parts):
                        self.parts = parts

        return Resp(self._parts)


class DummyClient:
    def __init__(self, parts):
        self.models = DummyModel(parts)


def test_generate_single_skips_invalid_inline_data(tmp_path, monkeypatch):
    part = type("Part", (), {"inline_data": type("InlineData", (), {"data": b"nope", "mime_type": "text/plain"})(), "text": None})()
    monkeypatch.setattr(nb, "client", DummyClient([part]))
    assert nb._generate_single("prompt", 0, tmp_path) is None


def test_generate_single_slugifies_prompt(tmp_path, monkeypatch):
    img = Image.new("RGB", (1, 1), color="red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    data = base64.b64encode(buf.getvalue()).decode()
    part = type("Part", (), {"inline_data": type("InlineData", (), {"data": data, "mime_type": "image/png"})(), "text": None})()
    monkeypatch.setattr(nb, "client", DummyClient([part]))
    out = nb._generate_single("he?ll*o:world", 0, tmp_path)
    assert out is not None
    assert Path(out).name == "he_ll_o_world_0.png"

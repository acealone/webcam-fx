from types import SimpleNamespace

import numpy as np

from core.compose import blend
from core.context import Detectors
from core.sound import play


def test_play_missing_file_is_silent(tmp_path):
    play(tmp_path / "does_not_exist.wav")


def test_blend_extremes():
    person = np.full((4, 4, 3), 200, np.uint8)
    bg = np.full((4, 4, 3), 10, np.uint8)
    mask = np.ones((4, 4, 1), np.float32)
    full = blend(person, mask, bg, 1.0)
    assert full.dtype == np.uint8 and (full == 200).all()
    assert (blend(person, mask, bg, 0.0) == 10).all()


def _face_result(box):
    if box is None:
        return SimpleNamespace(detections=None)
    xmin, ymin, w, h = box
    rbb = SimpleNamespace(xmin=xmin, ymin=ymin, width=w, height=h)
    return SimpleNamespace(detections=[SimpleNamespace(location_data=SimpleNamespace(relative_bounding_box=rbb))])


def test_face_uses_cache_when_detection_missing():
    results = iter([_face_result((0.1, 0.2, 0.3, 0.4)), _face_result(None)])
    det = Detectors(face_model=SimpleNamespace(process=lambda rgb: next(results)))
    rgb = np.zeros((4, 4, 3), np.uint8)
    assert det.face(rgb) == (0.1, 0.2, 0.3, 0.4)
    assert det.face(rgb) == (0.1, 0.2, 0.3, 0.4)


def test_play_unplayable_is_silent(tmp_path, monkeypatch):
    import winsound

    def fail(*args):
        raise RuntimeError("Failed to play sound")

    monkeypatch.setattr(winsound, "PlaySound", fail)
    wav = tmp_path / "broken.wav"
    wav.write_bytes(b"RIFF....not really")
    play(wav)


def test_blend_matches_formula_and_is_fast():
    import time
    rng = np.random.default_rng(3)
    person = rng.integers(0, 255, (360, 640, 3), np.uint8)
    bg = rng.integers(0, 255, (360, 640, 3), np.uint8)
    mask = rng.random((360, 640, 1), dtype=np.float32)
    expected = np.clip(person * (mask * 0.7) + bg * (1 - mask * 0.7), 0, 255).astype(np.uint8)
    assert np.abs(blend(person, mask, bg, 0.7).astype(int) - expected).max() <= 1
    blend(person, mask, bg)
    start = time.perf_counter()
    for _ in range(20):
        blend(person, mask, bg)
    assert (time.perf_counter() - start) / 20 < 0.006, "blend runs on every frame and must stay cheap"

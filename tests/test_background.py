import cv2
import numpy as np

from core.background import Background

H, W = 120, 160


def frame(value=100, seed=None):
    if seed is not None:
        return np.random.default_rng(seed).integers(0, 255, (H, W, 3), np.uint8)
    return np.full((H, W, 3), value, np.uint8)


def test_missing_file_unlocked(tmp_path):
    bg = Background(tmp_path / "data" / "background.png", frame())
    assert bg.locked is False
    assert bg.plate.shape == (H, W, 3)


def test_matching_file_loaded_and_locked(tmp_path):
    saved = frame(seed=1)
    path = tmp_path / "background.png"
    cv2.imwrite(str(path), saved)
    bg = Background(path, frame())
    assert bg.locked is True
    assert np.array_equal(bg.plate, saved)


def test_size_mismatch_ignored(tmp_path):
    path = tmp_path / "background.png"
    cv2.imwrite(str(path), np.zeros((10, 10, 3), np.uint8))
    assert Background(path, frame()).locked is False


def test_corrupt_file_ignored(tmp_path):
    path = tmp_path / "background.png"
    path.write_bytes(b"not a png")
    assert Background(path, frame()).locked is False


def test_capture_after_delay_saves_and_locks(tmp_path):
    path = tmp_path / "data" / "background.png"
    bg, new = Background(path, frame()), frame(seed=2)
    bg.start_capture(0.0)
    assert bg.countdown(1.0) == 4.0
    assert bg.update(new, 4.9) is False and bg.locked is False
    assert bg.update(new, 5.0) is True and bg.locked is True
    assert bg.countdown(5.1) is None
    assert np.array_equal(cv2.imread(str(path)), new)


def test_learn_skips_margin_around_person(tmp_path):
    bg = Background(tmp_path / "bg.png", frame(0))
    before = bg.plate.copy()
    mask = np.zeros((H, W, 1), np.float32)
    mask[50:70, 70:90] = 1.0                      # you, in the middle
    bg.learn(frame(255), mask)
    assert (bg.plate[60, 100] == before[60, 100]).all()   # 10 px right of you: inside the margin
    assert (bg.plate[0, 0] == 255).all()                  # far corner: learned


def test_learn_noop_when_locked(tmp_path):
    path = tmp_path / "background.png"
    cv2.imwrite(str(path), frame(7))
    bg = Background(path, frame())
    bg.learn(frame(255), np.zeros((H, W, 1), np.float32))
    assert (bg.plate == 7).all()

from types import SimpleNamespace as NS

import numpy as np
import pytest

from core.plugins import load_effect, load_gesture


@pytest.fixture
def sounds(monkeypatch):
    played = []
    monkeypatch.setattr("core.sound.play", lambda path: played.append(path.name))
    return played


def tear():
    from core.plugins import REPO_ROOT
    import importlib.util
    spec = importlib.util.spec_from_file_location("teleport_effect", REPO_ROOT / "effects/teleport/effect.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.tear


def person(h=480, w=640, rows=slice(380, 480)):
    img = np.random.default_rng(0).integers(0, 255, (h, w, 3), np.uint8)
    m = np.zeros((h, w, 1), np.float32)
    m[rows, 200:440] = 1.0
    return img, m


def test_tear_no_wraparound():
    img, m = person()
    for seed in range(10):
        _, out = tear()(img, m, 1.0, seed)
        assert out[:300].max() == 0, f"seed {seed}: part of you wrapped to the top"


def test_tear_deterministic():
    img, m = person(rows=slice(100, 400))
    a, b = tear()(img, m, 0.6, 42.0), tear()(img, m, 0.6, 42.0)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_sequence_and_sounds(sounds):
    img, m = person(60, 80, slice(10, 50))
    bg = np.zeros_like(img)
    eff = load_effect("teleport", {"fade": 0.35, "gone": 2.5})
    ctx = lambda t: NS(now=t, frame=img, mask=m, bg=bg)
    eff.start(ctx(0.0))
    assert sounds == ["teleport_out.wav"]
    done_at, k = None, 1
    while done_at is None and k < 200:
        t = k / 30
        out, done = eff.render(ctx(t))
        if abs(t - 1.0) < 1e-9:
            assert np.array_equal(out, bg), "while gone, only the background is shown"
        if abs(t - 3.0) < 1e-9:
            assert sounds == ["teleport_out.wav", "teleport_in.wav"]
        if done:
            done_at = t
        k += 1
    assert 3.2 <= done_at <= 3.3
    assert sounds == ["teleport_out.wav", "teleport_in.wav"]


def test_loads_via_plugins():
    assert load_gesture("two_fingers_forehead", {}) is not None
    eff = load_effect("teleport", {"fade": 0.35, "gone": 2.5})
    assert (eff.folder / "teleport_out.wav").is_file()

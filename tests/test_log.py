import importlib.util
from types import SimpleNamespace as NS

import cv2
import numpy as np
import pytest

from core.config import ConfigError
from core.plugins import REPO_ROOT, load_effect

H, W = 360, 640


def module():
    spec = importlib.util.spec_from_file_location("log_effect", REPO_ROOT / "effects/log/effect.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def you():
    frame = np.full((H, W, 3), 200, np.uint8)
    mask = np.zeros((H, W, 1), np.float32)
    mask[120:360, 220:420] = 1.0
    bg = np.full((H, W, 3), 50, np.uint8)
    return frame, mask, bg


clock = {"t": 0.0}


@pytest.fixture
def sounds(monkeypatch):
    played = []
    monkeypatch.setattr("core.sound.play", lambda path: played.append((path.name, clock["t"])))
    return played


def test_make_log_shape_and_alpha():
    img, alpha = module().make_log(200, seed=1)
    assert img.shape[0] == 200 and alpha.shape == img.shape[:2]
    assert abs(img.shape[1] - 64) <= 2                       # about a third as wide as tall
    assert alpha[100, img.shape[1] // 2] > 0.99               # solid wood in the middle
    assert alpha[0, 0] < 0.01                                 # rounded top: corner is empty


def test_timeline_and_sounds(sounds):
    frame, mask, bg = you()
    eff = load_effect("log", {"duration": 3.0, "smoke": 0.6})
    clock["t"] = 0.0
    eff.start(NS(now=0.0, frame=frame, mask=mask, bg=bg))
    done_at, k = None, 1
    while done_at is None and k < 300:
        t = clock["t"] = k / 30
        out, done = eff.render(NS(now=t, frame=frame, mask=mask, bg=bg))
        if k == 60:                                           # t = 2.0: log stands where you were
            assert (out[200, 235] == 50).all(), "you are gone: background where you stood"
            assert not (out[250, 320] == 50).all() and not (out[250, 320] == 200).all(), "log in the middle"
        if k == 123:                                          # t = 4.1
            assert not done
        if done:
            done_at = t
        k += 1
    assert done_at <= 4.25
    names = [n for n, _ in sounds]
    assert names == ["poof.wav", "clonk.wav", "poof.wav"]
    assert sounds[1][1] < 0.6 and sounds[2][1] >= 3.6 - 1e-9


def test_log_png_overrides_drawn_log(tmp_path, monkeypatch):
    monkeypatch.setattr("core.sound.play", lambda path: None)
    red = np.zeros((100, 40, 4), np.uint8)
    red[..., 2], red[..., 3] = 255, 255                      # opaque red BGRA
    cv2.imwrite(str(tmp_path / "log.png"), red)
    frame, mask, bg = you()
    eff = module().Effect({}, tmp_path)
    eff.start(NS(now=0.0, frame=frame, mask=mask, bg=bg))
    out, _ = eff.render(NS(now=2.0, frame=frame, mask=mask, bg=bg))
    assert tuple(out[250, 320]) == (0, 0, 255)


def test_nobody_in_picture_still_works(monkeypatch):
    monkeypatch.setattr("core.sound.play", lambda path: None)
    frame, _, bg = you()
    empty = np.zeros((H, W, 1), np.float32)
    eff = load_effect("log", {})
    eff.start(NS(now=0.0, frame=frame, mask=empty, bg=bg))
    out, done = eff.render(NS(now=2.0, frame=frame, mask=empty, bg=bg))
    assert out.shape == frame.shape and not done


@pytest.mark.parametrize("settings", [{"smoke": 0}, {"duration": -1}, {"duration": "3"}])
def test_bad_settings_rejected(settings):
    with pytest.raises(ConfigError):
        load_effect("log", settings)


def test_loads_via_plugins():
    eff = load_effect("log", {})
    assert (eff.folder / "poof.wav").is_file() and (eff.folder / "clonk.wav").is_file()


@pytest.mark.perf
def test_render_fast_enough(monkeypatch):
    import time
    monkeypatch.setattr("core.sound.play", lambda path: None)
    frame, mask, bg = you()
    eff = load_effect("log", {})
    eff.start(NS(now=0.0, frame=frame, mask=mask, bg=bg))
    for t in (0.3, 2.0, 3.9):
        eff.render(NS(now=t, frame=frame, mask=mask, bg=bg))
        start = time.perf_counter()
        for _ in range(10):
            eff.render(NS(now=t, frame=frame, mask=mask, bg=bg))
        assert (time.perf_counter() - start) / 10 < 0.025, f"too slow at t={t}"

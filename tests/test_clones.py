import importlib.util
from types import SimpleNamespace as NS

import numpy as np
import pytest

from core.config import ConfigError
from core.plugins import REPO_ROOT, load_effect

H, W = 360, 640


def module():
    spec = importlib.util.spec_from_file_location("clones_effect", REPO_ROOT / "effects/clones/effect.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def you():
    frame = np.random.default_rng(0).integers(1, 255, (H, W, 3), np.uint8)
    mask = np.zeros((H, W, 1), np.float32)
    mask[100:360, 280:360] = 1.0
    return frame, mask


@pytest.fixture
def sounds(monkeypatch):
    played = []
    monkeypatch.setattr("core.sound.play", lambda path: played.append((path.name, clock["t"])))
    return played


clock = {"t": 0.0}


def test_place_clone_offsets_and_scales():
    frame = np.zeros((H, W, 3), np.uint8)
    mask = np.zeros((H, W, 1), np.float32)
    mask[160:360, 280:360] = 1.0
    _, m = module().place_clone(frame, mask, 0.5, 100)
    ys, xs = np.nonzero(m[..., 0] > 0.5)
    assert abs(xs.mean() - 420) <= 3
    assert abs((m[..., 0] > 0.5).sum() / (mask > 0.5).sum() - 0.25) <= 0.025
    assert ys.max() == H - 1                       # still standing on the bottom edge


def test_place_clone_clips_at_border():
    frame, mask = you()
    img, m = module().place_clone(frame, mask, 0.85, 600)
    assert img.shape == frame.shape and m.shape == mask.shape


def test_smoke_deterministic_and_fades():
    smoke = module().smoke_alpha
    a, b = smoke((H, W), [(200, 180)], 0.3, 7.0), smoke((H, W), [(200, 180)], 0.3, 7.0)
    assert np.array_equal(a, b)
    assert a[180, 200] > 0.5
    assert smoke((H, W), [(200, 180)], 1.0, 7.0).max() < 0.05


def test_timeline_and_sounds(sounds):
    frame, mask = you()
    bg = np.zeros_like(frame)
    eff = load_effect("clones", {"duration": 4.0, "scale": 0.85, "offset": 0.32, "smoke": 0.6})
    clock["t"] = 0.0
    eff.start(NS(now=0.0, frame=frame, mask=mask, bg=bg))
    assert [s for s, _ in sounds] == ["poof.wav"]
    done_at, k = None, 1
    while done_at is None and k < 400:
        t = clock["t"] = k / 30
        out, done = eff.render(NS(now=t, frame=frame, mask=mask, bg=bg))
        if k == 60:                                               # t = 2.0: clones shown, no smoke
            assert out[250, 515:535].mean() > 0, "right clone visible"
            assert out[250, 105:125].mean() > 0, "left clone visible"
            assert np.array_equal(out[250, 300:340], frame[250, 300:340]), "you are drawn on top"
        if k == 153:                                              # t = 5.1
            assert not done
        if done:
            done_at = t
        k += 1
    assert done_at <= 5.25
    assert [s for s, _ in sounds] == ["poof.wav", "poof.wav"]
    assert sounds[1][1] >= 4.6 - 1e-9


@pytest.mark.parametrize("settings", [{"smoke": 0}, {"scale": "0.8"}, {"duration": -1}])
def test_bad_settings_rejected(settings):
    with pytest.raises(ConfigError):
        load_effect("clones", settings)


def test_loads_via_plugins():
    eff = load_effect("clones", {})
    assert (eff.folder / "poof.wav").is_file()


@pytest.mark.perf
def test_render_fast_enough(monkeypatch):
    """The effect must not drag a 30 fps call down: < 25 ms per frame at 640x360 in every phase."""
    import time
    monkeypatch.setattr("core.sound.play", lambda path: None)
    frame, mask = you()
    bg = np.zeros_like(frame)
    eff = load_effect("clones", {})
    eff.start(NS(now=0.0, frame=frame, mask=mask, bg=bg))
    for t in (0.3, 2.0, 4.9):
        eff.render(NS(now=t, frame=frame, mask=mask, bg=bg))       # warm-up
        start = time.perf_counter()
        for _ in range(10):
            eff.render(NS(now=t, frame=frame, mask=mask, bg=bg))
        assert (time.perf_counter() - start) / 10 < 0.025, f"too slow at t={t}"


def test_clones_land_at_fixed_spots_when_you_are_off_centre(sounds):
    """You sit 100 px right of centre: the clones still stand at w/2 +- offset*w, where the smoke is."""
    frame = np.random.default_rng(0).integers(1, 255, (H, W, 3), np.uint8)
    mask = np.zeros((H, W, 1), np.float32)
    mask[100:360, 380:460] = 1.0
    bg = np.zeros_like(frame)
    eff = load_effect("clones", {"offset": 0.32, "scale": 0.85})
    eff.start(NS(now=0.0, frame=frame, mask=mask, bg=bg))
    out, _ = eff.render(NS(now=2.0, frame=frame, mask=mask, bg=bg))
    visible = out.max(axis=2) > 0
    visible[:, 380:460] = False                        # ignore you
    cols = np.nonzero(visible.any(axis=0))[0]
    left, right = cols[cols < W / 2], cols[cols > W / 2]
    assert abs(left.mean() - (W / 2 - 0.32 * W)) <= 4
    assert abs(right.mean() - (W / 2 + 0.32 * W)) <= 4

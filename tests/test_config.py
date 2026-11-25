from pathlib import Path

import pytest

from core.config import ConfigError, load_config

REPO = Path(__file__).resolve().parents[1]


def write(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_defaults_filled(tmp_path):
    cfg = load_config(write(tmp_path, '[[triggers]]\ngesture = "g"\neffect = "e"\n'))
    assert cfg["camera"] == {"index": 0, "width": 640, "height": 480, "fps": 30}
    assert cfg["triggers"][0]["hold"] == 0.3
    assert cfg["triggers"][0]["rearm"] == 0.5
    assert cfg["gestures"] == {}
    assert cfg["effects"] == {}
    assert cfg["sound"] == {"mixer": True, "keep_alive": True}


def test_values_override_defaults(tmp_path):
    cfg = load_config(write(tmp_path, '[camera]\nwidth = 1280\n\n[[triggers]]\ngesture = "g"\neffect = "e"\nhold = 1.0\n'))
    assert cfg["camera"]["width"] == 1280
    assert cfg["camera"]["height"] == 480
    assert cfg["triggers"][0]["hold"] == 1.0
    assert cfg["triggers"][0]["rearm"] == 0.5


def test_trigger_missing_effect_raises(tmp_path):
    with pytest.raises(ConfigError) as err:
        load_config(write(tmp_path, '[[triggers]]\ngesture = "g"\n'))
    assert "effect" in str(err.value)
    assert "1" in str(err.value)


def test_repo_config_loads():
    cfg = load_config(REPO / "config.toml")
    assert cfg["triggers"][0]["gesture"] == "two_fingers_forehead"
    assert cfg["triggers"][0]["effect"] == "teleport"
    assert cfg["effects"]["teleport"] == {"fade": 0.35, "gone": 2.5}
    assert (cfg["camera"]["width"], cfg["camera"]["height"]) == (640, 360)
    pairs = [(t["gesture"], t["effect"]) for t in cfg["triggers"]]
    assert pairs == [("two_fingers_forehead", "teleport"), ("fingers_together_up", "log"),
                     ("crossed_fingers_plus", "clones")]      # together before plus: it can look like a plus too
    assert cfg["effects"]["log"] == {"duration": 3.0, "smoke": 0.6}
    assert cfg["effects"]["clones"] == {"duration": 4.0, "scale": 0.85, "offset": 0.32, "smoke": 0.6}


def test_single_bracket_triggers_raises(tmp_path):
    with pytest.raises(ConfigError) as err:
        load_config(write(tmp_path, '[triggers]\ngesture = "g"\neffect = "e"\n'))
    assert "[[triggers]]" in str(err.value)


def test_non_string_gesture_raises(tmp_path):
    with pytest.raises(ConfigError) as err:
        load_config(write(tmp_path, '[[triggers]]\ngesture = 5\neffect = "e"\n'))
    assert "gesture" in str(err.value)


@pytest.mark.parametrize("value", ['"0.3"', "-1", "true"])
def test_hold_must_be_positive_number(tmp_path, value):
    with pytest.raises(ConfigError) as err:
        load_config(write(tmp_path, f'[[triggers]]\ngesture = "g"\neffect = "e"\nhold = {value}\n'))
    assert "hold" in str(err.value)

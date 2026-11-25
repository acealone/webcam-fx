import pytest

from core.plugins import PluginError, available, load_effect, load_gesture


def make(root, rel, code):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(code, encoding="utf-8")


def test_available_lists_folders_with_module(tmp_path):
    make(tmp_path, "gestures/a/gesture.py", "class Gesture:\n    def __init__(self, settings): pass\n")
    (tmp_path / "gestures" / "b").mkdir()
    assert available("gesture", tmp_path) == ["a"]


def test_load_effect_passes_settings_and_folder(tmp_path):
    make(tmp_path, "effects/x/effect.py",
         "class Effect:\n    def __init__(self, settings, folder):\n"
         "        self.settings, self.folder = settings, folder\n")
    eff = load_effect("x", {"k": 1}, tmp_path)
    assert eff.settings == {"k": 1}
    assert eff.folder == tmp_path / "effects" / "x"


def test_unknown_name_lists_available(tmp_path):
    make(tmp_path, "gestures/a/gesture.py", "class Gesture:\n    def __init__(self, settings): pass\n")
    with pytest.raises(PluginError) as err:
        load_gesture("nope", {}, tmp_path)
    assert "nope" in str(err.value)
    assert "a" in str(err.value).split("nope", 1)[1]


def test_module_without_class_raises(tmp_path):
    make(tmp_path, "gestures/a/gesture.py", "x = 1\n")
    with pytest.raises(PluginError) as err:
        load_gesture("a", {}, tmp_path)
    assert "Gesture" in str(err.value)

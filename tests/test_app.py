from types import SimpleNamespace as NS

import numpy as np
import pytest

import core.app as app
from core.config import load_config
from core.plugins import REPO_ROOT


def test_virtual_camera_failure_exits_with_hint(monkeypatch, tmp_path):
    frame = np.zeros((48, 64, 3), np.uint8)
    released = []
    monkeypatch.setattr(app, "open_camera", lambda *a: (NS(release=lambda: released.append(1)), frame))
    monkeypatch.setattr(app.Detectors, "create", classmethod(lambda cls: cls()))

    def no_virtual_cam(*a, **k):
        raise RuntimeError("virtual camera output could not be started")

    monkeypatch.setattr(app.pyvirtualcam, "Camera", no_virtual_cam)
    with pytest.raises(SystemExit) as err:
        app.run(load_config(REPO_ROOT / "config.toml"), tmp_path / "bg.png")
    assert app.virtual_camera_hint() in str(err.value)
    assert released == [1]                     # webcam is freed again


def test_virtual_camera_hint_windows(monkeypatch):
    monkeypatch.setattr(app, "PLATFORM", "win32")
    assert "OBS" in app.virtual_camera_hint()


def test_virtual_camera_hint_linux(monkeypatch):
    monkeypatch.setattr(app, "PLATFORM", "linux")
    assert "sudo modprobe v4l2loopback devices=1 exclusive_caps=1 card_label=webcam-fx" in app.virtual_camera_hint()


def test_debug_lines_come_from_gestures_that_offer_them():
    class Plain:
        pass

    class Talkative:
        def debug(self, ctx):
            return f"seen {ctx}"

    assert app.debug_lines({"a": Plain(), "b": Talkative()}, "x") == ["seen x"]


def test_debug_printer_prints_at_most_twice_per_second(capsys):
    printer = app.DebugPrinter(interval=0.5)
    printer.maybe_print(["together: hands 1"], now=100.0)
    printer.maybe_print(["together: hands 2"], now=100.2)      # too soon: skipped
    printer.maybe_print(["together: hands 2", "plus: hands 2"], now=100.5)
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert lines[0].endswith("together: hands 1")
    assert lines[1].endswith("together: hands 2") and lines[2].endswith("plus: hands 2")
    assert lines[0][:2].isdigit()                               # starts with a time stamp


def test_debug_printer_silent_without_lines(capsys):
    app.DebugPrinter().maybe_print([], now=1.0)
    assert capsys.readouterr().out == ""

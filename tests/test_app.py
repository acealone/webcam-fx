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
    assert "OBS" in str(err.value)
    assert released == [1]                     # webcam is freed again

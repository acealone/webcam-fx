import pytest

from core.camera import open_camera


def test_open_camera_bad_index_exits_with_message():
    with pytest.raises(SystemExit) as err:
        open_camera(99, 640, 480, 30)
    assert "No webcam frame" in str(err.value)


def test_backend_per_platform(monkeypatch):
    import cv2
    import core.camera as camera
    monkeypatch.setattr(camera, "PLATFORM", "win32")
    assert camera.capture_backend() == cv2.CAP_DSHOW
    monkeypatch.setattr(camera, "PLATFORM", "linux")
    assert camera.capture_backend() == cv2.CAP_V4L2

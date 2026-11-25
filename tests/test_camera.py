import pytest

from core.camera import open_camera


def test_open_camera_bad_index_exits_with_message():
    with pytest.raises(SystemExit) as err:
        open_camera(99, 640, 480, 30)
    assert "No webcam frame" in str(err.value)

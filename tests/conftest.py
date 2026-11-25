import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root, so `import core` works


@pytest.fixture(autouse=True)
def no_real_audio_device(monkeypatch):
    """Tests never open a real audio output; tests that need the mixer install a fake stream."""
    import core.sound

    def refuse(mixer):
        raise OSError("no audio device in tests")

    core.sound.stop()
    monkeypatch.setattr(core.sound, "STREAM_FACTORY", refuse)
    yield
    core.sound.stop()

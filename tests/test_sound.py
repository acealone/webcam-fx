import sys
import wave

import numpy as np
import pytest

import core.sound
from core.sound import Mixer, load, play


def write_wav(path, samples, rate=44100, channels=1):
    data = (np.asarray(samples, np.float32) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels); w.setsampwidth(2); w.setframerate(rate); w.writeframes(data.tobytes())
    return path


class FakeStream:
    def close(self):
        pass


@pytest.fixture
def fake_mixer(monkeypatch):
    holder = {}

    def factory(mixer):
        holder["mixer"] = mixer
        return FakeStream()

    monkeypatch.setattr(core.sound, "STREAM_FACTORY", factory)
    return holder


def test_play_missing_file_is_silent(tmp_path):
    play(tmp_path / "does_not_exist.wav")


def test_mixer_sums_overlapping_sounds():
    m = Mixer()
    m.add(np.full(100, 0.25, np.float32))
    m.add(np.full(50, 0.5, np.float32))
    first = m.mix(80)
    assert np.allclose(first[:50], 0.75) and np.allclose(first[50:], 0.25)
    second = m.mix(80)
    assert np.allclose(second[:20], 0.25) and np.allclose(second[20:], 0.0)
    assert m.active == 0


def test_mixer_clips_loud_overlaps():
    m = Mixer()
    m.add(np.full(10, 0.8, np.float32))
    m.add(np.full(10, 0.8, np.float32))
    assert m.mix(10).max() <= 1.0


def test_second_sound_does_not_cut_the_first(tmp_path, fake_mixer):
    """winsound stops the running sound when a new one starts - the mixer must play both."""
    poof = write_wav(tmp_path / "poof.wav", np.full(22050, 0.3))
    clonk = write_wav(tmp_path / "clonk.wav", np.full(4410, 0.3))
    play(poof)
    fake_mixer["mixer"].mix(11025)                      # 0.25 s of the poof played
    play(clonk)
    assert fake_mixer["mixer"].active == 2
    assert np.allclose(fake_mixer["mixer"].mix(100), 0.6, atol=1e-3)


def test_load_converts_stereo_and_sample_rate(tmp_path):
    stereo = np.zeros(2 * 22050, np.float32)
    stereo[0::2], stereo[1::2] = 0.2, 0.4                # left 0.2, right 0.4, 1 s at 22050 Hz
    samples = load(write_wav(tmp_path / "s.wav", stereo, rate=22050, channels=2))
    assert abs(len(samples) - 44100) <= 2
    assert np.allclose(samples[100:200], 0.3, atol=1e-3)


def test_falls_back_when_no_audio_device(tmp_path, monkeypatch):
    """No output stream (no device, no PortAudio): the old players are used."""
    wav = write_wav(tmp_path / "x.wav", np.zeros(10))
    monkeypatch.setattr(core.sound, "PLATFORM", "linux")
    monkeypatch.setattr(core.sound.shutil, "which", lambda name: "/usr/bin/pw-play" if name == "pw-play" else None)
    started = []
    monkeypatch.setattr(core.sound.subprocess, "Popen", lambda args, **kw: started.append(args))
    play(wav)
    assert started == [["/usr/bin/pw-play", str(wav)]]


def test_start_reports_whether_the_mixer_runs(fake_mixer):
    assert core.sound.start() is True


def test_start_false_without_audio_device():
    assert core.sound.start() is False


# --- fallback players (restored: these were deleted by accident in commit ae8689d) ---

@pytest.fixture
def linux(monkeypatch, tmp_path):
    monkeypatch.setattr(core.sound, "PLATFORM", "linux")
    wav = tmp_path / "x.wav"
    wav.write_bytes(b"RIFF")
    started = []
    monkeypatch.setattr(core.sound.subprocess, "Popen", lambda args, **kw: started.append(args))
    return wav, started


def test_linux_uses_first_available_player(linux, monkeypatch):
    wav, started = linux
    monkeypatch.setattr(core.sound.shutil, "which", lambda name: "/usr/bin/paplay" if name == "paplay" else None)
    play(wav)
    assert started == [["/usr/bin/paplay", str(wav)]]


def test_linux_no_player_is_silent(linux, monkeypatch):
    wav, started = linux
    monkeypatch.setattr(core.sound.shutil, "which", lambda name: None)
    play(wav)
    assert started == []


def test_linux_player_failure_is_silent(linux, monkeypatch):
    wav, _ = linux
    monkeypatch.setattr(core.sound.shutil, "which", lambda name: "/usr/bin/pw-play")

    def broken(args, **kw):
        raise OSError("cannot start")

    monkeypatch.setattr(core.sound.subprocess, "Popen", broken)
    play(wav)


@pytest.mark.skipif(sys.platform != "win32", reason="winsound exists only on Windows")
def test_windows_unplayable_is_silent(tmp_path, monkeypatch):
    import winsound

    def fail(*args):
        raise RuntimeError("Failed to play sound")

    monkeypatch.setattr(winsound, "PlaySound", fail)
    wav = tmp_path / "broken.wav"
    wav.write_bytes(b"RIFF....not really")
    play(wav)


def test_status_names_the_device_and_activity(fake_mixer, monkeypatch):
    class NamedStream(FakeStream):
        device_name, active = "Test Headset", True

    monkeypatch.setattr(core.sound, "STREAM_FACTORY", lambda mixer: fake_mixer.setdefault("mixer", mixer) and NamedStream())
    assert core.sound.start() is True
    text = core.sound.status()
    assert "mixer on 'Test Headset'" in text and "active yes" in text and "playing 0" in text


def test_status_explains_fallback():
    core.sound.start()                                   # conftest: no device -> OSError
    assert core.sound.status().startswith("sound: system player")
    assert "no audio device in tests" in core.sound.status()


def test_mixer_can_be_switched_off(tmp_path, fake_mixer, monkeypatch):
    assert core.sound.start(use_mixer=False) is False
    assert "switched off in config.toml" in core.sound.status()
    wav = write_wav(tmp_path / "x.wav", np.zeros(10))
    monkeypatch.setattr(core.sound, "PLATFORM", "linux")
    monkeypatch.setattr(core.sound.shutil, "which", lambda name: "/usr/bin/aplay" if name == "aplay" else None)
    started = []
    monkeypatch.setattr(core.sound.subprocess, "Popen", lambda args, **kw: started.append(args))
    play(wav)
    assert started == [["/usr/bin/aplay", str(wav)]] and "mixer" not in fake_mixer

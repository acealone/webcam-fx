"""Non-blocking sound playback.

Preferred: one audio output that stays open for the whole session (sounddevice) with a small mixer, so
- overlapping sounds are mixed instead of the new one cutting off the old one (winsound plays one at a time),
- wireless/USB headsets don't have to wake up for every short sound (which swallows its beginning).
Fallback when no output can be opened: winsound on Windows, pw-play / paplay / aplay on Linux.
"""
import shutil
import subprocess
import sys
import threading
import wave
from pathlib import Path

import numpy as np

PLATFORM = sys.platform
LINUX_PLAYERS = ("pw-play", "paplay", "aplay")   # PipeWire, PulseAudio, ALSA
SAMPLE_RATE = 44100


class Mixer:
    """Sums all sounds that are currently playing. mix() is called from the audio thread."""

    def __init__(self):
        self._lock = threading.Lock()
        self._voices = []   # [samples, position]

    @property
    def active(self) -> int:
        with self._lock:
            return len(self._voices)

    def add(self, samples: np.ndarray) -> None:
        with self._lock:
            self._voices.append([samples, 0])

    def mix(self, frames: int) -> np.ndarray:
        out = np.zeros(frames, np.float32)
        with self._lock:
            for voice in self._voices:
                samples, pos = voice
                chunk = samples[pos:pos + frames]
                out[:len(chunk)] += chunk
                voice[1] = pos + frames
            self._voices = [v for v in self._voices if v[1] < len(v[0])]
        return np.clip(out, -1.0, 1.0)


def _open_stream(mixer: Mixer):
    import sounddevice as sd   # needs PortAudio (bundled on Windows; libportaudio2 / portaudio on Linux)

    def callback(outdata, frames, time_info, status):
        outdata[:, 0] = mixer.mix(frames)

    stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback)
    stream.start()
    return stream


STREAM_FACTORY = _open_stream   # tests replace this, so they never open a real audio device
_mixer = None
_stream = None
_failed = False
_cache = {}


def start() -> bool:
    """Open the shared audio output (once). True if the mixer runs, False -> fallback players are used."""
    global _mixer, _stream, _failed
    if _mixer is not None:
        return True
    if _failed:
        return False
    try:
        mixer = Mixer()
        _stream = STREAM_FACTORY(mixer)
        _mixer = mixer
        return True
    except Exception:   # no device, no PortAudio, device busy, ...
        _failed = True
        return False


def stop() -> None:
    global _mixer, _stream, _failed
    if _stream is not None:
        try:
            _stream.close()
        except Exception:
            pass
    _mixer = _stream = None
    _failed = False


def load(path: Path) -> np.ndarray:
    """WAV (16-bit PCM) as mono float32 at SAMPLE_RATE, cached."""
    key = str(path)
    if key not in _cache:
        with wave.open(key, "rb") as w:
            channels, rate, width = w.getnchannels(), w.getframerate(), w.getsampwidth()
            raw = w.readframes(w.getnframes())
        if width != 2:
            raise ValueError(f"{path}: only 16-bit WAV files are supported")
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        if channels > 1:
            x = x.reshape(-1, channels).mean(axis=1)
        if rate != SAMPLE_RATE:
            n = int(round(len(x) * SAMPLE_RATE / rate))
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        _cache[key] = np.ascontiguousarray(x, np.float32)
    return _cache[key]


def play(path: Path) -> None:
    """Start playing a WAV and return immediately. Missing file, player or audio device: silent."""
    path = Path(path)
    if not path.is_file():
        return
    if start():
        try:
            _mixer.add(load(path))
            return
        except Exception:   # unreadable / unsupported WAV: let the fallback player try
            pass
    _play_fallback(path)


def _play_fallback(path: Path) -> None:
    if PLATFORM == "win32":
        import winsound
        try:
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except RuntimeError:   # broken file or no audio device: the effect goes on silently
            pass
        return
    player = next((p for p in map(shutil.which, LINUX_PLAYERS) if p), None)
    if player:
        try:
            subprocess.Popen([player, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass

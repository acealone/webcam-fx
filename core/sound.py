"""Non-blocking sound playback: winsound on Windows, pw-play / paplay / aplay on Linux."""
import shutil
import subprocess
import sys
from pathlib import Path

PLATFORM = sys.platform
LINUX_PLAYERS = ("pw-play", "paplay", "aplay")   # PipeWire, PulseAudio, ALSA


def play(path: Path) -> None:
    """Start playing a WAV and return immediately. Missing file, player or audio device: silent."""
    path = Path(path)
    if not path.is_file():
        return
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

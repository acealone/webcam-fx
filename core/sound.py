"""Non-blocking sound playback (Windows)."""
from pathlib import Path

import winsound


def play(path: Path) -> None:
    path = Path(path)
    if path.is_file():
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)

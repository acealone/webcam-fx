"""The clean background plate shown where you are not (and everywhere while you're "gone")."""
from pathlib import Path

import cv2
import numpy as np

MARGIN = np.ones((41, 41), np.uint8)   # don't learn this close to you (hands, hair edges)


class Background:
    def __init__(self, path: Path, first_frame: np.ndarray):
        self.path = Path(path)
        self._capture_at = None
        saved = cv2.imread(str(self.path)) if self.path.is_file() else None
        if saved is not None and saved.shape == first_frame.shape:
            self.plate, self.locked = saved, True
            print(f"Using saved background {self.path} (press b to replace it)")
            return
        if saved is not None:
            h, w = first_frame.shape[:2]
            print(f"Ignoring {self.path}: it is {saved.shape[1]}x{saved.shape[0]}, camera is {w}x{h} - press b to recapture")
        self.plate = cv2.GaussianBlur(first_frame, (0, 0), 25)   # placeholder until learned or captured
        self.locked = False

    def learn(self, frame: np.ndarray, mask: np.ndarray) -> None:
        """Copy the live frame into the plate wherever you are not (only until a plate is locked)."""
        if self.locked:
            return
        near_you = cv2.dilate((mask[..., 0] > 0.1).astype(np.uint8), MARGIN)
        self.plate = np.where(near_you[..., None] == 0, frame, self.plate)

    def start_capture(self, now: float, delay: float = 5.0) -> None:
        self._capture_at = now + delay
        print(f"Step out of frame - capturing background in {delay:.0f} s")

    def countdown(self, now: float):
        return None if self._capture_at is None else self._capture_at - now

    def update(self, frame: np.ndarray, now: float) -> bool:
        """Call every frame. Returns True on the frame the background is captured."""
        if self._capture_at is None or now < self._capture_at:
            return False
        self.plate, self.locked, self._capture_at = frame.copy(), True, None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if cv2.imwrite(str(self.path), self.plate):
            print(f"Background captured and saved to {self.path}")
        else:
            print(f"Background captured, but saving to {self.path} failed")
        return True

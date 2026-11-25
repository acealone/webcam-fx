"""Clones: smoke bursts left and right, two live copies of you appear, stay, and vanish in smoke."""
from pathlib import Path

import cv2
import numpy as np

from core import sound
from core.compose import blend
from core.config import check_number
from core.smoke import SMOKE_COLOR, paint, smoke_alpha

def place_clone(frame, mask, scale: float, dx: float):
    """Copy of the picture, scaled around the horizontal centre, standing on the bottom edge, shifted dx px."""
    h, w = frame.shape[:2]
    m = np.float32([[scale, 0, (1 - scale) * w / 2 + dx], [0, scale, (1 - scale) * h]])
    img = cv2.warpAffine(frame, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
    msk = cv2.warpAffine(mask[..., 0], m, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
    return img, msk[..., None]


class Effect:
    def __init__(self, settings: dict, folder: Path):
        self.duration = check_number(settings.get("duration", 4.0), "effects.clones.duration")
        self.scale = check_number(settings.get("scale", 0.85), "effects.clones.scale", positive=True)
        self.offset = check_number(settings.get("offset", 0.32), "effects.clones.offset", positive=True)
        self.smoke = check_number(settings.get("smoke", 0.6), "effects.clones.smoke", positive=True)
        self.folder = Path(folder)
        self.t0, self._out_played = 0.0, False

    def start(self, ctx) -> None:
        self.t0, self._out_played = ctx.now, False
        sound.play(self.folder / "poof.wav")

    def render(self, ctx):
        frame, mask, bg = ctx.frame, ctx.mask, ctx.bg
        h, w = frame.shape[:2]
        el, s, d = ctx.now - self.t0, self.smoke, self.duration
        if el >= 2 * s + d:
            return blend(frame, mask, bg), True
        if el < s:                                   # smoke in, clones fade in inside the smoke
            phase, p = "in", el / s
            alpha = float(np.clip((p - 0.3) / 0.4, 0, 1))
        elif el < s + d:                             # clones standing next to you
            phase, p, alpha = "shown", None, 1.0
        else:                                        # smoke out, clones fade out
            phase, p = "out", (el - s - d) / s
            alpha = 1 - float(np.clip((p - 0.3) / 0.4, 0, 1))
            if not self._out_played:
                self._out_played = True
                sound.play(self.folder / "poof.wav")

        canvas = bg.astype(np.float32)
        cols = mask[..., 0].sum(axis=0)
        if cols.sum() >= 1:                          # nobody in the picture: no clones, just smoke
            you_x = float((cols * np.arange(w)).sum() / cols.sum())
            for side in (-1, 1):                     # clones always stand at the smoke spots, wherever you sit
                target = w / 2 + side * self.offset * w
                dx = target - (self.scale * you_x + (1 - self.scale) * w / 2)
                img, m = place_clone(frame, mask, self.scale, dx)
                paint(canvas, img, m[..., 0] * alpha)
        if phase != "shown":
            centers = [(w / 2 + side * self.offset * w, 0.55 * h) for side in (-1, 1)]
            paint(canvas, SMOKE_COLOR, smoke_alpha((h, w), centers, p, self.t0 + (0 if phase == "in" else 1)))
        return blend(frame, mask, canvas), False       # you on top of everything

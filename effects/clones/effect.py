"""Clones: smoke bursts left and right, two live copies of you appear, stay, and vanish in smoke."""
import random
from pathlib import Path

import cv2
import numpy as np

from core import sound
from core.compose import blend
from core.config import check_number

SMOKE_COLOR = np.array((225, 225, 230), np.float32)   # BGR, light grey


def place_clone(frame, mask, scale: float, dx: float):
    """Copy of the picture, scaled around the horizontal centre, standing on the bottom edge, shifted dx px."""
    h, w = frame.shape[:2]
    m = np.float32([[scale, 0, (1 - scale) * w / 2 + dx], [0, scale, (1 - scale) * h]])
    img = cv2.warpAffine(frame, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
    msk = cv2.warpAffine(mask[..., 0], m, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)
    return img, msk[..., None]


def smoke_alpha(shape_hw, centers, progress: float, seed):
    """Soft smoke puffs around each centre. progress 0..1: puffs grow and drift out, opacity fades.
    Drawn at quarter resolution and scaled up: the smoke is soft anyway, and it's 16x less work."""
    h, w = shape_hw
    q = 4
    rng = random.Random(seed)
    spread_x, spread_y = 0.12 * w / q, 0.30 * h / q        # cloud about the size of a clone's body
    layer = np.zeros((h // q, w // q), np.float32)
    for cx, cy in centers:
        for _ in range(22):
            ox, oy = rng.uniform(-1, 1) * spread_x, rng.uniform(-1, 1) * spread_y
            drift = 0.7 + 0.5 * progress                  # puffs drift outwards
            r = h / q * rng.uniform(0.08, 0.14) * (0.7 + 0.8 * progress)
            cv2.circle(layer, (int(cx / q + ox * drift), int(cy / q + oy * drift)), max(1, int(r)), 1.0, -1)
    layer = cv2.GaussianBlur(layer, (0, 0), max(1.0, h / q * 0.03))
    layer = cv2.resize(layer, (w, h), interpolation=cv2.INTER_LINEAR)
    opacity = min(1.0, 4 * progress) * (1 - progress) ** 0.8   # dense quickly, thins out towards the end
    return np.clip(layer, 0, 1) * opacity


def _paint(canvas, top, alpha):
    """canvas += (top - canvas) * alpha, only inside the box where alpha > 0 (much less work)."""
    x, y, bw, bh = cv2.boundingRect((alpha > 0.004).astype(np.uint8))
    if bw == 0:
        return
    roi = canvas[y:y + bh, x:x + bw]
    t = top[y:y + bh, x:x + bw] if top.ndim == 3 else top
    roi += (t - roi) * alpha[y:y + bh, x:x + bw, None]


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
        for side in (-1, 1):
            img, m = place_clone(frame, mask, self.scale, side * self.offset * w)
            _paint(canvas, img, m[..., 0] * alpha)
        if phase != "shown":
            centers = [(w / 2 + side * self.offset * w, 0.55 * h) for side in (-1, 1)]
            _paint(canvas, SMOKE_COLOR, smoke_alpha((h, w), centers, p, self.t0 + (0 if phase == "in" else 1)))
        return blend(frame, mask, canvas), False       # you on top of everything

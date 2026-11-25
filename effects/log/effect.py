"""Log: a smoke bomb goes off, you are replaced by a wooden log, then smoke again and you're back."""
import random
from pathlib import Path

import cv2
import numpy as np

from core import sound
from core.compose import blend
from core.config import check_number
from core.smoke import SMOKE_COLOR, paint, smoke_alpha

BARK = np.array((40, 75, 115), np.float32)      # BGR brown
CUT = np.array((110, 165, 205), np.float32)     # BGR light wood (the sawn top)


def make_log(height: int, seed):
    """An upright log drawn by code: bark streaks, knots, rounded ends, sawn top with rings.
    Returns (BGR uint8 image, alpha HxW float 0..1)."""
    rng = np.random.default_rng(random.Random(seed).getrandbits(32))
    h = int(height)
    w = max(8, int(round(h * 0.32)))
    cap = max(4, int(w * 0.3))                                          # height of the elliptic ends

    x = np.linspace(-1, 1, w)
    shade = 0.5 + 0.5 * np.sqrt(np.clip(1 - x ** 2, 0, 1))              # round: bright middle, dark sides
    streaks = np.zeros((h, w), np.float32)
    for _ in range(max(6, int(w * 0.7))):                               # vertical bark streaks
        cx, y0 = int(rng.integers(0, w)), int(rng.integers(0, h))
        streaks[y0:y0 + int(rng.integers(h // 6, h // 2)), cx] += rng.uniform(0.2, 0.5)
    streaks = cv2.GaussianBlur(streaks, (0, 0), sigmaX=0.7, sigmaY=3)
    img = BARK * shade[None, :, None] * (1 - np.clip(streaks, 0, 0.6))[..., None]
    for _ in range(2):                                                  # knots
        center = (int(rng.integers(w // 4, 3 * w // 4)), int(rng.integers(cap * 2, h - cap * 2)))
        cv2.ellipse(img, center, (max(2, w // 10), max(1, h // 40)), 0, 0, 360, tuple(map(float, BARK * 0.4)), -1)
        cv2.ellipse(img, center, (max(3, w // 7), max(2, h // 28)), 0, 0, 360, tuple(map(float, BARK * 0.6)), 1)

    top = (w // 2, cap // 2)                                            # sawn top with growth rings
    cv2.ellipse(img, top, (w // 2, cap // 2), 0, 0, 360, tuple(map(float, CUT)), -1)
    for i in range(1, 5):
        cv2.ellipse(img, top, (max(1, w // 2 * i // 5), max(1, cap // 2 * i // 5)), 0, 0, 360,
                    tuple(map(float, CUT * 0.75)), 1)

    alpha = np.zeros((h, w), np.float32)
    alpha[cap // 2:h - cap // 2, :] = 1.0
    cv2.ellipse(alpha, top, (w // 2, cap // 2), 0, 0, 360, 1.0, -1)
    cv2.ellipse(alpha, (w // 2, h - 1 - cap // 2), (w // 2, cap // 2), 0, 0, 360, 1.0, -1)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8)                        # soft edge
    return np.clip(img, 0, 255).astype(np.uint8), alpha


def _paste(layer_img, layer_alpha, img, alpha, x0, y0):
    """Put img/alpha into the full-frame layers at (x0, y0), clipped to the frame."""
    H, W = layer_alpha.shape
    h, w = alpha.shape
    x1, y1 = max(0, x0), max(0, y0)
    x2, y2 = min(W, x0 + w), min(H, y0 + h)
    if x2 <= x1 or y2 <= y1:
        return
    layer_img[y1:y2, x1:x2] = img[y1 - y0:y2 - y0, x1 - x0:x2 - x0]
    layer_alpha[y1:y2, x1:x2] = alpha[y1 - y0:y2 - y0, x1 - x0:x2 - x0]


class Effect:
    def __init__(self, settings: dict, folder: Path):
        self.duration = check_number(settings.get("duration", 3.0), "effects.log.duration")
        self.smoke = check_number(settings.get("smoke", 0.6), "effects.log.smoke", positive=True)
        self.folder = Path(folder)
        self.t0, self._clonk_played, self._out_played = 0.0, False, False

    def _log_image(self, height, seed):
        """Your own log.png (with transparency) from the effect folder if present, else the drawn log."""
        png = self.folder / "log.png"
        im = cv2.imread(str(png), cv2.IMREAD_UNCHANGED) if png.is_file() else None
        if im is None:
            return make_log(height, seed)
        width = max(1, int(round(im.shape[1] * height / im.shape[0])))
        im = cv2.resize(im, (width, height), interpolation=cv2.INTER_AREA)
        if im.ndim == 2:
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
        alpha = im[..., 3].astype(np.float32) / 255 if im.shape[2] == 4 else np.ones(im.shape[:2], np.float32)
        return np.ascontiguousarray(im[..., :3]), alpha

    def start(self, ctx) -> None:
        self.t0, self._clonk_played, self._out_played = ctx.now, False, False
        sound.play(self.folder / "poof.wav")
        h, w = ctx.frame.shape[:2]
        ys, xs = np.nonzero(ctx.mask[..., 0] > 0.5)
        if len(xs):                                   # the log stands where you stand, about your height
            cx, top, bottom = float(xs.mean()), int(ys.min()), int(ys.max())
        else:
            cx, top, bottom = w / 2, int(h * 0.25), h - 1
        height = int(np.clip((bottom - top) * 0.9, h * 0.3, h * 0.95))
        img, alpha = self._log_image(height, ctx.now)
        self.layer_img = np.zeros((h, w, 3), np.float32)
        self.layer_alpha = np.zeros((h, w), np.float32)
        _paste(self.layer_img, self.layer_alpha, img.astype(np.float32), alpha,
               int(round(cx - img.shape[1] / 2)), bottom + 1 - height)
        self.center = (cx, bottom + 1 - height / 2)

    def render(self, ctx):
        frame, mask, bg = ctx.frame, ctx.mask, ctx.bg
        h, w = frame.shape[:2]
        el, s, d = ctx.now - self.t0, self.smoke, self.duration
        if el >= 2 * s + d:
            return blend(frame, mask, bg), True
        if el < s:                                    # smoke in: you fade out, the log fades in
            phase, p = "in", el / s
            log_a = float(np.clip((p - 0.3) / 0.4, 0, 1))
            if log_a >= 1 and not self._clonk_played:
                self._clonk_played = True
                sound.play(self.folder / "clonk.wav")
        elif el < s + d:                              # only the log
            phase, p, log_a = "shown", None, 1.0
        else:                                         # smoke out: the log fades out, you're back
            phase, p = "out", (el - s - d) / s
            log_a = 1 - float(np.clip((p - 0.3) / 0.4, 0, 1))
            if not self._out_played:
                self._out_played = True
                sound.play(self.folder / "poof.wav")

        canvas = blend(frame, mask, bg, 1 - log_a).astype(np.float32)
        paint(canvas, self.layer_img, self.layer_alpha * log_a)
        if phase != "shown":
            seed = self.t0 + (0 if phase == "in" else 1)
            paint(canvas, SMOKE_COLOR, smoke_alpha((h, w), [self.center], p, seed, spread=(0.14, 0.38), puffs=45))
        return np.clip(canvas, 0, 255).astype(np.uint8), False

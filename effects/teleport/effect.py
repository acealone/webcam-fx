"""Teleport: you get torn by vertical slits, vanish, stay gone, then reappear the same way."""
import random
from pathlib import Path

import cv2
import numpy as np

from core import sound
from core.compose import blend


def tear(img, m, amount, seed):
    """Teleport tearing: narrow vertical slits cut through you (background shows through), the pieces
    slide up/down a little and smear vertically. Same seed = same slits, growing with amount 0..1."""
    rng = random.Random(seed)
    h, w = m.shape[:2]
    on = m[..., 0] > 0.3
    cols, rows = np.nonzero(on.any(axis=0))[0], np.nonzero(on.any(axis=1))[0]
    if len(cols) == 0:
        return img, m
    x0, x1, y0, y1 = int(cols[0]), int(cols[-1]) + 1, int(rows[0]), int(rows[-1]) + 1

    k = 1 + int(amount * 0.02 * h)                                  # light vertical smear, keeps you sharp
    img = cv2.blur(img, (1, k))
    m = cv2.blur(m[..., 0], (1, k))[..., None]

    def slide(a, dy):                                               # shift down (+) / up (-) without wrap-around
        out = np.zeros_like(a)
        if dy > 0:
            out[dy:] = a[:-dy]
        else:
            out[:dy] = a[-dy:]
        return out

    cuts = sorted(rng.randrange(x0, x1) for _ in range(10))        # pieces slide up/down -> stepped edges
    for a, b in zip([x0, *cuts], [*cuts, x1]):
        dy = int(rng.choice((-1, 1)) * rng.uniform(0.01, 0.06) * h * amount)
        if b > a and dy:
            img[:, a:b] = slide(img[:, a:b], dy)
            m[:, a:b] = slide(m[:, a:b], dy)

    for i in range(30):                                             # see-through slits, more and wider over time
        x, top = rng.randrange(x0, x1), rng.randrange(y0, y1)
        length, width = rng.uniform(0.3, 1.0) * (y1 - y0), rng.uniform(0.004, 0.012) * w
        if i < 6 + 24 * amount:
            m[top:top + int(length), x:x + max(1, int(width * (0.5 + 1.5 * amount)))] = 0

    for _ in range(int(15 + 45 * amount)):                          # thin dark streak lines
        x, y = rng.randrange(x0, x1), rng.randrange(y0, y1)
        img[y:y + int(rng.uniform(0.03, 0.15) * h), x] //= 3
    return img, m


class Effect:
    def __init__(self, settings: dict, folder: Path):
        self.fade = settings.get("fade", 0.35)   # seconds to vanish / reappear
        self.gone = settings.get("gone", 2.5)    # seconds invisible
        self.folder = Path(folder)
        self.state, self.t_state = "done", 0.0

    def start(self, ctx) -> None:
        self.state, self.t_state = "out", ctx.now
        sound.play(self.folder / "teleport_out.wav")

    def render(self, ctx):
        now = ctx.now
        el = now - self.t_state
        if self.state == "out" and el > self.fade:
            self.state, self.t_state = "gone", now
        elif self.state == "gone" and el > self.gone:
            self.state, self.t_state = "in", now
            sound.play(self.folder / "teleport_in.wav")
        elif self.state == "in" and el > self.fade:
            self.state = "done"
        el = now - self.t_state
        visible = {"done": 1.0, "gone": 0.0, "out": 1 - el / self.fade, "in": el / self.fade}[self.state]
        visible = float(np.clip(visible, 0, 1))

        person, pmask = ctx.frame, ctx.mask
        if self.state in ("out", "in"):            # vertical tearing during the transition
            person, pmask = tear(ctx.frame, ctx.mask, 1 - visible, seed=self.t_state)
        # stay opaque; the growing slits do the vanishing
        return blend(person, pmask, ctx.bg, visible ** 0.3), self.state == "done"

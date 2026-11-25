"""Smoke puffs shared by effects (clones, log)."""
import random

import cv2
import numpy as np

SMOKE_COLOR = np.array((225, 225, 230), np.float32)   # BGR, light grey


def smoke_alpha(shape_hw, centers, progress: float, seed, spread=(0.12, 0.30)):
    """Soft smoke puffs around each centre. progress 0..1: puffs grow and drift out, opacity fades.
    spread: half-size of each cloud as a share of (width, height).
    Drawn at quarter resolution and scaled up: the smoke is soft anyway, and it's 16x less work."""
    h, w = shape_hw
    q = 4
    rng = random.Random(seed)
    spread_x, spread_y = spread[0] * w / q, spread[1] * h / q
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


def paint(canvas, top, alpha):
    """canvas += (top - canvas) * alpha, only inside the box where alpha > 0 (much less work)."""
    x, y, bw, bh = cv2.boundingRect((alpha > 0.004).astype(np.uint8))
    if bw == 0:
        return
    roi = canvas[y:y + bh, x:x + bw]
    t = top[y:y + bh, x:x + bw] if top.ndim == 3 else top
    roi += (t - roi) * alpha[y:y + bh, x:x + bw, None]

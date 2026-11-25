import math
from types import SimpleNamespace as NS

import numpy as np

from core.plugins import load_gesture

W, H = 640, 360


def make_hand(base, angle_deg, length=90, open_hand=False, w=W, h=H):
    """21 relative landmarks: wrist at base (px), index+middle along angle (0 = right, 90 = up)."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), -math.sin(a)                 # image y grows downwards
    px, py = -uy, ux                                   # sideways, to separate index and middle
    bx, by = base

    def at(frac, side):
        return NS(x=(bx + ux * length * frac + px * side) / w, y=(by + uy * length * frac + py * side) / h)

    lm = [NS(x=bx / w, y=by / h) for _ in range(21)]
    lm[5], lm[6], lm[8] = at(0.4, -6), at(0.65, -6), at(1.0, -6)       # index
    lm[9], lm[10], lm[12] = at(0.4, 6), at(0.65, 6), at(1.0, 6)        # middle
    reach = 1.0 if open_hand else 0.25                                 # folded = tip back near the palm
    lm[13], lm[14], lm[16] = at(0.4, 16), at(0.55, 16), at(reach, 16)  # ring
    lm[17], lm[18], lm[20] = at(0.35, 24), at(0.5, 24), at(reach * 0.9, 24)  # pinky
    return NS(landmark=lm)


def detect(*hands):
    ctx = NS(hands=list(hands), frame=np.zeros((H, W, 3), np.uint8))
    return load_gesture("crossed_fingers_plus", {}).detect(ctx)


VERTICAL = make_hand((320, 260), 90)
HORIZONTAL = make_hand((250, 190), 0)


def test_plus_detected():
    assert detect(VERTICAL, HORIZONTAL) is True


def test_x_not_detected():
    assert detect(make_hand((280, 260), 45), make_hand((360, 260), 135)) is False


def test_single_hand_not_detected():
    assert detect(VERTICAL) is False


def test_plus_not_touching_not_detected():
    assert detect(VERTICAL, make_hand((50, 190), 0)) is False


def test_open_hands_not_detected():
    assert detect(make_hand((320, 260), 90, open_hand=True), make_hand((250, 190), 0, open_hand=True)) is False


def test_direction_uses_pixels():
    import importlib.util
    from core.plugins import REPO_ROOT
    spec = importlib.util.spec_from_file_location("cfp", REPO_ROOT / "gestures/crossed_fingers_plus/gesture.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lm = [NS(x=0.5, y=0.5) for _ in range(21)]
    for i in (5, 9):
        lm[i] = NS(x=0.4, y=0.6)
    for i in (8, 12):
        lm[i] = NS(x=0.5, y=0.5)                       # relative dx = 0.1, dy = -0.1
    assert abs(mod.direction(NS(landmark=lm), W, H) - math.degrees(math.atan2(36, 64))) < 0.1


def test_needs_hands_only():
    assert load_gesture("crossed_fingers_plus", {}).needs == {"hands"}


def test_plus_crossing_just_past_fingertips_detected():
    """Tracking of overlapping hands is imprecise: a crossing a few px beyond the fingertips still counts."""
    assert detect(VERTICAL, make_hand((250, 165), 0)) is True

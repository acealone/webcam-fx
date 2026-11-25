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


def fold(hand, *fingers):
    """Fold the given fingers ((pip, tip) pairs): tip ends up closer to the wrist than the pip."""
    lm = list(hand.landmark)
    w0 = lm[0]
    for pip, tip in fingers:
        lm[pip] = NS(x=(lm[pip].x + w0.x) / 2, y=(lm[pip].y + w0.y) / 2)
        lm[tip] = NS(x=(lm[pip].x * 3 + w0.x) / 4, y=(lm[pip].y * 3 + w0.y) / 4)
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


def test_open_hands_plus_detected():
    """Fuzzy: any stretched fingers forming a plus count, not only index + middle."""
    assert detect(make_hand((320, 260), 90, open_hand=True), make_hand((250, 190), 0, open_hand=True)) is True


def test_only_index_fingers_crossing_detected():
    one_finger = lambda base, angle: fold(make_hand(base, angle), (10, 12))
    assert detect(one_finger((320, 260), 90), one_finger((250, 190), 0)) is True


def test_fists_not_detected():
    fist = lambda base, angle: fold(make_hand(base, angle), (6, 8), (10, 12))
    assert detect(fist((320, 260), 90), fist((250, 190), 0)) is False


def test_debug_text_explains_what_is_seen():
    g = load_gesture("crossed_fingers_plus", {})
    text = g.debug(NS(hands=[VERTICAL], frame=np.zeros((H, W, 3), np.uint8)))
    assert "hands 1" in text
    assert "crossing no" in text
    text = g.debug(NS(hands=[VERTICAL, HORIZONTAL], frame=np.zeros((H, W, 3), np.uint8)))
    assert "hands 2" in text and "crossing yes" in text


def test_direction_uses_pixels():
    import importlib.util
    from core.plugins import REPO_ROOT
    spec = importlib.util.spec_from_file_location("cfp", REPO_ROOT / "gestures/crossed_fingers_plus/gesture.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # relative dx = 0.1, dy = -0.1 on 640x360 is 64 px right, 36 px up
    assert abs(mod.direction((0.4 * W, 0.6 * H), (0.5 * W, 0.5 * H)) - math.degrees(math.atan2(36, 64))) < 0.1


def test_needs_hands_only():
    assert load_gesture("crossed_fingers_plus", {}).needs == {"hands"}


def test_plus_crossing_just_past_fingertips_detected():
    """Tracking of overlapping hands is imprecise: a crossing a few px beyond the fingertips still counts."""
    assert detect(VERTICAL, make_hand((250, 165), 0)) is True


ALL_FINGERS = ((3, 4), (6, 8), (10, 12), (14, 16), (18, 20))


def test_hidden_vertical_fingers_detected_by_hand_axis():
    """Upright hand behind the other: tracking reports its covered fingers as bent, the palm still points up."""
    hidden = fold(make_hand((320, 260), 90), *ALL_FINGERS)
    assert detect(hidden, HORIZONTAL) is True


def test_hand_axis_alone_on_both_sides_does_not_trigger():
    """Two hand axes without any stretched finger (e.g. two fists) are not a plus."""
    assert detect(fold(make_hand((320, 260), 90), *ALL_FINGERS), fold(make_hand((250, 190), 0), *ALL_FINGERS)) is False


def test_debug_counts_hand_axes():
    g = load_gesture("crossed_fingers_plus", {})
    hidden = fold(make_hand((320, 260), 90), *ALL_FINGERS)
    text = g.debug(NS(hands=[hidden, HORIZONTAL], frame=np.zeros((H, W, 3), np.uint8)))
    assert "vertical 0 (+1 hand)" in text and "crossing yes" in text

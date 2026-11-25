"""Index + middle finger of both hands crossed like a plus sign: one hand vertical, one horizontal."""
import math

TOLERANCE = 30   # degrees away from exactly vertical / horizontal that still count


def _dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def two_finger_pose(hand) -> bool:
    """Index and middle stretched, ring and pinky folded (same rule as two_fingers_forehead)."""
    p = hand.landmark
    ext = lambda tip, pip: _dist(p[tip], p[0]) > _dist(p[pip], p[0]) * 1.15
    curl = lambda tip, pip: _dist(p[tip], p[0]) < _dist(p[pip], p[0])
    return ext(8, 6) and ext(12, 10) and curl(16, 14) and curl(20, 18)


def _segment(hand, w, h):
    """Two-finger segment in pixels: from the knuckles (5/9) to the fingertips (8/12)."""
    p = hand.landmark
    base = ((p[5].x + p[9].x) / 2 * w, (p[5].y + p[9].y) / 2 * h)
    tip = ((p[8].x + p[12].x) / 2 * w, (p[8].y + p[12].y) / 2 * h)
    return base, tip


def direction(hand, w, h) -> float:
    """Finger direction in degrees 0..180 measured in pixels: 0 = horizontal, 90 = vertical."""
    (x0, y0), (x1, y1) = _segment(hand, w, h)
    return math.degrees(math.atan2(-(y1 - y0), x1 - x0)) % 180


def segments_cross(p1, p2, q1, q2) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (orient(p1, p2, q1) * orient(p1, p2, q2) < 0) and (orient(q1, q2, p1) * orient(q1, q2, p2) < 0)


def _vertical(angle):
    return abs(angle - 90) <= TOLERANCE


def _horizontal(angle):
    return angle <= TOLERANCE or angle >= 180 - TOLERANCE


class Gesture:
    needs = {"hands"}

    def __init__(self, settings: dict):
        self.settings = settings

    def detect(self, ctx) -> bool:
        h, w = ctx.frame.shape[:2]
        hands = [hd for hd in ctx.hands if two_finger_pose(hd)]
        for i, a in enumerate(hands):
            for b in hands[i + 1:]:
                da, db = direction(a, w, h), direction(b, w, h)
                if ((_vertical(da) and _horizontal(db)) or (_horizontal(da) and _vertical(db))) \
                        and segments_cross(*_segment(a, w, h), *_segment(b, w, h)):
                    return True
        return False

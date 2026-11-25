"""Fingers of both hands crossed like a plus sign: one hand's finger(s) vertical, the other's horizontal.

Fuzzy on purpose: any stretched finger counts (thumb included), bent fingers are ignored. Tracking of two
overlapping hands is imprecise, so angles get a generous tolerance and finger lines are extended a bit.
"""
import math

TOLERANCE = 35   # degrees away from exactly vertical / horizontal that still count
MARGIN = 0.25    # finger lines are extended by this share at both ends
STRETCHED = 1.1  # tip must be this much farther from the wrist than the middle joint
FINGERS = ((2, 3, 4), (5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20))   # (base, middle joint, tip)


def _dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def finger_lines(hand, w, h):
    """Pixel lines (base -> tip) of all stretched fingers of a hand."""
    p = hand.landmark
    return [((p[b].x * w, p[b].y * h), (p[t].x * w, p[t].y * h))
            for b, j, t in FINGERS if _dist(p[t], p[0]) > _dist(p[j], p[0]) * STRETCHED]


def direction(p0, p1) -> float:
    """Direction of a pixel line in degrees 0..180: 0 = horizontal, 90 = vertical."""
    return math.degrees(math.atan2(-(p1[1] - p0[1]), p1[0] - p0[0])) % 180


def _extend(line, margin):
    (x0, y0), (x1, y1) = line
    ex, ey = (x1 - x0) * margin, (y1 - y0) * margin
    return (x0 - ex, y0 - ey), (x1 + ex, y1 + ey)


def segments_cross(p1, p2, q1, q2) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (orient(p1, p2, q1) * orient(p1, p2, q2) < 0) and (orient(q1, q2, p1) * orient(q1, q2, p2) < 0)


def _vertical(line):
    return abs(direction(*line) - 90) <= TOLERANCE


def _horizontal(line):
    a = direction(*line)
    return a <= TOLERANCE or a >= 180 - TOLERANCE


def analyse(hands, w, h) -> dict:
    """Everything the gesture looks at, for detect() and the debug view."""
    lines = [finger_lines(hd, w, h) for hd in hands]
    crossing = False
    for i in range(len(lines)):
        for k in range(i + 1, len(lines)):
            for la in lines[i]:
                for lb in lines[k]:
                    if ((_vertical(la) and _horizontal(lb)) or (_horizontal(la) and _vertical(lb))) \
                            and segments_cross(*_extend(la, MARGIN), *_extend(lb, MARGIN)):
                        crossing = True
    flat = [ln for hand_lines in lines for ln in hand_lines]
    return {"hands": len(hands), "fingers": [len(x) for x in lines],
            "vertical": sum(map(_vertical, flat)), "horizontal": sum(map(_horizontal, flat)),
            "crossing": crossing}


class Gesture:
    needs = {"hands"}

    def __init__(self, settings: dict):
        self.settings = settings

    def detect(self, ctx) -> bool:
        h, w = ctx.frame.shape[:2]
        return analyse(ctx.hands, w, h)["crossing"]

    def debug(self, ctx) -> str:
        h, w = ctx.frame.shape[:2]
        a = analyse(ctx.hands, w, h)
        fingers = "/".join(map(str, a["fingers"])) or "-"
        return (f"plus: hands {a['hands']}, stretched fingers {fingers}, vertical {a['vertical']}, "
                f"horizontal {a['horizontal']}, crossing {'yes' if a['crossing'] else 'no'}")

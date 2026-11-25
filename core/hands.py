"""Hand geometry shared by gestures (mediapipe hand landmarks, relative coordinates -> pixels)."""
import math

FINGERS = ((2, 3, 4), (5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20))   # (base, middle joint, tip)
STRETCHED = 1.1   # tip must be this much farther from the wrist than the middle joint


def dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def finger_lines(hand, w, h):
    """Pixel lines (base -> tip) of all stretched fingers of a hand, thumb included."""
    p = hand.landmark
    return [((p[b].x * w, p[b].y * h), (p[t].x * w, p[t].y * h))
            for b, j, t in FINGERS if dist(p[t], p[0]) > dist(p[j], p[0]) * STRETCHED]


def hand_axis(hand, w, h):
    """Pixel line from the middle knuckle onwards, as long as the palm: where the fingers would be.
    Reliable even when the fingers are hidden behind something."""
    p = hand.landmark
    wx, wy, kx, ky = p[0].x * w, p[0].y * h, p[9].x * w, p[9].y * h
    return (kx, ky), (2 * kx - wx, 2 * ky - wy)


def palm_length(hand, w, h) -> float:
    p = hand.landmark
    return math.hypot((p[9].x - p[0].x) * w, (p[9].y - p[0].y) * h)


def direction(p0, p1) -> float:
    """Direction of a pixel line in degrees 0..180: 0 = horizontal, 90 = vertical."""
    return math.degrees(math.atan2(-(p1[1] - p0[1]), p1[0] - p0[0])) % 180


def extend(line, margin):
    (x0, y0), (x1, y1) = line
    ex, ey = (x1 - x0) * margin, (y1 - y0) * margin
    return (x0 - ex, y0 - ey), (x1 + ex, y1 + ey)


def segments_cross(p1, p2, q1, q2) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (orient(p1, p2, q1) * orient(p1, p2, q2) < 0) and (orient(q1, q2, p1) * orient(q1, q2, p2) < 0)

"""Index and middle finger stretched, ring and pinky folded, fingertips at your forehead."""


def _dist(a, b):
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def is_salute(hand, face) -> bool:
    p = hand.landmark
    ext = lambda tip, pip: _dist(p[tip], p[0]) > _dist(p[pip], p[0]) * 1.15   # finger stretched
    curl = lambda tip, pip: _dist(p[tip], p[0]) < _dist(p[pip], p[0])         # finger folded
    if not (ext(8, 6) and ext(12, 10) and curl(16, 14) and curl(20, 18)):
        return False
    fx, fy, fw, fh = face
    tx, ty = (p[8].x + p[12].x) / 2, (p[8].y + p[12].y) / 2                   # between both fingertips
    return fx - 0.2 * fw < tx < fx + 1.2 * fw and fy - 0.6 * fh < ty < fy + 0.35 * fh


class Gesture:
    needs = {"face", "hands"}

    def __init__(self, settings: dict):
        self.settings = settings

    def detect(self, ctx) -> bool:
        face = ctx.face
        return face is not None and any(is_salute(h, face) for h in ctx.hands)

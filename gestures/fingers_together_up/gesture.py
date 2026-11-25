"""Both hands together in front of you, stretched fingers of both hands pointing up side by side.

Lenient on purpose: any stretched finger pointing up counts, and a hand whose fingers are hidden behind
the other counts by its hand axis, but at least one real finger must point up.

Hands pressed together are often tracked as ONE hand. A single hand counts only if it looks like that:
pointing up, seen from the side (narrow knuckle row - a normal "peace" sign shows the palm, which is wide)
and in front of the chest (below the face, roughly centred under it).
"""
from core.hands import direction, finger_lines, hand_axis, palm_length

TOLERANCE = 35   # degrees away from exactly vertical that still count
CLOSE = 1.5      # knuckles of both hands at most this many palm lengths apart
SIDE = 0.55      # single hand: knuckle row (index..pinky) at most this many palm lengths wide
UNDER = 0.75     # single hand: at most this many face widths left/right of the face centre


def _up(line) -> bool:
    (x0, y0), (x1, y1) = line
    return abs(direction((x0, y0), (x1, y1)) - 90) <= TOLERANCE and y1 < y0   # vertical and tip above base


def _side_ratio(hand, w, h) -> float:
    p = hand.landmark
    width = (((p[5].x - p[17].x) * w) ** 2 + ((p[5].y - p[17].y) * h) ** 2) ** 0.5
    return width / max(1.0, palm_length(hand, w, h))


def _under_face(hand, face, w, h) -> bool:
    if face is None:
        return False
    fx, fy, fw, fh = face
    k = hand.landmark[9]
    return k.y * h > (fy + fh) * h and abs(k.x * w - (fx + fw / 2) * w) <= UNDER * fw * w


def analyse(hands, w, h, face=None) -> dict:
    up = [sum(map(_up, finger_lines(hd, w, h))) for hd in hands]
    axis_up = [_up(hand_axis(hd, w, h)) for hd in hands]
    best_gap, match = None, False
    for i in range(len(hands)):
        for k in range(i + 1, len(hands)):
            a, b = hands[i].landmark[9], hands[k].landmark[9]
            gap = ((a.x - b.x) * w) ** 2 + ((a.y - b.y) * h) ** 2
            gap = gap ** 0.5 / max(1.0, (palm_length(hands[i], w, h) + palm_length(hands[k], w, h)) / 2)
            best_gap = gap if best_gap is None else min(best_gap, gap)
            pointing = bool((up[i] or axis_up[i]) and (up[k] or axis_up[k]) and (up[i] or up[k]))
            match = match or (pointing and gap <= CLOSE)
    side = [_side_ratio(hd, w, h) for hd in hands]
    under = [_under_face(hd, face, w, h) for hd in hands]
    for i in range(len(hands)):                     # pressed hands tracked as one
        match = match or bool((up[i] or axis_up[i]) and side[i] <= SIDE and under[i])
    return {"hands": len(hands), "up": up, "axis_up": sum(axis_up), "gap": best_gap,
            "side": min(side) if side else None, "under": any(under), "match": match}


class Gesture:
    needs = {"hands", "face"}

    def __init__(self, settings: dict):
        self.settings = settings

    def detect(self, ctx) -> bool:
        h, w = ctx.frame.shape[:2]
        return analyse(ctx.hands, w, h, ctx.face)["match"]

    def debug(self, ctx) -> str:
        h, w = ctx.frame.shape[:2]
        a = analyse(ctx.hands, w, h, ctx.face)
        up = "/".join(map(str, a["up"])) or "-"
        gap = "-" if a["gap"] is None else f"{a['gap']:.1f}"
        side = "-" if a["side"] is None else f"{a['side']:.2f}"
        return (f"together: hands {a['hands']}, fingers up {up} (+{a['axis_up']} hand), "
                f"distance {gap} palms (max {CLOSE}), one hand: side {side} (max {SIDE}), "
                f"under face {'yes' if a['under'] else 'no'}, match {'yes' if a['match'] else 'no'}")

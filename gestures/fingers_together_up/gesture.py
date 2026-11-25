"""Both hands together in front of you, stretched fingers of both hands pointing up side by side.

Lenient on purpose: any stretched finger pointing up counts, and a hand whose fingers are hidden behind
the other counts by its hand axis, but at least one real finger must point up. A single hand never counts
(that would be a normal "peace" sign in a call).
"""
from core.hands import direction, finger_lines, hand_axis, palm_length

TOLERANCE = 35   # degrees away from exactly vertical that still count
CLOSE = 1.5      # knuckles of both hands at most this many palm lengths apart


def _up(line) -> bool:
    (x0, y0), (x1, y1) = line
    return abs(direction((x0, y0), (x1, y1)) - 90) <= TOLERANCE and y1 < y0   # vertical and tip above base


def analyse(hands, w, h) -> dict:
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
    return {"hands": len(hands), "up": up, "axis_up": sum(axis_up), "gap": best_gap, "match": match}


class Gesture:
    needs = {"hands"}

    def __init__(self, settings: dict):
        self.settings = settings

    def detect(self, ctx) -> bool:
        h, w = ctx.frame.shape[:2]
        return analyse(ctx.hands, w, h)["match"]

    def debug(self, ctx) -> str:
        h, w = ctx.frame.shape[:2]
        a = analyse(ctx.hands, w, h)
        up = "/".join(map(str, a["up"])) or "-"
        gap = "-" if a["gap"] is None else f"{a['gap']:.1f}"
        return (f"together: hands {a['hands']}, fingers up {up} (+{a['axis_up']} hand), "
                f"distance {gap} palms (max {CLOSE}), match {'yes' if a['match'] else 'no'}")

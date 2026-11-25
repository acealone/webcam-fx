"""Fingers of both hands crossed like a plus sign: one hand's finger(s) vertical, the other's horizontal.

Fuzzy on purpose: any stretched finger counts (thumb included), bent fingers are ignored. Tracking of two
overlapping hands is imprecise, so angles get a generous tolerance and finger lines are extended a bit.
A hand whose fingers are hidden behind the other hand still counts by its hand axis (wrist -> knuckles,
continued to about the fingertips), but at least one side of the plus must be a real stretched finger.
"""
from core.hands import direction, extend, finger_lines, hand_axis, segments_cross

TOLERANCE = 35   # degrees away from exactly vertical / horizontal that still count
MARGIN = 0.25    # finger lines are extended by this share at both ends


def _vertical(line):
    return abs(direction(*line) - 90) <= TOLERANCE


def _horizontal(line):
    a = direction(*line)
    return a <= TOLERANCE or a >= 180 - TOLERANCE


def analyse(hands, w, h) -> dict:
    """Everything the gesture looks at, for detect() and the debug view."""
    fingers = [finger_lines(hd, w, h) for hd in hands]
    axes = [hand_axis(hd, w, h) for hd in hands]
    candidates = [[(ln, True) for ln in f] + [(ax, False)] for f, ax in zip(fingers, axes)]
    crossing = False
    for i in range(len(hands)):
        for k in range(i + 1, len(hands)):
            for la, a_finger in candidates[i]:
                for lb, b_finger in candidates[k]:
                    if (a_finger or b_finger) \
                            and ((_vertical(la) and _horizontal(lb)) or (_horizontal(la) and _vertical(lb))) \
                            and segments_cross(*extend(la, MARGIN), *extend(lb, MARGIN)):
                        crossing = True
    flat = [ln for f in fingers for ln in f]
    return {"hands": len(hands), "fingers": [len(f) for f in fingers],
            "vertical": sum(map(_vertical, flat)), "horizontal": sum(map(_horizontal, flat)),
            "vertical_hands": sum(map(_vertical, axes)), "horizontal_hands": sum(map(_horizontal, axes)),
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
        return (f"plus: hands {a['hands']}, stretched fingers {fingers}, "
                f"vertical {a['vertical']} (+{a['vertical_hands']} hand), "
                f"horizontal {a['horizontal']} (+{a['horizontal_hands']} hand), "
                f"crossing {'yes' if a['crossing'] else 'no'}")

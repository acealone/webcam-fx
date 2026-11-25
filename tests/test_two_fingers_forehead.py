from types import SimpleNamespace as NS

from core.plugins import load_gesture

FACE = (0.4, 0.2, 0.2, 0.25)          # xmin, ymin, width, height (relative)


def hand(points, dx=0.0, dy=0.0):
    lm = [NS(x=0.5 + dx, y=0.6 + dy) for _ in range(21)]          # everything at the wrist by default
    for i, (x, y) in points.items():
        lm[i] = NS(x=x + dx, y=y + dy)
    return NS(landmark=lm)


SALUTE = {5: (0.48, 0.48), 6: (0.48, 0.40), 8: (0.48, 0.25),       # index stretched up
          10: (0.52, 0.40), 12: (0.52, 0.25),                       # middle stretched up
          14: (0.55, 0.45), 16: (0.55, 0.52),                       # ring folded
          18: (0.58, 0.47), 20: (0.57, 0.53)}                       # pinky folded
OPEN = {**SALUTE, 16: (0.55, 0.25), 20: (0.58, 0.30)}               # ring + pinky stretched too


def detect(h, face=FACE):
    return load_gesture("two_fingers_forehead", {}).detect(NS(face=face, hands=[h]))


def test_salute_at_forehead_detected():
    assert detect(hand(SALUTE)) is True


def test_open_hand_not_detected():
    assert detect(hand(OPEN)) is False


def test_salute_away_from_face_not_detected():
    assert detect(hand(SALUTE, dy=0.3)) is False


def test_no_face_not_detected():
    assert detect(hand(SALUTE), face=None) is False


def test_needs_face_and_hands():
    assert load_gesture("two_fingers_forehead", {}).needs == {"face", "hands"}

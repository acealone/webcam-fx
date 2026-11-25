from types import SimpleNamespace as NS

import numpy as np

from core.plugins import load_gesture
from tests.test_crossed_fingers_plus import ALL_FINGERS, fold, make_hand

H, W = 360, 640


FACE = (0.42, 0.1, 0.16, 0.3)              # relative face box above the hands, centred at x = 320 px


def detect(*hands, face=FACE):
    ctx = NS(hands=list(hands), face=face, frame=np.zeros((H, W, 3), np.uint8))
    return load_gesture("fingers_together_up", {}).detect(ctx)


LEFT = make_hand((305, 300), 90)          # two hands side by side, fingers pointing up, pressed together
RIGHT = make_hand((335, 300), 90)


def test_hands_together_fingers_up_detected():
    assert detect(LEFT, RIGHT) is True


def test_hands_apart_not_detected():
    assert detect(make_hand((150, 300), 90), make_hand((500, 300), 90)) is False


def test_single_hand_not_detected():
    """A single hand with two fingers up is a normal 'peace' sign in a call."""
    assert detect(LEFT) is False


def test_fingers_pointing_down_not_detected():
    assert detect(make_hand((305, 150), 270), make_hand((335, 150), 270)) is False


def test_plus_pose_not_detected():
    assert detect(make_hand((320, 260), 90), make_hand((250, 190), 0)) is False


def test_two_fists_not_detected():
    assert detect(fold(LEFT, *ALL_FINGERS), fold(RIGHT, *ALL_FINGERS)) is False


def test_hidden_back_hand_detected_by_hand_axis():
    assert detect(fold(LEFT, *ALL_FINGERS), RIGHT) is True


def test_debug_text():
    g = load_gesture("fingers_together_up", {})
    text = g.debug(NS(hands=[LEFT, RIGHT], face=FACE, frame=np.zeros((H, W, 3), np.uint8)))
    assert text.startswith("together:") and "hands 2" in text and "match yes" in text


# Pressed together, tracking often sees ONE hand, seen from the side (narrow knuckle row), in front of the chest.
SIDE_VIEW = make_hand((320, 300), 90, spread=0.2)


def test_single_hand_seen_from_side_in_front_of_chest_detected():
    assert detect(SIDE_VIEW) is True


def test_single_palm_facing_hand_not_detected():
    """A normal peace sign shows the palm: the knuckle row is wide."""
    assert detect(make_hand((320, 300), 90)) is False


def test_single_side_hand_off_to_the_side_not_detected():
    assert detect(make_hand((560, 300), 90, spread=0.2)) is False


def test_single_side_hand_without_face_not_detected():
    assert detect(SIDE_VIEW, face=None) is False


def test_single_side_hand_above_the_face_line_not_detected():
    assert detect(make_hand((320, 120), 90, spread=0.2)) is False


def test_debug_shows_single_hand_checks():
    g = load_gesture("fingers_together_up", {})
    text = g.debug(NS(hands=[SIDE_VIEW], face=FACE, frame=np.zeros((H, W, 3), np.uint8)))
    assert "side 0." in text and "under face yes" in text and "match yes" in text


def test_needs_face_and_hands():
    assert load_gesture("fingers_together_up", {}).needs == {"hands", "face"}

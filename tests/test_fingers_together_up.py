from types import SimpleNamespace as NS

import numpy as np

from core.plugins import load_gesture
from tests.test_crossed_fingers_plus import ALL_FINGERS, fold, make_hand

H, W = 360, 640


def detect(*hands):
    return load_gesture("fingers_together_up", {}).detect(NS(hands=list(hands), frame=np.zeros((H, W, 3), np.uint8)))


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
    text = g.debug(NS(hands=[LEFT, RIGHT], frame=np.zeros((H, W, 3), np.uint8)))
    assert text.startswith("together:") and "hands 2" in text and "match yes" in text

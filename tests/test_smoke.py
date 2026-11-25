import numpy as np

from core.smoke import SMOKE_COLOR, paint, smoke_alpha

H, W = 360, 640


def test_smoke_deterministic_and_fades():
    a, b = smoke_alpha((H, W), [(200, 180)], 0.3, 7.0), smoke_alpha((H, W), [(200, 180)], 0.3, 7.0)
    assert np.array_equal(a, b)
    assert a[180, 200] > 0.5
    assert smoke_alpha((H, W), [(200, 180)], 1.0, 7.0).max() < 0.05


def test_smoke_spread_is_adjustable():
    narrow = smoke_alpha((H, W), [(320, 180)], 0.3, 1.0, spread=(0.05, 0.05))
    wide = smoke_alpha((H, W), [(320, 180)], 0.3, 1.0, spread=(0.30, 0.40))
    assert (wide > 0.1).sum() > 2 * (narrow > 0.1).sum()


def test_paint_only_touches_the_alpha_box():
    canvas = np.zeros((H, W, 3), np.float32)
    alpha = np.zeros((H, W), np.float32)
    alpha[10:20, 30:40] = 1.0
    paint(canvas, SMOKE_COLOR, alpha)
    assert (canvas[15, 35] == SMOKE_COLOR).all()
    assert canvas[100, 100].max() == 0

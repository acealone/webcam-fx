"""Image compositing helpers."""
import numpy as np


def blend(person: np.ndarray, mask: np.ndarray, bg: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """Person over background. mask: HxWx1 float 0..1, alpha scales the whole person."""
    a = mask * alpha
    return np.clip(person * a + bg * (1 - a), 0, 255).astype(np.uint8)

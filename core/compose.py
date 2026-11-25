"""Image compositing helpers."""
import numpy as np


def blend(person: np.ndarray, mask: np.ndarray, bg: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """Person over background. mask: HxWx1 float 0..1, alpha scales the whole person.
    Same as person*a + bg*(1-a), computed in place as bg + (person - bg)*a (runs on every frame)."""
    a = mask if alpha == 1.0 else mask * np.float32(alpha)
    out = person.astype(np.float32)
    out -= bg
    out *= a
    out += bg
    np.clip(out, 0, 255, out=out)
    return out.astype(np.uint8)

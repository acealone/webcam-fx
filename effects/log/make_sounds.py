"""make_sounds.py - generates the original sounds of the log effect: poof.wav (smoke) and clonk.wav (wood)."""
import os, wave

import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(23)


def save(name, x):
    x = (x / np.abs(x).max() * 0.8 * 32767).astype(np.int16)
    with wave.open(os.path.join(HERE, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes())
    print("wrote", name)


t = np.linspace(0, 0.5, int(SR * 0.5), endpoint=False)                    # poof: muffled burst + low thump
noise = np.convolve(rng.standard_normal(len(t)), np.ones(30) / 30, mode="same")
noise *= np.minimum(1, t / 0.005) * np.exp(-t / 0.12)
thump = np.sin(2 * np.pi * np.cumsum(120 * 0.5 ** (t / 0.5)) / SR) * np.exp(-t / 0.08)
save("poof.wav", 0.7 * noise / np.abs(noise).max() + 0.5 * thump)

t = np.linspace(0, 0.35, int(SR * 0.35), endpoint=False)                  # clonk: hollow wooden knock
knock = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
            for f, a, tau in ((380, 1.0, 0.07), (776, 0.6, 0.045), (1150, 0.35, 0.03), (1730, 0.2, 0.02)))
click = np.zeros_like(t); click[:120] = rng.standard_normal(120) * np.hanning(240)[120:]
save("clonk.wav", knock + 0.4 * click)

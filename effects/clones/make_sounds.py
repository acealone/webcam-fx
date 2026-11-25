"""make_sounds.py - generates the original "poof" sound (poof.wav) for the clones effect."""
import os, wave

import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(11)

t = np.linspace(0, 0.5, int(SR * 0.5), endpoint=False)
noise = np.convolve(rng.standard_normal(len(t)), np.ones(30) / 30, mode="same")   # muffled burst
noise *= np.minimum(1, t / 0.005) * np.exp(-t / 0.12)
freq = 120 * (60 / 120) ** (t / 0.5)                                              # low thump, falling
thump = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.08)
x = 0.7 * noise / np.abs(noise).max() + 0.5 * thump
x = (x / np.abs(x).max() * 0.8 * 32767).astype(np.int16)
with wave.open(os.path.join(HERE, "poof.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes())
print("wrote poof.wav")

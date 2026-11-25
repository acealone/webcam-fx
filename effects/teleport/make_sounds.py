"""make_sounds.py - generates original teleport sound effects (teleport_out.wav / teleport_in.wav).

Replace the WAV files with your own clips if you like; teleport_cam.py just plays whatever is there.
"""
import os, wave
import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7)

def zip_sound(f0, f1, dur):
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    freq = f0 * (f1 / f0) ** (t / dur)                                   # exponential pitch sweep
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR + 0.8 * np.sin(2 * np.pi * 35 * t))  # with shimmer
    whoosh = np.convolve(rng.standard_normal(len(t)), np.ones(6) / 6, mode="same")      # airy noise
    env = np.minimum(1, t / 0.008) * np.exp(-t / (dur * 0.4))           # quick attack, fast decay
    click = np.zeros_like(t); click[:220] = np.hanning(440)[220:] * rng.standard_normal(220)
    return (0.6 * tone + 0.35 * whoosh) * env + 0.5 * click

def save(name, x):
    x = (x / np.abs(x).max() * 0.8 * 32767).astype(np.int16)
    with wave.open(os.path.join(HERE, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes())
    print("wrote", name)

save("teleport_out.wav", zip_sound(350, 2800, 0.35))   # rising "zip" when you vanish
save("teleport_in.wav", zip_sound(2800, 350, 0.35))    # falling "zip" when you reappear

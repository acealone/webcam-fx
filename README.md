# webcam-fx

Gesture-triggered webcam effects for video calls (Microsoft Teams, or anything that accepts a webcam).
Make a gesture in front of your camera and an effect plays on your video — for example, put two fingers
to your forehead and you **teleport** away: torn by vertical slits, gone for a moment, then back.

It runs on Windows. Your webcam goes in, the processed picture goes out through **OBS Virtual Camera**,
which you select as the camera in Teams.

## Setup (once)

1. **Install OBS Studio** — it provides the "OBS Virtual Camera" device. OBS itself doesn't need to run.
   ```powershell
   winget install OBSProject.OBSStudio
   ```
2. **Install Python 3.12** (`winget install Python.Python.3.12`).
3. **Create the environment** in the repo folder:
   ```powershell
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
   `mediapipe` is pinned to 0.10.21 on purpose: newer releases remove the API used here.

## Use

```powershell
.venv\Scripts\python run.py
```

1. A preview window opens. Click it, press **`b`** and step out of the picture: 5 seconds later the empty
   room is captured as your background and saved to `data/background.png` (reused on every start).
2. In Teams: **Settings → Devices → Camera → OBS Virtual Camera**.
   If it's missing, quit Teams completely (tray icon → Quit) and start it again.
3. Make a gesture. With the default config: index and middle finger stretched, ring and pinky folded,
   fingertips against your forehead for 0.3 s → teleport.

Keys in the preview window:

| Key | Action |
|-----|--------|
| `b` | capture a new background (5 s countdown, overwrites `data/background.png`) |
| `d` | debug view: output, background, person mask side by side |
| `q` | quit |

The green line at the bottom shows fps and how many milliseconds each step takes.
After an effect, its gesture is locked until you release it (see `rearm` below), so holding your
fingers to your head doesn't teleport you again and again.

## Configuration — `config.toml`

```toml
[camera]
index = 0          # which webcam
width = 640        # 640x480 keeps most USB webcams at 30 fps; 1280x720 is often only ~7 fps
height = 480
fps = 30

[[triggers]]                       # one block per gesture -> effect pair
gesture = "two_fingers_forehead"   # folder name in gestures/
effect = "teleport"                # folder name in effects/
hold = 0.3                         # seconds the gesture must be held
rearm = 0.5                        # seconds the gesture must be gone before it can trigger again

[effects.teleport]                 # settings passed to the effect
fade = 0.35
gone = 2.5
```

If several triggers match at the same moment, the first one in the file wins. Only one effect runs at a time.
Settings for a gesture go in `[gestures.<name>]`, the same way.

## Project layout

```
run.py                 entry point
config.toml            which gesture triggers which effect, plus settings
core/                  camera, person mask, background, triggers, plugin loading, sound, main loop
gestures/<name>/       one folder per gesture  (gesture.py)
effects/<name>/        one folder per effect   (effect.py + its sounds/assets)
tests/                 pytest, runs without a camera
data/                  local runtime files (background.png) - not committed
```

Everything runs in one program because only one app can use the webcam and the virtual camera at a time.

## Add a gesture

Create `gestures/<name>/gesture.py`:

```python
class Gesture:
    needs = {"face", "hands"}          # shared detections you use: "face", "hands"

    def __init__(self, settings: dict):  # your [gestures.<name>] table from config.toml
        self.settings = settings

    def detect(self, ctx) -> bool:       # called every frame while no effect runs
        return ...                       # True while the gesture is shown
```

`ctx` gives you `frame` (BGR image), `rgb`, `mask` (person mask, HxWx1, 0..1), `bg` (background plate),
`now` (seconds), `face` (`(xmin, ymin, width, height)` relative to the frame, last known box, or `None`)
and `hands` (mediapipe hand landmarks). `face` and `hands` are computed only when a gesture uses them.

## Add an effect

Create `effects/<name>/effect.py`:

```python
class Effect:
    def __init__(self, settings: dict, folder):  # your [effects.<name>] table; folder = effects/<name>/
        ...

    def start(self, ctx):                         # the gesture fired
        ...

    def render(self, ctx):                        # every frame until done
        return output_frame, done                 # BGR image, True when finished
```

Put sounds and other assets next to `effect.py` and load them via `folder`. Useful helpers:
`core.compose.blend(person, mask, bg, alpha)` and `core.sound.play(path)` (non-blocking WAV).

Then connect it in `config.toml` with a `[[triggers]]` block.

## Tests

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

## Known limits

- Windows only (DirectShow camera, `winsound`).
- Sound effects play on your PC only; other call participants don't hear them yet
  (that needs a virtual audio device).
- New Teams may not list OBS Virtual Camera on every setup; Teams in the browser does.

## License

MIT — see [LICENSE](LICENSE). The teleport sounds are generated by `effects/teleport/make_sounds.py`.

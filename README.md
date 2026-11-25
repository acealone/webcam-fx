# webcam-fx

Gesture-triggered webcam effects for video calls (Microsoft Teams, or anything that accepts a webcam).
Make a gesture in front of your camera and an effect plays on your video:

| Gesture | Effect |
|---------|--------|
| **Two fingers to the forehead** — index and middle finger stretched, ring and pinky folded, fingertips against your forehead | **teleport** — you get torn by vertical slits, vanish for a moment, and come back the same way |
| **Crossed fingers, plus sign** — stretched fingers of both hands crossing like a `+` (not an `x`): one hand's finger(s) pointing up, the other's sideways. Any fingers count, and the upright hand may be hidden behind the other | **clones** — smoke bursts left and right of you, two copies of you appear in it, stay a few seconds and vanish in smoke again |
| **Fingers together, pointing up** — both hands pressed together in front of your chest (below your face), stretched fingers of both hands pointing up side by side. Works even when the camera merges your pressed hands into one hand | **log** — a smoke bomb goes off, a wooden log stands where you were, and after a few seconds another smoke bomb brings you back |

It runs on Windows and Linux. Your webcam goes in, the processed picture goes out through a virtual camera
(**OBS Virtual Camera** on Windows, **v4l2loopback** on Linux), which you select as the camera in Teams.

## Setup on Windows (once)

For Linux see [Linux](#linux).

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
3. Make a gesture from the table above and hold it for 0.3 s.

The picture is 16:9 (640x360). If you change the camera size, the saved background no longer fits:
the program says so at startup — press `b` once to capture a new one.

Keys in the preview window:

| Key | Action |
|-----|--------|
| `b` | capture a new background (5 s countdown, overwrites `data/background.png`) |
| `d` | debug view: output, background, person mask side by side, plus what each gesture sees (e.g. how many hands) — also printed to the terminal twice per second, so you can copy it afterwards |
| `q` | quit |

The green line at the bottom shows fps and how many milliseconds each step takes.
After an effect, its gesture is locked until you release it (see `rearm` below), so holding your
fingers to your head doesn't teleport you again and again.

## Linux

Tested setup: Python 3.12 via [uv](https://docs.astral.sh/uv/), the `v4l2loopback` kernel module as virtual
camera, PortAudio for sound (all effect sounds through one open audio output, so nothing gets cut off; without
it the system player `pw-play`, `paplay` or `aplay` is used).
`mediapipe` 0.10.21 has no packages for Python 3.13+, which is why uv fetches Python 3.12 for this project.

### 1. Install the packages

The kernel module is built for your kernel (DKMS), so the **headers of the kernel you run** are needed.

**Arch Linux**
```bash
sudo pacman -S --needed uv v4l2loopback-dkms v4l-utils portaudio linux-headers   # linux-lts -> linux-lts-headers, linux-zen -> linux-zen-headers
```

**CachyOS**
```bash
sudo pacman -S --needed uv v4l2loopback-dkms v4l-utils portaudio linux-cachyos-headers
# other CachyOS kernels need their own headers, e.g. linux-cachyos-lts -> linux-cachyos-lts-headers
# (pacman -Q | grep linux-cachyos shows which kernel you have)
```

**Ubuntu / Debian**
```bash
sudo apt install v4l2loopback-dkms v4l-utils libportaudio2 linux-headers-$(uname -r)
curl -LsSf https://astral.sh/uv/install.sh | sh      # or: pipx install uv
```

**Fedora**
```bash
# v4l2loopback comes from RPM Fusion (free)
sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install v4l2loopback v4l-utils portaudio uv
```

With **Secure Boot** enabled, the freshly built kernel module must be signed (DKMS/akmods guide you through
enrolling a key), otherwise `modprobe` fails with "Key was rejected by service".

### 2. Create the environment (in the repo folder)

```bash
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
```

### 3. Load the virtual camera

Once (until the next reboot):
```bash
sudo modprobe v4l2loopback devices=1 exclusive_caps=1 card_label=webcam-fx
```
Permanently:
```bash
echo v4l2loopback | sudo tee /etc/modules-load.d/v4l2loopback.conf
echo "options v4l2loopback devices=1 exclusive_caps=1 card_label=webcam-fx" | sudo tee /etc/modprobe.d/v4l2loopback.conf
```
`exclusive_caps=1` is needed so browsers (and Teams in them) list the camera.

### 4. Pick your webcam and run

```bash
v4l2-ctl --list-devices
```
Your webcam shows up with one or more `/dev/videoN` nodes — use the **first** one as `index` in
`config.toml` (`/dev/video2` → `index = 2`). Don't pick the `webcam-fx` entry: that's the output.

```bash
.venv/bin/python run.py
```

### 5. Teams on Linux

Microsoft has no Teams desktop app for Linux anymore. Use Teams in **Chrome / Edge / Firefox**
(teams.microsoft.com), or the community app **teams-for-linux** (AUR `teams-for-linux-bin`, Flatpak
`com.github.IsmaelMartinez.teams_for_linux`), and choose **webcam-fx** as camera.

On **Wayland** (KDE, GNOME) the preview window runs through XWayland, which is installed by default.
If it doesn't open, start with `QT_QPA_PLATFORM=xcb .venv/bin/python run.py`.

## Configuration — `config.toml`

```toml
[camera]
index = 0          # which webcam
width = 640        # 640x360 (16:9) keeps most USB webcams at 30 fps; bigger sizes are often 7-20 fps
height = 360
fps = 30

[[triggers]]                       # one block per gesture -> effect pair
gesture = "two_fingers_forehead"   # folder name in gestures/
effect = "teleport"                # folder name in effects/
hold = 0.3                         # seconds the gesture must be held
rearm = 0.5                        # seconds the gesture must be gone before it can trigger again

[[triggers]]                       # before the plus: pressed-together hands can look like a plus too
gesture = "fingers_together_up"
effect = "log"

[[triggers]]
gesture = "crossed_fingers_plus"
effect = "clones"

[effects.teleport]                 # settings passed to the effect
fade = 0.35                        # seconds to vanish / reappear
gone = 2.5                         # seconds invisible

[effects.clones]
duration = 4.0                     # seconds the clones stay
scale = 0.85                       # clone size (they stand a bit further back)
offset = 0.32                      # distance from the centre, as a fraction of the width
smoke = 0.6                        # seconds per smoke burst

[effects.log]
duration = 3.0                     # seconds you stay a log
smoke = 0.6
```

The log is drawn by code. To use your own picture instead, put a `log.png` (ideally with a transparent
background) into `effects/log/` — it is scaled to your height.

Sounds play through one audio output that stays open (`[sound] mixer = true`), so they don't cut each
other off and wireless headsets don't swallow their beginning. The terminal shows the output at startup
(`sound: mixer on '...'`). With `mixer = false` the system player is used instead (one sound at a time).

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
.venv\Scripts\python -m pip install -r requirements-dev.txt     # Linux: uv pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest                                    # Linux: .venv/bin/python -m pytest
```

Timing checks depend on the machine and are skipped by default; run them with `pytest -m perf`.

## Known limits

- Windows and Linux only (no macOS).
- Sound effects play on your PC only; other call participants don't hear them yet
  (that needs a virtual audio device).
- New Teams may not list OBS Virtual Camera on every setup; Teams in the browser does.

## License

MIT — see [LICENSE](LICENSE). All sounds are original and generated by the `make_sounds.py` in each effect folder.

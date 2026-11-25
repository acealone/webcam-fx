# webcam-fx: repo structure for gestures and effects

Date: 2026-11-25 · Status: draft for approval

## Intent

The teleport webcam (one script, `%USERPROFILE%\teleport\teleport_cam.py`) becomes a GitHub
project. More gestures and effects will follow, so each gesture and each effect gets its own folder,
and a settings file decides which gesture triggers which effect. Output goes to Microsoft Teams via
OBS Virtual Camera, as today.

## Goals

- Split the current script into a shared **core** plus one **gesture** (`two_fingers_forehead`) and
  one **effect** (`teleport`), with no change in behaviour (see "Behaviour to keep").
- Gestures and effects are independent and combined in `config.toml`.
- Adding a gesture or effect = new folder + a line in `config.toml`. The core is not edited.
- A README that lets someone (or future-you) set it up from zero on Windows.

## Non-goals (for now)

- New gestures or effects.
- Virtual microphone / sound into Teams (waits for VB-Cable, separate task).
- 720p capture, GUI, installer/exe, pip packaging.
- Running several effects at the same time.

## Anti-goals (failure even if it "works")

- Committing `background.png` (photo of the user's room), the anime reference image, the venv, or any
  copyrighted sound/image.
- Any regression of current behaviour: re-arm lock, saved background, background capture with `b`,
  frame rate, sound.
- A core that has to be edited for every new effect or gesture.

## Constraints

- Windows only; runs in the Windows Python 3.12 venv (not WSL: no webcam there).
- **One process** owns the webcam and the virtual camera, so all gestures/effects run inside one
  program. Plugins are modules loaded by that program, not separate scripts.
- `mediapipe==0.10.21` pinned (newer releases drop `mp.solutions`), `numpy<2`, `opencv-python`,
  `pyvirtualcam`. OBS Studio installed for the virtual camera driver.
- Camera default 640x480 @ 30 (measured: the C310/index 0 gives 7.4 fps at 720p, 29 fps at 480p).

## Approaches

- **A) One folder per gesture and per effect, discovered by folder name — picked.** Each plugin keeps
  its own assets (sounds, models) next to its code; core stays untouched when adding plugins.
- B) One flat file per gesture/effect, shared `assets/` folder. Less nesting, but assets drift away
  from their effect and gestures with helper files get messy. Not picked.
- C) Installable pip plugins (entry points). Overkill for a personal project. Dropped.

## Design

### Layout

```
webcam-fx/                         (e.g. %USERPROFILE%\webcam-fx)
├─ run.py                          entry point: python run.py [--config config.toml]
├─ config.toml                     camera, background, triggers, per-plugin settings
├─ requirements.txt                pinned runtime deps
├─ README.md
├─ .gitignore                      .venv/, data/, __pycache__/, *.pyc
├─ data/                           git-ignored, created at runtime: background.png
├─ core/
│  ├─ app.py                       main loop, preview window, keys, timing overlay
│  ├─ camera.py                    open webcam (index/size/fps, MJPG attempt, prints format)
│  ├─ background.py                plate: load/save data/background.png, auto-learn, b-capture
│  ├─ context.py                   per-frame Context (see below)
│  ├─ triggers.py                  hold time + re-arm lock per trigger
│  ├─ plugins.py                   discovery/loading of gestures/* and effects/*
│  └─ sound.py                     play(path) non-blocking (winsound)
├─ gestures/
│  └─ two_fingers_forehead/gesture.py
├─ effects/
│  └─ teleport/
│     ├─ effect.py                 state sequence out → gone → in, tear(), sounds
│     ├─ make_sounds.py            regenerates the two WAVs (original sounds)
│     ├─ teleport_out.wav
│     └─ teleport_in.wav
├─ tests/                          pytest, no camera needed
└─ docs/superpowers/specs/         this document
```

### Plugin contracts

- A **gesture** is `gestures/<name>/gesture.py` with `class Gesture`:
  - `__init__(self, settings: dict)` — its `[gestures.<name>]` table from config (may be empty).
  - `needs: set[str]` — which shared detections it uses (`"face"`, `"hands"`), so the core only runs
    the models some armed gesture needs.
  - `detect(self, ctx) -> bool` — is the gesture present in this frame.
- An **effect** is `effects/<name>/effect.py` with `class Effect`:
  - `__init__(self, settings: dict, folder: Path)` — its `[effects.<name>]` table, plus its own folder
    for assets.
  - `start(self, ctx)` — called when triggered (teleport plays its out-sound here).
  - `render(self, ctx) -> tuple[np.ndarray, bool]` — output frame and `done`.
- Discovery: `<name>` in config = folder name. Unknown name or missing class → clear error at startup
  listing the available names.

### Per-frame Context

Built once per frame by the core and passed to gestures and effects:
`frame` (BGR), `rgb`, `mask` (person segmentation, HxWx1 float), `bg` (current background plate),
`now`, and lazily computed `face` (last known face box, cached when the hand covers the face) and
`hands` (hand landmarks). Segmentation runs every frame (needed for background learning and effects);
face/hands whenever no effect is running and some configured trigger's gesture needs them, *including
locked triggers* (releasing a lock depends on seeing the gesture is gone). The cached face box survives
effect runs.

When no effect runs, the output is the person blended over the background plate (as today), not the
raw camera frame.

### Triggers

- `config.toml` holds a list of `[[triggers]]` with `gesture`, `effect`, optional `hold` (default 0.3 s)
  and `rearm` (default 0.5 s).
- While an effect runs, no gestures are evaluated (as today). After a trigger fires, it stays locked
  until its gesture has been absent for `rearm` seconds in a row (today's behaviour, now per trigger).
- If several triggers match in the same frame, the first in the file wins.

### Behaviour to keep (current script = reference)

Background: `data/background.png` loaded on start if size matches (else ignored with a message);
`b` = 5 s countdown, capture, save, lock; auto-learn only while no plate is locked and no effect runs,
skipping a dilated margin around the person. Keys: `b`, `d` (debug view: output | plate | mask),
`q`. Preview hints (no plate / countdown / trigger locked) and the green timing overlay. Teleport:
FADE 0.35 s, GONE 2.5 s, slit/step/streak tearing with fixed seed per transition, no wrap-around,
sounds on vanish and reappear.

### config.toml (shape)

```toml
[camera]
index = 0
width = 640
height = 480
fps = 30

[[triggers]]
gesture = "two_fingers_forehead"
effect = "teleport"
hold = 0.3
rearm = 0.5

[effects.teleport]
fade = 0.35
gone = 2.5
```

### Tests (pytest, no camera)

- Trigger hold + re-arm lock, simulated at 30 fps with hold 0.3 s / rearm 0.5 s, run in sequence
  (these passed against the current script and are the regression guard):
  1. gesture held 1 s → fires once at ~0.33 s, then locked
  2. gesture still held 3 s after the effect → no fire, stays locked
  3. held 3 s with every 5th frame missed by hand tracking → no fire, stays locked
  4. gesture absent only 0.3 s → stays locked
  5. gesture held again 1 s → no fire (still locked)
  6. gesture absent 0.7 s → unlocks
  7. gesture held 1 s → fires again
  Plus: hold shorter than 0.3 s doesn't fire; a missed frame during the hold restarts the hold;
  with two triggers matching the same frame, the first in the file wins.
- `tear()`: no wrap-around, same seed → same result, amount 1 removes everything.
- Background load: size mismatch ignored, missing file handled.
- Plugin discovery: loads `two_fingers_forehead` and `teleport`; unknown name → clear error.
- Config loading with defaults.
- Live check on the webcam is done by the user (Claude cannot see the camera).

### Environment and migration

- New repo folder `%USERPROFILE%\webcam-fx`, own `.venv` inside it (git-ignored); README shows
  setup with `python -m venv .venv` + `pip install -r requirements.txt`.
- The old `%USERPROFILE%\teleport` folder is left untouched; the user deletes it when happy.
- Existing `background.png` is copied to `data/` so no recapture is needed.
- Git: local repo on `main`, remote `https://github.com/acealone/webcam-fx.git` (exists, **public**,
  empty). Push only after the user has seen the result.
- Because the repo is public: no personal paths or names in committed files (use `%USERPROFILE%` /
  relative paths in README and docs), and commits use an author email the user has approved.

## Decided by the user

- License: **MIT** (`LICENSE` in repo root, copyright holder: the GitHub account `acealone`).
- Commit author email: **GitHub noreply** (`32741143+acealone@users.noreply.github.com`), set in the
  repo's local git config only (global configs stay unchanged).

## Calls made by Claude (check these)

- Pinned versions = what works in the old venv: mediapipe 0.10.21, numpy 1.26.4,
  opencv-python 4.11.0.86, pyvirtualcam 0.15.0; pytest only for development.
- Runtime data (background.png) lives in git-ignored `data/`.
- New `.venv` inside the repo; old teleport folder untouched.
- Generic preview hint when a trigger is locked: "<gesture> locked - release the gesture".
- Tests run in the Windows `.venv` (`.venv\Scripts\python -m pytest`).
- Commit author name and MIT copyright holder = `acealone` (not the real name), to match the
  noreply choice. Easy to change before the first push.

## Left to the builder

Internal function names, exact split of helper code inside `core/`, README wording, test file layout.

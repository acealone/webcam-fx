# Linux support

Date: 2026-11-25 · Status: approved by the user in chat

## Intent
webcam-fx should also run on well-known Linux distros: Arch / CachyOS (the user's own), Ubuntu / Debian,
Fedora. Output goes to a v4l2loopback virtual camera that Teams (browser or teams-for-linux) can select.

## Design
- `core/sound.py`: Windows → `winsound` as today. Linux → first available of `pw-play`, `paplay`, `aplay`
  started with `subprocess.Popen` (non-blocking, output discarded); no player or a failing player → silent.
- `core/camera.py`: capture backend per platform — DirectShow on Windows, V4L2 on Linux.
  `[camera] index` = `/dev/video<index>` on Linux.
- `core/app.py`: the "virtual camera could not start" hint per platform (OBS on Windows, v4l2loopback
  `modprobe` line on Linux). pyvirtualcam picks the loopback device itself.
- Platform checks read a module attribute (`PLATFORM = sys.platform`) so tests can switch it.
- README: Linux section per distro family — packages (uv, v4l2loopback, v4l-utils, kernel headers),
  Python 3.12 via `uv` (mediapipe 0.10.21 has no wheels for 3.13+), loading the module (once and
  permanently), finding the webcam index, Teams options, Secure Boot note, Wayland note.

## Verification
All tests on Windows as before; Linux code paths tested platform-independently by switching `PLATFORM`;
full suite additionally run under Linux in WSL (Ubuntu) with a uv-managed Python 3.12 venv outside the
repo. Live test with webcam/loopback/Teams: the user on CachyOS.

## Non-goals
macOS, packaging (AUR/Flatpak), a loopback setup script.

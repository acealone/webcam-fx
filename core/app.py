"""Main loop: webcam -> gestures/effects -> OBS Virtual Camera, plus a preview window."""
import time
from pathlib import Path

import cv2
import numpy as np
import pyvirtualcam

from core.background import Background
from core.camera import open_camera
from core.compose import blend
from core.context import Context, Detectors
from core.plugins import REPO_ROOT, load_effect, load_gesture
from core.triggers import Trigger, fire_first

KEYS_HELP = "Preview window: b = capture background (5 s delay), d = debug view, q = quit"


def run(config: dict, background_path: Path = REPO_ROOT / "data" / "background.png") -> None:
    # load all plugins first, so a typo in config.toml fails before the camera is opened
    gestures = {t["gesture"]: load_gesture(t["gesture"], config["gestures"].get(t["gesture"], {}))
                for t in config["triggers"]}
    effects = {t["effect"]: load_effect(t["effect"], config["effects"].get(t["effect"], {}))
               for t in config["triggers"]}
    triggers = [Trigger(t["gesture"], t["effect"], t["hold"], t["rearm"]) for t in config["triggers"]]
    if not triggers:
        print("No [[triggers]] in config.toml - the camera works, but no gesture does anything")

    cam_cfg = config["camera"]
    cap, frame = open_camera(cam_cfg["index"], cam_cfg["width"], cam_cfg["height"], cam_cfg["fps"])
    h, w = frame.shape[:2]
    detectors = Detectors.create()
    background = Background(background_path, frame)
    active, debug, timing = None, False, {}

    def tick(stage, t0):   # per-stage time in ms (smoothed) for the overlay
        t1 = time.perf_counter()
        timing[stage] = 0.9 * timing.get(stage, (t1 - t0) * 1000) + 0.1 * (t1 - t0) * 1000
        return t1

    try:
        with pyvirtualcam.Camera(w, h, cam_cfg["fps"], fmt=pyvirtualcam.PixelFormat.BGR) as cam:
            print(f"Streaming to {cam.device}. {KEYS_HELP}")
            while True:
                t0 = time.perf_counter()
                ok, frame = cap.read()
                if not ok:
                    break
                now = time.time()
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                t0 = tick("camera", t0)

                mask = detectors.segment(rgb)
                if active is None:                 # never learn the background mid-effect
                    background.learn(frame, mask)
                t0 = tick("segment", t0)

                ctx = Context(frame, mask, background.plate, now, detectors, rgb)
                if active is None and triggers:   # face/hands only run if a gesture asks for them
                    fired = fire_first(triggers, [gestures[t.gesture].detect(ctx) for t in triggers], now)
                    if fired:
                        active = effects[fired.effect]
                        active.start(ctx)
                t0 = tick("gesture", t0)

                if active is not None:
                    out, done = active.render(ctx)
                    if done:
                        active = None
                else:
                    out = blend(frame, mask, background.plate)
                cam.send(out)
                t0 = tick("compose", t0)

                # preview only (not sent to Teams): debug view = output | background plate | person mask
                preview = out
                if debug:
                    mask_img = cv2.cvtColor((mask[..., 0] * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
                    preview = np.hstack([out, background.plate, mask_img])
                preview = cv2.resize(preview, None, fx=0.33 if debug else 0.5, fy=0.33 if debug else 0.5)
                countdown = background.countdown(now)
                locked = [t for t in triggers if t.locked]
                if countdown is not None:
                    hint = f"Step out of frame! Capturing background in {countdown:.0f} s"
                elif not background.locked:
                    hint = "No clean background yet - press b, then step out of frame"
                elif active is None and locked:
                    hint = f"{locked[0].gesture} locked - release the gesture"
                else:
                    hint = ""
                if hint:
                    cv2.putText(preview, hint, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                stats = (f"{1000 / max(sum(timing.values()), 1):.0f} fps | "
                         + " ".join(f"{s} {v:.0f}" for s, v in timing.items()) + " ms")
                cv2.putText(preview, stats, (10, preview.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
                cv2.imshow("webcam-fx preview", preview)

                key = cv2.waitKey(1) & 0xFF
                t0 = tick("preview", t0)
                if key == ord("q"):
                    break
                if key == ord("d"):
                    debug = not debug
                if key == ord("b"):
                    background.start_capture(now)
                background.update(frame, now)
    finally:
        cap.release()
        cv2.destroyAllWindows()

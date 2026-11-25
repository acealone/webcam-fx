"""Open the webcam."""
import cv2


def open_camera(index: int, width: int, height: int, fps: int):
    """Returns (cap, first_frame). Exits with a clear message if the camera gives no frame."""
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))   # ignored by some webcams
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    ok, frame = cap.read() if cap.isOpened() else (False, None)
    if not ok:
        cap.release()
        raise SystemExit("No webcam frame - close Teams/other apps using the camera "
                         "or change [camera] index in config.toml")
    fourcc = (int(cap.get(cv2.CAP_PROP_FOURCC)) & 0xFFFFFFFF).to_bytes(4, "little").decode(errors="replace")
    h, w = frame.shape[:2]
    print(f"Camera delivers {w}x{h} as {fourcc!r}, driver reports {cap.get(cv2.CAP_PROP_FPS):.0f} fps")
    return cap, frame

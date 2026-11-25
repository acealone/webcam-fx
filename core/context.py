"""Shared per-frame data and the detection models gestures/effects use."""
import cv2


class Detectors:
    """Owns the mediapipe models. Pass stand-ins in tests; use Detectors.create() for the real ones."""

    def __init__(self, segmenter=None, face_model=None, hands_model=None):
        self.segmenter, self.face_model, self.hands_model = segmenter, face_model, hands_model
        self.last_face = None   # kept across frames and effects: your hand may hide your face

    @classmethod
    def create(cls):
        import mediapipe as mp
        return cls(
            mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1),
            mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6),
            mp.solutions.hands.Hands(max_num_hands=2, min_detection_confidence=0.6, min_tracking_confidence=0.5),
        )

    def segment(self, rgb):
        """Person mask, HxWx1 float 0..1, slightly blurred."""
        return cv2.GaussianBlur(self.segmenter.process(rgb).segmentation_mask, (0, 0), 3)[..., None]

    def face(self, rgb):
        """(xmin, ymin, width, height) relative to the frame; last known box if none is found now."""
        det = self.face_model.process(rgb).detections
        if det:
            b = det[0].location_data.relative_bounding_box
            self.last_face = (b.xmin, b.ymin, b.width, b.height)
        return self.last_face

    def hands(self, rgb):
        return self.hands_model.process(rgb).multi_hand_landmarks or []


class Context:
    """Everything a gesture or effect may look at for the current frame."""

    def __init__(self, frame, mask, bg, now, detectors, rgb=None):
        self.frame, self.mask, self.bg, self.now, self.detectors = frame, mask, bg, now, detectors
        self.rgb = rgb if rgb is not None else cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._face = self._hands = None
        self._face_done = False

    @property
    def face(self):
        if not self._face_done:                  # run the model at most once per frame
            self._face, self._face_done = self.detectors.face(self.rgb), True
        return self._face

    @property
    def hands(self):
        if self._hands is None:
            self._hands = self.detectors.hands(self.rgb)
        return self._hands



import os
import urllib.request

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "hand_landmarker.task")



class LegacyBackend:
    name = "mediapipe.solutions (legacy)"

    def __init__(self, max_hands=2, det_conf=0.6, track_conf=0.5):
        hands_mod = self._find_hands_module()
        if hands_mod is None:
            raise ImportError("mp.solutions.hands unavailable")
        self._hands = hands_mod.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=det_conf,
            min_tracking_confidence=track_conf,
        )

    @staticmethod
    def _find_hands_module():
        try:
            import mediapipe as mp
            return mp.solutions.hands
        except (ImportError, AttributeError):
            pass
        
        try:
            import mediapipe.python.solutions.hands as hands
            return hands
        except (ImportError, AttributeError):
            pass
        # (c) from-import form
        try:
            from mediapipe.solutions import hands
            return hands
        except (ImportError, AttributeError):
            pass
        return None

    def hands(self, rgb, timestamp_ms):
        res = self._hands.process(rgb)
        out = []
        if res.multi_hand_landmarks:
            for hand in res.multi_hand_landmarks:
                out.append([(lm.x, lm.y) for lm in hand.landmark])
        return out

    def wrists(self, rgb, timestamp_ms):
        return [h[0] for h in self.hands(rgb, timestamp_ms)]

    def close(self):
        try:
            self._hands.close()
        except Exception:  # noqa: BLE001
            pass



def ensure_model(path=MODEL_PATH, url=MODEL_URL, quiet=False):
    """Download the hand landmarker model bundle if we don't have it."""
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not quiet:
        print(f"[gesture] downloading hand model (~7 MB) -> {path}")
    urllib.request.urlretrieve(url, path)
    if not quiet:
        print("[gesture] model ready")
    return path


class TasksBackend:
    name = "mediapipe Tasks HandLandmarker"

    def __init__(self, max_hands=2, det_conf=0.6, track_conf=0.5,
                 model_path=MODEL_PATH):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        ensure_model(model_path)

        
        try:
            self._Image = mp.Image
            self._ImageFormat = mp.ImageFormat
        except AttributeError:
            from mediapipe.python._framework_bindings.image import Image
            from mediapipe.python._framework_bindings.image_frame import ImageFormat
            self._Image = Image
            self._ImageFormat = ImageFormat

        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=det_conf,
            min_tracking_confidence=track_conf,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts = -1

    def hands(self, rgb, timestamp_ms):
        ts = int(timestamp_ms)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts

        mp_img = self._Image(image_format=self._ImageFormat.SRGB, data=rgb)
        res = self._landmarker.detect_for_video(mp_img, ts)
        out = []
        for hand in (res.hand_landmarks or []):
            out.append([(lm.x, lm.y) for lm in hand])
        return out

    def wrists(self, rgb, timestamp_ms):
        return [h[0] for h in self.hands(rgb, timestamp_ms)]

    def close(self):
        try:
            self._landmarker.close()
        except Exception:  # noqa: BLE001
            pass


def make_backend(max_hands=2, det_conf=0.6, track_conf=0.5):
    errors = []
    for cls in (LegacyBackend, TasksBackend):
        try:
            backend = cls(max_hands=max_hands, det_conf=det_conf,
                          track_conf=track_conf)
            print(f"[gesture] using {backend.name}")
            return backend
        except Exception as e:  # noqa: BLE001
            errors.append(f"  - {cls.__name__}: {type(e).__name__}: {e}")
    raise RuntimeError(
        "no hand-tracking backend available:\n" + "\n".join(errors)
    )



WRIST = 0
FINGER_MCP = (5, 9, 13, 17)     
FINGER_TIP = (8, 12, 16, 20)    


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def extended_fingers(landmarks, ratio: float = 1.35) -> int:
    
    if not landmarks or len(landmarks) < 21:
        return 0
    wrist = landmarks[WRIST]
    n = 0
    for mcp_i, tip_i in zip(FINGER_MCP, FINGER_TIP):
        d_mcp = _dist(landmarks[mcp_i], wrist)
        if d_mcp < 1e-6:
            continue
        if _dist(landmarks[tip_i], wrist) / d_mcp > ratio:
            n += 1
    return n


def is_open_palm(landmarks, ratio: float = 1.35, min_fingers: int = 3) -> bool:
    return extended_fingers(landmarks, ratio) >= min_fingers
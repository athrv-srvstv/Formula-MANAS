

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
        
        try:
            from mediapipe.solutions import hands
            return hands
        except (ImportError, AttributeError):
            pass
        return None

    def wrists(self, rgb, timestamp_ms):
        res = self._hands.process(rgb)
        out = []
        if res.multi_hand_landmarks:
            for hand in res.multi_hand_landmarks:
                w = hand.landmark[0]        
                out.append((w.x, w.y))
        return out

    def close(self):
        try:
            self._hands.close()
        except Exception:  
            pass



def ensure_model(path=MODEL_PATH, url=MODEL_URL, quiet=False):
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

    def wrists(self, rgb, timestamp_ms):
        
        ts = int(timestamp_ms)
        if ts <= self._last_ts:
            ts = self._last_ts + 1
        self._last_ts = ts

        mp_img = self._Image(image_format=self._ImageFormat.SRGB, data=rgb)
        res = self._landmarker.detect_for_video(mp_img, ts)
        out = []
        for hand in (res.hand_landmarks or []):
            w = hand[0]                    
            out.append((w.x, w.y))
        return out

    def close(self):
        try:
            self._landmarker.close()
        except Exception:  
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
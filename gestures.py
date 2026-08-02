

import math
import threading
import time

import config as C


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class GestureInput:
    name = "gesture"

    def __init__(self, cam_index: int = 0):
        self.ok = False
        self._steer = 0.0
        self._throttle = 0.0
        self._lock = threading.Lock()
        self._running = True
        self._hands_seen = False
        self._neutral = C.THROTTLE_NEUTRAL
        self._calibrate_request = False
        self._last_mid_y = None

        
        import cv2
        from hand_tracking import make_backend

        self._cv2 = cv2
        self._cap = cv2.VideoCapture(cam_index)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"could not open camera {cam_index} "
                "(in use by another app, or no camera present?)"
            )
        
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self._backend = make_backend(
            max_hands=2, det_conf=0.6, track_conf=0.5
        )

        self.ok = True
        self._t0 = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    
    def _loop(self):
        cv2 = self._cv2
        while self._running:
            grabbed, frame = self._cap.read()
            if not grabbed:
                time.sleep(0.01)
                continue

            frame = cv2.flip(frame, 1)              
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ts_ms = (time.time() - self._t0) * 1000.0

            try:
                wrists = self._backend.wrists(rgb, ts_ms)
            except Exception:  
                wrists = []

            with self._lock:
                steer, throttle = self._steer, self._throttle

            if len(wrists) >= 2:
                self._hands_seen = True
                wrists.sort(key=lambda p: p[0])     
                (lx, ly), (rx, ry) = wrists[0], wrists[1]

                angle = math.degrees(math.atan2(ry - ly, rx - lx))
                steer = _clamp(angle / C.WHEEL_MAX_DEG, -1.0, 1.0)

                mid_y = (ly + ry) / 2.0
                self._last_mid_y = mid_y

                
                if self._calibrate_request:
                    self._neutral = mid_y
                    self._calibrate_request = False
                    print(f"[gesture] neutral set to {mid_y:.3f} "
                          f"(raise hands = gas, lower = brake)")

                
                rng = max(C.THROTTLE_RANGE, 1e-6)
                raw = (self._neutral - mid_y) / rng
                if abs(raw) < C.THROTTLE_DEADZONE:
                    raw = 0.0
                throttle = _clamp(raw, -1.0, 1.0)

                if C.SHOW_CAMERA_DEBUG:
                    self._annotate(frame, (lx, ly), (rx, ry), steer, throttle,
                                   mid_y)
            else:
                
                if not C.THROTTLE_HOLD_ON_LOST:
                    throttle = 0.0
                steer *= 0.7
                if C.SHOW_CAMERA_DEBUG:
                    self._hint(frame, len(wrists))

            with self._lock:
                a = C.GESTURE_SMOOTHING
                self._steer = (1 - a) * self._steer + a * steer
                self._throttle = (1 - a) * self._throttle + a * throttle

            if C.SHOW_CAMERA_DEBUG:
                cv2.imshow("wheel (press q to hide)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    C.SHOW_CAMERA_DEBUG = False
                    cv2.destroyAllWindows()

    
    def _annotate(self, frame, lp, rp, steer, throttle, mid_y=None):
        cv2 = self._cv2
        h, w = frame.shape[:2]
        p1 = (int(lp[0] * w), int(lp[1] * h))
        p2 = (int(rp[0] * w), int(rp[1] * h))

        
        ny = int(self._neutral * h)
        cv2.line(frame, (0, ny), (w, ny), (120, 120, 120), 1)
        cv2.putText(frame, "neutral", (w - 90, ny - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 1)
        
        gy = int((self._neutral - C.THROTTLE_RANGE) * h)
        by = int((self._neutral + C.THROTTLE_RANGE) * h)
        cv2.line(frame, (0, gy), (w, gy), (0, 180, 0), 1)
        cv2.line(frame, (0, by), (w, by), (0, 0, 200), 1)

        cv2.line(frame, p1, p2, (0, 220, 0), 4)
        cv2.circle(frame, p1, 12, (0, 120, 255), -1)
        cv2.circle(frame, p2, 12, (0, 120, 255), -1)

        col = (0, 220, 0) if throttle > 0.05 else (
            (0, 0, 255) if throttle < -0.05 else (200, 200, 200))
        cv2.putText(frame, f"steer {steer:+.2f}  gas {throttle:+.2f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2)
        if mid_y is not None:
            cv2.putText(frame, f"hands y {mid_y:.2f}  neutral {self._neutral:.2f}",
                        (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 255, 255), 1)
        cv2.putText(frame, "press C in GAME window to recalibrate",
                    (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (200, 200, 200), 1)

    def _hint(self, frame, n_found):
        cv2 = self._cv2
        msg = "show BOTH hands" if n_found < 2 else ""
        if msg:
            cv2.putText(frame, msg, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0, 200, 255), 2)

    
    def read(self):
        with self._lock:
            return self._steer, self._throttle

    def calibrate(self):
        
        self._calibrate_request = True
        print("[gesture] hold the wheel comfortably... calibrating")

    def close(self):
        self._running = False
        try:
            self._backend.close()
        except Exception:  
            pass
        try:
            if getattr(self, "_cap", None) is not None:
                self._cap.release()
        except Exception:  
            pass
        try:
            self._cv2.destroyAllWindows()
        except Exception:  
            pass


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
        self._narrow = C.THROTTLE_GRIP_NARROW
        self._wide = C.THROTTLE_GRIP_WIDE
        self._span = C.THROTTLE_CALIBRATE_SPAN
        self._calibrate_request = False
        self._last_grip = None

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
            except Exception:  # noqa: BLE001 - never kill the thread
                wrists = []

            with self._lock:
                steer, throttle = self._steer, self._throttle

            if len(wrists) >= 2:
                self._hands_seen = True
                wrists.sort(key=lambda p: p[0])     # left hand first by x
                (lx, ly), (rx, ry) = wrists[0], wrists[1]

                angle = math.degrees(math.atan2(ry - ly, rx - lx))
                steer = _clamp(angle / C.WHEEL_MAX_DEG, -1.0, 1.0)

                
                grip = math.hypot(rx - lx, ry - ly)
                self._last_grip = grip

                if self._calibrate_request:
                    half = self._span / 2.0
                    self._narrow = max(grip - half, 0.02)
                    self._wide = grip + half
                    self._calibrate_request = False
                    print(f"[gesture] coast width set to {grip:.3f} "
                          f"(gas below {self._narrow:.3f}, "
                          f"brake above {self._wide:.3f})")

                span = max(self._wide - self._narrow, 1e-6)
                raw = 1.0 - 2.0 * (grip - self._narrow) / span
                if abs(raw) < C.THROTTLE_DEADZONE:
                    raw = 0.0
                throttle = _clamp(raw, -1.0, 1.0)

                if C.SHOW_CAMERA_DEBUG:
                    self._annotate(frame, (lx, ly), (rx, ry), steer, throttle,
                                   grip)
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

    def _annotate(self, frame, lp, rp, steer, throttle, grip=None):
        cv2 = self._cv2
        h, w = frame.shape[:2]
        p1 = (int(lp[0] * w), int(lp[1] * h))
        p2 = (int(rp[0] * w), int(rp[1] * h))

       
        if throttle > 0.05:
            line_col = (0, 220, 0)          # green = accelerating
        elif throttle < -0.05:
            line_col = (0, 0, 255)          # red = braking
        else:
            line_col = (200, 200, 200)      # grey = coasting
        cv2.line(frame, p1, p2, line_col, 4)
        cv2.circle(frame, p1, 12, (0, 120, 255), -1)
        cv2.circle(frame, p2, 12, (0, 120, 255), -1)

        bar_y = h - 40
        x0, x1 = 20, w - 20
        cv2.line(frame, (x0, bar_y), (x1, bar_y), (90, 90, 90), 3)

        def bx(val):
            lo, hi = self._narrow, self._wide
            t = (val - lo) / max(hi - lo, 1e-6)
            t = min(max(t, 0.0), 1.0)
            return int(x0 + t * (x1 - x0))

        cv2.line(frame, (bx(self._narrow), bar_y - 12),
                 (bx(self._narrow), bar_y + 12), (0, 220, 0), 3)
        cv2.line(frame, (bx(self._wide), bar_y - 12),
                 (bx(self._wide), bar_y + 12), (0, 0, 255), 3)
        cv2.putText(frame, "GAS", (bx(self._narrow) - 14, bar_y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 0), 1)
        cv2.putText(frame, "BRAKE", (bx(self._wide) - 24, bar_y + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        if grip is not None:
            cv2.circle(frame, (bx(grip), bar_y), 9, line_col, -1)

        cv2.putText(frame, f"steer {steer:+.2f}   gas {throttle:+.2f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, line_col, 2)
        if grip is not None:
            cv2.putText(frame,
                        f"grip {grip:.3f}  (gas<{self._narrow:.2f} "
                        f"brake>{self._wide:.2f})",
                        (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 255, 255), 1)
        cv2.putText(frame, "hands CLOSE = go, WIDE = slow   |   C = calibrate",
                    (10, h - 62), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
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
#
    def calibrate(self):
       
        self._calibrate_request = True
        print("[gesture] hold hands at coast width... calibrating")

    def close(self):
        self._running = False
        try:
            self._backend.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            if getattr(self, "_cap", None) is not None:
                self._cap.release()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._cv2.destroyAllWindows()
        except Exception:  # noqa: BLE001
            pass


import json
import socket
import threading
import time
from collections import deque
from typing import Optional

import config as C


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _sane(msg) -> bool:
    
    if not isinstance(msg, dict):
        return False
    for key, limit in (("pos", 1e9), ("x", 1e6), ("speed", 1e6)):
        v = msg.get(key)
        if v is None:
            continue
        if not isinstance(v, (int, float)):
            return False
        if v != v or abs(v) > limit:      
            return False
    steer = msg.get("steer")
    if steer is not None and (not isinstance(steer, (int, float))
                              or steer != steer or abs(steer) > 10):
        return False
    return True


class NetworkPeer:
    def __init__(self, is_host: bool, host_ip: str, port: int):
        self.is_host = is_host
        self.port = port
        self.peer_addr = None if is_host else (host_ip, port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if is_host:
            self.sock.bind(("0.0.0.0", port))
        self.sock.settimeout(0.5)

        
        self._buf = deque(maxlen=32)
        self._last_seq = -1
        self._recv_times = deque(maxlen=60)   
        self._seq = 0                 
        self._lock = threading.Lock()
        self._running = True

        self._rx = threading.Thread(target=self._recv_loop, daemon=True)
        self._rx.start()

    def _recv_loop(self):
        while self._running:
            try:
                data, addr = self.sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                msg = json.loads(data.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if not _sane(msg):
                continue          
            if self.is_host:
                self.peer_addr = addr

            seq = msg.get("seq", 0)
            now = time.time()
            with self._lock:
                
                if seq <= self._last_seq and self._last_seq - seq < 1000:
                    continue
                self._last_seq = seq
                self._buf.append((now, msg))
                self._recv_times.append(now)

    def send(self, state: dict):
        if self.peer_addr is None:
            return  
        self._seq += 1
        state = dict(state, seq=self._seq)
        try:
            self.sock.sendto(json.dumps(state).encode("utf-8"), self.peer_addr)
        except OSError:
            pass

    @property
    def remote(self) -> Optional[dict]:
        with self._lock:
            return self._buf[-1][1] if self._buf else None

    def remote_interpolated(self, delay: Optional[float] = None,
                            track_len: Optional[float] = None) -> Optional[dict]:
        
        with self._lock:
            buf = list(self._buf)
            interval = self._mean_interval()

        if not buf:
            return None

        if delay is None:
            delay = max(min(interval * 2.0, 0.25), 0.03)

        render_at = time.time() - delay
        newest_t, newest_s = buf[-1]

        if render_at >= newest_t:
           
            dt = min(render_at - newest_t, C.NET_MAX_EXTRAPOLATE)
            pos = newest_s.get("pos", 0.0) + newest_s.get("speed", 0.0) * dt
            if track_len:
                pos %= track_len
            return {**newest_s, "pos": pos}

        if render_at <= buf[0][0]:
            return dict(buf[0][1])

        lo, hi = buf[0], buf[-1]
        for a, b in zip(buf, buf[1:]):
            if a[0] <= render_at <= b[0]:
                lo, hi = a, b
                break

        t_prev, s_prev = lo
        t_curr, s_curr = hi
        span = t_curr - t_prev
        if span <= 1e-6:
            return dict(s_curr)

        a = (render_at - t_prev) / span
        a = 0.0 if a < 0.0 else (1.0 if a > 1.0 else a)

        p0 = s_prev.get("pos", 0.0)
        p1 = s_curr.get("pos", 0.0)
        if track_len:
           
            if p1 - p0 < -track_len / 2.0:
                p1 += track_len
            elif p1 - p0 > track_len / 2.0:
                p0 += track_len
            pos = (p0 + (p1 - p0) * a) % track_len
        else:
            pos = p0 + (p1 - p0) * a

        return {
            **s_curr,
            "pos": pos,
            "x": _lerp(s_prev.get("x", 0.0), s_curr.get("x", 0.0), a),
            "steer": _lerp(s_prev.get("steer", 0.0), s_curr.get("steer", 0.0), a),
            "speed": _lerp(s_prev.get("speed", 0.0), s_curr.get("speed", 0.0), a),
        }

    def _mean_interval(self) -> float:
        n = len(self._recv_times)
        if n < 2:
            return 1.0 / 60.0
        span = self._recv_times[-1] - self._recv_times[0]
        return span / (n - 1) if span > 0 else 1.0 / 60.0

    def connected(self, timeout: float = 2.0) -> bool:
        with self._lock:
            return bool(self._buf) and \
                (time.time() - self._buf[-1][0]) < timeout

    def stats(self) -> dict:
        with self._lock:
            n = len(self._recv_times)
            rate = 0.0
            if n >= 2:
                span = self._recv_times[-1] - self._recv_times[0]
                if span > 0:
                    rate = (n - 1) / span
            return {"pps": rate, "seq": self._last_seq}

    def close(self):
        self._running = False
        try:
            self.sock.close()
        except OSError:
            pass
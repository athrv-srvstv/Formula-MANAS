
import config as C


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Player:
    def __init__(self, name: str = "P1"):
        self.name = name
        self.pos = 0.0        
        self.x = 0.0          
        self.speed = 0.0     
        self.steer = 0.0      
        
        self.speed_mult = 1.0

    def update(self, dt: float, steer_in: float, throttle_in: float,
               curve_here: float, track_len: float):
        steer_in = _clamp(steer_in, -1.0, 1.0)
        throttle_in = _clamp(throttle_in, -1.0, 1.0)

        self.steer += (steer_in - self.steer) * min(C.STEER_RESPONSE * dt, 1.0)

        mult = max(self.speed_mult, 0.1)
        if throttle_in > 0:
            self.speed += C.ACCEL * mult * throttle_in * dt
        elif throttle_in < 0:
            self.speed += C.BRAKE * throttle_in * dt   # throttle_in is negative
        else:
            self.speed -= C.FRICTION * dt

        cap = (C.MAX_SPEED if abs(self.x) <= C.ROAD_W
               else C.OFFROAD_MAX_SPEED) * mult
        self.speed = _clamp(self.speed, 0.0, cap)

        
        comp = 1.0 / (mult ** C.STEER_SPEED_COMPENSATION)
        self.x += self.steer * C.STEER_STRENGTH * comp * self.speed * dt
        self.x -= curve_here * C.CENTRIFUGAL * self.speed * dt
        self.x = _clamp(self.x, -C.X_BOUND, C.X_BOUND)

        self.pos += self.speed * dt
        while self.pos >= track_len:
            self.pos -= track_len
        while self.pos < 0:
            self.pos += track_len

    def state(self) -> dict:
        return {
            "name": self.name,
            "pos": round(self.pos, 2),
            "x": round(self.x, 2),
            "steer": round(self.steer, 3),
            "speed": round(self.speed, 1),
        }
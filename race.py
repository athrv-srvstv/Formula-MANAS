

import time

import config as C

WAITING = "waiting"
COUNTDOWN = "countdown"
RACING = "racing"
FINISHED = "finished"


def _fmt(t: float) -> str:
    if t is None:
        return "--:--.---"
    m = int(t // 60)
    s = t - m * 60
    return f"{m}:{s:06.3f}"


class Race:
    def __init__(self, total_laps: int = None, countdown: float = None):
        self.total_laps = total_laps or C.RACE_TOTAL_LAPS
        self.countdown_len = (countdown if countdown is not None
                              else C.RACE_COUNTDOWN)
        
        self.state = WAITING
        self.timer = self.countdown_len

        self.lap = 1
        self.lap_times = []
        self.race_time = 0.0
        self._lap_start = 0.0
        self.finish_time = None
        self.best_lap = None

        self.opponent_finished_at = None
        self.place = None

        self._flash = 0.0          # "LAP 2" banner timer
        self._banner = ""

    def update(self, dt: float, opponent_ready: bool = True) -> bool:
        
        if self._flash > 0.0:
            self._flash = max(self._flash - dt, 0.0)

        if self.state == WAITING:
            if opponent_ready:
                self.state = COUNTDOWN
                self.timer = self.countdown_len
            return False

        if self.state == COUNTDOWN:
            if not opponent_ready:          # peer dropped -- go back to wait
                self.state = WAITING
                self.timer = self.countdown_len
                return False
            self.timer -= dt
            if self.timer <= 0.0:
                self.state = RACING
                self.race_time = 0.0
                self._lap_start = 0.0
                self._banner = "GO!"
                self._flash = C.RACE_BANNER_TIME
            return False                    # engine held during countdown

        if self.state == RACING:
            self.race_time += dt
            return True

        return False                        

    def check_lap(self, prev_pos: float, new_pos: float, track_len: float):
        if self.state != RACING:
            return

        half = track_len / 2.0
        delta = new_pos - prev_pos

        if delta < -half:                  
            self._complete_lap()
        elif delta > half:                  
            if self.lap > 1:
                self.lap -= 1

    def _complete_lap(self):
        split = self.race_time - self._lap_start
        self.lap_times.append(split)
        self._lap_start = self.race_time
        if self.best_lap is None or split < self.best_lap:
            self.best_lap = split

        if self.lap >= self.total_laps:
            self.state = FINISHED
            self.finish_time = self.race_time
            self._banner = "FINISH!"
            self._flash = C.RACE_BANNER_TIME * 2.5
        else:
            self.lap += 1
            self._banner = f"LAP {self.lap}  -  SPEED UP!"
            self._flash = C.RACE_BANNER_TIME

    def speed_multiplier(self) -> float:
        
        m = 1.0 + (self.lap - 1) * C.RACE_LAP_SPEED_STEP
        return min(m, C.RACE_LAP_SPEED_MAX)

    @property
    def counting_down(self) -> bool:
        return self.state == COUNTDOWN

    @property
    def waiting(self) -> bool:
        return self.state == WAITING

    @property
    def finished(self) -> bool:
        return self.state == FINISHED

    def countdown_text(self) -> str:
        n = int(self.timer) + 1
        return str(max(n, 1))

    def banner(self):
        if self._flash <= 0.0 or not self._banner:
            return None, 0.0
        peak = C.RACE_BANNER_TIME * (2.5 if self._banner == "FINISH!" else 1.0)
        return self._banner, max(min(self._flash / peak, 1.0), 0.0)

    def note_opponent(self, remote_state: dict):
        if remote_state is None or self.opponent_finished_at is not None:
            return
        if remote_state.get("done"):
            self.opponent_finished_at = remote_state.get("rt", 0.0)

    def resolve_place(self):
        if not self.finished or self.place is not None:
            return
        if self.opponent_finished_at is None:
            self.place = 1
        else:
            self.place = 1 if self.finish_time <= self.opponent_finished_at else 2

    def summary_lines(self):
        out = [f"TIME  {_fmt(self.finish_time)}"]
        if self.best_lap is not None:
            out.append(f"BEST LAP  {_fmt(self.best_lap)}")
        for i, t in enumerate(self.lap_times, 1):
            out.append(f"  lap {i}   {_fmt(t)}")
        if self.place:
            out.append("")
            out.append("1st place!" if self.place == 1 else "2nd place")
        return out


format_time = _fmt
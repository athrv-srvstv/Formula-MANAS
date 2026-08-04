"""Race flow: countdown -> racing -> finished.

STATES
------
  COUNTDOWN : engine held, "3 / 2 / 1 / GO!" on screen. Both peers count
              down independently but start from the same wall-clock moment
              (see sync note below), so neither gets a head start.
  RACING    : normal play. Laps are counted, lap times recorded.
  FINISHED  : the player has completed TOTAL_LAPS. Their car coasts to a
              stop and the results are shown. The other player can keep
              going until they finish too.

LAP DETECTION
-------------
`player.pos` already wraps from ~track_len back to 0 in player.update(), so
a lap is simply "pos jumped backwards by more than half the track". Checking
the jump size (rather than just pos < prev) means reversing over the line
doesn't wrongly award a lap -- and it decrements instead, so you can't farm
laps by rocking back and forth across the start.

START SYNC
----------
Both machines run their own countdown. The host stamps its intended start
time into the packets it sends; the client adopts it. On a LAN the clock
offset is small, but even if it weren't, both sides tick down from the same
duration, so the race length each player experiences is identical.
"""

import time

import config as C

COUNTDOWN = "countdown"
RACING = "racing"
FINISHED = "finished"


def _fmt(t: float) -> str:
    """Seconds -> M:SS.mmm"""
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
        self.state = COUNTDOWN
        self.timer = self.countdown_len

        self.lap = 1
        self.lap_times = []
        self.race_time = 0.0
        self._lap_start = 0.0
        self.finish_time = None
        self.best_lap = None

        # set when we see the opponent finish, so we can show places
        self.opponent_finished_at = None
        self.place = None

        self._flash = 0.0          # "LAP 2" banner timer
        self._banner = ""

    # -- per-frame ---------------------------------------------------------
    def update(self, dt: float) -> bool:
        """Advance the clock. Returns True if control is allowed this frame."""
        if self._flash > 0.0:
            self._flash = max(self._flash - dt, 0.0)

        if self.state == COUNTDOWN:
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

        return False                        # FINISHED -> no more control

    # -- lap counting ------------------------------------------------------
    def check_lap(self, prev_pos: float, new_pos: float, track_len: float):
        """Call once per frame with the player's position before/after."""
        if self.state != RACING:
            return

        half = track_len / 2.0
        delta = new_pos - prev_pos

        if delta < -half:                   # wrapped forwards over the line
            self._complete_lap()
        elif delta > half:                  # reversed back over the line
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
            self._banner = f"LAP {self.lap}"
            self._flash = C.RACE_BANNER_TIME

    # -- presentation helpers ---------------------------------------------
    @property
    def counting_down(self) -> bool:
        return self.state == COUNTDOWN

    @property
    def finished(self) -> bool:
        return self.state == FINISHED

    def countdown_text(self) -> str:
        """'3', '2', '1' -- or 'GO!' during the brief post-zero flash."""
        n = int(self.timer) + 1
        return str(max(n, 1))

    def banner(self):
        """Current banner text and its 0..1 fade, or (None, 0)."""
        if self._flash <= 0.0 or not self._banner:
            return None, 0.0
        peak = C.RACE_BANNER_TIME * (2.5 if self._banner == "FINISH!" else 1.0)
        return self._banner, max(min(self._flash / peak, 1.0), 0.0)

    def note_opponent(self, remote_state: dict):
        """Track whether the opponent has already finished, for placings."""
        if remote_state is None or self.opponent_finished_at is not None:
            return
        if remote_state.get("done"):
            self.opponent_finished_at = remote_state.get("rt", 0.0)

    def resolve_place(self):
        """1st or 2nd, once we've finished."""
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
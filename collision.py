
import config as C


class CrashState:

    def __init__(self):
        self.timer = 0.0          # seconds of crash left
        self.grace = 0.0          # seconds of post-crash invulnerability
        self.kind = None          # 'prop' | 'car' | None
        self.count = 0            # crashes this session
        self.flash = 0.0          # visual flash intensity, 0..1

    @property
    def active(self) -> bool:
        return self.timer > 0.0

    @property
    def invulnerable(self) -> bool:
        return self.timer > 0.0 or self.grace > 0.0

    def start(self, kind: str):
        
        if self.invulnerable:
            return False
        self.timer = C.CRASH_DURATION
        self.kind = kind
        self.count += 1
        self.flash = 1.0
        return True

    def update(self, dt: float):
        if self.timer > 0.0:
            self.timer = max(self.timer - dt, 0.0)
            if self.timer == 0.0:
                self.kind = None
                self.grace = C.CRASH_GRACE   # start the recovery window
        elif self.grace > 0.0:
            self.grace = max(self.grace - dt, 0.0)
        if self.flash > 0.0:
            self.flash = max(self.flash - dt / C.CRASH_FLASH_TIME, 0.0)


def segments_crossed(prev_pos: float, new_pos: float, track_len: float):
    seg_l = C.SEG_L
    if new_pos < prev_pos:              # wrapped past the finish line
        new_pos += track_len
    first = int(prev_pos // seg_l)
    last = int(new_pos // seg_l)
    if last - first > 64:
        last = first + 64
    for s in range(first, last + 1):
        yield s


def check_prop_collision(lines, prev_pos, new_pos, player_x, track_len):
    
    n = len(lines)
    car_half = C.CAR_HALF_WIDTH

    if C.SCENERY_WALL_ENABLED and abs(player_x) >= C.SCENERY_WALL_X:
        return lines[int(new_pos // C.SEG_L) % n]

    depth = max(int(C.PROP_DEPTH_SEGMENTS), 1)
    for s in segments_crossed(prev_pos, new_pos, track_len):
        for back in range(depth):
            line = lines[(s - back) % n]
            if line.sprite is None:
                continue
            half = line.prop_half or C.PROP_HALF_WIDTH
            if abs(player_x - line.prop_x) < (half + car_half):
                return line
    return None


def check_car_collision(my_pos, my_x, other_pos, other_x, track_len):
    dz = abs(my_pos - other_pos)
    dz = min(dz, track_len - dz)          
    if dz > C.CAR_LENGTH:
        return False
    return abs(my_x - other_x) < C.CAR_HALF_WIDTH * 2


def apply_penalty(player, crash: CrashState, kind: str) -> bool:
    if not crash.start(kind):
        return False
    if kind == "prop":
        player.speed *= C.CRASH_SPEED_KEEP
    else:                                  
        player.speed *= C.BUMP_SPEED_KEEP
    return True

import config as C


class CrashState:

    def __init__(self):
        self.timer = 0.0          
        self.grace = 0.0          
        self.kind = None          
        self.count = 0           
        self.flash = 0.0          

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
                self.grace = C.CRASH_GRACE   
        elif self.grace > 0.0:
            self.grace = max(self.grace - dt, 0.0)
        if self.flash > 0.0:
            self.flash = max(self.flash - dt / C.CRASH_FLASH_TIME, 0.0)


def segments_crossed(prev_pos: float, new_pos: float, track_len: float):
    """Yield segment indices between two positions, handling lap wrap."""
    seg_l = C.SEG_L
    if new_pos < prev_pos:              
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
    for s in segments_crossed(prev_pos, new_pos, track_len):
        line = lines[s % n]
        if line.sprite is None:
            continue
        centre = line.spriteX * C.ROAD_W
        half = getattr(line, "collide_half", C.PROP_HALF_WIDTH)
        if abs(player_x - centre) < (half + car_half):
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
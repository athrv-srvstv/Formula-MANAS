

import math
import random
from typing import List, Optional

import pygame

import config as C


class Line:
    __slots__ = (
        "i", "x", "y", "z", "X", "Y", "W", "scale", "curve",
        "spriteX", "clip", "sprite", "collide_half",
        "prop_x", "prop_half",
        "rock", "rock_x", "rock_half",
        "grass_color", "rumble_color", "road_color",
    )

    def __init__(self, i: int):
        self.i = i
        self.x = self.y = self.z = 0.0      # world position
        self.X = self.Y = self.W = 0.0      # projected screen position/width
        self.scale = 0.0
        self.curve = 0.0
        self.spriteX = 0.0                  # roadside sprite offset
        self.clip = 0.0
        self.sprite: Optional[pygame.Surface] = None

       
        self.prop_x = 0.0
        self.prop_half = 0.0
        self.collide_half = C.PROP_HALF_WIDTH

        
        self.rock: Optional[pygame.Surface] = None
        self.rock_x = 0.0
        self.rock_half = 0.0

        self.grass_color = C.DARK_GRASS
        self.rumble_color = C.BLACK_RUMBLE
        self.road_color = C.DARK_ROAD

    def project(self, cam_x: float, cam_y: float, cam_z: float):
        self.scale = C.CAM_D / (self.z - cam_z)
        self.X = (1 + self.scale * (self.x - cam_x)) * C.WINDOW_WIDTH / 2
        self.Y = (1 - self.scale * (self.y - cam_y)) * C.WINDOW_HEIGHT / 2
        self.W = self.scale * C.ROAD_W * C.WINDOW_WIDTH / 2


def build_track(sprites: List[pygame.Surface],
                rocks: Optional[List[pygame.Surface]] = None) -> List[Line]:
    lines: List[Line] = []
    for i in range(C.NUM_SEGMENTS):
        line = Line(i)
        line.z = i * C.SEG_L + 0.00001  

        
        if i < C.RACE_LINE_SEGMENTS:
            check = (i // 1) % 2
            line.grass_color = C.LIGHT_GRASS if check else C.DARK_GRASS
            line.rumble_color = (C.WHITE_RUMBLE if check else C.BLACK_RUMBLE)
            line.road_color = (C.WHITE_RUMBLE if check else C.BLACK_RUMBLE)
            lines.append(line)
            continue

        band = (i // 3) % 2
        line.grass_color = C.LIGHT_GRASS if band else C.DARK_GRASS
        line.rumble_color = C.WHITE_RUMBLE if band else C.BLACK_RUMBLE
        line.road_color = C.LIGHT_ROAD if band else C.DARK_ROAD

        if 300 < i < 700:
            line.curve = 0.5          # right curve
        if i > 750:
            line.y = math.sin(i / 30.0) * 1500   # rolling hills
        if i > 1100:
            line.curve = -0.7         # left curve

        
        if sprites:
            
            sx = None
            prop = None
            
            wx = None
            prop = None
            rows = C.PROP_ROWS_X          
            if i % 7 == 0:
                wx, prop = -rows[0], sprites[(i // 7) % len(sprites)]
            elif i % 7 == 3:
                wx, prop = rows[0], sprites[(i // 7 + 2) % len(sprites)]
            elif i % 9 == 0:
                wx, prop = -rows[1], sprites[(i // 9 + 4) % len(sprites)]
            elif i % 9 == 4:
                wx, prop = rows[1], sprites[(i // 9 + 5) % len(sprites)]
            elif i % 11 == 0:
                wx, prop = -rows[2], sprites[(i // 11 + 1) % len(sprites)]
            elif i % 13 == 0:
                wx, prop = rows[2], sprites[(i // 13 + 3) % len(sprites)]

            if i == 400:                      # landmark prop
                wx, prop = -rows[2], sprites[6 % len(sprites)]

            if prop is not None:
                line.sprite = prop
                line.prop_x = float(wx)
                line.prop_half = C.PROP_WORLD_WIDTH / 2.0
                line.collide_half = line.prop_half
                line.spriteX = wx / C.ROAD_W

        lines.append(line)

    if rocks and C.ROCK_ENABLED:
        _scatter_rocks(lines, rocks)

    return lines


def _scatter_rocks(lines: List[Line], rocks: List[pygame.Surface]):
    
    rng = random.Random(C.ROCK_SEED)
    n = len(lines)
    limit = C.ROAD_W * C.ROCK_SPREAD
    half = C.ROCK_WORLD_WIDTH / 2.0

    first = C.ROCK_START_CLEAR_SEGMENTS
    last = n - C.ROCK_START_CLEAR_SEGMENTS
    if last <= first:
        return

    placed = []
    attempts = 0
    while len(placed) < C.ROCK_COUNT and attempts < C.ROCK_COUNT * 40:
        attempts += 1
        seg = rng.randrange(first, last)
        if any(abs(seg - s) < C.ROCK_MIN_SEGMENT_GAP for s in placed):
            continue
        line = lines[seg]
        line.rock = rocks[rng.randrange(len(rocks))]
        line.rock_x = rng.uniform(-limit, limit)
        line.rock_half = half
        placed.append(seg)
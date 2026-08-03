

import math
from typing import List, Optional

import pygame

import config as C


class Line:
    __slots__ = (
        "i", "x", "y", "z", "X", "Y", "W", "scale", "curve",
        "spriteX", "clip", "sprite", "collide_half",
        "prop_x", "prop_half",
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

        self.grass_color = C.DARK_GRASS
        self.rumble_color = C.BLACK_RUMBLE
        self.road_color = C.DARK_ROAD

    def project(self, cam_x: float, cam_y: float, cam_z: float):
        self.scale = C.CAM_D / (self.z - cam_z)
        self.X = (1 + self.scale * (self.x - cam_x)) * C.WINDOW_WIDTH / 2
        self.Y = (1 - self.scale * (self.y - cam_y)) * C.WINDOW_HEIGHT / 2
        self.W = self.scale * C.ROAD_W * C.WINDOW_WIDTH / 2


def build_track(sprites: List[pygame.Surface]) -> List[Line]:
    """Recreates the original circuit: right curve, hills, left curve, props."""
    lines: List[Line] = []
    for i in range(C.NUM_SEGMENTS):
        line = Line(i)
        line.z = i * C.SEG_L + 0.00001  # tiny epsilon avoids /0 in project()

        band = (i // 3) % 2
        line.grass_color = C.LIGHT_GRASS if band else C.DARK_GRASS
        line.rumble_color = C.WHITE_RUMBLE if band else C.BLACK_RUMBLE
        line.road_color = C.LIGHT_ROAD if band else C.DARK_ROAD

        if 300 < i < 700:
            line.curve = 0.5          
        if i > 750:
            line.y = math.sin(i / 30.0) * 1500   # rolling hills
        if i > 1100:
            line.curve = -0.7         

        
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
    return lines
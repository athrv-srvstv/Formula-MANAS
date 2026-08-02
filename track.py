
import math
from typing import List, Optional

import pygame

import config as C


class Line:
    __slots__ = (
        "i", "x", "y", "z", "X", "Y", "W", "scale", "curve",
        "spriteX", "clip", "sprite", "collide_half",
        "grass_color", "rumble_color", "road_color",
    )

    def __init__(self, i: int):
        self.i = i
        self.x = self.y = self.z = 0.0      
        self.X = self.Y = self.W = 0.0      
        self.scale = 0.0
        self.curve = 0.0
        self.spriteX = 0.0                  
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
    lines: List[Line] = []
    for i in range(C.NUM_SEGMENTS):
        line = Line(i)
        line.z = i * C.SEG_L + 0.00001  

        band = (i // 3) % 2
        line.grass_color = C.LIGHT_GRASS if band else C.DARK_GRASS
        line.rumble_color = C.WHITE_RUMBLE if band else C.BLACK_RUMBLE
        line.road_color = C.LIGHT_ROAD if band else C.DARK_ROAD

        if 300 < i < 700:
            line.curve = 0.5          
        if i > 750:
            line.y = math.sin(i / 30.0) * 1500   
        if i > 1100:
            line.curve = -0.7         

        
        if sprites:
            sx = None
            prop = None
            if i % 20 == 0:
                if i < 300:
                    sx, prop = -2.6, sprites[4 % len(sprites)]
                elif i > 800:
                    sx, prop = -1.9, sprites[0 % len(sprites)]
                else:
                    sx, prop = -1.7, sprites[3 % len(sprites)]
            elif i % 17 == 0:
                sx, prop = 2.1, sprites[5 % len(sprites)]
            elif i % 23 == 0:
                sx, prop = 1.6, sprites[1 % len(sprites)]

            if i == 400:                      
                sx, prop = -2.2, sprites[6 % len(sprites)]

            if prop is not None:
                
                if abs(sx) < C.PROP_MIN_OFFSET:
                    sx = C.PROP_MIN_OFFSET if sx >= 0 else -C.PROP_MIN_OFFSET
                line.spriteX, line.sprite = sx, prop
                
                line.collide_half = (
                    prop.get_width() * C.PROP_COLLIDE_RATIO
                )

        lines.append(line)
    return lines
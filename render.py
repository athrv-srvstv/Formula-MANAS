

from typing import List, Optional

import pygame

import config as C
import sprite_stack
from track import Line


def _draw_quad(surface, color, x1, y1, w1, x2, y2, w2):
    pygame.draw.polygon(
        surface, color,
        [(x1 - w1, y1), (x2 - w2, y2), (x2 + w2, y2), (x1 + w1, y1)],
    )


class Renderer:
    def __init__(self, window: pygame.Surface, lines: List[Line],
                 background: pygame.Surface):
        self.window = window
        self.lines = lines
        self.N = len(lines)

        bw, bh = background.get_width(), background.get_height()
        self.bg = pygame.Surface((bw * 3, bh))
        for k in range(3):
            self.bg.blit(background, (bw * k, 0))
        self.bg_rect = self.bg.get_rect(topleft=(-bw, C.BG_Y_OFFSET))
        self._bg_tile_w = bw
        self._bg_base_y = C.BG_Y_OFFSET
        self._cam_h_ref = None       

    def scroll_background(self, curve: float, speed: float):
        if speed > 0:
            self.bg_rect.x -= curve * 2
        elif speed < 0:
            self.bg_rect.x += curve * 2
        if self.bg_rect.right < C.WINDOW_WIDTH:
            self.bg_rect.x = -self._bg_tile_w
        elif self.bg_rect.left > 0:
            self.bg_rect.x = -self._bg_tile_w

    def draw(self, cam_x: float, pos: float, cam_extra_h: float,
             speed: float, remote: Optional[dict] = None):
        
        lines, N = self.lines, self.N
        self.window.fill(C.SKY_FILL)
        self.window.blit(self.bg, self.bg_rect)

        start = int(pos // C.SEG_L)
        cam_h = lines[start].y + cam_extra_h

        
        if self._cam_h_ref is None:
            self._cam_h_ref = cam_h
        dy = (cam_h - self._cam_h_ref) * C.BG_VERTICAL_PARALLAX / 100.0
        self.bg_rect.y = int(self._bg_base_y + dy)

        x = dx = 0.0
        maxy = C.WINDOW_HEIGHT

        
        for n in range(start, start + C.SHOW_N_SEG):
            cur = lines[n % N]
            cur.project(cam_x - x, cam_h,
                        pos - (N * C.SEG_L if n >= N else 0))
            x += dx            
            dx += cur.curve
            cur.clip = maxy

            
            if cur.scale <= 0:
                continue

            if cur.Y >= maxy:
                continue
            maxy = cur.Y

            prev = lines[(n - 1) % N]
            if prev.scale <= 0:      
                continue
            _draw_quad(self.window, cur.grass_color,
                       0, prev.Y, C.WINDOW_WIDTH, 0, cur.Y, C.WINDOW_WIDTH)
            _draw_quad(self.window, cur.rumble_color,
                       prev.X, prev.Y, prev.W * 1.2,
                       cur.X, cur.Y, cur.W * 1.2)
            _draw_quad(self.window, cur.road_color,
                       prev.X, prev.Y, prev.W, cur.X, cur.Y, cur.W)

        remote_seg = None
        if remote is not None:
            remote_seg = int(remote["pos"] // C.SEG_L) % N

        for n in range(start + C.SHOW_N_SEG, start + 1, -1):
            idx = n % N
            self._draw_prop(lines[idx])
            if remote_seg is not None and idx == remote_seg:
                self._draw_remote(lines[idx], remote)

    def _draw_prop(self, line: Line):
        
        spr = line.sprite
        if spr is None or line.W <= 0:
            return

        src_w, src_h = spr.get_width(), spr.get_height()
        if src_w <= 0 or src_h <= 0:
            return

        
        px_per_world = line.W / C.ROAD_W

        dest_w = (line.prop_half * 2.0) * px_per_world
        dest_h = dest_w * (src_h / src_w)          
        centre_x = line.X + line.prop_x * px_per_world
        dest_x = centre_x - dest_w / 2.0
        dest_y = line.Y - dest_h                    

        if dest_w < 1 or dest_h < 1:
            return
        if dest_w > C.WINDOW_WIDTH * C.PROP_MAX_UPSCALE:
            return
        if dest_x + dest_w < 0 or dest_x > C.WINDOW_WIDTH:
            return

        clip_h = dest_y + dest_h - line.clip
        if clip_h < 0:
            clip_h = 0
        if clip_h >= dest_h:
            return

        scaled = pygame.transform.scale(spr, (int(dest_w), int(dest_h)))
        crop = scaled.subsurface(0, 0, int(dest_w),
                                 max(int(dest_h - clip_h), 1))
        self.window.blit(crop, (dest_x, dest_y))

    
    def _draw_remote(self, line: Line, remote: dict):
        
        if line.scale <= 0:
            return
        sx = line.X + line.scale * remote["x"] * C.WINDOW_WIDTH / 2
        sy = line.Y

        #
        scale = (line.W * 2.0 / 3.0) / sprite_stack.NATIVE_W
        if scale < 0.5:          
            return
        if scale > C.CAR_SCALE * 1.6:   
            return

        angle = remote["steer"] * C.CAR_MAX_TURN + line.curve * 12.0
        sprite_stack.draw_stack(
            self.window, remote["color"], sx, sy,
            angle_deg=angle,
            scale=scale,
            layer_spacing=C.CAR_LAYER_SPACING,
            swing=C.CAR_SWING,
            rot_factor=C.CAR_ROT_FACTOR,
            front_anchored=C.CAR_FRONT_ANCHORED,
        )
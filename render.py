
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
            x += dx            # keep curve accumulation for EVERY segment
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
            self._cam_pos = pos
            self._track_len = N * C.SEG_L

        
        drew_remote = False
        for n in range(start + C.SHOW_N_SEG, start - 1, -1):
            idx = n % N
            self._draw_prop(lines[idx])
            self._draw_rock(lines[idx])
            if remote_seg is not None and idx == remote_seg:
                self._draw_remote(lines[idx], remote, start, n - start)
                drew_remote = True

        
        if remote is not None and not drew_remote:
            self._draw_remote(lines[(start + C.CAR_NEAR_CLAMP_SEGS) % N],
                              remote, start, 0)

    def _draw_world_sprite(self, line: Line, spr, world_x, half):
        
        if spr is None or line.W <= 0:
            return
        src_w, src_h = spr.get_width(), spr.get_height()
        if src_w <= 0 or src_h <= 0:
            return

        px_per_world = line.W / C.ROAD_W
        dest_w = (half * 2.0) * px_per_world
        dest_h = dest_w * (src_h / src_w)
        dest_x = line.X + world_x * px_per_world - dest_w / 2.0
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

    def _draw_rock(self, line: Line):
        self._draw_world_sprite(line, line.rock, line.rock_x, line.rock_half)

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

    def _lerp_projection(self, seg: int, frac: float, start: int):
        
        n = self.N
        a = self.lines[seg % n]
        b = self.lines[(seg + 1) % n]
        if a.scale <= 0 or b.scale <= 0:
            return None
        if abs(b.Y - a.Y) > C.WINDOW_HEIGHT:
            return a.X, a.Y, a.W
        f = 0.0 if frac < 0.0 else (1.0 if frac > 1.0 else frac)
        return (a.X + (b.X - a.X) * f,
                a.Y + (b.Y - a.Y) * f,
                a.W + (b.W - a.W) * f)

    def _draw_remote(self, line: Line, remote: dict, start: int = 0,
                     dz_segs: int = 99):
        
        track_len = getattr(self, "_track_len", self.N * C.SEG_L)
        cam_pos = getattr(self, "_cam_pos", 0.0)

        rel_z = remote["pos"] - cam_pos
        if rel_z < -track_len / 2.0:
            rel_z += track_len
        elif rel_z > track_len / 2.0:
            rel_z -= track_len

        min_z = C.CAR_NEAR_CLAMP_SEGS * C.SEG_L
        eff_z = max(rel_z, min_z)
        if rel_z > C.SHOW_N_SEG * C.SEG_L:
            return

        seg_f = (cam_pos + eff_z) / C.SEG_L
        seg = int(seg_f)
        proj = self._lerp_projection(seg, seg_f - seg, start)
        if proj is None:
            if line.scale <= 0 or line.W <= 0:
                return
            proj = (line.X, line.Y, line.W)
        px_X, px_Y, px_W = proj
        if px_W <= 0:
            return

        px_per_world = px_W / C.ROAD_W
        sx = px_X + remote["x"] * px_per_world
        sy = min(px_Y, C.WINDOW_HEIGHT - 40)

        car_px = C.CAR_WORLD_WIDTH * px_per_world
        scale = car_px / sprite_stack.NATIVE_W
        if scale < C.CAR_MIN_DRAW_SCALE:
            return
        scale = min(scale, C.CAR_MAX_DRAW_SCALE)
        car_px = scale * sprite_stack.NATIVE_W
        if sx < -car_px or sx > C.WINDOW_WIDTH + car_px:
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
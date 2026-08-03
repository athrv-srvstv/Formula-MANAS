

import math
from functools import lru_cache
from typing import Optional, Sequence, Tuple

import pygame

NATIVE_W, NATIVE_H = 20, 12
N_SLICES = 10


def _shade(rgb: Tuple[int, int, int], d: int) -> Tuple[int, int, int]:
    return (
        max(min(rgb[0] + d, 255), 0),
        max(min(rgb[1] + d, 255), 0),
        max(min(rgb[2] + d, 255), 0),
    )



@lru_cache(maxsize=8)
def make_slices(body_rgb: Tuple[int, int, int]) -> Tuple[pygame.Surface, ...]:
    body = body_rgb
    dark = _shade(body, -70)
    glass = (80, 140, 180)
    dark_gray = (40, 40, 40)
    yellow = (255, 215, 0)
    white = (240, 240, 240)

    slices = []
    for i in range(N_SLICES):
        surf = pygame.Surface((NATIVE_W, NATIVE_H), pygame.SRCALPHA)

        if i == 0:                      # front bumper + headlights
            pygame.draw.rect(surf, dark_gray, (2, 6, 16, 4))
            pygame.draw.rect(surf, yellow, (3, 7, 3, 2))
            pygame.draw.rect(surf, yellow, (14, 7, 3, 2))

        elif 1 <= i <= 3:               # hood / front fenders
            pygame.draw.rect(surf, body, (2, 4, 16, 6))

        elif 4 <= i <= 6:               # cabin: windshield - roof
            pygame.draw.rect(surf, body, (3, 2, 14, 8))
            glass_y = 3 if i == 4 else 2
            pygame.draw.rect(surf, glass, (5, glass_y, 10, 3))

        elif 7 <= i <= 8:               # rear deck / trunk
            pygame.draw.rect(surf, body, (2, 4, 16, 6))

        else:                           # rear bumper -- faces the camera
            pygame.draw.rect(surf, dark, (1, 4, 18, 6))
            pygame.draw.rect(surf, body, (2, 6, 16, 3))     # taillight bar
            pygame.draw.rect(surf, white, (8, 7, 4, 2))     # plate

        slices.append(surf)

    return tuple(slices)


@lru_cache(maxsize=256)
def _scaled(body_rgb: Tuple[int, int, int], bucket: int) -> Tuple[pygame.Surface, ...]:
    
    s = bucket / 2.0
    w = max(int(NATIVE_W * s), 1)
    h = max(int(NATIVE_H * s), 1)
    return tuple(
        pygame.transform.scale(sl, (w, h)) for sl in make_slices(body_rgb)
    )



def load_stack_from_sheet(
    path: str,
    frame_w: int,
    frame_h: int,
    count: Optional[int] = None,
    vertical: bool = False,
    front_first: bool = True,
) -> Tuple[pygame.Surface, ...]:
    
    sheet = pygame.image.load(path).convert_alpha()
    sw, sh = sheet.get_size()
    n = (sh // frame_h) if vertical else (sw // frame_w)
    if count is not None:
        n = min(n, count)

    frames = []
    for i in range(n):
        rect = pygame.Rect(0, i * frame_h, frame_w, frame_h) if vertical \
            else pygame.Rect(i * frame_w, 0, frame_w, frame_h)
        frames.append(sheet.subsurface(rect).copy())

    if not front_first:
        frames.reverse()
    return tuple(frames)



def draw_stack(
    surface: pygame.Surface,
    body_rgb: Tuple[int, int, int],
    cx: float,
    cy: float,
    angle_deg: float = 0.0,
    scale: float = 7.0,
    layer_spacing: float = 0.42,
    swing: float = 1.8,
    rot_factor: float = 0.25,
    front_anchored: bool = False,
    slices: Optional[Sequence[pygame.Surface]] = None,
):
    
    if slices is not None:
        layers = tuple(slices)
    else:
        bucket = max(int(round(scale * 2)), 1)
        layers = _scaled(tuple(body_rgb), bucket)

    n = len(layers)
    if n == 0:
        return

    rad = math.radians(angle_deg)
    spacing = layer_spacing * scale
    sway = swing * scale
    sin_a, cos_a = math.sin(rad), math.cos(rad)

    for i, img in enumerate(layers):
        depth = i if front_anchored else (n - 1) - i
        offset_x = sin_a * depth * sway
        offset_y = -cos_a * depth * spacing

        if rot_factor:
            img = pygame.transform.rotate(img, -angle_deg * rot_factor)

        rect = img.get_rect(center=(int(cx + offset_x), int(cy + offset_y)))
        surface.blit(img, rect)
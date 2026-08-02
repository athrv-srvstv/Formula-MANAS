"""Sprite-stacked car -- depth-sliced (front -> rear) for a true back view.

CONSTRUCTION
------------
Each slice is a VERTICAL cross-section of the car (its width x height at one
point along its length). Slice 0 is the front bumper, the last slice is the
rear bumper. We draw front-first so the REAR ends up on top, nearest the
camera -- which is exactly what you see in a chase cam.

Each slice is nudged upward as it gets further from the camera, so the nose
recedes into the distance. The rear bumper is the anchor and never moves;
(cx, cy) is its center.

TURNING
-------
Rotating the whole sprite would just spin a flat image. Instead each slice is
offset SIDEWAYS in proportion to how far it is from the anchor:

    offset_x = sin(angle) * depth_factor * swing

With depth_factor largest at the front, the rear bumper stays planted and the
nose swings out -- the car pivots around its back axle, like a real car.
Set front_anchored=False to flip it (nose planted, tail swings out) if you
prefer that look.

A small counter-rotation (rot_factor) is layered on top so slices also tilt
slightly, which smooths the stair-stepping on the pixel grid.

ART
---
The car is generated procedurally at a low native resolution (20x12) and
scaled up with nearest-neighbour, keeping crisp pixel edges. Supply your own
layers via `slices=` (see load_stack_from_sheet) whenever you have real art.
"""

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


# ---------------------------------------------------------------------------
# Procedural car -- native resolution, front (0) -> rear (N-1)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=8)
def make_slices(body_rgb: Tuple[int, int, int]) -> Tuple[pygame.Surface, ...]:
    """Build one car's slices, tinted to `body_rgb`. Cached per colour."""
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

        elif 4 <= i <= 6:               # cabin: windshield -> roof
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
    """Nearest-neighbour scaled slices, cached in half-step size buckets.

    Bucketing keeps the opponent car from re-scaling 10 surfaces every frame
    as it approaches, which would tank the framerate.
    """
    s = bucket / 2.0
    w = max(int(NATIVE_W * s), 1)
    h = max(int(NATIVE_H * s), 1)
    return tuple(
        pygame.transform.scale(sl, (w, h)) for sl in make_slices(body_rgb)
    )


# ---------------------------------------------------------------------------
# Real spritesheet loader -- drop in art whenever you have it
# ---------------------------------------------------------------------------
def load_stack_from_sheet(
    path: str,
    frame_w: int,
    frame_h: int,
    count: Optional[int] = None,
    vertical: bool = False,
    front_first: bool = True,
) -> Tuple[pygame.Surface, ...]:
    """Slice a sheet into layers ordered FRONT -> REAR.

      frame_w/h   : size of one layer frame
      vertical    : frames run top-to-bottom instead of left-to-right
      front_first : False if frame 0 is the REAR of the car (we reverse it)

    Pass the result to draw_stack(slices=...). Note these are used at their
    native size -- pre-scale them yourself if needed.
    """
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


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
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
    """Draw the car with (cx, cy) at the REAR bumper (nearest the camera).

    angle_deg      : steering angle in degrees (+ = right)
    scale          : pixel multiplier on the 20x12 native art
    layer_spacing  : vertical recede per slice, as a fraction of scale
    swing          : how far the nose swings when turning
    rot_factor     : extra per-slice tilt, 0 disables
    front_anchored : True pins the NOSE and swings the tail instead
    slices         : your own layers (front->rear); skips the built-in car
    """
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

    # front-first draw order => rear bumper lands on top, nearest the camera
    for i, img in enumerate(layers):
        depth = i if front_anchored else (n - 1) - i
        offset_x = sin_a * depth * sway
        offset_y = -cos_a * depth * spacing

        if rot_factor:
            img = pygame.transform.rotate(img, -angle_deg * rot_factor)

        rect = img.get_rect(center=(int(cx + offset_x), int(cy + offset_y)))
        surface.blit(img, rect)
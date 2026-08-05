

import math
import os
import random
from typing import List

import pygame

import config as C

IMG_DIR = "images"


def _ridge_points(x0, x1, base_y, peak_y, rng, passes=5, roughness=0.55):
    
    pts = [(x0, base_y), ((x0 + x1) / 2.0, peak_y), (x1, base_y)]
    amp = (base_y - peak_y) * roughness

    for _ in range(passes):
        new_pts = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            mx = (a[0] + b[0]) / 2.0
            my = (a[1] + b[1]) / 2.0 + rng.uniform(-amp, amp)
            my = min(max(my, peak_y - amp), base_y)   # keep it sane
            new_pts.append((mx, my))
            new_pts.append(b)
        pts = new_pts
        amp *= 0.5              # finer detail each pass

    return pts


def _placeholder_bg() -> pygame.Surface:
    
    w = C.WINDOW_WIDTH
    h = C.BG_HEIGHT
    base = h                      
    surf = pygame.Surface((w, h))

    for y in range(h):
        t = y / h
        pygame.draw.line(
            surf,
            (int(92 + 78 * t), int(150 + 74 * t), int(224 - 36 * t)),
            (0, y), (w, y),
        )

    
    rng = random.Random(C.BG_SEED)

    
    ranges = [
        (-140, w * 0.62, h * 0.34, (128, 156, 150), 0.45),
        (w * 0.28, w * 1.16, h * 0.24, (100, 132, 120), 0.55),
        (-90, w * 0.34, h * 0.44, (78, 110, 96), 0.60),
        (w * 0.62, w + 150, h * 0.38, (70, 102, 90), 0.60),
    ]
    for x0, x1, peak, colour, rough in ranges:
        pts = _ridge_points(x0, x1, base, peak, rng, roughness=rough)
        pygame.draw.polygon(surf, colour, pts)

    
    haze_h = max(int(h * 0.10), 6)
    haze = pygame.Surface((w, haze_h), pygame.SRCALPHA)
    for y in range(haze_h):
        a = int(210 * (y / haze_h) ** 1.4)
        pygame.draw.line(haze, (150, 190, 170, a), (0, y), (w, y))
    surf.blit(haze, (0, h - haze_h))

    return surf


def _placeholder_prop(idx: int) -> pygame.Surface:
    
    surf = pygame.Surface((120, 220), pygame.SRCALPHA)

    if idx % 4 == 1:
        
        pygame.draw.rect(surf, (110, 110, 115), (56, 110, 8, 110))
        pygame.draw.rect(surf, (225, 200, 60), (28, 60, 64, 52),
                         border_radius=6)
        pygame.draw.rect(surf, (60, 55, 30), (28, 60, 64, 52), width=3,
                         border_radius=6)
        return surf

    if idx % 4 == 2:
        c = (26, 92, 38)
        pygame.draw.circle(surf, c, (44, 180), 34)
        pygame.draw.circle(surf, c, (76, 182), 30)
        pygame.draw.circle(surf, (32, 108, 44), (60, 160), 32)
        return surf

    pygame.draw.rect(surf, (76, 52, 34), (52, 130, 18, 90))
    canopy = [(22, 84, 34), (30, 104, 42), (18, 72, 30)]
    c = canopy[idx % len(canopy)]
    pygame.draw.circle(surf, c, (60, 96), 52)
    pygame.draw.circle(surf, c, (32, 128), 34)
    pygame.draw.circle(surf, c, (88, 128), 34)
    pygame.draw.circle(surf, _lighten(c, 18), (52, 78), 26)
    return surf


def _lighten(c, d):
    return (min(c[0] + d, 255), min(c[1] + d, 255), min(c[2] + d, 255))


def _placeholder_rock(idx: int) -> pygame.Surface:
    w, h = 140, 100
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rng = random.Random(900 + idx)

    base = rng.randint(150, 180)
    body = (base, base - 18, base - 42)
    lite = (base + 34, base + 38, base + 44)
    dark = (base - 34, base - 32, base - 28)

    pts = []
    n = 11
    for i in range(n):
        a = math.tau * i / n
        r = rng.uniform(0.72, 1.0)
        pts.append((w / 2 + math.cos(a) * (w / 2 - 6) * r,
                    h - 8 - abs(math.sin(a)) * (h - 20) * r))
    pygame.draw.polygon(surf, body, pts)
    pygame.draw.polygon(surf, dark, pts, width=3)

    for _ in range(2):
        i = rng.randrange(n)
        a, b, c = pts[i], pts[(i + 1) % n], (w / 2, h * 0.45)
        pygame.draw.polygon(surf, lite, [a, b, c])

    pygame.draw.ellipse(surf, (40, 40, 46, 120), (10, h - 16, w - 20, 14))
    return surf


def load_rocks() -> List[pygame.Surface]:
    return [_placeholder_rock(i).convert_alpha() for i in range(4)]


def load_background() -> pygame.Surface:
    path = os.path.join(IMG_DIR, "bg.png")
    if os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
    else:
        img = _placeholder_bg().convert_alpha()
    return pygame.transform.scale(
        img, (C.WINDOW_WIDTH, img.get_height())
    )


def load_props() -> List[pygame.Surface]:
    props: List[pygame.Surface] = []
    for i in range(1, 8):
        path = os.path.join(IMG_DIR, f"{i}.png")
        if os.path.exists(path):
            props.append(pygame.image.load(path).convert_alpha())
        else:
            props.append(_placeholder_prop(i).convert_alpha())
    return props
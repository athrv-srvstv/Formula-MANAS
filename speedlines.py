

import math
import random

import pygame

import config as C


class SpeedLine:
    __slots__ = ("angle", "radius", "speed", "length", "width", "life",
                 "max_life", "bright")

    def __init__(self, angle, radius, speed, length, width, life, bright):
        self.angle = angle
        self.radius = radius
        self.speed = speed
        self.length = length
        self.width = width
        self.life = life
        self.max_life = life
        self.bright = bright

    def update(self, dt):
        self.life -= dt
        self.radius += self.speed * dt
        self.speed *= (1.0 + C.SPEEDLINE_ACCEL * dt)
        self.length += self.speed * dt * C.SPEEDLINE_STRETCH


class SpeedLines:
    def __init__(self):
        self.lines = []
        self._prev_speed = 0.0
        self._debt = 0.0

    def _spawn(self, n, cx, cy):
        max_r = math.hypot(C.WINDOW_WIDTH, C.WINDOW_HEIGHT) * 0.6
        for _ in range(int(n)):
            self.lines.append(SpeedLine(
                angle=random.uniform(0.0, math.tau),
                radius=random.uniform(C.SPEEDLINE_INNER_RADIUS,
                                      C.SPEEDLINE_INNER_RADIUS * 1.9),
                speed=random.uniform(*C.SPEEDLINE_SPEED),
                length=random.uniform(*C.SPEEDLINE_LENGTH),
                width=random.randint(*C.SPEEDLINE_WIDTH),
                life=random.uniform(*C.SPEEDLINE_LIFE),
                bright=random.randint(*C.SPEEDLINE_BRIGHT),
            ))
        if len(self.lines) > C.SPEEDLINE_MAX:
            del self.lines[:len(self.lines) - C.SPEEDLINE_MAX]
        self._max_r = max_r

    def update(self, dt, speed, cx, cy):
        if dt <= 0:
            return

        accel = (speed - self._prev_speed) / dt
        self._prev_speed = speed

        frac = min(speed / max(C.MAX_SPEED, 1e-6), 1.0)
        rate = 0.0

       
        if frac > C.SPEEDLINE_MIN_SPEED_FRAC:
            span = 1.0 - C.SPEEDLINE_MIN_SPEED_FRAC
            t = (frac - C.SPEEDLINE_MIN_SPEED_FRAC) / max(span, 1e-6)
            rate = C.SPEEDLINE_RATE * (t ** C.SPEEDLINE_CURVE)
            # extra surge while genuinely accelerating
            if accel > C.SPEEDLINE_ACCEL_MIN:
                rate *= C.SPEEDLINE_ACCEL_BOOST

        if rate > 0.0:
            self._debt += rate * dt
            n = int(self._debt)
            if n > 0:
                self._debt -= n
                self._spawn(n, cx, cy)
        else:
            self._debt = 0.0

        for ln in self.lines:
            ln.update(dt)
        limit = math.hypot(C.WINDOW_WIDTH, C.WINDOW_HEIGHT) * 0.75
        self.lines = [ln for ln in self.lines
                      if ln.life > 0.0 and ln.radius < limit]

    def draw(self, surface, cx, cy):
        if not self.lines:
            return
        layer = pygame.Surface((C.WINDOW_WIDTH, C.WINDOW_HEIGHT),
                               pygame.SRCALPHA)
        for ln in self.lines:
            t = max(ln.life / ln.max_life, 0.0)
            fade = math.sin(math.pi * (1.0 - t)) if t < 1.0 else 0.0
            alpha = int(C.SPEEDLINE_ALPHA * fade)
            if alpha <= 3:
                continue

            ca, sa = math.cos(ln.angle), math.sin(ln.angle)
            x1 = cx + ca * ln.radius
            y1 = cy + sa * ln.radius
            x2 = cx + ca * (ln.radius + ln.length)
            y2 = cy + sa * (ln.radius + ln.length)
            pygame.draw.line(
                layer, (ln.bright, ln.bright, ln.bright, alpha),
                (int(x1), int(y1)), (int(x2), int(y2)), ln.width)
        surface.blit(layer, (0, 0))

    def clear(self):
        self.lines.clear()
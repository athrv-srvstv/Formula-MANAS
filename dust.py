

import math
import random

import pygame

import config as C


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "tint")

    def __init__(self, x, y, vx, vy, life, size, tint):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = size
        self.tint = tint

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= (1.0 - C.DUST_DRAG * dt)
        self.vy *= (1.0 - C.DUST_DRAG * dt)
        self.vy -= C.DUST_RISE * dt          
        self.size += C.DUST_GROWTH * dt      


class DustSystem:
    def __init__(self):
        self.particles = []
        self._prev_speed = 0.0
        self._emit_debt = 0.0                

    def _spawn(self, n, cx, cy, spread_x, base_vx, base_vy, offroad):
        for _ in range(int(n)):
            tint = (
                random.randint(*C.DUST_TINT_DIRT)
                if offroad else random.randint(*C.DUST_TINT_ROAD)
            )
            self.particles.append(Particle(
                x=cx + random.uniform(-spread_x, spread_x),
                y=cy + random.uniform(-4, 6),
                vx=base_vx + random.uniform(-C.DUST_JITTER, C.DUST_JITTER),
                vy=base_vy + random.uniform(-C.DUST_JITTER, C.DUST_JITTER),
                life=random.uniform(*C.DUST_LIFE),
                size=random.uniform(*C.DUST_SIZE),
                tint=tint,
            ))
        if len(self.particles) > C.DUST_MAX:
            del self.particles[:len(self.particles) - C.DUST_MAX]

    def update(self, dt, speed, steer, throttle, car_x, car_y, offroad):
        if dt <= 0:
            return

        accel = (speed - self._prev_speed) / dt
        self._prev_speed = speed
        speed_frac = min(speed / max(C.MAX_SPEED, 1e-6), 1.0)

        rate = 0.0
        vx = vy = 0.0
        spread = C.DUST_SPREAD

        if throttle > 0.3 and speed_frac < C.DUST_LAUNCH_SPEED_FRAC:
            rate += C.DUST_RATE_LAUNCH * throttle
            vy += C.DUST_VY_BACK

        if accel < -C.DUST_BRAKE_ACCEL:
            rate += C.DUST_RATE_BRAKE * min(
                abs(accel) / max(C.BRAKE, 1e-6), 1.5)
            spread *= 1.6
            vy += C.DUST_VY_BACK * 0.5

        if abs(steer) > C.DUST_STEER_MIN and speed_frac > 0.15:
            rate += C.DUST_RATE_CORNER * abs(steer) * speed_frac
            vx += -math.copysign(C.DUST_VX_CORNER * abs(steer), steer)

        if offroad:
            rate *= C.DUST_OFFROAD_MULT
            rate += C.DUST_RATE_OFFROAD * speed_frac

        if rate > 0.0:
            self._emit_debt += rate * dt
            n = int(self._emit_debt)
            if n > 0:
                self._emit_debt -= n
                self._spawn(n, car_x, car_y, spread, vx, vy, offroad)
        else:
            self._emit_debt = 0.0

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0.0]

    def draw(self, surface):
        if not self.particles:
            return
        
        layer = pygame.Surface(
            (C.WINDOW_WIDTH, C.WINDOW_HEIGHT), pygame.SRCALPHA)
        for p in self.particles:
            t = max(p.life / p.max_life, 0.0)
            alpha = int(C.DUST_ALPHA * (t ** 0.7))
            if alpha <= 2:
                continue
            r = max(int(p.size), 1)
            pygame.draw.circle(
                layer, (p.tint, p.tint - 8, p.tint - 22, alpha),
                (int(p.x), int(p.y)), r)
        surface.blit(layer, (0, 0))

    def clear(self):
        self.particles.clear()
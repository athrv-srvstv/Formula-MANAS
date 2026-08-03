

import argparse
import random
import sys

import pygame

import config as C
import assets
from track import build_track
from render import Renderer
from player import Player
from network import NetworkPeer
from inputs import make_input
from collision import (CrashState, check_prop_collision,
                       check_car_collision, apply_penalty)
import sprite_stack
from dust import DustSystem


def parse_args():
    p = argparse.ArgumentParser(description="Gesture racer (2-player)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--host", action="store_true", help="host the match")
    g.add_argument("--join", metavar="HOST_IP", help="join a hosted match")
    p.add_argument("--port", type=int, default=C.DEFAULT_PORT)
    p.add_argument("--keyboard", action="store_true",
                   help="force keyboard control (no webcam)")
    p.add_argument("--name", default=None, help="HUD label")
    return p.parse_args()


def draw_own_car(surface, body_rgb, steer, shake_x=0.0, shake_y=0.0):
    
    cx = C.WINDOW_WIDTH / 2 + steer * C.CAR_DRIFT_PX + shake_x
    cy = C.WINDOW_HEIGHT - 90 + shake_y   # rear bumper anchor
    sprite_stack.draw_stack(
        surface, body_rgb, cx, cy,
        angle_deg=steer * C.CAR_MAX_TURN,
        scale=C.CAR_SCALE,
        layer_spacing=C.CAR_LAYER_SPACING,
        swing=C.CAR_SWING,
        rot_factor=C.CAR_ROT_FACTOR,
        front_anchored=C.CAR_FRONT_ANCHORED,
    )


def draw_hud(surface, font, player, connected, control_name,
             steer=0.0, throttle=0.0, net_pps=0.0, crash=None):
    kmh = int(player.speed / 60)     # arbitrary "speed unit" for flavor
    lines = [
        f"{player.name}   {kmh} km/h",
        f"steer {steer:+.2f}   gas {throttle:+.2f}",
        f"control: {control_name}" + ("   [C] calibrate"
                                      if control_name == "gesture" else ""),
        ("opponent: connected  %.0f pkt/s" % net_pps) if connected
        else "opponent: waiting...",
        f"crashes: {crash.count}",
    ]
    y = 12
    for i, text in enumerate(lines):
        col = (255, 255, 255) if i != 3 or connected else (255, 200, 80)
        surface.blit(font.render(text, True, (0, 0, 0)), (13, y + 1))  # shadow
        surface.blit(font.render(text, True, col), (12, y))
        y += 26

    if crash is not None and crash.active:
        if crash.kind == "prop":
            msg, sub = "CRASH!", "slowing down..."
        else:
            msg, sub = "CONTACT!", "watch your line"
        big = pygame.font.SysFont("consolas", 46, bold=True)
        small = pygame.font.SysFont("consolas", 24)

        surf = big.render(msg, True, (255, 210, 70))
        rect = surf.get_rect(center=(C.WINDOW_WIDTH // 2,
                                     C.WINDOW_HEIGHT // 3))
        surface.blit(big.render(msg, True, (50, 18, 0)), rect.move(3, 3))
        surface.blit(surf, rect)

        s2 = small.render(sub, True, (255, 245, 220))
        r2 = s2.get_rect(center=(C.WINDOW_WIDTH // 2, rect.bottom + 20))
        surface.blit(small.render(sub, True, (50, 18, 0)), r2.move(2, 2))
        surface.blit(s2, r2)


def main():
    args = parse_args()
    is_host = args.host
    host_ip = "" if is_host else args.join
    name = args.name or ("HOST" if is_host else "GUEST")

    # host = red, client = blue; opponent is the other color
    local_color = (C.HOST_CAR.r, C.HOST_CAR.g, C.HOST_CAR.b) if is_host \
        else (C.CLIENT_CAR.r, C.CLIENT_CAR.g, C.CLIENT_CAR.b)
    remote_color = (C.CLIENT_CAR.r, C.CLIENT_CAR.g, C.CLIENT_CAR.b) if is_host \
        else (C.HOST_CAR.r, C.HOST_CAR.g, C.HOST_CAR.b)

    pygame.init()
    pygame.display.set_caption(f"Gesture Racer -- {name}")
    window = pygame.display.set_mode((C.WINDOW_WIDTH, C.WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20)

    props = assets.load_props()
    background = assets.load_background()
    lines = build_track(props)
    N = len(lines)
    track_len = N * C.SEG_L

    renderer = Renderer(window, lines, background)
    player = Player(name=name)
    net = NetworkPeer(is_host=is_host, host_ip=host_ip, port=args.port)
    controller = make_input(prefer_gesture=not args.keyboard)

    print(f"[net] {'hosting on' if is_host else 'joining'} "
          f"{'0.0.0.0' if is_host else host_ip}:{args.port}")

    crash = CrashState()
    dust = DustSystem()
    shake_x = shake_y = 0.0
    cam_extra_h = 1500.0  
    running = True
    while running:
        dt = clock.tick(C.FPS) / 1000.0
        dt = min(dt, 0.05)  

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_c:
                    controller.calibrate()

        steer_in, throttle_in = controller.read()
        curve_here = lines[int(player.pos // C.SEG_L) % N].curve

        crash.update(dt)
        if crash.active:
            
            spin = C.CRASH_STEER_SPIN * (1 if crash.count % 2 else -1)
            steer_in, throttle_in = spin, 0.0

        prev_pos = player.pos
        player.update(dt, steer_in, throttle_in, curve_here, track_len)

        net.send(player.state())
        if C.NET_INTERP_ENABLED:
            rstate = net.remote_interpolated(
                delay=C.NET_INTERP_DELAY, track_len=track_len)
        else:
            rstate = net.remote
        remote = None
        if rstate is not None:
            remote = {
                "pos": rstate.get("pos", 0.0),
                "x": rstate.get("x", 0.0),
                "steer": rstate.get("steer", 0.0),
                "color": remote_color,
            }

        if not crash.invulnerable:
            hit = check_prop_collision(lines, prev_pos, player.pos,
                                       player.x, track_len)
            if hit is not None:
                apply_penalty(player, crash, "prop")
            elif remote is not None and check_car_collision(
                    player.pos, player.x,
                    remote["pos"], remote["x"], track_len):
                apply_penalty(player, crash, "car")
                player.x += 120.0 if player.x >= remote["x"] else -120.0

        if crash.flash > 0.0:
            amp = C.CRASH_SHAKE_PX * crash.flash
            shake_x = random.uniform(-amp, amp)
            shake_y = random.uniform(-amp, amp)
        else:
            shake_x = shake_y = 0.0

        
        dust_x = C.WINDOW_WIDTH / 2 + player.steer * C.CAR_DRIFT_PX + shake_x
        dust_y = C.WINDOW_HEIGHT - 78 + shake_y
        dust.update(dt, player.speed, player.steer, throttle_in,
                    dust_x, dust_y, abs(player.x) > C.ROAD_W)

        renderer.scroll_background(curve_here, player.speed)
        renderer.draw(player.x, player.pos, cam_extra_h, player.speed, remote)
        dust.draw(window)          
        draw_own_car(window, local_color, player.steer, shake_x, shake_y)

        if crash.flash > 0.0:
            flash = pygame.Surface((C.WINDOW_WIDTH, C.WINDOW_HEIGHT),
                                   pygame.SRCALPHA)
            flash.fill((210, 120, 40, int(70 * crash.flash)))
            window.blit(flash, (0, 0))
        draw_hud(window, font, player, net.connected(), controller.name,
                 steer_in, throttle_in, net.stats()["pps"], crash)

        pygame.display.update()

    controller.close()
    net.close()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()


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
from speedlines import SpeedLines
import race as race_mod
from race import Race


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
    cy = C.WINDOW_HEIGHT - 90 + shake_y   
    sprite_stack.draw_stack(
        surface, body_rgb, cx, cy,
        angle_deg=steer * C.CAR_MAX_TURN,
        scale=C.CAR_SCALE,
        layer_spacing=C.CAR_LAYER_SPACING,
        swing=C.CAR_SWING,
        rot_factor=C.CAR_ROT_FACTOR,
        front_anchored=C.CAR_FRONT_ANCHORED,
    )


def draw_race_overlay(surface, race, remote_lap=None):
    
    cx = C.WINDOW_WIDTH // 2

    if race.counting_down:
        frac = race.timer - int(race.timer)      
        size = int(120 + 70 * frac)
        f = pygame.font.SysFont("consolas", size, bold=True)
        txt = race.countdown_text()
        surf = f.render(txt, True, (255, 230, 90))
        rect = surf.get_rect(center=(cx, C.WINDOW_HEIGHT // 2 - 40))
        surface.blit(f.render(txt, True, (40, 20, 0)), rect.move(4, 4))
        surface.blit(surf, rect)

        sub = pygame.font.SysFont("consolas", 26)
        s2 = sub.render("get ready", True, (255, 255, 255))
        surface.blit(s2, s2.get_rect(center=(cx, rect.bottom + 24)))
        return

    text, fade = race.banner()
    if text:
        size = 84 if text == "FINISH!" else 62
        f = pygame.font.SysFont("consolas", size, bold=True)
        surf = f.render(text, True, (255, 235, 120))
        surf.set_alpha(int(255 * min(fade * 1.6, 1.0)))
        rect = surf.get_rect(center=(cx, C.WINDOW_HEIGHT // 3))
        surface.blit(surf, rect)

    if race.finished:
        lines = race.summary_lines()
        big = pygame.font.SysFont("consolas", 38, bold=True)
        small = pygame.font.SysFont("consolas", 24)

        panel_h = 90 + 30 * len(lines)
        panel = pygame.Surface((460, panel_h), pygame.SRCALPHA)
        panel.fill((15, 18, 28, 215))
        prect = panel.get_rect(center=(cx, C.WINDOW_HEIGHT // 2))
        surface.blit(panel, prect)

        title = big.render("RACE COMPLETE", True, (255, 220, 90))
        surface.blit(title, title.get_rect(center=(cx, prect.top + 34)))

        y = prect.top + 78
        for ln in lines:
            col = (255, 255, 255)
            if ln.startswith("  lap"):
                col = (185, 195, 210)
            elif "place" in ln:
                col = (140, 255, 160)
            s = small.render(ln, True, col)
            surface.blit(s, s.get_rect(midleft=(prect.left + 40, y)))
            y += 30

        hint = small.render("Esc to quit", True, (150, 160, 175))
        surface.blit(hint, hint.get_rect(center=(cx, prect.bottom - 20)))


def draw_hud(surface, font, player, connected, control_name,
             steer=0.0, throttle=0.0, net_pps=0.0, crash=None,
             race=None, remote_lap=None, rival_gap=None):
    kmh = int(player.speed / 60)     
    lines = [
        f"{player.name}   {kmh} km/h",
        f"steer {steer:+.2f}   gas {throttle:+.2f}",
        f"control: {control_name}" + ("   [C] calibrate"
                                      if control_name == "gesture" else ""),
        ("opponent: connected  %.0f pkt/s" % net_pps) if connected
        else "opponent: waiting...",
        f"crashes: {crash.count}",
    ]
    if race is not None:
        lines.insert(1, f"LAP {min(race.lap, race.total_laps)}/{race.total_laps}"
                        f"   {race_mod.format_time(race.race_time)}")
        if remote_lap:
            lines.append(f"rival lap: {remote_lap}")
    if rival_gap is not None:
        
        metres = abs(rival_gap) / C.SEG_L * C.GAP_METRES_PER_SEGMENT
        if rival_gap > 0:
            lines.append(f"rival AHEAD  {metres:.0f}m")
        else:
            lines.append(f"rival behind {metres:.0f}m")
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
    
    player.x = -C.START_OFFSET_X if is_host else C.START_OFFSET_X
    net = NetworkPeer(is_host=is_host, host_ip=host_ip, port=args.port)
    controller = make_input(prefer_gesture=not args.keyboard)

    print(f"[net] {'hosting on' if is_host else 'joining'} "
          f"{'0.0.0.0' if is_host else host_ip}:{args.port}")

    crash = CrashState()
    dust = DustSystem()
    speedlines = SpeedLines()
    race = Race()
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

        
        can_drive = race.update(dt)
        if not can_drive:
            steer_in = 0.0
            throttle_in = 0.0
            if race.finished:
                player.speed = max(
                    player.speed - C.RACE_FINISH_BRAKE * dt, 0.0)
            else:
                player.speed = 0.0

        crash.update(dt)
        if crash.active:
            
            spin = C.CRASH_STEER_SPIN * (1 if crash.count % 2 else -1)
            steer_in, throttle_in = spin, 0.0

        prev_pos = player.pos
        player.update(dt, steer_in, throttle_in, curve_here, track_len)
        race.check_lap(prev_pos, player.pos, track_len)

        my_state = player.state()
        my_state["lap"] = race.lap
        my_state["done"] = race.finished
        my_state["rt"] = round(race.race_time, 3)
        net.send(my_state)
        if C.NET_INTERP_ENABLED:
            rstate = net.remote_interpolated(
                delay=C.NET_INTERP_DELAY, track_len=track_len)
        else:
            rstate = net.remote
        rival_gap = None
        if rstate is not None:
            d = rstate.get("pos", 0.0) - player.pos
            if d > track_len / 2:
                d -= track_len
            elif d < -track_len / 2:
                d += track_len
            rival_gap = d

        race.note_opponent(rstate)
        race.resolve_place()
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

       
        vp_x = C.WINDOW_WIDTH / 2
        vp_y = C.WINDOW_HEIGHT * C.SPEEDLINE_VP_Y
        if C.SPEEDLINE_ENABLED:
            speedlines.update(dt, player.speed, vp_x, vp_y)

        renderer.scroll_background(curve_here, player.speed)
        renderer.draw(player.x, player.pos, cam_extra_h, player.speed, remote)
        dust.draw(window)          
        draw_own_car(window, local_color, player.steer, shake_x, shake_y)

        if C.SPEEDLINE_ENABLED:
            speedlines.draw(window, vp_x, vp_y)

        if crash.flash > 0.0:
            flash = pygame.Surface((C.WINDOW_WIDTH, C.WINDOW_HEIGHT),
                                   pygame.SRCALPHA)
            flash.fill((210, 120, 40, int(70 * crash.flash)))
            window.blit(flash, (0, 0))
        draw_hud(window, font, player, net.connected(), controller.name,
                 steer_in, throttle_in, net.stats()["pps"], crash,
                 race, rstate.get("lap") if rstate else None, rival_gap)

        draw_race_overlay(window, race)

        pygame.display.update()

    controller.close()
    net.close()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
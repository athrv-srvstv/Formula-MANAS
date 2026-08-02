# Gesture Racer — 2-player pseudo-3D racing

A two-player racer built on the classic Outrun-style pseudo-3D road. You
steer by miming an **invisible steering wheel** in front of your webcam;
your opponent is synced over the network and drawn ahead of you with a
**sprite-stacked** car. Back-view perspective, host = red, guest = blue.

If MediaPipe/OpenCV or a camera isn't available, it automatically falls
back to **arrow keys**, so it runs anywhere.

## Install

```bash
pip install -r requirements.txt
```

`pygame` is required. `opencv-python` + `mediapipe` are only needed for
gesture control.

Drop the original project's art into an `images/` folder next to the code
(`bg.png`, `1.png` … `7.png`). If it's missing, the game generates simple
placeholder graphics so it still runs.

## Run

Two terminals on one machine (easiest for testing):

```bash
python main.py --host
python main.py --join 127.0.0.1
```

Two machines on the same network:

```bash
# Machine A — note its LAN IP (e.g. 192.168.1.20)
python main.py --host
# Machine B
python main.py --join 192.168.1.20
```

Flags: `--keyboard` (force keys), `--name YOU`, `--port N` (must match on
both peers). `Esc` or closing the window quits.

## Controls

**Gestures** — hold both hands up like you're gripping a wheel:

| Do this | Effect |
|---|---|
| Tilt the wheel (one hand higher than the other) | Steer |
| Raise both hands | Accelerate |
| Lower both hands | Brake |
| Drop your hands | Coast, straighten |

A small camera window shows the tracked wheel; press `q` in it to hide.

**Keyboard fallback** — arrow keys (↑ gas, ↓ brake, ←/→ steer).

## How it fits together

| File | Responsibility |
|---|---|
| `main.py` | Arg parsing, game loop, own-car draw, HUD |
| `config.py` | All tunables (physics feel, gesture sensitivity, colors) |
| `track.py` | `Line` segments + circuit layout + projection math |
| `render.py` | Road, parallax background, roadside props, opponent car |
| `player.py` | Continuous physics (throttle / friction / centrifugal) |
| `network.py` | UDP peer-to-peer state sync (non-blocking, crash-safe) |
| `inputs.py` | Input abstraction + keyboard controller |
| `gestures.py` | MediaPipe invisible-wheel controller (own thread) |
| `sprite_stack.py` | Procedural sprite-stacked car + renderer |
| `assets.py` | Asset loading with placeholder fallbacks |

## Tuning

Nearly everything you'd want to feel out lives in `config.py`:
`WHEEL_MAX_DEG` (how far to tilt for full lock), `THROTTLE_TOP/BOTTOM`
(hand-height gas/brake band), `GESTURE_SMOOTHING` (jitter filter),
`MAX_SPEED`/`ACCEL`/`CENTRIFUGAL` (driving feel).

## Known limitations / next steps

- **No lap logic / collisions yet.** Cars pass through each other; add an
  x-overlap + pos-overlap check in the loop for contact, and a lap counter
  keyed on `pos` wrapping.
- **Opponent only visible when ahead of you** (it's a back-view racer, so
  that's expected). If you want a rear-view mirror, project a second small
  camera looking backward.
- **Opponent heading is approximated** from their steer + local curve;
  fine visually, but true heading would come from sending a heading value.
- **2 players only.** UDP peering generalizes to N with a small lobby, or
  move to a client/server hub for more racers.
# Formula-MANAS

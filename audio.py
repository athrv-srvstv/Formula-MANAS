"""Procedurally synthesized audio -- no sound files required.

Everything you hear is generated from maths at startup (or, for the engine,
continuously while you drive). That means no asset hunting, no licensing
questions, and the engine note can track your speed smoothly instead of
being a fixed loop that obviously repeats.

THE ENGINE NOTE
---------------
The hard part of a racing engine sound is that its pitch must slide
continuously with RPM. Pre-rendering a handful of loops and switching
between them clicks audibly at every switch, because the waveform jumps
mid-cycle.

So instead we generate short buffers (~60ms) on a background thread and
queue them back-to-back on one mixer channel, carrying the oscillator PHASE
across buffer boundaries. Continuous phase means no discontinuity, so no
clicks, and the pitch can change every buffer. It's a tiny software
synthesizer running alongside the game.

The timbre is a stack of harmonics (like a real engine's firing orders)
plus a little noise for grit, with the higher harmonics coming in as revs
rise so it gets harsher under load rather than just higher.

Everything degrades gracefully: if numpy or the mixer is unavailable the
whole module turns into no-ops and the game runs silently.
"""

import threading
import time

import config as C

try:
    import numpy as np
    _HAVE_NUMPY = True
except ImportError:                     # pragma: no cover
    _HAVE_NUMPY = False

SAMPLE_RATE = 22050
BUFFER_MS = 60


# ---------------------------------------------------------------------------
# Waveform helpers (pure numpy -- testable without pygame or a sound card)
# ---------------------------------------------------------------------------
def _to_int16(mono):
    """Float [-1,1] -> stereo int16, the format pygame's mixer wants."""
    mono = np.clip(mono, -1.0, 1.0)
    pcm = (mono * 32767.0).astype(np.int16)
    return np.repeat(pcm[:, None], 2, axis=1)


def engine_buffer(n, freq, throttle, phase, rng, load=0.5):
    """One chunk of engine tone, continuing from `phase`.

    Returns (samples_float, next_phase). Keeping the phase lets the caller
    stitch buffers together seamlessly.

    TIMBRE: fundamental + a strong 2nd + a light 3rd that opens up with load.
    Deliberately restrained. Piling on 4th/6th harmonics and a sawtooth edge
    (an earlier version did) makes it buzz like a kazoo rather than rumble --
    a real exhaust has far less high-harmonic content than you'd expect.
    The 3rd harmonic growing with load is what gives it bite under
    acceleration without making it shrill at cruise.
    """
    t = np.arange(n, dtype=np.float64)
    inc = 2.0 * np.pi * freq / SAMPLE_RATE
    ph = phase + inc * t

    wave = np.sin(ph)
    wave += 0.40 * np.sin(2 * ph)
    wave += (0.10 + 0.14 * load) * np.sin(3 * ph)
    wave /= 1.5

    # a little combustion roughness; too much reads as static
    wave += rng.normal(0.0, 0.02 + 0.03 * load, n)

    amp = C.SFX_ENGINE_VOLUME * (0.35 + 0.65 * throttle)
    return wave * amp, (phase + inc * n) % (2.0 * np.pi)


def noise_burst(dur, kind="crash", seed=0):
    """One-shot noise-based effect."""
    n = int(SAMPLE_RATE * dur)
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, dur, n, endpoint=False)
    x = rng.normal(0.0, 1.0, n)

    if kind == "crash":
        # bright impact that decays into a low thud
        env = np.exp(-t * 9.0)
        low = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 5.0)
        x = x * env * 0.7 + low * 0.6
    elif kind == "screech":
        # band-ish noise: smooth it, then ring-modulate for a squeal
        k = 12
        x = np.convolve(x, np.ones(k) / k, mode="same")
        x = x * (0.6 + 0.4 * np.sin(2 * np.pi * 900 * t))
        x *= np.minimum(t * 8.0, 1.0)
    elif kind == "rumble":
        k = 45
        x = np.convolve(x, np.ones(k) / k, mode="same") * 2.2
    return np.clip(x, -1.0, 1.0)


def tone(freq, dur, kind="beep", seed=0):
    """One-shot pitched effect (countdown beeps, lap chime, finish jingle)."""
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0.0, dur, n, endpoint=False)
    if kind == "beep":
        env = np.minimum(t * 60.0, 1.0) * np.exp(-t * 4.5)
        x = (np.sin(2 * np.pi * freq * t)
             + 0.35 * np.sin(4 * np.pi * freq * t)) * env
    elif kind == "chime":
        env = np.exp(-t * 3.0)
        x = (np.sin(2 * np.pi * freq * t)
             + 0.5 * np.sin(2 * np.pi * freq * 1.5 * t)
             + 0.25 * np.sin(2 * np.pi * freq * 2.0 * t)) * env
    return np.clip(x * 0.6, -1.0, 1.0)


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
class Audio:
    """Owns the mixer, the engine synth thread and the one-shot effects."""

    def __init__(self):
        self.ok = False
        self._engine_freq = C.SFX_ENGINE_BASE_HZ
        self._engine_throttle = 0.0
        self._engine_load = 0.0
        self._running = False
        self._sounds = {}
        self._lock = threading.Lock()

        if not C.SFX_ENABLED or not _HAVE_NUMPY:
            return
        try:
            import pygame
            pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
            pygame.mixer.init(SAMPLE_RATE, -16, 2, 512)
            pygame.mixer.set_num_channels(16)
            self._pygame = pygame
        except Exception as e:                      # noqa: BLE001
            print(f"[audio] disabled ({type(e).__name__}: {e})")
            return

        try:
            self._build_effects()
            self._engine_channel = pygame.mixer.Channel(0)
            self._loop_channel = pygame.mixer.Channel(1)
            self.ok = True
        except Exception as e:                      # noqa: BLE001
            print(f"[audio] effect build failed ({e})")
            return

        self._running = True
        self._thread = threading.Thread(target=self._engine_loop, daemon=True)
        self._thread.start()

    # -- one-shot effects ---------------------------------------------------
    def _snd(self, mono):
        return self._pygame.sndarray.make_sound(
            np.ascontiguousarray(_to_int16(mono)))

    def _build_effects(self):
        self._sounds["crash"] = self._snd(noise_burst(0.55, "crash", 1))
        self._sounds["rock"] = self._snd(noise_burst(0.40, "crash", 7))
        self._sounds["screech"] = self._snd(noise_burst(0.50, "screech", 3))
        self._sounds["offroad"] = self._snd(noise_burst(1.00, "rumble", 5))
        self._sounds["beep"] = self._snd(tone(660, 0.18, "beep"))
        self._sounds["go"] = self._snd(tone(1040, 0.45, "beep"))
        self._sounds["lap"] = self._snd(tone(880, 0.5, "chime"))
        # finish: a short rising arpeggio
        parts = [tone(660, 0.16, "chime"), tone(880, 0.16, "chime"),
                 tone(1320, 0.5, "chime")]
        self._sounds["finish"] = self._snd(np.concatenate(parts))

        for key, vol in (("crash", 0.9), ("rock", 0.8), ("screech", 0.5),
                         ("offroad", 0.45), ("beep", 0.7), ("go", 0.85),
                         ("lap", 0.7), ("finish", 0.9)):
            self._sounds[key].set_volume(vol * C.SFX_MASTER_VOLUME)

    def play(self, name):
        if not self.ok:
            return
        snd = self._sounds.get(name)
        if snd is None:
            return
        try:
            snd.play()
        except Exception:                           # noqa: BLE001
            pass

    def loop_surface(self, offroad: bool, screech: float):
        """Continuous surface noise: off-road rumble / tyre scrub."""
        if not self.ok:
            return
        try:
            if offroad:
                if not self._loop_channel.get_busy():
                    self._loop_channel.play(self._sounds["offroad"], loops=-1)
                self._loop_channel.set_volume(0.5 * C.SFX_MASTER_VOLUME)
            elif screech > 0.5:
                if not self._loop_channel.get_busy():
                    self._loop_channel.play(self._sounds["screech"], loops=-1)
                self._loop_channel.set_volume(
                    min((screech - 0.5) * 1.4, 1.0) * 0.4
                    * C.SFX_MASTER_VOLUME)
            else:
                self._loop_channel.stop()
        except Exception:                           # noqa: BLE001
            pass

    # -- engine -------------------------------------------------------------
    def set_engine(self, speed_frac: float, throttle: float):
        """Update the engine note. Cheap; safe to call every frame."""
        speed_frac = max(min(speed_frac, 1.4), 0.0)
        # A gearbox: the note climbs, drops on the shift, then climbs again.
        # Without this a single sweep from idle to top sounds like a siren.
        gears = C.SFX_GEARS
        g = min(int(speed_frac * gears), gears - 1)
        within = speed_frac * gears - g
        freq = C.SFX_ENGINE_BASE_HZ * (1.0 + C.SFX_ENGINE_RANGE * within)
        freq *= (1.0 + 0.06 * g)          # each gear sits slightly higher
        with self._lock:
            self._engine_freq = freq
            self._engine_throttle = max(min(throttle, 1.0), 0.0)
            self._engine_load = max(min(speed_frac, 1.0), 0.0)

    def _engine_loop(self):
        n = int(SAMPLE_RATE * BUFFER_MS / 1000)
        phase = 0.0
        rng = np.random.default_rng(11)
        while self._running:
            try:
                with self._lock:
                    freq = self._engine_freq
                    thr = self._engine_throttle
                    load = self._engine_load
                buf, phase = engine_buffer(n, freq, thr, phase, rng, load)
                snd = self._snd(buf)
                # Queue rather than play: the channel plays them back to back,
                # and continuous phase means the joins are inaudible.
                if self._engine_channel.get_queue() is None:
                    if self._engine_channel.get_busy():
                        self._engine_channel.queue(snd)
                    else:
                        self._engine_channel.play(snd)
                else:
                    time.sleep(BUFFER_MS / 4000.0)
                    continue
            except Exception:                       # noqa: BLE001
                time.sleep(0.05)
                continue
            time.sleep(BUFFER_MS / 3000.0)

    def stop(self):
        self._running = False
        if not self.ok:
            return
        try:
            self._pygame.mixer.stop()
        except Exception:                           # noqa: BLE001
            pass
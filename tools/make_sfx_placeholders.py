#!/usr/bin/env python3
"""Writes placeholder sound effects (square and noise blips, mono 16-bit 18500 Hz WAV) for the sample map:
jump, hit, game_over, coin, die, fall, splosh, spike, pop, sizzle. Replaced by real samples later; ids and file names stay the same.
Usage: make_sfx_placeholders.py OUT_DIR"""
import math
import os
import random
import struct
import sys
import wave

RATE = 18500


def square(freq_from, freq_to, seconds, volume=0.5):
    n = int(RATE * seconds)
    out, phase = [], 0.0
    for i in range(n):
        f = freq_from + (freq_to - freq_from) * i / n
        phase += f / RATE
        env = 1.0 - i / n
        out.append(int(32767 * volume * env * (1.0 if (phase % 1.0) < 0.5 else -1.0)))
    return out


def noise(seconds, volume=0.5):
    rng = random.Random(1)
    n = int(RATE * seconds)
    return [int(32767 * volume * (1.0 - i / n) * rng.uniform(-1, 1)) for i in range(n)]


def sizzle(seconds, volume=0.5):
    # crackle: noise gated by random on/off grains (every 1.5 ms), decaying; own synthesis
    rng = random.Random(7)
    n = int(RATE * seconds)
    grain, on, out = int(RATE * 0.0015), 1, []
    for i in range(n):
        if i % grain == 0:
            on = 1 if rng.random() < 0.6 * (1.0 - i / n) + 0.15 else 0
        out.append(int(32767 * volume * (1.0 - i / n) ** 1.5 * on * rng.uniform(-1, 1)))
    return out


def sequence(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


SOUNDS = {
    "jump": lambda: square(300, 700, 0.18),
    "hit": lambda: noise(0.30),
    "game_over": lambda: sequence(square(440, 440, 0.2), square(330, 330, 0.2), square(220, 220, 0.5)),
    "coin": lambda: sequence(square(988, 988, 0.08), square(1319, 1319, 0.30)),
    "die": lambda: square(140, 60, 0.30, 0.7),
    "fall": lambda: square(900, 120, 0.60),
    "splosh": lambda: noise(0.40, 0.6),
    "sizzle": lambda: sizzle(0.45),
    "pop": lambda: sequence(square(2600, 1200, 0.05, 0.7), square(1600, 800, 0.04, 0.4)),
    "spike": lambda: sequence(square(2400, 2400, 0.03, 0.6), square(1800, 1800, 0.03, 0.3)),
}


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, make in SOUNDS.items():
        with wave.open(os.path.join(out_dir, name + ".wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(b"".join(struct.pack("<h", s) for s in make()))


if __name__ == "__main__":
    main(sys.argv[1])

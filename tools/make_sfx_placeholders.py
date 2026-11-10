#!/usr/bin/env python3
"""Writes placeholder sound effects (square and noise blips, mono 16-bit 18500 Hz WAV) for the sample map:
jump, hit, game_over, coin. Replaced by real samples later; ids and file names stay the same.
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

#!/usr/bin/env python3
"""Renders the Gumbirds sound effects (mono 16-bit 18500 Hz WAV, one per ADPCM-A sample of assets/sound/sample-map.yaml).
Own synthesis only, no recorded or copied material. Each effect is layered the way a YM2610 patch would be:
4-operator FM voices (algorithms 0, 4, 5, 7, operator 1 feedback), SSG square with a 4-bit 60 Hz volume macro,
SSG style clocked noise, pitch sweeps, then a baked-in master chain (shelf EQ, saturation, compressor, very short
room) and a low-pass under 8 kHz before the resample from 55500 Hz to 18500 Hz. Output is deterministic (fixed seeds).
Usage: make_sfx.py OUT_DIR [-v] [name ...]   (no names: every effect; -v prints length and ADPCM bytes per effect)"""
import os
import random
import sys
import wave

import numpy as np

RATE = 18500
OS = 3                      # synthesis runs at 3x the output rate so FM sidebands fold less
SR = RATE * OS
BUDGET = 393216             # V ROM share of the effects (384 KB); the music keeps 128 KB
_K = np.arange(-75, 76)
FIR = np.sinc(2 * 7900.0 / SR * _K) * 2 * 7900.0 / SR * np.hamming(151)


def n_(ms):
    return int(round(SR * ms / 1000.0))


def tms(ms):
    return np.arange(n_(ms)) * 1000.0 / SR


def hz(note):
    if not isinstance(note, str):
        return float(note)
    semis = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[note[0]] + ("#" in note)
    return 440.0 * 2 ** ((semis - 9) / 12.0 + int(note[-1]) - 4)


def curve(ms, *pts):
    """Frequency over ms from (ms, Hz) points: exponential glide between points, held outside them."""
    return np.exp(np.interp(tms(ms), [p[0] for p in pts], np.log([p[1] for p in pts])))


def env(n, a, d, hold=0.0):
    """OPN style envelope over n samples: linear attack a ms, hold ms, exponential decay that is -60 dB after d ms."""
    t = np.arange(n) * 1000.0 / SR
    return np.where(t < a, t / max(a, 1e-9), 10.0 ** (-3.0 * np.maximum(t - a - hold, 0.0) / d))


def fm4(f, alg, ops, fb=0.0):
    """Four operators on the frequency curve f. ops: 4 x (ratio, level, attack ms, decay ms[, hold ms]);
    level is the amplitude of a carrier and the modulation index (radians) of a modulator. fb feeds operator 1 back."""
    f = np.asarray(f, float)
    ph = 2 * np.pi * np.cumsum(f) / SR
    e = [o[1] * env(len(f), *o[2:]) for o in ops]

    def osc(i, mod=0.0):
        return e[i] * np.sin(ph * ops[i][0] + mod)

    o1 = 0.0
    for _ in range(4):      # shortcut: fixed-point feedback, not the chip's two-sample average; upgrade if a patch needs fb 7 noise
        o1 = osc(0, fb * o1)
    if alg == 0:
        return osc(3, osc(2, osc(1, o1)))
    if alg == 4:
        return osc(1, o1) + osc(3, osc(2))
    if alg == 5:
        return osc(1, o1) + osc(2, o1) + osc(3, o1)
    assert alg == 7, alg
    return o1 + osc(1) + osc(2) + osc(3)


def fm2(f, d, idx=1.0, ratio=1.0, mdec=None, fb=0.0, a=1.0, hold=0.0):
    """One modulator/carrier stack (algorithm 4 with the second stack silent)."""
    return fm4(f, 4, ((ratio, idx, 0.5, mdec or d, hold), (1.0, 1.0, a, d, hold), (1, 0, 1, 1), (1, 0, 1, 1)), fb)


def noise(ms, clock, seed):
    """SSG style noise: a random bit held until the noise clock (Hz, value or curve) ticks."""
    n = n_(ms)
    idx = np.floor(np.cumsum(np.broadcast_to(np.asarray(clock, float), n)) / SR).astype(int)
    return (np.random.default_rng(seed).integers(0, 2, idx[-1] + 2) * 2.0 - 1.0)[idx]


def ssg(f, vol):
    """SSG square; vol is stepped at 60 Hz and snapped to the chip's 3 dB levels (a volume macro)."""
    step = n_(1000 / 60.0)
    v = vol[::step].repeat(step)[:len(f)]
    q = np.where(v > 2 ** -7.5, 2.0 ** (np.round(2 * np.log2(np.maximum(v, 1e-9))) / 2), 0.0)
    return np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * q


def arp(ms, names, step, d):
    n, s = n_(ms), n_(step)
    f = np.repeat([hz(names[i % len(names)]) for i in range(n // s + 1)], s)[:n]
    return ssg(f, env(n, 1, d))


def mix(ms, *parts):
    """parts: (start ms, signal, gain); anything past ms is cut."""
    out = np.zeros(n_(ms))
    for at, sig, gain in parts:
        s = n_(at)
        k = min(len(sig), len(out) - s)
        if k > 0:
            out[s:s + k] += gain * sig[:k]
    return out


def lp(x, fc):
    a = 1.0 - np.exp(-2 * np.pi * fc / SR)
    return np.convolve(x, a * (1 - a) ** np.arange(min(len(x), int(7 / a) + 1)))[:len(x)]


def hp(x, fc):
    return x - lp(x, fc)


def echo(x, ms, gain):
    y, d = x.copy(), n_(ms)
    y[d:] += gain * x[:-d]
    return y


def room(x, ms, wet):
    """Very short room: a handful of decaying, darkened reflections inside ms."""
    rng = np.random.default_rng(5)
    out = np.zeros(len(x))
    for frac in np.sort(rng.uniform(0.12, 1.0, max(6, int(ms / 8)))):
        d = n_(ms * frac)
        if d < len(x):
            out[d:] += np.exp(-3.0 * frac) * rng.choice((-1.0, 1.0)) * x[:len(x) - d]
    return x + wet * lp(out, 3500.0)


def master(x, drive=1.6, thr=0.35, ratio=3.0, rm=0.0, wet=0.15, low=0.0, high=0.0):
    """Shelf EQ, saturation, compressor (60 Hz RMS detector, so the transient stays), room, low-pass, 18500 Hz, peak 0.9."""
    x = hp(x, 35.0)
    x = x + low * lp(x, 220.0) + high * hp(x, 3000.0)
    x = np.tanh(drive * x / np.max(np.abs(x))) / np.tanh(drive)
    x = x * np.minimum(1.0, (thr / (np.sqrt(lp(x * x, 60.0)) + 1e-9)) ** (1 - 1 / ratio))
    if rm:
        x = room(x, rm, wet)
    y = np.convolve(x, FIR, "same")[::OS]
    fade = RATE * 6 // 1000
    y[-fade:] *= np.linspace(1.0, 0.0, fade)
    return y * 0.9 / np.max(np.abs(y))


# ---- patches ----

def bell(freq, ms, d=None):
    d = d or ms
    return fm4(curve(ms, (0, hz(freq))), 5, ((3.5, 1.8, 0.3, d * 0.35), (1, 1, 0.5, d), (2, 0.35, 0.5, d * 0.6), (4, 0.15, 0.5, d * 0.3)))


def brass(freq, ms):
    return fm2(curve(ms, (0, hz(freq))), ms * 0.5, idx=2.4, mdec=ms * 0.9, a=14, hold=ms * 0.55, fb=0.4)


def click():
    return fm4(curve(12, (0, 1900)), 7, ((1, 1, 0.2, 5), (2.7, 0.8, 0.2, 4), (4.1, 0.6, 0.2, 3), (1.5, 0.8, 0.2, 6)), fb=2.5)


def phrase(patch, notes, gain=1.0):
    """notes: (start ms, note, length ms)."""
    return [(at, patch(note, ln), gain) for at, note, ln in notes]


def pop(f0, wet, double):
    burst = noise(40, 9000, 21) * env(n_(40), 0.3, 25)
    drop = fm2(curve(140, (0, f0), (60, 300)), 85, idx=0.7, mdec=25)
    parts = [(0, click(), 0.9), (0, burst, 0.8), (0, drop, 1.0)] + ([(8, click(), 0.7)] if double else [])
    return master(mix(140, *parts), drive=2.0, thr=0.2, ratio=6, rm=40, wet=wet)


def hit():
    knock = fm4(curve(260, (0, 400), (200, 90)), 0, ((3.5, 2.0, 0.3, 40), (1, 2.5, 0.3, 60), (3.5, 1.5, 0.3, 50), (1, 1, 0.5, 230)), fb=0.3)
    slap = lp(noise(80, 7000, 31), 4000) * env(n_(80), 0.3, 55)
    return master(mix(260, (0, knock, 1), (0, slap, 0.7)), drive=2.6, thr=0.25, ratio=5, rm=30, wet=0.1, low=0.4)


def vib(f, rate, depth):
    return f * (1 + depth * np.sin(2 * np.pi * rate * np.arange(len(f)) / SR))


def die():
    f = vib(curve(420, (0, 600), (400, 150)), 9, 0.03)
    a = fm2(f, 300, idx=1.6, hold=120, a=3)
    b = fm2(f * 1.0595, 300, idx=1.6, hold=120, a=3)
    tick = noise(12, 9000, 41) * env(n_(12), 0.2, 8)
    return master(echo(mix(420, (0, a, 0.6), (0, b, 0.5), (0, tick, 0.6)), 70, 0.3), drive=1.8, rm=30, wet=0.1)


def fall():
    f = vib(curve(700, (0, 1400), (680, 180)), 7, 0.06 * tms(700) / 700)
    return master(mix(700, (0, fm2(f, 250, idx=0.35, hold=450, a=8), 1), (40, fm2(f * 0.5, 250, idx=0.3, hold=410, a=8), 0.3)), drive=1.3, rm=35, wet=0.12)


def sizzle():
    n, g = n_(520), n_(1.5)
    steps = n // g + 1
    gate = np.repeat((np.random.default_rng(61).random(steps) < 0.15 + 0.6 * (1 - np.arange(steps) / steps)).astype(float), g)[:n]
    crackle = noise(520, curve(520, (0, 9000), (500, 4000)), 62) * gate * env(n, 1, 600)
    hiss = hp(noise(520, 16000, 63), 3000) * env(n, 20, 420)
    whump = fm2(curve(140, (0, 95), (120, 50)), 130, idx=1.5, mdec=50)
    return master(mix(520, (0, crackle, 0.8), (0, hiss, 0.35), (0, whump, 0.8)), drive=2.2, rm=25, wet=0.08)


def spike():
    p1 = fm2(curve(180, (0, 2400)), 150, idx=2.0, mdec=18)
    p2 = fm2(curve(180, (0, 3100)), 110, idx=1.5, mdec=14, ratio=1.41)
    tick = noise(8, 12000, 71) * env(n_(8), 0.2, 5)
    return master(mix(180, (0, p1, 0.8), (0, p2, 0.5), (0, tick, 0.7)), drive=1.6, thr=0.25, ratio=5, rm=25, wet=0.1)


def game_over():
    lead = phrase(brass, [(0, "A4", 230), (220, "G4", 230), (440, "F4", 230), (660, "E4", 300)])
    chord = [(960, fm2(curve(1240, (0, hz(nn))), 900, idx=2.4, mdec=500, a=14, hold=250, fb=0.4), 0.5) for nn in ("A3", "C4", "E4", "A4")]
    return master(mix(2200, *lead, *chord, (0, arp(960, ("A3", "C4", "E4"), 55, 2000), 0.15)), drive=1.5, rm=300, wet=0.2)


def start():
    swell = hp(noise(330, 9000, 81), 2500) * (tms(330) / 330) ** 2
    notes = phrase(bell, [(0, "C5", 150), (110, "E5", 150), (220, "G5", 150), (330, "C6", 370)])
    return master(mix(700, *notes, (0, swell, 0.3)), drive=1.4, rm=45, wet=0.15)


def round_go():
    stabs = phrase(brass, [(0, "G4", 170), (0, "D5", 170), (220, "C5", 380), (220, "G5", 380)], 0.6)
    snare = hp(noise(160, 11000, 91), 1200) * env(n_(160), 0.5, 130)
    return master(mix(600, *stabs, (220, snare, 0.6)), drive=1.8, thr=0.3, rm=40)


def banner_in():
    whoosh = lp(noise(400, curve(400, (0, 1500), (380, 9000)), 101) * (tms(400) / 400) ** 1.5, 5000)
    thud = fm2(curve(100, (0, 150), (80, 70)), 95, idx=1.8, mdec=30)
    return master(mix(500, (0, whoosh, 0.6), (395, thud, 1.0)), drive=1.8, low=0.4, rm=30)


def pump(f0, f1):
    squeak = fm2(curve(160, (0, f0), (140, f1)), 110, idx=1.4, fb=0.8, a=15, hold=40, mdec=150)
    breath = hp(noise(160, 8000, 111), 2000) * env(n_(160), 20, 120)
    return master(mix(160, (0, squeak, 1), (0, breath, 0.25)), drive=1.5, rm=20, wet=0.1)


def rival_launch():
    rise = fm2(curve(300, (0, 400), (280, 1200)), 200, idx=1.0, a=10, hold=100)
    puff = lp(noise(40, 8000, 115), 3000) * env(n_(40), 0.5, 35)
    return master(mix(300, (0, rise, 1), (0, puff, 0.5)), rm=30)


def bump():
    return master(fm2(curve(150, (0, 260), (50, 180), (140, 240)), 140, idx=2.2, mdec=60))


def chute():
    gate = mix(260, *[(at, env(n_(55), 8, 50), 1.0) for at in (0, 60, 120)])
    whoomp = fm2(curve(220, (0, 300), (200, 200)), 200, idx=0.8, a=10)
    return master(mix(260, (0, lp(noise(260, 5000, 121), 3000) * gate, 0.7), (20, whoomp, 0.8)), rm=30)


def defeat():
    return master(mix(300, *phrase(bell, [(0, "E5", 90), (70, "G5", 90), (140, "B5", 160)]), (0, click(), 0.5)), drive=1.4, rm=35)


def vent_warn():
    r = tms(600) / 600
    hiss = hp(noise(600, 7000, 131), 1500) * r ** 2
    rumble = fm2(curve(600, (0, 60)), 5000, idx=2.5, fb=0.6) * r
    return master(mix(600, (0, hiss, 0.6), (0, rumble, 0.9)), drive=2.0, low=0.5)


def vent_burst():
    n = n_(650)
    blast = fm2(curve(450, (0, 200), (300, 80)), 400, idx=4.0, fb=1.0, mdec=250)
    air = noise(650, 10000, 141) * (env(n, 0.5, 150) + 0.35 * env(n, 0.5, 640))
    return master(mix(650, (0, blast, 1), (0, air, 0.8)), drive=3.0, thr=0.2, ratio=6, low=0.5, rm=40)


def flipper():
    twang = fm2(curve(220, (0, 500), (60, 900), (200, 650)), 200, idx=2.5, ratio=2.0, mdec=80)
    return master(mix(220, (0, twang, 1), (0, click(), 0.5)), rm=25)


def grab_rise():
    blips = [(i * 80, fm2(curve(75, (0, f), (60, f * 1.25)), 70, idx=0.8, a=4), 0.8) for i, f in enumerate((200, 270, 340, 420, 500))]
    wet = lp(noise(450, 3000, 151), 1200) * env(n_(450), 40, 420)
    return master(mix(450, *blips, (0, wet, 0.3)), low=0.3, rm=60, wet=0.2)


def grab_bite():
    snap = fm2(curve(300, (0, 700), (200, 120)), 260, idx=4.0, ratio=3.5, mdec=50)
    slap = lp(noise(60, 8000, 161), 4500) * env(n_(60), 0.3, 40)
    return master(mix(300, (0, snap, 1), (0, slap, 0.7)), drive=2.6, thr=0.22, ratio=6, rm=30)


def grate():
    shape = np.sin(np.pi * tms(600) / 600) ** 1.5
    whoosh = lp(noise(600, curve(600, (0, 2000), (550, 8000)), 171), 5000) * shape
    air = fm2(curve(600, (0, 500), (580, 900)), 5000, idx=0.2) * shape
    return master(mix(600, (0, whoosh, 0.8), (0, air, 0.35)), drive=1.3, rm=40)


def bubble_puff():
    bloop = fm2(curve(180, (0, 350), (120, 600)), 130, idx=0.8, a=8, hold=30)
    breath = hp(noise(70, 7000, 181), 2500) * env(n_(70), 5, 60)
    return master(mix(180, (0, bloop, 1), (0, breath, 0.15)), rm=30)


def stage_clear():
    lead = phrase(brass, [(0, "C5", 130), (120, "E5", 130), (240, "G5", 130), (360, "C6", 250), (600, "G5", 130), (720, "C6", 880)])
    under = phrase(brass, [(0, "E4", 130), (120, "G4", 130), (240, "C5", 130), (360, "E5", 250), (600, "D5", 130), (720, "C5", 880), (720, "E5", 880), (720, "G5", 880)], 0.5)
    return master(mix(1600, *lead, *under, (0, arp(1600, ("C6", "E6", "G6"), 45, 1800), 0.1)), drive=1.5, rm=250, wet=0.18)


def perfect():
    run = phrase(bell, [(i * 70, nn, 160) for i, nn in enumerate("C5 D5 E5 G5 A5 C6 D6 E6 G6 A6 C7".split())])
    chord = phrase(bell, [(770, nn, 1030) for nn in ("C6", "E6", "G6", "C7")], 0.6)
    return master(mix(1800, *run, *chord, (770, arp(700, ("C7", "E7", "G7"), 40, 700), 0.08)), drive=1.4, rm=300, wet=0.2, high=0.15)


def tally_tick():
    return master(mix(45, (0, click(), 0.8), (0, fm2(curve(45, (0, 1600)), 30, idx=0.8), 1)), drive=1.3)


def tally_bonus():
    crash = hp(noise(250, 14000, 191), 3000) * env(n_(250), 0.5, 200)
    return master(mix(500, *phrase(bell, [(0, nn, 500) for nn in ("C6", "E6", "G6")], 0.7), (0, crash, 0.35)), rm=50)


def pickup(k, third):
    bloop = fm2(curve(130, (0, 500 * k), (90, 1000 * k)), 120, idx=0.9, a=3)
    parts = [(0, bloop, 1), (60, bell(2000 * k, 160, 150), 0.6)] + ([(75, bell(2500 * k, 165, 160), 0.45)] if third else [])
    return master(mix(240 if third else 220, *parts), drive=1.4, rm=30)


def rival_warn():
    def buzz(f, ln):
        return fm2(curve(ln, (0, f)), ln * 0.8, idx=3.0, fb=0.9, hold=ln * 0.5, a=3)
    return master(mix(350, (0, buzz(311, 110), 1), (150, buzz(330, 200), 1)), drive=2.2)


def gum_low():
    beep = fm2(curve(120, (0, 880)), 60, idx=0.5, a=5, hold=70) * (0.75 + 0.25 * np.sin(2 * np.pi * 30 * tms(120) / 1000))
    return master(mix(300, (0, beep, 1), (150, beep, 1)), drive=1.2, rm=25)


def life_lost():
    drop = lp(noise(400, curve(400, (0, 6000), (380, 800)), 201), 4000) * env(n_(400), 10, 380)
    return master(mix(700, *phrase(brass, [(0, "E5", 160), (150, "C5", 160), (300, "A4", 400)]), (300, drop, 0.35)), rm=60)


def continue_tick():
    return master(mix(180, (0, click(), 0.8), (0, fm2(curve(160, (0, 220)), 150, idx=1.2, mdec=60), 0.9)), drive=1.5)


def continue_yes():
    notes = phrase(bell, [(0, "C5", 150), (80, "E5", 150), (160, "G5", 150), (240, "C6", 150), (320, "E6", 280)])
    return master(mix(600, *notes), drive=1.5, rm=45, high=0.3)


def ne_move():
    return master(mix(50, (0, fm2(curve(50, (0, 1200)), 30, idx=1.0, mdec=10), 1), (0, click(), 0.3)), drive=1.3)


def ne_confirm():
    return master(fm2(curve(150, (0, 800), (69, 800), (70, 1200)), 100, idx=1.0, hold=50), drive=1.3, rm=20)


def ne_done():
    notes = phrase(bell, [(0, "G5", 160), (100, "C6", 160), (200, "E6", 160), (300, "G6", 160), (400, "C7", 500)])
    return master(echo(mix(900, *notes), 120, 0.3), drive=1.4, rm=80)


# Old placeholder takes (owner verdict 2026-11-14), ported unchanged from tools/make_sfx_placeholders.py at bd4aa43^.
# Plain square / white noise with a linear fade at the old levels, so they skip the master chain and the peak check.
def _square(f0, f1, seconds, volume=0.5):
    n, phase, out = int(RATE * seconds), 0.0, []
    for i in range(n):
        phase += (f0 + (f1 - f0) * i / n) / RATE
        out.append(int(32767 * volume * (1.0 - i / n) * (1.0 if (phase % 1.0) < 0.5 else -1.0)))
    return out


def _old_noise(seconds, volume=0.5):
    rng, n = random.Random(1), int(RATE * seconds)
    return [int(32767 * volume * (1.0 - i / n) * rng.uniform(-1, 1)) for i in range(n)]


OLD = {   # int16 sample lists, written as is
    "jump": lambda: _square(300, 700, 0.18),
    "splosh": lambda: _old_noise(0.40, 0.6),
    "coin": lambda: _square(988, 988, 0.08) + _square(1319, 1319, 0.30),
}


# name: (length ms, renderer). game_over and stage_clear are preview only: those events play the music jingles.
SOUNDS = {
    "flap_a": (180, OLD["jump"]), "flap_b": (180, OLD["jump"]), "flap_c": (180, OLD["jump"]),   # one sound, three slots: the 3-way rotation stays in the engine
    "pop_a": (140, lambda: pop(1800, 0.15, 0)), "pop_b": (140, lambda: pop(2200, 0.3, 0)), "pop_c": (140, lambda: pop(1500, 0.15, 1)),
    "hit": (260, hit), "die": (420, die), "fall": (700, fall), "splosh": (400, OLD["splosh"]), "sizzle": (520, sizzle), "spike": (180, spike),
    "coin": (380, OLD["coin"]), "game_over": (2200, game_over), "start": (700, start), "round_go": (600, round_go), "banner_in": (500, banner_in),
    "pump_a": (160, lambda: pump(300, 520)), "pump_b": (160, lambda: pump(420, 700)), "rival_launch": (300, rival_launch),
    "bump": (150, bump), "chute": (260, chute), "defeat": (300, defeat), "vent_warn": (600, vent_warn), "vent_burst": (650, vent_burst),
    "flipper": (220, flipper), "grab_rise": (450, grab_rise), "grab_bite": (300, grab_bite), "grate": (600, grate),
    "bubble_puff": (180, bubble_puff), "stage_clear": (1600, stage_clear), "perfect": (1800, perfect), "tally_tick": (45, tally_tick),
    "tally_bonus": (500, tally_bonus), "pickup": (220, lambda: pickup(1.0, 0)), "pickup_streak": (240, lambda: pickup(4.0 / 3, 1)),
    "rival_warn": (350, rival_warn), "gum_low": (300, gum_low), "life_lost": (700, life_lost), "continue_tick": (180, continue_tick),
    "continue_yes": (600, continue_yes), "ne_move": (50, ne_move), "ne_confirm": (150, ne_confirm), "ne_done": (900, ne_done),
}


def adpcm_bytes(samples):
    """ADPCM-A: 4 bits per sample, samples padded to 256-byte blocks."""
    return -(-(-(-samples // 2)) // 256) * 256


def main():
    args = [a for a in sys.argv[1:] if a != "-v"]
    out_dir, names = args[0], args[1:] or list(SOUNDS)
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for name in names:
        ms, fn = SOUNDS[name]
        y = fn()
        old = isinstance(y, list)
        if old:
            y = np.array(y) / 32767.0
        # self-check: the length is the planned one, the level is sane, nothing blew up
        assert abs(len(y) - RATE * ms / 1000.0) <= 2, (name, len(y))
        assert np.all(np.isfinite(y)) and (old or 0.89 < np.max(np.abs(y)) <= 0.9001), name
        with wave.open(os.path.join(out_dir, name + ".wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(np.round(y * 32767).astype("<i2").tobytes())
        total += adpcm_bytes(len(y))
        if "-v" in sys.argv:
            print("%-14s %5d ms %6d bytes" % (name, ms, adpcm_bytes(len(y))))
    assert total <= BUDGET, total
    print("make_sfx: %d effects, %d ADPCM-A bytes of %d" % (len(names), total, BUDGET))


if __name__ == "__main__":
    main()

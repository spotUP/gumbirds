#!/usr/bin/env python3
"""Round-clear jingle drafts for Gumbirds. Mono, 18500 Hz, 16-bit PCM WAV, peak -1 dBFS.
Usage: python3 make_jingles.py   (writes next to this script, plus numbers.txt and index.html)"""
import math, os, wave
import numpy as np

R = 18500
HERE = os.path.dirname(os.path.abspath(__file__))
PEAK = 10 ** (-1 / 20)


def hz(m): return 440.0 * 2 ** ((m - 69) / 12)


def tvec(sec): return np.arange(int(R * sec)) / R


def osc(kind, f, n):
    """f: scalar or array of Hz. Phase accumulated so slides are clean. Square/saw are band-limited by harmonic sum."""
    f = np.broadcast_to(np.asarray(f, float), (n,))
    ph = np.cumsum(f) / R
    if kind == "sine": return np.sin(2 * np.pi * ph)
    if kind == "tri": return 2 / np.pi * np.arcsin(np.sin(2 * np.pi * ph))
    f0 = float(f.mean()); top = max(1, int(7500 / f0))
    out = np.zeros(n)
    if kind == "square":
        for k in range(1, top + 1, 2): out += np.sin(2 * np.pi * k * ph) / k
        return out * 4 / np.pi
    if kind == "saw":
        for k in range(1, top + 1): out += np.sin(2 * np.pi * k * ph) / k
        return out * 2 / np.pi
    raise ValueError(kind)


def adsr(n, a=0.003, d=0.05, s=0.7, r=0.04):
    na, nd, nr = int(R * a), int(R * d), int(R * r)
    e = np.full(n, s)
    na = min(na, n); e[:na] = np.linspace(0, 1, na, endpoint=False) if na else 1
    nd = min(nd, n - na); e[na:na + nd] = np.linspace(1, s, nd)
    nr = min(nr, n); e[n - nr:] *= np.linspace(1, 0, nr)
    return e


def expdec(n, tau, a=0.0015):
    t = np.arange(n) / R
    return np.exp(-t / tau) * np.minimum(1, t / a)


def place(buf, t0, x, g=1.0):
    i = int(R * t0); x = x[:max(0, len(buf) - i)]; buf[i:i + len(x)] += g * x


def note(buf, t0, m, dur, kind="square", g=0.3, env=None, detune=0.0, slide=None):
    n = int(R * dur); f = hz(m)
    if slide is not None: f = f * 2 ** (np.linspace(slide, 0, n) / 12)
    x = osc(kind, f, n)
    if detune: x = 0.5 * x + 0.5 * osc(kind, f * 2 ** (detune / 12), n)
    place(buf, t0, x * (env if env is not None else adsr(n)), g)


def noise_pop(buf, t0, g=0.5, ms=40, seed=1, bright=0.85):
    rng = np.random.default_rng(seed); n = int(R * ms / 1000)
    x = rng.uniform(-1, 1, n); y = np.zeros(n); p = 0.0
    for i in range(n):  # one-pole high-pass
        y[i] = bright * (y[i - 1] + x[i] - p) if i else x[0]; p = x[i]
    place(buf, t0, y * expdec(n, ms / 1000 / 4, 0.0004), g)


def fm(buf, t0, m, dur, ratio=3.5, index=3.0, tau=0.4, g=0.3):
    n = int(R * dur); t = np.arange(n) / R; f = hz(m)
    idx = index * np.exp(-t / (tau * 0.6))
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * ratio * t))
    place(buf, t0, x * expdec(n, tau, 0.001) * np.minimum(1, (dur - t) / 0.03), g)


def pop_body(buf, t0, g=0.6, f0=1100, f1=160, ms=90):
    n = int(R * ms / 1000); t = np.arange(n) / R
    f = f1 + (f0 - f1) * np.exp(-t / (ms / 1000 / 4))
    place(buf, t0, np.sin(2 * np.pi * np.cumsum(f) / R) * expdec(n, ms / 1000 / 3, 0.0005), g)
    noise_pop(buf, t0, g * 0.6, 35, seed=7)


# C = 60. Melodies are original, written for this draft.
def j1():  # rising major arpeggio with pop accents
    b = np.zeros(int(R * 1.6)); step = 0.095
    seq = [72, 76, 79, 84, 88, 91, 96]
    for i, m in enumerate(seq):
        t = i * step
        note(b, t, m, 0.16, "square", 0.22, expdec(int(R * 0.16), 0.07))
        note(b, t, m - 12, 0.16, "tri", 0.25, expdec(int(R * 0.16), 0.09))
        if i % 2 == 1: noise_pop(b, t, 0.18, 25, seed=i)
    t = len(seq) * step
    for m in (72, 76, 79, 84): note(b, t, m, 0.75, "square", 0.12, adsr(int(R * 0.75), 0.004, 0.1, 0.6, 0.35))
    note(b, t, 60, 0.75, "tri", 0.3, adsr(int(R * 0.75), 0.004, 0.1, 0.7, 0.35))
    noise_pop(b, t, 0.3, 45, seed=21)
    return b


def j2():  # bouncy two-bar riff, fast sixteenths
    b = np.zeros(int(R * 1.8)); e = 0.095
    riff = [(67, 1), (67, 1), (74, 1), (71, 1), (72, 1), (69, 1), (74, 2),
            (71, 1), (71, 1), (79, 1), (76, 1), (74, 1), (72, 1), (79, 1)]
    t = 0.0
    for m, ln in riff:
        d = e * ln * 0.8
        note(b, t, m, d, "square", 0.24, adsr(int(R * d), 0.002, 0.04, 0.5, 0.03), detune=0.1)
        note(b, t, m - 24 if m < 72 else m - 12, d, "tri", 0.3, adsr(int(R * d), 0.002, 0.04, 0.7, 0.03))
        t += e * ln
    for m in (79, 83, 86): note(b, t, m, 0.37, "square", 0.15, adsr(int(R * 0.37), 0.003, 0.05, 0.6, 0.2))
    note(b, t, 55, 0.35, "tri", 0.3, adsr(int(R * 0.35), 0.003, 0.05, 0.7, 0.2))
    return b


def j3():  # chime cascade: FM bells climbing, pentatonic, then a high shimmer
    b = np.zeros(int(R * 1.9)); scale = [72, 74, 76, 79, 81, 84, 86, 88, 91, 93, 96]
    for i, m in enumerate(scale):
        fm(b, i * 0.085, m, 0.9, 3.5, 2.5, 0.28, 0.2)
    t = len(scale) * 0.085
    for k, m in enumerate((84, 88, 91, 96)): fm(b, t + k * 0.012, m, 0.9, 2.0, 1.2, 0.5, 0.16)
    fm(b, t, 60, 0.9, 1.0, 0.8, 0.5, 0.22)
    return b


def j4():  # brassy square fanfare: triplet kick-off, then rising held chords
    b = np.zeros(int(R * 1.8))
    def brass(t0, ms, dur, g=0.16):
        n = int(R * dur); e = adsr(n, 0.012, 0.08, 0.8, min(0.1, dur / 2))
        for m in ms:
            vib = 1 + 0.003 * np.sin(2 * np.pi * 5.5 * np.arange(n) / R)
            x = osc("square", hz(m) * vib, n) * 0.6 + osc("saw", hz(m) * 1.004 * vib, n) * 0.4
            place(b, t0, x * e, g)
    for k, m in enumerate((67, 67, 67)): brass(k * 0.1, (m, m + 4), 0.09)
    brass(0.30, (72, 76), 0.22); brass(0.54, (74, 79), 0.2); brass(0.78, (76, 84), 0.22)
    brass(1.02, (79, 84, 88), 0.75, 0.13)
    for t0, m in ((0.0, 48), (0.3, 48), (0.54, 50), (0.78, 52), (1.02, 55)):
        note(b, t0, m, 0.2 if t0 < 1 else 0.7, "tri", 0.35, expdec(int(R * (0.2 if t0 < 1 else 0.7)), 0.3))
    noise_pop(b, 1.02, 0.25, 50, seed=4)
    return b


def j5():  # cute pluck run ending on a gum pop
    b = np.zeros(int(R * 1.5)); run = [76, 79, 83, 84, 88, 91, 95, 96]
    for i, m in enumerate(run):
        t = i * 0.075; n = int(R * 0.35)
        x = osc("tri", hz(m), n) + 0.4 * osc("sine", hz(m) * 2, n) * np.exp(-np.arange(n) / R / 0.03)
        place(b, t, x * expdec(n, 0.09), 0.3)
    t = len(run) * 0.075 + 0.07
    n = int(R * 0.45)
    place(b, t, osc("tri", hz(88), n) * expdec(n, 0.25) * 0.22)  # held bell tone under the pop
    pop_body(b, t + 0.08, 0.7, 1300, 170, 100)
    place(b, t + 0.30, osc("tri", hz(96), int(R * 0.3)) * expdec(int(R * 0.3), 0.12), 0.15)
    return b


JINGLES = [
    ("jingle_1_arpeggio_pops", "Arpeggio and pops", "Rising C major arpeggio in square and triangle with noise pops on the off beats, ends on a held chord.", j1),
    ("jingle_2_bouncy_riff", "Bouncy riff", "Two-bar staccato square riff over a triangle bass, answered by a bright G major hit.", j2),
    ("jingle_3_chime_cascade", "Chime cascade", "Eleven FM bells climbing a pentatonic scale, ringing into a high shimmer. Softest and most sparkly.", j3),
    ("jingle_4_brass_fanfare", "Brass fanfare", "Triplet kick-off then rising two-note chords on detuned square and saw with light vibrato, one long final chord.", j4),
    ("jingle_5_pluck_pop", "Pluck run and pop", "Fast triangle pluck run up two octaves, ending on a pitch-falling gum pop and a small bell tail.", j5),
]


def finish(x):
    x = x - x.mean()
    nf = int(R * 0.03)
    x[-nf:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, nf)))
    x[:int(R * 0.001)] *= np.linspace(0, 1, int(R * 0.001))
    x = x - x.mean()
    return x * (PEAK / np.abs(x).max())


def read(path):
    with wave.open(path) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() == R
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768


def main():
    lines = ["name duration_s peak_dBFS rms_dBFS dc_offset adpcm_a_bytes first_nonquiet_ms"]
    rows = []
    for fn, title, desc, fnc in JINGLES:
        x = finish(fnc())
        with wave.open(os.path.join(HERE, fn + ".wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(R)
            w.writeframes(np.round(x * 32767).astype("<i2").tobytes())
        y = read(os.path.join(HERE, fn + ".wav"))
        dur = len(y) / R; pk = 20 * math.log10(np.abs(y).max()); rms = 20 * math.log10(math.sqrt((y ** 2).mean()))
        nz = int(np.argmax(np.abs(y) > 0.01)) / R * 1000
        m = f"{dur:.3f} s, peak {pk:.2f} dBFS, RMS {rms:.2f} dBFS, DC {y.mean():+.6f}, ADPCM-A {len(y) // 2} bytes"
        lines.append(f"{fn} {dur:.3f} {pk:.2f} {rms:.2f} {y.mean():+.6f} {len(y) // 2} {nz:.1f}")
        rows.append(f'<div class="row"><h2>{title}</h2><div class="d">{desc}</div>'
                    f'<audio controls preload="auto" src="{fn}.wav"></audio><div class="m">{m}</div></div>')
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(lines) + "\n")
    html = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Gumbirds round clear jingle drafts</title>'
            '<style>body{background:#f2f3f5;color:#222;font-family:system-ui,sans-serif;margin:0;padding:32px;max-width:860px}'
            'h1{font-size:22px}.row{border-top:1px solid #d0d3d8;padding:14px 0}.row h2{font-size:16px;margin:0 0 4px}'
            '.d{color:#444;margin-bottom:8px}.m{color:#666;font-size:13px;margin-top:6px}audio{width:100%;max-width:520px}</style></head><body>'
            '<h1>Gumbirds round clear jingle drafts</h1><p>Placeholders for the ALL POPPED banner (120 frames). Synthesized, 18500 Hz mono 16 bit. '
            'Not yet listened to by anyone; the numbers only prove length and level.</p>' + "".join(rows) + '</body></html>')
    open(os.path.join(HERE, "index.html"), "w").write(html)


main()

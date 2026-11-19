"""Six synthesized gum pop drafts (mono, 16 bit, 18500 Hz = ADPCM-A rate). All from scratch, fixed seed.
Run: /opt/homebrew/bin/python3.14 -I make_pops.py   (writes WAVs and numbers.txt next to this script)"""
import math, os, random, wave
import numpy as np

R = 18500
OUT = os.path.dirname(os.path.abspath(__file__))
TAU = 2 * math.pi


def n_of(sec): return int(R * sec)


def noise(rng, n): return [rng.uniform(-1, 1) for _ in range(n)]


def hp(x, a=0.9):  # one-pole high-pass
    y, px, py = [], 0.0, 0.0
    for v in x:
        py = a * (py + v - px); px = v; y.append(py)
    return y


def lp(x, a=0.2):  # one-pole low-pass
    y, p = [], 0.0
    for v in x:
        p += a * (v - p); y.append(p)
    return y


def env_exp(n, tau, attack=0.0004):
    na = max(1, int(R * attack))
    return [(min(1.0, i / na)) * math.exp(-i / (R * tau)) for i in range(n)]


def sweep(n, f0, f1, curve=4.0):  # sine with exponential-ish pitch fall, f0 -> f1 over n samples
    out, ph = [], 0.0
    for i in range(n):
        t = i / n
        f = f1 + (f0 - f1) * math.exp(-curve * t)
        ph += f / R
        out.append(math.sin(TAU * ph))
    return out


def mix(n, *parts):  # parts: (offset_samples, samples, gain)
    out = [0.0] * n
    for off, s, g in parts:
        for i, v in enumerate(s):
            if off + i < n: out[off + i] += v * g
    return out


def mul(a, b): return [x * y for x, y in zip(a, b)]


def finish(x, sec):
    n = n_of(sec)
    x = (x + [0.0] * n)[:n]
    nf = int(R * 0.012)  # 12 ms cosine fade so the end never clicks
    for i in range(nf):
        x[n - nf + i] *= 0.5 * (1 + math.cos(math.pi * i / nf))
    pk = max(abs(v) for v in x) or 1.0
    g = (10 ** (-3 / 20)) / pk
    return [int(round(32767 * v * g)) for v in x]


def p1(rng):  # dry snap
    n = n_of(0.09)
    return finish(mul(hp(noise(rng, n), 0.92), env_exp(n, 0.012, 0.0002)), 0.09)


def p2(rng):  # wet smack: noise + falling body
    n = n_of(0.17)
    body = mul(sweep(n, 420, 140, 5), env_exp(n, 0.05, 0.001))
    nz = mul(lp(hp(noise(rng, n), 0.6), 0.55), env_exp(n, 0.02, 0.0004))
    return finish(mix(n, (0, body, 1.0), (0, nz, 0.8)), 0.17)


def p3(rng):  # rubbery pock
    n = n_of(0.15)
    s = mul(sweep(n, 900, 180, 7), env_exp(n, 0.045, 0.0005))
    att = mul(noise(rng, n_of(0.01)), env_exp(n_of(0.01), 0.003, 0.0002))
    return finish(mix(n, (0, s, 1.0), (0, att, 0.5)), 0.15)


def p4(rng):  # double pop: stretch then snap, 2 transients
    n = n_of(0.24)
    t1 = mul(sweep(n_of(0.07), 260, 520, -3.0), [math.sin(math.pi * i / n_of(0.07)) for i in range(n_of(0.07))])
    c1 = mul(lp(hp(noise(rng, n_of(0.05)), 0.8), 0.6), env_exp(n_of(0.05), 0.008, 0.0003))
    c2 = mul(hp(noise(rng, n_of(0.12)), 0.85), env_exp(n_of(0.12), 0.02, 0.0002))
    b2 = mul(sweep(n_of(0.12), 500, 200, 5), env_exp(n_of(0.12), 0.03, 0.0005))
    return finish(mix(n, (0, t1, 0.25), (n_of(0.06), c1, 0.7), (n_of(0.11), c2, 1.0), (n_of(0.11), b2, 0.5)), 0.24)


def p5(rng):  # bright cartoon pop: rising chirp cut by snap
    n = n_of(0.16)
    nc = n_of(0.07)
    ch = sweep(nc, 700, 2400, -2.0)
    ch = [v * min(1.0, i / 60) for i, v in enumerate(ch)]
    sn = mul(hp(noise(rng, n - nc), 0.88), env_exp(n - nc, 0.018, 0.0002))
    ring = mul(sweep(n - nc, 1800, 1500, 1), env_exp(n - nc, 0.02, 0.0002))
    return finish(mix(n, (0, ch, 0.45), (nc, sn, 1.0), (nc, ring, 0.3)), 0.16)


def p6(rng):  # soft thick bubble: low thump + small splat tail
    n = n_of(0.22)
    th = mul(sweep(n, 220, 70, 5), env_exp(n, 0.06, 0.003))
    th2 = lp(mul(noise(rng, n_of(0.04)), env_exp(n_of(0.04), 0.012, 0.002)), 0.15)
    sp = mul(lp(noise(rng, n_of(0.08)), 0.3), [math.exp(-i / (R * 0.03)) * min(1, i / 80) for i in range(n_of(0.08))])
    return finish(mix(n, (0, th, 1.0), (0, th2, 2.0), (n_of(0.05), sp, 0.35)), 0.22)


SOUNDS = [("pop_1_dry_snap", p1), ("pop_2_wet_smack", p2), ("pop_3_rubbery_pock", p3),
          ("pop_4_double_pop", p4), ("pop_5_bright_cartoon", p5), ("pop_6_soft_bubble", p6)]


def centroid(x):
    if len(x) < 8: return 0.0
    w = x * np.hanning(len(x)); m = np.abs(np.fft.rfft(w)); f = np.fft.rfftfreq(len(x), 1 / R)
    return float((m * f).sum() / (m.sum() or 1))


lines = ["name duration_ms peak_dBFS rms_dBFS centroid_first20ms_Hz centroid_tail_Hz last_sample"]
for name, fn in SOUNDS:
    s = fn(random.Random(1234))
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(R)
        w.writeframes(np.array(s, dtype="<i2").tobytes())
    a = np.array(s, dtype=float) / 32768
    first = a[:int(R * .02)]; tail = a[len(a) // 2:]
    lines.append("%s %.1f %.2f %.2f %.0f %.0f %d" % (
        name, 1000 * len(a) / R, 20 * math.log10(np.abs(a).max()), 20 * math.log10(math.sqrt((a ** 2).mean())),
        centroid(first), centroid(tail), s[-1]))
open(os.path.join(OUT, "numbers.txt"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))

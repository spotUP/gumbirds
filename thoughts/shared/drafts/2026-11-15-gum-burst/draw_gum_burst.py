#!/usr/bin/env python3
"""GUM-BURST drafts: 3 hand-pixelled nozzle burst variants for the bonus stage gum machines.
Every pixel is hand placed: frames are lists of (x, y, "row") strings and hand-drawn stamps at hand-chosen positions.
No generated shapes, gradients or noise. Frame 32x32, drawn at (nozzle x, nozzle top - 24): rows 0-23 are above the cap,
rows 24-31 overlay the cap (the puff sprite is in front of the nozzle sprite).
Run: /opt/homebrew/opt/python@3.11/bin/python3.11 -I thoughts/shared/drafts/2026-11-15-gum-burst/draw_gum_burst.py
"""
import os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
NOZ = os.path.join(HERE, "../../../spot/drafts/2026-11-13-bonus-nozzles")
PAL = {"K": "180829", "D": "2a0a24", "M": "7b1842", "C": "b5203f", "R": "ef4a52", "S": "ff9a86", "W": "fff7f0", "P": "ef4a94",
       "L": "f7a3cd", "B": "7a86c0", "N": "3a3f78", "A": "c6d2f0", "O": "ffb02e", "Y": "fff0a8",
       "V": "b52984"}   # V is the one new colour (gum shadow): the nozzle palette had 14 of 15 used
RGB = {k: tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) + (255,) for k, v in PAL.items()}
BG = (24, 28, 56)

# cap rows (the nozzle collar), hand copied from nozzles_A and re-lit with gum glow
R0 = "BKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKN"
R1G = "KBBADDDDDMVVPPLLLPPPVVMDDDDDNNNK"
R2G = ".KBBABDDLVPWPPWPPWPVLVMPDDBNNNK."
R2GF = "KBBAABDDLVPWPPWPPWPVLVMPDDBNNNNK"
R3 = ".K" + "BN" * 14 + "K."
R3F = "K" + "BN" * 15 + "K"
GLOW = [(0, 25, R1G), (0, 26, R2G)]
UP1 = [(0, 23, R0), (0, 24, R1G), (0, 25, R2GF), (0, 26, R3)]                    # collar lifted 1 px
UP2 = [(0, 22, R0), (0, 23, R1G), (0, 24, R2GF), (0, 25, R3F), (0, 26, R3)]      # collar lifted 2 px
FADE = [(8, 26, "L..P..L..P..P..V")]

ST = {  # hand-drawn droplets, light from the upper left
    "d1": ["LP", "PV"],
    "d2": [".L.", "LWP", ".PV"],
    "b3": ["LLP", "LWV", "PVM"],
    "s4": [".LP.", "LWPV", "PPVM", ".VM."],
    "s5": [".LLP.", "LWLPV", "LLPPV", "PPPVM", ".VVM."],
    "s6": [".LLLP.", "LWWLPV", "LWLPPV", "LPPPVM", "PPVPVM", ".VVMM."],
    "tear4": [".L..", ".L..", ".LP.", "LWPV", "LLPV", "PPVM", ".VM."],
    "tear5": ["..L..", "..L..", ".LP..", ".LLP.", "LWLPV", "LLPPV", "PPPVM", ".VVM."],
    "up3": [".L.", "LWP", "LPV", "LPV", ".P.", ".V."],
    "sq6": [".LLPP.", "LWLPPV", "PPPVVM"],
    "sq8": ["..LLPP..", ".LWLPPV.", "LPPPPVVM"],
    "upL": [".LL..", "LWLP.", "LLPPV", ".PPV.", "...V."],
    "upR": ["..LL.", ".LWLP", "LPPPV", ".PVV.", ".V..."],
    "dnL": ["...L.", "..LP.", ".LLPV", "LWPPV", ".PVM."],
    "dnR": [".L...", ".LP..", "LLPV.", "LWPPV", ".PVM."],
}
def S(n, x, y): return [(x, y + i, r) for i, r in enumerate(ST[n])]
def rows(y, *xr): return [(xr[i], y + i // 2, xr[i + 1]) for i in range(0, len(xr), 2)]

DOME1 = rows(20, 13, "KKKKKK", 11, "KKLLLLPPKK", 10, "KLWWLPPPPVVK", 11, "LLLPPPPVVM")
DOME2 = rows(16, 12, "KKKKKKKK", 10, "KKLLLLLPPPKK", 9, "KLLWWLLPPPPPVK", 8, "KLWWWLLPPPPPVVVK", 8, "KLLWLLPPPPPPVVMK",
             8, "KPLLPPPPPPVPVMMK", 8, "KKPPPPPPVPVVMMKK")
LIP_BIG = [(8, 21, "LL"), (20, 21, "PV"), (8, 22, "LWLP......PPVM"), (9, 23, "KLLPPPPPPVVMK")]
LIP_MID = [(10, 22, "LLP......PVM"), (10, 23, "KLPPPPPPVVMK")]
LIP_SMALL = [(11, 23, "KLPPPPVVMK")]
LIP_TINY = [(13, 23, "PLPPVM")]
MOUND_BIG = rows(19, 12, "LLWLPPVM", 11, "LLWWLPPPVM", 10, "LLWLLPPPPVVM", 9, "KLLLLPPPPPVVMK", 9, "KPLPPPPPVPVVMK")
MOUND_MID = rows(20, 11, "LLWLPPPVVM", 10, "LLWLLPPPVVVM", 10, "KLLPPPPPVVMK", 10, "KPPPPPVPVVMK")
MOUND_SMALL = rows(21, 12, "LLPPPVVM", 11, "KLWLPPPVVK", 11, "KPLPPPVVMK")

# ---------------- A: tight pop ----------------
A_POP = [(15, 8, "LL"), (15, 9, "WL"), (7, 10, "L"), (15, 10, "WP"), (24, 10, "P"), (7, 11, "LL"), (14, 11, "LWWP"), (23, 11, "PV"),
         (8, 12, "LWL"), (14, 12, "LWWP"), (21, 12, "LPV"), (9, 13, "LWLL"), (13, 13, "LWWWWP"), (19, 13, "LLPV"),
         (10, 14, "LLWLWWWWWLPPV"), (10, 15, "LWWWWWWWWLPV"), (9, 16, "LLWWWYYWWWLPPV"),
         (2, 17, "LLLLPPPLWWWYYYYWWLPPPVVVMM"), (1, 18, "LWLLPPPPLLWWWYYWWWLPPPVPVVMK"), (4, 19, "PPVPPLLLWWWWWWLPPPVVVMK"),
         (8, 20, "PPLLLWWWWLPPVVMK"), (9, 21, "PPLLLLLPPPVVMK"), (9, 22, "KPPLLPPPPVVVMK"), (9, 23, "KPPPPPPVPVVMMK")]
A = ([3, 3, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4], [
    GLOW,
    UP1 + DOME1,
    UP2 + DOME2,
    UP1 + A_POP,
    GLOW + LIP_BIG + S("upL", 2, 12) + S("upL", 7, 5) + S("up3", 14, 2) + S("upR", 20, 5) + S("upR", 25, 12)
    + [(9, 19, "L"), (8, 18, "L"), (8, 17, "P"), (22, 19, "P"), (23, 18, "V"), (23, 17, "P"), (15, 11, "W"), (14, 12, "WYW"), (15, 13, "W"),
       (15, 9, "P"), (12, 10, "L"), (19, 10, "V")],
    GLOW + LIP_MID + S("s4", 1, 10) + S("s4", 6, 3) + S("s4", 14, 0) + S("s4", 22, 3) + S("s4", 27, 10)
    + [(8, 17, "L"), (7, 15, "P"), (23, 17, "V"), (24, 15, "P"), (15, 8, "L"), (15, 11, "P"), (15, 14, "W")],
    GLOW + LIP_MID + S("dnL", 0, 13) + S("s4", 6, 4) + S("s4", 14, 1) + S("s4", 22, 4) + S("dnR", 27, 13),
    GLOW + LIP_SMALL + S("tear4", 1, 15) + S("tear4", 6, 6) + S("s4", 14, 3) + S("tear4", 22, 6) + S("tear4", 27, 15),
    GLOW + LIP_SMALL + S("sq6", 0, 21) + S("tear4", 6, 12) + S("tear4", 14, 7) + S("tear4", 22, 12) + S("sq6", 26, 21),
    LIP_TINY + [(1, 23, "PLPV"), (27, 23, "PLPV")] + S("tear4", 6, 17) + S("tear4", 14, 13) + S("tear4", 22, 17),
    LIP_TINY + [(2, 23, "PV"), (28, 23, "PV")] + S("sq6", 5, 21) + S("sq6", 21, 21) + S("tear4", 14, 17) + S("d1", 3, 18) + S("d1", 27, 18),
    FADE + S("sq8", 12, 21) + [(6, 23, "PLPV"), (22, 23, "PLV")] + S("d1", 10, 18) + S("d1", 20, 18),
    FADE + LIP_TINY + [(7, 23, "P"), (23, 23, "V")],
])

# ---------------- B: big spray ----------------
B_JET = rows(2, 13, "LLLLPP", 11, "LLWWWLLPPV", 10, "LWWWWWLLPPPV", 10, "LLWWLLPPPPVV", 10, "PLLLLPPPPVVM", 11, "PLLPPPPVVM",
             12, "LLPPPVVM", 12, "LWLPPVVM", 13, "LWLPVM", 13, "LWLPVM", 13, "LLPPVM", 12, "LLWLPPVM", 12, "LWWLPPVM", 12, "LWWLPPVM",
             11, "LLWWLPPPVM", 11, "LWWWLLPPVM", 10, "LLWWYWLLPPVM", 9, "LLWWYYYWLPPPVM", 8, "LLWWYYYYWWLPPVVM", 8, "PLLWWYYWWLLPPVMK",
             8, "KPPLLLLLPPPPVVMK") + [(5, 19, "LP"), (4, 18, "L"), (25, 19, "PV"), (27, 18, "P"), (0, 20, "Y"), (31, 19, "Y")]
B_FAN = rows(6, 15, "LP", 15, "LP", 14, "LPV", 15, "PV", 15, "LP", 15, "L", 15, "LP", 14, "LPV", 14, "LWPV", 13, "LWLPV", 13, "LWLPVM",
             12, "LLWLPPVM", 11, "LLWWLPPVVM", 10, "LLWWWLPPPVVM", 9, "PLLWWLLPPPVVMK", 9, "KPLLLLPPPPVVMK", 9, "KPPLLPPPVPVVMK",
             9, "KPPLLPPPVPVVMK") + [(7, 8, "P................V"), (8, 9, "L..............P"), (8, 10, "P..............V"),
                                     (9, 11, "L............P"), (10, 12, "LP.........PV"), (12, 13, "LP"), (17, 13, "PPV")]   # bowed side strands
B = ([3, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4], [
    GLOW,
    UP1 + DOME1,
    UP2 + DOME2 + [(0, 20, "Y"), (31, 19, "Y"), (1, 18, "O"), (30, 17, "O")],
    UP2 + B_JET,
    UP1 + B_FAN + S("s6", 13, 0) + S("s5", 4, 3) + S("s5", 23, 3),
    GLOW + MOUND_BIG + S("sq6", 13, 0) + S("s5", 1, 2) + S("s5", 26, 2) + S("d2", 8, 0) + S("d2", 21, 1) + S("d2", 0, 10) + S("d2", 29, 9)
    + [(15, 4, "L"), (15, 6, "P"), (16, 8, "L"), (15, 10, "P"), (15, 12, "L"), (16, 14, "P"), (15, 16, "LP"), (14, 18, "LPV"),
       (9, 6, "P"), (11, 8, "L"), (21, 6, "V"), (19, 8, "P")],
    GLOW + MOUND_MID + S("s6", 13, 1) + S("s5", 0, 5) + S("s5", 27, 5) + S("d2", 6, 2) + S("d2", 23, 2) + S("d2", 0, 14) + S("d2", 29, 13)
    + [(15, 9, "L"), (16, 12, "P"), (15, 15, "L"), (15, 17, "P")],
    GLOW + MOUND_MID + S("tear5", 0, 8) + S("tear5", 27, 8) + S("s6", 13, 3) + S("d2", 5, 6) + S("d2", 24, 5) + S("d1", 0, 19) + S("d1", 30, 18),
    GLOW + MOUND_SMALL + S("tear5", 0, 13) + S("tear5", 27, 13) + S("tear5", 13, 6) + S("tear4", 5, 10) + S("tear4", 24, 9),
    MOUND_SMALL + S("sq6", 0, 21) + S("sq6", 26, 21) + S("tear5", 13, 11) + S("tear4", 5, 15) + S("tear4", 24, 14),
    MOUND_SMALL + [(0, 23, "PLPPV"), (1, 25, "LP"), (1, 26, "P"), (27, 23, "PLPPV"), (29, 25, "PV"), (30, 26, "V")]
    + S("tear5", 13, 16) + S("sq6", 4, 21) + S("tear4", 24, 17),
    MOUND_SMALL + S("sq8", 12, 20) + S("d1", 9, 17) + S("d1", 21, 16) + [(15, 15, "W"), (14, 16, "LWL")] + S("sq6", 23, 21)
    + [(5, 23, "PLPV"), (1, 26, "L"), (1, 27, "P"), (2, 28, "V"), (30, 27, "P"), (29, 28, "V")],
    MOUND_MID + S("d1", 8, 19) + S("d1", 22, 19) + [(24, 23, "PLV"), (2, 29, "P"), (29, 29, "V"), (6, 23, "P")],
    FADE + MOUND_SMALL + [(8, 22, "P"), (22, 22, "V")],
    FADE + LIP_TINY,
])

# ---------------- C: stringy stretch ----------------
C_RIM = [(8, 23, "KKPLLPPPPPVVVMKK")]
C_TENT = rows(7, 12, "LLLLLPPP", 10, "LLWWWLLPPPPV", 9, "LLWWWWLLPPPPVV", 9, "LWWWLLLPPPPPVV", 9, "LLWLLPPPPPPVVM", 9, "PLLLPPPPPPVVVM",
              10, "PLLPPPPPVVVM", 11, "PLLPPPVVVM", 11, "LLPPPPVVM", 12, "LWPPPVVM", 12, "LWLPPVVM", 12, "LWLPPVVM", 11, "LLWLPPPVVM",
              10, "LLWWLPPPVVVM", 9, "LLWWLLPPPPVVVM", 8, "KLLWLLPPPPPVVVMK")
C_WEB = rows(1, 13, "LLLPPP", 11, "LLWWLLPPPV", 11, "LWWWLPPPPV", 11, "LLWLPPPPVM", 11, "PLLPPPPVVM", 12, "PLPPPVVM", 12, "LP.PP.VM",
             11, "LP..LP..VM", 11, "LP..LP..VM", 10, "LP...LP...VM", 10, "LP...LP...VM", 9, "LL....LP....VM", 9, "LP....LP....PV",
             9, "LP....LP....PV", 9, "LP....WP....PV", 9, "LLP...LP...PVM", 10, "LP...LP...PV", 10, "LLP..LP..PVM", 10, "LWLP.LP.PPVM",
             9, "LLWLPLLPPPVVVM", 9, "LWWLLLPPPPVVVM", 8, "KLLWLLPPPPPVVVMK")
C_HAIR = rows(0, 13, "LLPPPV", 12, "LWLPPPVM", 12, "PLPPPVVM", 13, "LP.P.V", 12, "L...P...V", 11, "L....L....V", 10, "L.....P.....P",
              10, "L.....L.....V", 9, "LL.....P.....PV", 8, "LWL.....L.....LPV", 9, "PV.....P.....PVM", 10, "L....LWL.....V",
              10, "L....LPV.....P", 10, "P.....P......V", 10, "L.....L.....PV", 10, "LP....P.....V", 11, "L....L....PV", 11, "LP...P....V",
              11, "LLP..LP..PV", 11, "LWLP.LP.PVM", 10, "LLWLPLLPPVVM", 9, "LLWLLLPPPPVVVM", 8, "KPLLLLPPPPPVVVMK")
C_SNAP = [(16, 2, "W"), (15, 3, "WYW"), (16, 4, "W"), (8, 4, "W"), (24, 4, "W"), (16, 6, "L"), (6, 7, "LLP"), (16, 7, "P"), (23, 7, "PPV"),
          (5, 8, "L..LP"), (15, 8, "L"), (22, 8, "LP..V"), (4, 9, "L...PV"), (16, 9, "P"), (22, 9, "PV...V"), (4, 10, "L"), (17, 10, "L"),
          (27, 10, "P"), (4, 11, "P"), (16, 11, "P"), (27, 11, "V"), (5, 12, "L"), (15, 12, "L"), (26, 12, "P"), (5, 13, "P"), (15, 13, "LP"),
          (26, 13, "V"), (6, 14, "L"), (16, 14, "P"), (25, 14, "P"), (7, 15, "L"), (17, 15, "L"), (24, 15, "PV"), (8, 16, "LP"), (16, 16, "LP"),
          (23, 16, "PV"), (9, 17, "L"), (16, 17, "P"), (22, 17, "PV"), (10, 18, "LP"), (15, 18, "LP"), (21, 18, "PV"), (11, 19, "LP.LLP...PV"),
          (11, 20, "LLPLWPPPVV"), (10, 21, "LLWLLPPPVVVM"), (9, 22, "KLWLLPPPPPVVMK"), (9, 23, "KPLLPPPPPVVVMK")]
C_MOUND = rows(20, 10, "LLPLLWPPPVVM", 9, "LLWWLLPPPPVVVM", 9, "KLWLLPPPPPVVMK", 9, "KPLLPPPPPVVVMK")
C = ([3, 3, 3, 2, 2, 2, 3, 3, 2, 2, 3, 3, 4, 4], [
    GLOW,
    UP1 + DOME1,
    UP2 + DOME2,
    UP1 + C_RIM + C_TENT,
    UP1 + C_RIM + C_WEB,
    UP1 + C_RIM + C_HAIR,
    GLOW + C_SNAP,
    GLOW + C_MOUND + S("b3", 3, 13) + S("b3", 14, 10) + S("b3", 25, 13)
    + [(5, 16, "LP"), (6, 17, "LL"), (8, 18, "LP"), (9, 19, "LLP"), (15, 13, "LP"), (16, 14, "L"), (16, 15, "P"), (15, 16, "LP"), (15, 17, "L"),
       (15, 18, "LP"), (15, 19, "LP"), (25, 16, "PV"), (24, 17, "PV"), (22, 18, "PV"), (20, 19, "PPV")],
    GLOW + C_MOUND + rows(17, 14, "LLPP", 12, "LLWLPPPV", 11, "LWWLLPPPVV") + S("b3", 2, 19) + S("b3", 26, 19)
    + [(5, 20, "LP"), (6, 21, "LLP"), (8, 22, "L"), (25, 20, "PV"), (23, 21, "PVV"), (23, 22, "V")],
    GLOW + rows(20, 8, "LLLWLLPPPPPPVVVM", 7, "LLWWLLLPPPPPPVVVVM", 7, "KLLLLPPPPPPPVVVVMK", 8, "KPLPPPPPPVPVVVMK")
    + S("b3", 1, 21) + S("b3", 28, 21) + [(4, 23, "LP"), (26, 23, "PV")],
    rows(19, 13, "LLPPV", 11, "LLWLPPPVVM", 10, "LLWLLPPPVVVM", 10, "KLLPPPPPVVMK", 10, "KPPPPPVPVVMK")
    + [(0, 23, "PLPV"), (1, 25, "LP"), (1, 26, "PV"), (28, 23, "PLPV"), (29, 25, "PV"), (29, 26, "VM")],
    MOUND_SMALL + [(1, 27, "L"), (1, 28, "P"), (30, 27, "P"), (30, 28, "V"), (1, 23, "P"), (29, 23, "V")],
    FADE + rows(22, 13, "LLPPVV", 12, "KLPPPVMK") + [(2, 29, "P"), (29, 29, "V")],
    FADE + [(14, 23, "LPPV")],
])

def render(items):
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for x, y, r in items:
        assert 0 <= y < 32 and x >= 0 and x + len(r) <= 32, (x, y, r)
        for i, c in enumerate(r):
            if c != ".": im.putpixel((x + i, y), RGB[c])
    return im

def main():
    noz = Image.open(os.path.join(NOZ, "nozzles_A_1x.png")).convert("RGBA").crop((0, 16, 32, 40))   # nozzle 0, 24 px tall
    puff = Image.open(os.path.join(NOZ, "puff_A_1x.png")).convert("RGBA")
    old = [puff.crop((i * 32, 0, i * 32 + 32, 24)) for i in range(4)]
    def scene(fr):   # 40x52: burst frame at top-24 over the nozzle, like main.c draws the puff
        s = Image.new("RGBA", (40, 52), BG + (255,)); s.alpha_composite(noz, (4, 26))
        if fr: s.alpha_composite(fr, (4, 2))
        return s
    def up(im, k=3): return im.resize((im.width * k, im.height * k), Image.NEAREST)
    def gif(path, frames, ticks):
        fs = [up(scene(f)).convert("RGB") for f in frames] + [up(scene(None)).convert("RGB")]
        fs[0].save(path, save_all=True, append_images=fs[1:], duration=[round(t * 1000 / 60) for t in ticks] + [700], loop=0)
    gif(os.path.join(HERE, "current_puff_3x.gif"), old, [4] * 4)
    html = ["<!doctype html><meta charset=utf-8><title>Gum burst drafts</title><style>body{background:#14182c;color:#e8eaf4;font:15px/1.5 system-ui;margin:24px;max-width:1500px}img{image-rendering:pixelated;display:block;margin:8px 0}h2{margin-top:36px;color:#f7a3cd}.row{display:flex;gap:28px;align-items:flex-end}</style>",
            "<h1>Gum burst for the bonus nozzles (drafts, 2026-11-15)</h1><p>Frame 32x32 (4 tiles), drawn at nozzle top - 24 in the puff sprite slots. Nozzle palette + 1 new gum shadow colour = 15. Details: README.md.</p>",
            "<h2>Current in-game puff (4 frames, 16 ticks)</h2><img src=current_puff_3x.gif>"]
    used = set()
    for name, title, (ticks, frames) in (("A", "A: tight pop", A), ("B", "B: big spray", B), ("C", "C: stringy stretch", C)):
        ims = [render(f) for f in frames]; assert len(ims) == len(ticks)
        for im in ims: used |= {c for _, c in im.getcolors(999) if c[3]}
        strip = Image.new("RGBA", (32 * len(ims), 32), (0, 0, 0, 0))
        for i, im in enumerate(ims): strip.paste(im, (i * 32, 0))
        strip.save(os.path.join(HERE, "%s_burst_strip_1x.png" % name))
        gif(os.path.join(HERE, "%s_burst_3x.gif" % name), ims, ticks)
        n = len(ims); cmp_ = Image.new("RGBA", (40 * n, 104), BG + (255,))
        for i in range(n):
            if i < 4: cmp_.paste(scene(old[i]), (i * 40, 0))
            elif i == 4: cmp_.paste(scene(None), (i * 40, 0))
            cmp_.paste(scene(ims[i]), (i * 40, 52))
        up(cmp_).save(os.path.join(HERE, "%s_compare_3x.png" % name))
        html.append("<h2>%s (%d frames, %d ticks = %.2f s)</h2><div class=row><img src=%s_burst_3x.gif><img src=current_puff_3x.gif></div><p>Top row: current puff on the nozzle. Bottom row: new burst, all frames, 3x.</p><img src=%s_compare_3x.png><p>1x strip (import source), shown 2x:</p><img src=%s_burst_strip_1x.png style='width:%dpx;background:#182038'>" % (title, n, sum(ticks), sum(ticks) / 60, name, name, name, 64 * n))
        print(name, n, "frames", sum(ticks), "ticks", n * 4, "tiles")
    pal_old = {RGB[k] for k in PAL if k != "V"}
    assert used <= set(RGB.values()) and len(used | pal_old) <= 15, len(used | pal_old)
    print("colours used by bursts:", len(used), "nozzle palette total:", len(used | pal_old))
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(html))

if __name__ == "__main__":
    main()

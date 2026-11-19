#!/usr/bin/env python3
"""Gumbirds countdown, option A "Gum tube", polish pass 2 (draft only, no game data).
Hand-placed pixel data only: every glyph row is typed. A repeated stroke cross-section is a typed string that is
reused (SA, SB, ... below), exactly like the [row] * n repeats in the first draft. No shape, font or gradient
formula. The dither rows are typed by hand and thin out along the stroke on purpose.
Reuses the helpers and the original A grids from ../2026-11-17-countdown/draw_countdown.py (before/after sheet).
Run: python3.14 -I draw_countdown_a2.py
"""
import os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "2026-11-17-countdown"))
import draw_countdown as old  # noqa: E402  (rgba, glyph, word, up, on_dark, original A)
BG = os.path.join(HERE, "..", "2026-11-10-backgrounds-final")
MOODS = ("dusk", "moon", "storm")

# 12 colours + transparent. Light pink -> magenta -> violet: the shadow turns in hue, it does not just get darker.
PAL = {"k": "160826", "d": "3c1266", "m": "681a7c", "r": "9c2088", "R": "c82e90", "p": "ee4c9c", "P": "ff86b8",
       "l": "ffb4cc", "w": "ffe2dc", "W": "ffffff", "v": "9a5ae0", "V": "c8a0f6"}
# palette swap on the same tiles: Hot Gum bubble colours
PAL_HOT = {"k": "080818", "d": "5a0c2e", "m": "8a1430", "r": "c0201e", "R": "e63a1e", "p": "ff7a1a", "P": "ffa922",
           "l": "ffdc4a", "w": "fff3b0", "W": "ffffff", "v": "d42a7a", "V": "ff8ab8"}

# vertical stroke cross-sections, 10 px (outline, rim, highlight, light, P/p dither, mid, dark pink, r/m dither, shade, outline)
SA, SB = "kPlPPpRrmk", "kPlPppRmmk"
SH1, SH2, SH3 = "kPWPPpRrmk", "kPWwPpRmmk", "kPwPppRmmk"       # white streak on the highlight column
SV1, SV2, SV3 = "kPlPppRmvk", "kPlPPpRrvk", "kPlPppRmVk"       # violet bounce light on the shade edge
SC = "kPlPppRmdk"                                              # cast shadow right under a bar
D8, D14, D17, D18 = "." * 8, "." * 14, "." * 17, "." * 18

O_TOP = [
 "......kkkkkkkkkkkkkkkk......",
 "....kkPPPPPPPPPPPPPPPPkk....",
 "...kPPllWWWWwllllllllPPpk...",
 "..kPPlWWWwwPPPPPPPPPPPPprk..",
 ".kPPlWwPPPPpPPpPpPpPppppRrk.",
 ".kPllPPppppppppppppppppRRrk."]
O_BOTTOM = [
 "kPlPPpRrmkkkkkkkkkkPlPppRmmk",
 "kPlPppRPPPPPPPPPPPPPlPPpRrmk",
 "kPlPPpPllWWwlllllllllPppRmmk",
 ".kPlPPPPPPpPPpPpPpPppppRrk..",
 ".kPPlPpppppppppppppppppRrmk.",
 "..kPPppRRrRRrRrRrrRrrrrmmk..",
 "...kppRrmmmmvvVVvvmmmmddk...",
 "....kkrmmmmvvvvmmmmdddkk....",
 "......kkkkkkkkkkkkkkkk......"]
GS_ARC = [  # G and S share the open top arc
 "kPPlPPppRRrRRrRrRrrRrrrrrrmk",
 "kPlPPpRrmmmvvVvmmmmmvvmmddk.",
 "kPlPppRmmkkkkkkkkkkkkkkkkk..",
 "kPlPPpRrmkk................."]

A2 = {
 "E": [
 "..kkkkkkkkkkkkkkkkkkkk..",
 ".kPPPPPPPPPPPPPPPPPPPPk.",
 "kPllWWWWwllllllllllllPrk",
 "kPlwPPPPpPPpPpPpPpppppRk",
 "kPlPpppppppppppppppppRrk",
 "kPlPppRRrRRrRrRrrRrrrrmk",
 "kPlPppRrmmmmvvVvvmmmddk.",
 "kPlPppRrmkkkkkkkkkkkkk..",
 SC + D14, SH1 + D14, SH2 + D14, SA + D14,
 "kPlPppRmmkkkkkkkkkkk....",
 "kPlPPpRPPPPPPPPPPPPPk...",
 "kPlPppPllWWwlllllllPrk..",
 "kPlPPpPPPPpPPpPpPpppRk..",
 "kPlPpppppppppppppppRrk..",
 "kPlPPpRRrRRrRrRrrRrrmk..",
 "kPlPppRrmmmvvVvmmmddk...",
 "kPlPPpRrmkkkkkkkkkkk....",
 SC + D14, SA + D14, SB + D14, SA + D14,
 "kPlPppRmmkkkkkkkkkkkkk..",
 "kPlPPpRPPPPPPPPPPPPPPPk.",
 "kPlPppPllWWwlllllllllPrk",
 "kPlPPpPPPPpPPpPpPpPpppRk",
 "kPlPpppppppppppppppppRrk",
 "kPPppRRRrRRrRrRrrRrrrrmk",
 ".krrmmmmvvVvvmmmmmmmddk.",
 "..kkkkkkkkkkkkkkkkkkkk.."],
 "T": [
 "..kkkkkkkkkkkkkkkkkkkk..",
 ".kPPPPPPPPPPPPPPPPPPPPk.",
 "kPllWWWWwllllllllllllPrk",
 "kPlwPPPPpPPpPpPpPpppppRk",
 "kPPppppppppppppppppppRrk",
 "kpRRrRRrPlPPpRrmRrRrrrrk",
 ".kmmvVvmPlPppRmmmvvmddk.",
 "..kkkkkkPlPPpRrmkkkkkk.."] + ["......." + s + "......." for s in (
 SC, SH1, SH2, SH1, SH3, SA, SA, SB, SA, SB, SB, SA, SV1, SV2, SV3, SV2, SV1,
 "kPlPppRrmk",
 "kPPpppRmmk",
 "kPPppRrrmk",
 "kPpppRrmdk",
 "kppRRrmmdk",
 ".kRrrmmdk.",
 "..kkkkkk..")],
 "O": O_TOP + [
 "kPPlPPppRRrRRrRrRrrPPppRrmdk",
 "kPlPPpRrmmmvvVvmmmrPlPpRrmmk",
 "kPlPppRmmkkkkkkkkkmPlPPpRrmk",
 "kPlPPpRrmkk......kkPlPppRmmk",
 SH1 + D8 + SB, SH2 + D8 + SA, SH1 + D8 + SB, SH3 + D8 + SA, SA + D8 + SA, SA + D8 + SB,
 SB + D8 + SV1, SA + D8 + SV2, SB + D8 + SV3, SB + D8 + SV2, SA + D8 + SV1, SB + D8 + SA,
 "kPlPppRmmkk......kkPlPPpRrmk"] + O_BOTTOM,
 "G": O_TOP + GS_ARC + [
 SH1 + D18, SH2 + D18, SH1 + D18, SH3 + D18, SA + D18,
 "kPlPPpRrmk...kkkkkkkkkkkkk..",
 "kPlPppRmmk..kPPPPPPPPPPPPPk.",
 "kPlPPpRrmk..kPllWWwllllllPrk",
 "kPlPppRmmk..kPPpPpPPlPPpRrmk",
 "kPlPPpRrmk..kppppppPlPppRmmk",
 "kPlPppRmmk..kRRrRrrPlPPpRrmk",
 "kPlPPpRrmk...kmvvmdPlPppRmmk",
 "kPlPppRmmkk...kkkkkPlPPpRrmk"] + O_BOTTOM,
 "S": [
 "......kkkkkkkkkkkkkkkkkkk...",
 "....kkPPPPPPPPPPPPPPPPPPPkk.",
 "...kPPllWWWWwllllllllllllPrk",
 "..kPPlWWWwwPPPPPPPPPPPPPPprk",
 ".kPPlWwPPPPpPPpPpPpPppppppRk",
 ".kPllPPpppppppppppppppppRRrk"] + GS_ARC + [
 SB + D18,
 "kPlPPpRrmkk.................",
 "kPlPppRrmkkkkkkkkkkkkkkk....",
 "kPPlPPpRPPPPPPPPPPPPPPPPkk..",
 ".kPPlPPPllWWwlllllllllllPPk.",
 ".kPPPllPPPPPpPPpPpPpPppppRrk",
 "..kpPPPPpppppppppppPlPPpRrmk",
 "...kpRRrRRrRrRrrRrrPlPppRmmk",
 "....kkrmmmvvVvmmmmdPlPPpRrmk",
 "......kkkkkkkkkkkkkPlPppRmmk",
 ".................kkPlPPpRrmk",
 D18 + SB, D18 + SA,
 "..kkkkkkkkkkkkkkkkkPlPppRmmk",
 ".kPPPPPPPPPPPPPPPPPPlPPpRrmk",
 "kPPllWWwlllllllllllllPppRmmk",
 "kPlWwPPPPpPPpPpPpPpPpppRrmk.",
 "kPPPpppppppppppppppppRRrmk..",
 ".kppRRrRRrRrRrrRrrrrrrmmdk..",
 ".kRrmmmmvvVVvvmmmmmmmmddk...",
 "..kkmmmmvvvmmmmmmmmdddkk....",
 "....kkkkkkkkkkkkkkkkkk......"],
 "!": [
 "..kkkkkk..", ".kPPPPPPk.", "kPlWWWPpRk", "kPWWWwPpRk", "kPlWwPPpRk", "kPlwPPpRrk", "kPlPPpPRrk", "kPlPPppRmk",
 "kPlPPpRrmk", "kPlPppRmmk", "kPlPPpRrmk", ".kPlPpRmk.", ".kPlpRrmk.", ".kPlPpRmk.", ".kPlpRrvk.", ".kPPpRmvk.",
 "..kPpRmk..", "..kPpRmk..", "..kppRmk..", "..kpRrdk..", "..krmvdk..", "...kkkk...", "..........", "..kkkkkk..",
 ".kPPPPPPk.", "kPlWWwPpRk", "kPlWwPppRk", "kPlPPpRrmk", "kPPpppRrmk", "kppRRrmvdk", ".kRmmvVdk.", "..kkkkkk.."],
}

def check():  # every glyph is a full 32-row rectangle of known palette characters; palette fits one Neo Geo palette
    assert set(A2) == set("GETSO!") and len(PAL) <= 15 and set(PAL) == set(PAL_HOT)
    for ch, rows in A2.items():
        assert len(rows) == 32, (ch, len(rows))
        for y, row in enumerate(rows):
            assert len(row) == len(rows[0]), (ch, y, len(row), row)
            assert set(row) <= set(PAL) | {"."}, (ch, y, row)

def tiles():  # real 16x16 tile set: cut every glyph on the tile grid, drop empty tiles, dedupe identical ones
    raw, uniq = 0, set()
    for rows in A2.values():
        w = -(-len(rows[0]) // 16) * 16
        rows = [r.ljust(w, ".") for r in rows]
        for ty in range(0, 32, 16):
            for tx in range(0, w, 16):
                t = tuple(r[tx:tx + 16] for r in rows[ty:ty + 16])
                if any(set(r) != {"."} for r in t):
                    raw += 1
                    uniq.add(t)
    return raw, len(uniq)

def stack(ims, pad=6):
    out = Image.new("RGBA", (max(i.width for i in ims), sum(i.height for i in ims) + pad * (len(ims) - 1)), (36, 18, 56, 255))
    y = 0
    for i in ims:
        out.paste(i, (0, y))
        y += i.height + pad
    return out

def main():
    check()
    raw, uniq = tiles()
    used = {c for rows in A2.values() for row in rows for c in row} - {"."}
    assert used == set(PAL), set(PAL) - used
    save = lambda im, name: im.save(os.path.join(HERE, name))
    W = lambda text, pal=PAL: old.word(text, A2, pal)
    gs, go = W("GET SET"), W("GO!")
    for name, im in (("getset", gs), ("go", go)):
        save(old.on_dark(im), "A2_%s_1x.png" % name)
        save(old.up(old.on_dark(im), 3), "A2_%s_3x.png" % name)
        for mood in MOODS:
            m = Image.open(os.path.join(BG, "scene_%s_1x.png" % mood)).convert("RGBA")
            assert m.size == (320, 224), m.size
            m.alpha_composite(im, ((320 - im.width) // 2, 84 - im.height // 2))
            save(old.up(m, 2), "mock_%s_%s_2x.png" % (mood, name))
    save(old.up(stack([old.on_dark(W("GET SET", PAL_HOT)), old.on_dark(W("GO!", PAL_HOT))]), 3), "A2-hot_3x.png")
    save(old.up(stack([old.on_dark(old.word(t, old.A, old.PAL_A)) for t in ("GET SET", "GO!")]
                      + [old.on_dark(gs), old.on_dark(go)]), 3), "compare_A_vs_A2_3x.png")
    frames = []  # GO! pop-in: sprite shrink (sixteenths) and y offset only, no extra tiles
    for s, dy in ((4, 0), (8, 0), (12, 0), (16, 0), (16, -4), (16, -2), (16, 1), (16, 0)):
        f = Image.new("RGBA", (go.width + 12, go.height + 16), (36, 18, 56, 255))
        g = go.resize((go.width * s // 16, go.height * s // 16), Image.NEAREST)
        f.alpha_composite(g, ((f.width - g.width) // 2, (f.height - g.height) // 2 + dy))
        frames.append(old.up(f, 3).convert("RGB").quantize(32, dither=Image.Dither.NONE))  # RGBA straight to P scrambles the colours
    frames[0].save(os.path.join(HERE, "anim_A2_go_3x.gif"), save_all=True, append_images=frames[1:],
                   duration=[50] * 7 + [900], loop=0)
    cols = {ch: -(-len(rows[0]) // 16) for ch, rows in A2.items()}
    html = ['<!doctype html><meta charset="utf-8"><title>Gumbirds countdown A2</title>',
            '<style>body{background:#14121c;color:#e6e2f0;font:15px/1.5 system-ui,sans-serif;margin:24px}'
            'img{image-rendering:pixelated;display:block;margin:6px 0 18px}h2{margin-top:36px;border-top:1px solid #3a3550;'
            'padding-top:16px}.row{display:flex;gap:24px;flex-wrap:wrap;align-items:flex-end}</style>',
            '<h1>Gumbirds countdown: option A "Gum tube", polish pass</h1>',
            '<p>%d colours + transparent, one palette. %d unique 16x16 tiles (%d before dedupe). Hand-typed grids.</p>' % (len(used), uniq, raw),
            '<h2>Before (top two) and after (bottom two), 3x</h2><img src="compare_A_vs_A2_3x.png">',
            '<h2>Polished A</h2><div class="row"><div>1x<img src="A2_getset_1x.png"><img src="A2_go_1x.png"></div>'
            '<div>3x<img src="A2_getset_3x.png"></div><div>3x<img src="A2_go_3x.png"></div>'
            '<div>GO! pop-in, 3x (hardware shrink + position only)<img src="anim_A2_go_3x.gif"></div></div>',
            '<h2>Mock frames, 2x</h2>']
    for mood in MOODS:
        html.append('<div class="row"><div>%s<img src="mock_%s_getset_2x.png"></div><div>%s<img src="mock_%s_go_2x.png"></div></div>' % ((mood,) * 4))
    html.append('<h2>Hot Gum palette swap (same tiles), 3x</h2><img src="A2-hot_3x.png">')
    readme = ['# Countdown option A "Gum tube", polish pass (A2)', "",
              "Draft only, no game code. Run `python3.14 -I draw_countdown_a2.py`; view `index.html`.", "",
              "- Letter height 32 px. Glyph widths: " + ", ".join("%s %d" % (c, len(A2[c][0])) for c in "GETSO!") + ".",
              "- Colours: %d + transparent, one palette." % len(used),
              "- 16x16 tiles: %d unique (%d non-empty cells before dedupe; first draft counted 22 cells)." % (uniq, raw),
              "- Sprite columns: GET SET %d, GO! %d." % (sum(cols[c] for c in "GETSET"), sum(cols[c] for c in "GO!")),
              "- Hot Gum palette swap kept: same tiles, second palette (`A2-hot_3x.png`).",
              "- GO! pop-in uses sprite shrink and y offset only.",
              "- Mock plates: ../2026-11-10-backgrounds-final/scene_<mood>_1x.png.", "",
              "| Key | Pink | Hot | Role |", "|---|---|---|---|"]
    role = {"k": "outline", "d": "deepest shade (violet)", "m": "shade", "r": "dark pink", "R": "dark mid", "p": "mid",
            "P": "light / rim", "l": "highlight band", "w": "highlight edge", "W": "specular", "v": "bounce light",
            "V": "bounce light peak"}
    readme += ["| %s | #%s | #%s | %s |" % (c, PAL[c], PAL_HOT[c], role[c]) for c in PAL]
    readme += ["", "## Changed against the first A",
               "- Vertical strokes 8 px -> 10 px, letters G O S 24 -> 28 px and E T 22 -> 24 px wide (same tile cells).",
               "- 9 -> 12 colours: darker outline, a violet deepest shade, a dark-mid pink, a bounce-light peak.",
               "- Hand dither rows/columns between light and mid pink and between dark pink and shade.",
               "- Wider white specular on every stroke start, cast shadow under each bar, bounce light on the lower right edges."]
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(html) + "\n")
    open(os.path.join(HERE, "README.md"), "w").write("\n".join(readme) + "\n")
    print("colours", len(used), "tiles raw", raw, "unique", uniq)

if __name__ == "__main__":
    main()

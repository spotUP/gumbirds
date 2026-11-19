#!/usr/bin/env python3.14 -I
"""Player 2 palette drafts: palette swaps of the player half of assets/flier/sootling_sheet.png.
Run from the repo root: python3.14 -I thoughts/shared/drafts/2026-11-16-p2-colours/draw_p2_colours.py
Palette order is the sheet json order (15 colours, hardware colour 0 is transparent):
outline, body x5 (dark to crest), beak/feet x3, gum x5, white."""
import json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../../.."))
BG = os.path.join(ROOT, "thoughts/shared/drafts/2026-11-10-backgrounds-final")

# Hand-picked. Every channel sits on the Neo Geo 5-bit grid (checked below).
FAMILIES = {
    "mint green": ["081018",
                   "08314a", "105a5a", "219c6b", "73de8c", "d6ffc6",   # body: blue-teal shadow, yellow-green light
                   "841839", "e7424a", "ffa573",                       # beak and feet: coral
                   "08526b", "10a594", "5ae7b5", "adffd6", "e7fff7",   # gum: aqua mint, bluer than the rival lime
                   "ffffff"],
    "sky blue":   ["080821",
                   "29298c", "215ac6", "39a5ef", "8cdeff", "effff7",   # body: violet shadow, brighter than the P1 navy
                   "8c4210", "f7a510", "ffef73",                       # beak and feet: gold
                   "18318c", "2173d6", "52b5ff", "a5deff", "e7f7ff",   # gum
                   "ffffff"],
    "sun yellow": ["180810",
                   "6b2118", "b55a10", "efa518", "ffde42", "ffffad",   # body: red-brown shadow, lemon light
                   "31186b", "6342c6", "ad94ff",                       # beak and feet: violet
                   "8c3908", "de8408", "ffc621", "ffef7b", "ffffd6",   # gum
                   "ffffff"],
}
GRID = {(v << 3) | (v >> 2) for v in range(32)}


def rgb(h):
    c = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    assert all(v in GRID for v in c), f"{h} is off the 5-bit grid"
    return c


def main():
    meta = json.load(open(os.path.join(ROOT, "assets/flier/sootling_sheet.json")))
    sheet = Image.open(os.path.join(ROOT, "assets/flier/sootling_sheet.png")).convert("RGBA")
    p1 = [tuple(c) for c in meta["palettes"]["player"]]
    frames = meta["animations"]["player"]
    half = sheet.crop((0, 0, sheet.width, max(f["y"] + f["h"] for f in frames)))
    index = {c: i for i, c in enumerate(p1)}
    src = list(half.getdata())
    assert all(a == 0 or (r, g, b) in index for r, g, b, a in src), "player half has a colour outside its palette"

    sheets = {}
    for name, hexes in FAMILIES.items():
        pal = [rgb(h) for h in hexes]
        assert len(pal) == len(p1) and len(set(pal)) == len(pal), name
        out = Image.new("RGBA", half.size)
        out.putdata([(0, 0, 0, 0) if a == 0 else pal[index[(r, g, b)]] + (255,) for r, g, b, a in src])
        slug = name.split()[0]
        out.save(os.path.join(HERE, f"sheet_{slug}_1x.png"))
        out.resize((out.width * 3, out.height * 3), Image.NEAREST).save(os.path.join(HERE, f"sheet_{slug}_3x.png"))
        sheets[name] = out

    def cut(img, f):
        return img.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))

    tb = meta["tables"]["clip_first"]
    d = meta["defines"]
    picks = [tb[d["CLIP_FLAP2"]], tb[d["CLIP_FALL"]], tb[d["CLIP_WALK0"]] + 2]
    cast = [("P1", lambda i: cut(sheet, frames[i]))]
    cast += [(n, lambda i, s=s: cut(s, frames[i])) for n, s in sheets.items()]
    cast += [("rival", lambda i: cut(sheet, meta["animations"]["cpu"][i]))]

    # shortcut: the game has no day mood (src/core/game.h: moon, dusk, storm), so "day" is a flat stand-in band
    day = Image.new("RGB", (320, 224), rgb("6bb5ef"))
    day.paste(rgb("e7f7ff"), (0, 96, 320, 150))
    moods = {m: Image.open(os.path.join(BG, f"scene_{m}_1x.png")).convert("RGB") for m in ("dusk", "moon", "storm")}
    moods["day stand-in"] = day
    for mood, scene in moods.items():
        scene = scene.copy()
        for row, y in enumerate((14, 78, 142)):          # sky, mid planes, near planes
            for col, (_, get) in enumerate(cast):
                f = get(picks[row])
                scene.paste(f, (22 + col * 60, y), f)
                if col:                                   # each one again right beside P1's neighbour for the close call
                    scene.paste(f, (22 + col * 60 + 26, y + 8), f)
        scene.resize((640, 448), Image.NEAREST).save(os.path.join(HERE, f"compare_{mood.split()[0]}_2x.png"))

    sw = lambda hexes: "".join(f'<span style="background:#{h}" title="#{h}"></span>' for h in hexes)
    html = ["<!doctype html><meta charset=utf-8><title>Gumbirds player 2 colours</title>",
            "<style>body{background:#1c1f26;color:#dde;font:15px system-ui;margin:24px}img{image-rendering:pixelated;display:block;margin:8px 0}"
            ".sw span{display:inline-block;width:28px;height:28px}h2{margin-top:36px}.row{display:flex;gap:24px;flex-wrap:wrap}</style>",
            "<h1>Gumbirds player 2 colour drafts</h1>",
            "<p>Palette swaps of the player sheet (same pixels). Order: outline, body x5, beak x3, gum x5, white.</p>",
            f'<p>Player 1 (in game)</p><div class=sw>{sw("%02x%02x%02x" % c for c in p1)}</div>',
            f'<p>Rival (in game)</p><div class=sw>{sw("%02x%02x%02x" % tuple(c) for c in meta["palettes"]["cpu"])}</div>']
    for name, hexes in FAMILIES.items():
        html.append(f'<p>{name.capitalize()}: {" ".join(hexes)}</p><div class=sw>{sw(hexes)}</div>')
    html.append("<h2>Against each sky mood (2x)</h2><p>Left to right: player 1, mint green, sky blue, sun yellow, rival. "
                "Each one is drawn twice. Rows: flap, fall, walk.</p>")
    for mood in moods:
        html.append(f'<p>{mood.capitalize()}</p><img src="compare_{mood.split()[0]}_2x.png">')
    html.append("<h2>Sheets</h2><div class=row>")
    for name in FAMILIES:
        s = name.split()[0]
        html.append(f'<div><p>{name.capitalize()} 3x (<a style="color:#9cf" href="sheet_{s}_1x.png">1x</a>)</p><img src="sheet_{s}_3x.png"></div>')
    html.append("</div>")
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(html))


main()

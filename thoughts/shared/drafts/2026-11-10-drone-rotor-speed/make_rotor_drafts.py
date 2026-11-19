#!/opt/homebrew/bin/python3.14 -I
"""Drone rotor speed draft (art draft only, nothing here feeds the ROM).

Reads only files in this folder:
  src_obstacle_sheet.png / .json   copy of assets/obstacles/obstacle_sheet.*
  src_scene_dusk_1x.png            copy of drafts/2026-11-10-backgrounds-final/scene_dusk_1x.png
Writes GIFs, frame sheets, numbers.txt and index.html next to itself.

Usage:  /opt/homebrew/bin/python3.14 -I make_rotor_drafts.py
"""
import json
import math
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FW, FH = 28, 20            # drone frame
CW, CH = 64, 40            # GIF canvas (1x), shown at 4x by the page
SKY = (0x16, 0x1a, 0x33)   # plain dark sky tone
BG_CROP = (150, 44)        # top-left of the 64x40 crop in the dusk scene

# snapped sheet colours (as they are in the sheet PNG)
INK, ROTOR, MID, LITE, BODYL = "080810", "a5adce", "5a6384", "8c94b5", "6b7394"
DARK, DARK2, WHITE = "394252", "394263", "ffffff"


def rgb(h):
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def load_frames(name):
    sheet = Image.open(os.path.join(HERE, "src_obstacle_sheet.png")).convert("RGBA")
    meta = json.load(open(os.path.join(HERE, "src_obstacle_sheet.json")))
    out = []
    for r in meta["animations"][name]:
        out.append(sheet.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])))
    return out, meta


def span(cx, hw):
    return [x for x in range(FW) if abs(x - cx) <= hw]


def blur_rotor(body, theta):
    """One frame: body rows 5..19 from `body` untouched, rows 0..4 redrawn as a
    motion-blur disc. Two blades; theta = blade angle (period pi)."""
    im = body.copy()
    px = im.load()
    for y in range(0, 5):
        for x in range(FW):
            if not (y == 4 and 11 <= x <= 16):      # keep the mast top row
                px[x, y] = (0, 0, 0, 0)

    def put(x, y, c):
        if 0 <= x < FW:
            px[x, y] = rgb(c)

    # --- the disc: same silhouette in every frame (no wide/narrow flip)
    for x in range(4, 24):
        put(x, 1, INK if 7 <= x <= 20 else DARK2)          # top rim, soft toward the tips
    for x in range(1, 27):
        put(x, 2, DARK if x in (1, 26) else MID if x in (2, 3, 24, 25) else BODYL)
    for x in range(3, 25):
        put(x, 3, DARK2 if x in (3, 4, 23, 24) else MID)
    for x in list(range(4, 11)) + list(range(17, 24)):
        put(x, 4, DARK if x in (4, 5, 22, 23) else INK)    # underside shadow

    # --- see-through slots in the under row, a quarter turn away from the blades
    for s in (1, -1):
        gx = 13.5 + 9.5 * math.cos(theta + math.pi / 2) * s
        for x in span(gx, 1.0):
            if not 10 <= x <= 17 and 5 <= x <= 22:
                px[x, 3] = (0, 0, 0, 0)

    # --- the two blade streaks; back one first so the front one wins
    blades = sorted(((math.sin(theta) * s, math.cos(theta) * s) for s in (1, -1)))
    for depth, c in blades:
        cx = 13.5 + 9.5 * c
        if depth < -0.3:                     # far side: dim, seen through the disc
            for x in span(cx, 2.5):
                put(x, 2, LITE)
            for x in span(cx, 1.0):
                put(x, 1, MID)
        elif depth > 0.3:                    # near side: bright streak with a white core
            for x in span(cx, 3.5):
                put(x, 2, ROTOR)
            for x in span(cx, 1.5):
                put(x, 2, WHITE)
            for x in span(cx, 2.5):
                put(x, 3, LITE)
        else:                                # edge-on at the tip
            for x in span(cx, 3.0):
                put(x, 2, ROTOR)
            tip = cx + (1.5 if c > 0 else -1.5)
            for x in span(tip, 1.0):
                put(x, 2, WHITE)
            for x in span(cx, 1.5):
                put(x, 3, LITE)
    return im


def blur_set(orig, n):
    """n frames; lamp on for 2 frames, off for 2 (same pattern as today's sheet)."""
    out = []
    for k in range(n):
        body = orig[0] if (k % 4) < 2 else orig[2]
        out.append(blur_rotor(body, math.pi * k / n))
    return out


def delays_cs(n_frames, ticks):
    """GIF delays in 1/100 s. Target ticks/60 s per frame; the rounding error is
    carried to the next frame so the running time stays within 0.5/100 s."""
    out, done = [], 0
    for i in range(1, n_frames + 1):
        t = round(i * ticks * 100 / 60)
        out.append(t - done)
        done = t
    return out


def loop_len(cycle, ticks):
    """Shortest whole number of cycles whose length is a whole number of 1/100 s."""
    k = 1
    while (cycle * k * ticks * 100) % 60:
        k += 1
    return cycle * k


def canvases():
    plain = Image.new("RGBA", (CW, CH), SKY + (255,))
    scene = Image.open(os.path.join(HERE, "src_scene_dusk_1x.png")).convert("RGBA")
    crop = scene.crop((BG_CROP[0], BG_CROP[1], BG_CROP[0] + CW, BG_CROP[1] + CH))
    return {"plain": plain, "dusk": crop}


def save_gif(name, frames, ticks, bgs, fw, fh):
    n = loop_len(len(frames), ticks)
    d = delays_cs(n, ticks)
    for bgname, bg in bgs.items():
        comp = []
        for i in range(n):
            c = bg.copy()
            c.alpha_composite(frames[i % len(frames)], ((CW - fw) // 2, (CH - fh) // 2))
            comp.append(c.convert("RGB"))
        strip = Image.new("RGB", (CW * len(frames), CH))
        for i in range(len(frames)):
            strip.paste(comp[i], (CW * i, 0))
        pal = strip.quantize(256, dither=Image.Dither.NONE)
        pf = [c.quantize(palette=pal, dither=Image.Dither.NONE) for c in comp]
        pf[0].save(os.path.join(HERE, "%s_%s.gif" % (name, bgname)), save_all=True,
                   append_images=pf[1:], duration=[x * 10 for x in d], loop=0,
                   optimize=False, disposal=1)
    return n, d


def save_sheet(name, frames, fw, fh):
    im = Image.new("RGBA", ((fw + 2) * len(frames) - 2, fh), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        im.paste(f, ((fw + 2) * i, 0))
    im.save(os.path.join(HERE, "sheet_%s_1x.png" % name))
    return im.size


def tiles(frame):
    """16x16 cuts, frame at the cell origin (the real pipeline may align otherwise)."""
    w, h = frame.size
    out = []
    for ty in range(0, h, 16):
        for tx in range(0, w, 16):
            t = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
            t.paste(frame.crop((tx, ty, min(tx + 16, w), min(ty + 16, h))), (0, 0))
            out.append(t.tobytes())
    return out


def palette_use(frames, meta):
    names = list(meta["palette"].keys())           # sheet json order = index 1..15
    target = [rgb(meta["palette"][k].lstrip("#")) for k in names]
    used = set()
    for f in frames:
        for p in set(f.get_flattened_data() if hasattr(f, "get_flattened_data") else f.getdata()):
            if p[3]:
                best = min(range(len(target)), key=lambda i: sum((target[i][j] - p[j]) ** 2 for j in range(3)))
                used.add(best)
    return ["%d %s" % (i + 1, names[i]) for i in sorted(used)]


def main():
    orig, meta = load_frames("drone")
    bot, _ = load_frames("bot")
    v2 = blur_set(orig, 4)
    v3 = blur_set(orig, 8)
    bgs = canvases()
    plain_only = {"plain": bgs["plain"]}

    # body rows must be identical to the sheet (rows 5..19; lamp follows the sheet pattern)
    for k, f in enumerate(v2 + v3):
        ref = orig[0] if (k % 4) < 2 else orig[2]
        assert f.crop((0, 5, FW, FH)).tobytes() == ref.crop((0, 5, FW, FH)).tobytes()
        assert f.crop((11, 4, 17, 5)).tobytes() == ref.crop((11, 4, 17, 5)).tobytes()

    variants = [
        # key, label, frames, ticks
        ("v0", "V0  today: 4 frames, new frame every 2 game frames (30 per second)", orig, 2),
        ("v1", "V1  same 4 frames, new frame every 7 game frames (naive switch)", orig, 7),
        ("v2", "V2  4 redrawn blur frames, every 7 game frames", v2, 7),
        ("v3", "V3  8 redrawn blur frames, every 7 game frames", v3, 7),
        ("v2_t4", "V2 at 4 game frames (only if the global speed changes; islands would move 1.75 times faster)", v2, 4),
        ("v3_t4", "V3 at 4 game frames (only if the global speed changes; islands would move 1.75 times faster)", v3, 4),
    ]
    lines = ["Drone rotor speed draft, numbers", "generated by make_rotor_drafts.py", ""]
    lines.append("Frame size 28 x 20 px = 2 x 2 tiles of 16 x 16 = 4 tiles per frame (frame at the cell origin;")
    lines.append("the real cut is done by tools/sprite_pipeline.py and may align differently: unverified).")
    today_unique = len(set(t for f in orig for t in tiles(f)))
    lines.append("Today (CPU animation, tiles deduplicated across frames): %d unique tiles for the 4 drone frames." % today_unique)
    lines.append("Hardware auto-animation: no dedup inside a group, tiles = frames x 4, group base aligned to 4 or 8.")
    lines.append("")
    rows = []
    for key, label, frames, ticks in variants:
        n, d = save_gif(key, frames, ticks, bgs, FW, FH)
        group = len(frames) * 4
        uniq = len(set(t for f in frames for t in tiles(f)))
        hz = 60 / ticks
        lines.append(label)
        lines.append("  frames %d, tiles per frame 4, frame rate %.2f per second, full cycle %d game frames (%.2f s)"
                     % (len(frames), hz, len(frames) * ticks, len(frames) * ticks / 60))
        if key == "v0":
            lines.append("  C ROM tiles: %d (dedup, as built today); extra: 0" % today_unique)
        else:
            lines.append("  C ROM tiles as an auto-animation group: %d (distinct pictures among them: %d); extra over today's %d: +%d"
                         % (group, uniq, today_unique, group - today_unique))
        lines.append("  palette indices used (sheet json order, 0 = transparent): " + ", ".join(palette_use(frames, meta)))
        lines.append("  GIF: %d frames per loop, delays in 1/100 s: %s (target %.3f; error carried forward, loop length exact)"
                     % (n, " ".join(map(str, d[:6])) + (" ..." if n > 6 else ""), ticks * 100 / 60))
        lines.append("")
        rows.append((key, label))
    save_sheet("v0_v1", orig, FW, FH)
    save_sheet("v2", v2, FW, FH)
    save_sheet("v3", v3, FW, FH)

    # bot: today 8 ticks; 4-group A B A B at 7; the study's 8-group A x4 B x4 at 7 = 28 ticks per picture
    bw, bh = bot[0].size
    bot_rows = [
        ("bot_today", "Bot today: 2 frames, every 8 game frames", bot, 8),
        ("bot_t7", "Bot as a 4-frame group A B A B, every 7 game frames", bot, 7),
        ("bot_t28", "Bot as the study's 8-frame group A A A A B B B B at 7 game frames (28 per picture)", bot, 28),
    ]
    for key, label, frames, ticks in bot_rows:
        n, d = save_gif(key, frames, ticks, plain_only, bw, bh)
        lines.append(label)
        lines.append("  GIF: %d frames per loop, delays in 1/100 s: %s (target %.3f)" % (n, " ".join(map(str, d[:6])), ticks * 100 / 60))
    lines.append("  Bot tiles: 28 x 28 = 4 tiles per frame; 4-frame group 16 tiles, 8-frame group 32 tiles.")
    lines.append("")
    lines.append("Colours: only colours already in the obstacle sheet; no new palette entry; no dithering.")
    lines.append("Palette index order is the sheet json order; the built palette order was not checked (no build allowed).")
    open(os.path.join(HERE, "numbers.txt"), "w").write("\n".join(lines) + "\n")

    def fig(key, label, bgname, w, h):
        return ('<figure><img src="%s_%s.gif" width="%d" height="%d" alt="%s"><figcaption>%s</figcaption></figure>'
                % (key, bgname, w * 4, h * 4, label, label))

    def sheet(name, label, nfr):
        w = (FW + 2) * nfr - 2
        return ('<figure><img src="sheet_%s_1x.png" width="%d" height="%d" alt="%s"><figcaption>%s</figcaption></figure>'
                % (name, w * 8, FH * 8, label, label))

    html = ["<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Drone rotor speed draft</title><style>",
            "body{background:#1b1c1f;color:#d9dadd;font:15px/1.45 -apple-system,'Helvetica Neue',Arial,sans-serif;margin:28px}",
            "h1{font-size:22px;margin:0 0 6px}h2{font-size:17px;margin:30px 0 10px;border-bottom:1px solid #3a3c42;padding-bottom:4px}",
            "p{max-width:920px;color:#b4b6bc;margin:6px 0}",
            ".row{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start}",
            "figure{margin:0;background:#25272b;border:1px solid #3a3c42;border-radius:3px;padding:10px;max-width:100%;overflow-x:auto}",
            "figcaption{margin-top:8px;font-size:13px;color:#c6c8cd;max-width:256px}",
            ".wide figcaption{max-width:none}",
            "img{image-rendering:pixelated;display:block}",
            ".sheet img{background:#16181d}",
            "</style></head><body>",
            "<h1>Drone rotor at hardware auto-animation speed</h1>",
            "<p>All pictures run at exact game timing (60 game frames per second) and are shown at 4 times size. "
            "Today the processor changes the rotor picture every 2 game frames. Hardware auto-animation shares one speed with the floating islands: "
            "a new picture every 7 game frames, about 8.6 per second. Question: which version still reads as a spinning rotor?</p>",
            "<p>In V2 and V3 only the rotor (top 5 pixel rows) is redrawn. Body, lamp, size and colours are unchanged. "
            "The lamp blinks slower at the hardware speed in V1, V2 and V3 (about twice per second instead of 7.5 times).</p>"]
    for bgname, title in (("plain", "On plain dark sky"), ("dusk", "On the dusk background (crop)")):
        html.append("<h2>%s</h2><div class='row'>" % title)
        for key, label in rows[:4]:
            html.append(fig(key, label, bgname, CW, CH))
        html.append("</div>")
    html.append("<h2>If the global speed were changed to 4 game frames (15 per second)</h2><div class='row'>")
    for bgname in ("plain", "dusk"):
        for key, label in rows[4:]:
            html.append(fig(key, label, bgname, CW, CH))
    html.append("</div>")
    html.append("<h2>Bot obstacle</h2><div class='row'>")
    for key, label, _, _ in bot_rows:
        html.append(fig(key, label, "plain", CW, CH))
    html.append("</div>")
    html.append("<h2>Frame sheets at 8 times size</h2><div class='sheet wide'>")
    html.append(sheet("v0_v1", "V0 and V1: today's 4 frames (rotor wide, narrow, wide, narrow; lamp on, on, off, off)", 4))
    html.append("<p></p>" + sheet("v2", "V2: 4 blur frames (bright streak: tips, right, centre, left)", 4))
    html.append("<p></p>" + sheet("v3", "V3: 8 blur frames (same sweep in half steps)", 8))
    html.append("</div><p>Tile counts and palette use: numbers.txt in this folder.</p></body></html>")
    open(os.path.join(HERE, "index.html"), "w").write("\n".join(html) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

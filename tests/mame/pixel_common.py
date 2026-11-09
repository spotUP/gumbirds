"""Shared helpers for the MAME snapshot pixel checks (python3.14 -I, Pillow)."""
import re
from PIL import Image

TOL = 12


def palettes_rgb(c_path, name):
    """All palettes of generated set `name` as lists of 8-bit RGB tuples (transparent entry 0 dropped).
    Palette words are DRGB; the 5-bit channel is expanded the way the hardware does it."""
    text = open(c_path).read()
    body = re.search(name + r"_palettes\[[^\]]*\]\[16\]\s*=\s*\{(.*?)\n\};", text, re.S).group(1)
    out = []
    for row in re.findall(r"\{([^{}]*)\}", body):
        cols = set()
        for w in re.findall(r"0x[0-9a-fA-F]+", row)[1:]:
            w = int(w, 16)
            ch = []
            for shift, lsb in ((8, 14), (4, 13), (0, 12)):
                v5 = (((w >> shift) & 0xF) << 1) | ((w >> lsb) & 1)
                ch.append((v5 << 3) | (v5 >> 2))
            cols.add(tuple(ch))
        out.append([c for c in cols if c != (0, 0, 0)])
    return out


def colours(c_path, name):
    return {c for pal in palettes_rgb(c_path, name) for c in pal}


def near(p, c):
    return max(abs(p[i] - c[i]) for i in range(3)) <= TOL


def exclusive(own, other):
    """Colours of `own` that no colour of `other` is within tolerance of (checks stay independent)."""
    return [c for c in own if not any(near(c, o) for o in other)]


def count(png, cols, box):
    """Pixels of snapshot `png` inside box (320x224 coordinates) matching any colour in cols."""
    im = Image.open(png).convert("RGB")
    w, h = im.size
    x0, y0, x1, y1 = box
    sx, sy = w / 320.0, h / 224.0
    n = 0
    for y in range(max(0, int(y0 * sy)), min(h, int(y1 * sy))):
        for x in range(max(0, int(x0 * sx)), min(w, int(x1 * sx))):
            p = im.getpixel((x, y))
            if any(near(p, c) for c in cols):
                n += 1
    return n, im.size

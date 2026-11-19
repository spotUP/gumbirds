"""Writes backdrop_<mood>_384_1x.png: the wide-arena backdrop (no islands, no fliers) unrolled to the 384 px arena.

The screen is 320 px wide and the planes scroll at different speeds, so one seamless 384 px picture does not exist.
Arena x 32..351 is the true screen at camera 32. Arena x 0..31 is taken from the screen at camera 0 and arena
x 352..383 from the screen at camera 64. The near plane and the hazard are exact everywhere; the far planes and
the sky jump at arena x 32 and 352. Run: /opt/homebrew/bin/python3.14 -I make_backdrops.py
"""
import os, sys, importlib.util
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(HERE, '..', '2026-11-10-backgrounds-wide', 'draw_backgrounds_wide.py')
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('bgwide', src)
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)
for m in ('moon', 'dusk', 'storm'):
    md = bg.Mood(m)
    md.prep()
    c0, c32, c64 = (md.frame(4, actors=False, cam=c) for c in (0, 32, 64))
    out = np.zeros((224, 384, 3), np.uint8)
    out[:, 0:32] = c0[:, 0:32]
    out[:, 32:352] = c32
    out[:, 352:384] = c64[:, 288:320]
    Image.fromarray(out, 'RGB').save(os.path.join(HERE, 'backdrop_%s_384_1x.png' % m))
    L = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
    for y0, y1 in ((30, 70), (70, 110), (110, 150), (150, 192)):
        h = np.histogram(L[y0:y1], bins=range(0, 257, 16))[0]
        print(m, y0, y1, ' '.join('%2d' % round(100 * v / h.sum()) for v in h))

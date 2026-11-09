"""Visual proof by pixels: obstacle palette colours appear at the screen position of every on-screen
obstacle during play, and not there before start.
Usage: check_obstacle_pixels.py hero_sprites.c obs_sprites.c city_sprites.c pre_start.png playing.png obstacles.txt
obstacles.txt: one line per active obstacle written by boot_check.lua from RAM at the playing
snapshot: "type x y w h" (hit box, pixels). Only obstacle colours that no hero or city palette uses are
counted. Needs at least one on-screen obstacle. Exit 1 on failure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_common as pc

MARGIN, MIN_PER_OBSTACLE, MAX_BEFORE = 8, 30, 5
NAMES = ["vent", "cable", "drone", "bot"]


def main():
    hero_c, obs_c, city_c, pre, play, obs_txt = sys.argv[1:7]
    cols = pc.exclusive(sorted(pc.colours(obs_c, "obs")), sorted(pc.colours(hero_c, "hero") | pc.colours(city_c, "city")))
    boxes = []
    for line in open(obs_txt):
        t, x, y, w, h = (int(v) for v in line.split())
        if -w < x < 320:
            boxes.append((t, x, y, w, h))
    ok = bool(boxes)
    if not boxes:
        print("[FAIL] no on-screen obstacle in the playing snapshot (%s)" % obs_txt)
    for t, x, y, w, h in boxes:
        box = (x - MARGIN, y - MARGIN, x + w + MARGIN, y + h + MARGIN)
        npl, size = pc.count(play, cols, box)
        nb, _ = pc.count(pre, cols, box)
        good = npl >= MIN_PER_OBSTACLE and nb <= MAX_BEFORE
        ok = ok and good
        print("%s %s obstacle pixels in box %s (%d obstacle-only colours): before start %d (max %d), playing %d (min %d)"
              % ("[OK]" if good else "[FAIL]", NAMES[t], box, len(cols), nb, MAX_BEFORE, npl, MIN_PER_OBSTACLE))
    sys.exit(0 if ok else 1)


main()

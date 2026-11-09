"""Visual proof by pixels: hero palette colours appear in the hero screen box during play, never before start.
Usage: check_hero_pixels.py hero_sprites.c obs_sprites.c city_sprites.c pre_start.png playing.png   (python3.14 -I, Pillow)
Only hero palette 0 colours (palette 1 is the laser, owned by check_laser_pixels.py) that no obstacle or city palette uses are counted, so this check does not pass on other art.
Exit 1 on failure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_common as pc

HERO_X, GROUND_Y, BOX_W, BOX_H, MARGIN = 48, 176, 48, 48, 12
MIN_PLAYING, MAX_BEFORE = 200, 5


def main():
    hero_c, obs_c, city_c, pre, play = sys.argv[1:6]
    cols = pc.exclusive(sorted(pc.palettes_rgb(hero_c, "hero")[0]), sorted(pc.colours(obs_c, "obs") | pc.colours(city_c, "city")))
    left = HERO_X - 11 - MARGIN
    box = (left, GROUND_Y - BOX_H - MARGIN, left + BOX_W + 2 * MARGIN, GROUND_Y + MARGIN)
    nb, size = pc.count(pre, cols, box)
    npl, _ = pc.count(play, cols, box)
    ok = nb <= MAX_BEFORE and npl >= MIN_PLAYING
    print("%s hero pixels in box %s (image %s, %d hero-only colours): before start %d (max %d), playing %d (min %d)"
          % ("[OK]" if ok else "[FAIL]", box, size, len(cols), nb, MAX_BEFORE, npl, MIN_PLAYING))
    sys.exit(0 if ok else 1)


main()

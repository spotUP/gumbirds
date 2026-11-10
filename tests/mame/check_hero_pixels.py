"""Visual proof by pixels: hero palette colours appear in the flier screen box during play.
Usage: check_hero_pixels.py hero_sprites.c obs_sprites.c city_sprites.c pre_start.png playing.png   (python3.14 -I, Pillow)
Arena: the flier stands on the middle island (spawn x FLIER_START_X, island top y 140; hero sprite is still the runner frames, placeholder). Only hero palette 0 colours (palette 1 is the old laser/hit flash) that no obstacle or city palette uses are counted, so this check does not pass on other art. The attract demo also flies the flier, so the pre-start snapshot is reported but not bounded.
Exit 1 on failure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_common as pc

FLIER_X, ISLAND_TOP_Y, BOX_W, BOX_H, MARGIN = 160, 140, 48, 48, 12
MIN_PLAYING = 200


def main():
    hero_c, obs_c, city_c, pre, play = sys.argv[1:6]
    cols = pc.exclusive(sorted(pc.palettes_rgb(hero_c, "hero")[0]), sorted(pc.colours(obs_c, "obs") | pc.colours(city_c, "city")))
    left = FLIER_X - BOX_W // 2 - MARGIN
    box = (left, ISLAND_TOP_Y - BOX_H - MARGIN, left + BOX_W + 2 * MARGIN, ISLAND_TOP_Y + MARGIN)
    nb, size = pc.count(pre, cols, box)
    npl, _ = pc.count(play, cols, box)
    ok = npl >= MIN_PLAYING
    print("%s hero pixels in box %s (image %s, %d hero-only colours): attract (pre-start) %d, playing %d (min %d)"
          % ("[OK]" if ok else "[FAIL]", box, size, len(cols), nb, npl, MIN_PLAYING))
    sys.exit(0 if ok else 1)


main()

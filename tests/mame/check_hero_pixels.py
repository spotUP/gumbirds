"""Visual proof by pixels: Sootling player palette colours appear in the flier screen box during play.
Usage: check_hero_pixels.py sootling_sprites.c obs_sprites.c city_sprites.c pre_start.png playing.png   (python3.14 -I, Pillow)
Arena: the flier stands on the middle island (spawn x FLIER_START_X, island top y 140; the player is the Sootling sprite). Only Sootling palette 0 colours (palette 1 is the red-balloon computer palette) that no obstacle or city palette uses are counted, so this check does not pass on other art. The hero is hidden before play, so the pre-start snapshot is bounded near 0.
Exit 1 on failure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_common as pc

FLIER_X, ISLAND_TOP_Y, BOX_W, BOX_H, MARGIN = 160, 140, 32, 32, 12
# Sootling 2-balloon frames are 207-263 opaque px of which only part uses player-only colours (balloon greens, body);
# measured 2026-11-10: playing 135 with the v5 32 x 48 art, 182 with the 24 x 32 art. Before start no Sootling sprite is drawn (main.c hero_and_mode draws only in FLOW_PLAYING), so attract must be near 0; the 196 measured with v5 was a palette coincidence with other art. The old 200 was the runner sprite. The city and obstacle
# palettes share none of these colours, so an empty or wrong-art box stays near 0.
MIN_PLAYING = 100
MAX_ATTRACT = 10


def main():
    hero_c, obs_c, city_c, pre, play = sys.argv[1:6]
    cols = pc.exclusive(sorted(pc.palettes_rgb(hero_c, "sootling")[0]), sorted(pc.colours(obs_c, "obs") | pc.colours(city_c, "city")))
    left = FLIER_X - BOX_W // 2 - MARGIN
    box = (left, ISLAND_TOP_Y - BOX_H - MARGIN, left + BOX_W + 2 * MARGIN, ISLAND_TOP_Y + MARGIN)
    nb, size = pc.count(pre, cols, box)
    npl, _ = pc.count(play, cols, box)
    ok = npl >= MIN_PLAYING and nb <= MAX_ATTRACT
    print("%s hero pixels in box %s (image %s, %d hero-only colours): attract (pre-start) %d (max %d), playing %d (min %d)"
          % ("[OK]" if ok else "[FAIL]", box, size, len(cols), nb, MAX_ATTRACT, npl, MIN_PLAYING))
    sys.exit(0 if ok else 1)


main()

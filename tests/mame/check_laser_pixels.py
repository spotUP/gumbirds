"""Reachability proof for the laser, by pixels and RAM numbers from tests/mame/laser_check.lua.
Usage: check_laser_pixels.py hero_sprites.c obs_sprites.c city_sprites.c heat_sprites.c heat_zero.png beam.png kill.png laser.txt
laser.txt: "heat H0 H1", "beam bx by" (bolt left edge, top, pixels), "kill kx ky bonus_delta kills_before kills_after chain_before".
Checks (python3.14 -I, Pillow; exit 1 on failure):
  1. laser-only colours (hero palette 1 colours no other palette uses) are in the beam box with a bolt in
     flight and not there before the first shot;
  2. the heat bar colours (heat palette colours no other set uses) grow in the bar box when heat rises;
  3. the kill counter rose by one and the bonus by 200 x multiplier (chain before + 1, capped at CHAIN_MAX);
  4. hero palette 1 colours grow around the kill position two frames after the kill (hit flash)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_common as pc

KILL_SCORE, CHAIN_MAX = 200, 5
BEAM_W, BEAM_H, MARGIN = 24, 5, 10
MIN_BEAM, MAX_BEFORE, MIN_BAR_GROWTH, MIN_FLASH = 40, 5, 30, 8
BAR_BOX = (56, 36, 56 + 16 * 8 + 8, 56)  # HEAT_BAR_X/Y in src/main.c, bar is 16 x 8 pixels per pair
FLASH_R = 14


def main():
    hero_c, obs_c, city_c, heat_c, zero, beam, kill, txt = sys.argv[1:9]
    pals = pc.palettes_rgb(hero_c, "hero")
    others = pc.colours(obs_c, "obs") | pc.colours(city_c, "city") | pc.colours(heat_c, "heat") | set(pals[0])
    laser = pc.exclusive(sorted(pals[1]), sorted(others))
    heat = pc.exclusive(sorted(pc.colours(heat_c, "heat")),
                        sorted(pc.colours(obs_c, "obs") | pc.colours(city_c, "city") | set(pals[0]) | set(pals[1])))
    vals = {}
    for line in open(txt):
        p = line.split()
        if p:
            vals[p[0]] = [int(v) for v in p[1:]]
    ok = True

    def report(good, text):
        nonlocal ok
        ok = ok and good
        print("%s %s" % ("[OK]" if good else "[FAIL]", text))

    if "beam" not in vals or "kill" not in vals or "heat" not in vals:
        print("[FAIL] laser.txt incomplete: %s" % sorted(vals))
        sys.exit(1)
    bx, by = vals["beam"]
    box = (bx - MARGIN, by - MARGIN, bx + 24 + BEAM_W + MARGIN, by + 12 + BEAM_H + MARGIN)
    nb, _ = pc.count(zero, laser, box)
    nl, _ = pc.count(beam, laser, box)
    report(nl >= MIN_BEAM and nb <= MAX_BEFORE,
           "beam pixels in box %s (%d laser-only colours): before first shot %d (max %d), bolt in flight %d (min %d)"
           % (box, len(laser), nb, MAX_BEFORE, nl, MIN_BEAM))
    h0, h1 = vals["heat"]
    z, _ = pc.count(zero, heat, BAR_BOX)
    b, _ = pc.count(beam, heat, BAR_BOX)
    report(h1 > h0 and b - z >= MIN_BAR_GROWTH,
           "heat bar pixels in box %s (%d bar-only colours): heat %d -> %d, pixels %d -> %d (growth min %d)"
           % (BAR_BOX, len(heat), h0, h1, z, b, MIN_BAR_GROWTH))
    kx, ky, delta, kb, ka, chain = vals["kill"]
    want = KILL_SCORE * min(chain + 1, CHAIN_MAX)
    report(ka == kb + 1 and delta == want,
           "kill counter %d -> %d, bonus +%d (expected %d = %d x multiplier %d)"
           % (kb, ka, delta, want, KILL_SCORE, min(chain + 1, CHAIN_MAX)))
    fbox = (kx - FLASH_R, ky - FLASH_R, kx + FLASH_R, ky + FLASH_R)
    # The flash frame is mostly white (shared with other palettes), so count every hero palette 1 colour
    # and require growth over the pre-shot snapshot in the same box.
    flash_cols = sorted(pals[1])
    nf, _ = pc.count(kill, flash_cols, fbox)
    nz, _ = pc.count(zero, flash_cols, fbox)
    report(nf - nz >= MIN_FLASH,
           "hit flash pixels (palette 1 colours) in box %s: before %d, after kill %d (growth min %d)" % (fbox, nz, nf, MIN_FLASH))
    sys.exit(0 if ok else 1)


main()

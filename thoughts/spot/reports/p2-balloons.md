# P2 balloons after parachute - findings (no defect reproduced in data)

Measured in real MAME (UniBIOS, coin, P1 Start, P2 Start, P2 button A) via tests/mame/coop_check.lua, once flapping at once and once
with the chute held ~630 frames until landing:
- hero[1].balloons = 2 in PARACHUTE, after release (ALIVE) and after landing. Core is fine (matches the host probe).
- P2 body sprite (pool object 30, hardware sprite 251) SCB1 tile/attr read from VRAM: PARACHUTE shows flap2 frame 0 (tile 0x729),
  ALIVE shows flap2 frames (0x72d/0x73e/0x742), landed shows breathe2 (0x7e4/0x7e7/0x75a). Decoded against
  build/gen/sootling_sprites.c these are the 2-balloon clips, the same set P1 uses. Attr palette = SOOT_P2_PAL_SLOT, and the
  palette RAM slot equals sootling_extra_palettes[0] at every sample (no overwrite).
- Later in the run P2 loses a balloon to a hit (bal 2 -> 1), normal.

So tiles, palette and state are right. Not verified: pixels on screen. Remaining suspect (unconfirmed): in PARACHUTE the balloon
body (sprite 251) is drawn under the chute object (sprites 254..256, higher index = on top), so chute art may cover the balloons;
the chute is hidden after release only through POOL_F_BLINK. Needs one screenshot of P2 mid-chute and just after release.

Change: coop_check.lua now also asserts balloons == 2 and the P2 body SCB1 tile/palette after the chute release
(coop_probe.c entries 22, 23). It passes; it does not fail pre-fix because no code fix was found.
Gates run: gmake test-coop only (no src change). Not run: host tests, test-arcade.

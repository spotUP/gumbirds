# Gum Trip drafts: gum pickup, rival Sootling, gum meter

Date: 2026-11-10. Status: drafts for a pick, nothing is wired into the game.

Open `index.html` in a browser for the gallery. All numbers are in `numbers.txt` (written by the script).

Regenerate from the repo root:

    /opt/homebrew/bin/python3.14 -I thoughts/shared/drafts/2026-11-10-gum-trip-pickup-rival/draw_pickup_rival.py

Add `--contact` to also write `pickup_contact_3x.png` (all pickup frames on one grey sheet, for judging only).

The script reads `assets/flier/sootling_sheet.png` and `.json` (read only). The sky crops (`sky_*_1x.png`) and the
HUD tag crop (`hud_tag_storm_1x.png`) are copies taken from the backgrounds-final and hud-title-final draft folders;
they live in this folder so the script does not depend on those folders after the first run.

## Pickup candidates

All three use magenta (255,0,255) as the key colour, colour values in multiples of 8, no dither and no checker.
The idle loop has 16 frames at 15 frames per second. The collect effect has 8 frames of 32x32.
The vertical bob is not drawn into the tiles: the game moves the sprite by the offsets listed in `numbers.txt`
(-2 to +3 px), so a pickup costs no extra tiles for the bob.

| | Candidate | Size | Colours | Sprite columns | Unique 16x16 tiles (idle + collect) |
|---|---|---|---|---|---|
| A | Wrapped gum drop: pink ball with pale stripes that roll, two teal wrapper ears that flutter | 24x24 | 13 | 2 | 64 + 32 = 96 |
| B | Spinning gumball: three-colour swirl ball (blue, white, pink) that turns around a tilted axis | 16x16 | 12 | 1 | 16 + 32 = 48 |
| C | Twirling gum stick: pink stick half out of a blue foil wrapper, turns around its long axis | 24x24 | 11 | 2 | 63 + 24 = 87 |

Collect effects: A bursts into six gum blobs and two wrapper scraps with sparkles; B throws a ring that grows and
thins, three small balls and eight glints; C sends five gum blobs up in a spiral that end in sparkles.

Worst case sprites per scanline added: A 4, B 3, C 4 (two pickups level on screen, one of them in its collect effect).

### How the motion is simulated

One joint spring system (`sim()` in the script) runs for 14 loop periods with a periodic gust as the driver. Only
the last period is recorded, so the loop closes without a seam. The system has these parts:

- Bob: a mass on a spring (natural frequency 1.25 per loop, damping ratio 0.18), lifted by the gust.
- Squash: a surface tension spring (3 per loop, damping 0.12) driven by the bob acceleration. Volume stays constant:
  the x radius is multiplied by (1 + q), the y radius is divided by it.
- Tilt: a torsion spring (1.1 per loop) driven by a side gust.
- Wrapper ears (candidate A): two lighter springs (2.3 and 2.9 per loop) that chase the opposite of the tilt and the
  bob speed, so the ears lag behind the ball and ring out of step with each other.
- Spin (candidates B and C): angular speed under air drag with one torque kick per loop, so the turn speeds up and
  slows down. Candidate C adds a twist spring driven by the angular acceleration: the stick ends lag the middle.
- Collect effects: particles with a radial launch, air drag and gravity (`burst()`); the ring of B grows on an
  exponential ease while its thickness falls.

Every frame is an analytic shape (ellipsoid, fan, box) sampled 5x5 per pixel, lit from the upper left, then banded
into a hand-chosen ramp per material with a hue shift from dark to light. One keyline colour goes around it. Stray
single pixels are removed.

### Pickup ranking

1. **A, wrapped gum drop.** Reads as sweet in the shortest time: the wrapper ears give a silhouette that no hazard and
   no flier bubble has. The teal ears separate it from the pink flier bubbles. The cost is the highest tile count (96).
2. **B, spinning gumball.** Cheapest (one sprite column, 48 tiles) and the ring collect effect is the clearest of the
   three. The risk: a 16x16 ball without ears reads less clearly as gum, more like a gem or marble.
3. **C, twirling gum stick.** Different shape, but the weakest drawing: the edge-on frames are 3 px wide and almost
   vanish in rain, and the two frames with the foil flash are close to white and lose the form. It needs a hand pass
   before it can compete.

None of the three uses orange or yellow, a spark shape, or the double lobe on a neck.

## Rival variants

All three use the accepted 63 Sootling frames. Palette values are multiples of 8 and are listed per index (1..15)
in `numbers.txt`. Index meaning: 1 keyline, 2..5 fur dark to light, 6 rim and eye white, 7..9 beak and feet,
10..14 gum, 15 white.

- **A, Hornet.** Palette swap only. Charcoal fur, yellow eyes and rim, red beak, amber gum. 0 frames changed.
- **B, Bone.** Palette swap only. Pale bone fur, red eyes and rim, dark beak, violet gum. 0 frames changed.
- **C, Bruiser.** Palette swap plus angry brows. Purple fur, pale yellow eyes, scarlet gum. The brows cut the top of
  each eye at a slant. 41 of 63 frames change, 123 tile references change, 111 new unique 16x16 tiles.

Each rival adds 2 sprite columns; two rivals level add 4 sprites per scanline, the same as two computer fliers.

### Rival ranking

1. **B, Bone.** The only variant with a light body, so it is the easiest to tell from both dark player birds at 1x on
   all three skies. Red eyes say enemy with no tile change. Violet gum is far from the pink and green player gum.
2. **C, Bruiser.** The brows are the strongest "angry" signal at 3x, and scarlet gum reads as danger. At 1x the purple
   fur is close to the moon sky and to the player 1 blue, and the brows cost 111 new tiles.
3. **A, Hornet.** Yellow eyes read well, but the charcoal body is close to player 1 on the storm sky, and amber gum
   sits in the colour family of the ember and fire hazards.

## Meter variants

Both sit under the "PLAYER 1" tag in place of the three life dots, on the fix layer. Nine states are shown: 8 fill
steps and empty. At 2 steps or fewer the same tiles take a second, orange palette as a low warning.

- **A, gum tube.** One gum ball icon and four tube cells of two 4 px segments each. 5 fix cells, 4 unique tiles,
  8 colours per palette.
- **B, four double lobes.** Each cell is a double-lobe bubble; each lobe is one step. 4 fix cells, 3 unique tiles,
  7 colours per palette.

Ranking: **A first.** It reads as a level and each of the 8 steps is one clear segment. B matches the bubble shape,
but the lobes read as hearts, so a player can take them for lives.

## Doubts

- No separate player 2 palette exists in the source (`SOOT_PAL_SLOT`: palette 0 player, palette 1 computer fliers).
  The "player 2" bird in every still is the computer palette (red-brown body, green gum). If player 2 gets its own
  palette, the rivals need a second check next to it.
- The task asked for palettes in multiples of 8. The accepted Sootling palettes use 5-bit values expanded to 8 bits
  (for example 41, 82, 156), which are not multiples of 8. `numbers.txt` lists both player palettes snapped down
  to multiples of 8 for comparison; the stills use the accepted values for the players.
- The plan says pool objects have 3 sprites each. Pickups A and C use 2 columns in idle and 2 in the collect effect;
  B uses 1 and 2. All fit, but the collect effect is 32x32 where the idle is 16 or 24 wide.
- Tile counts assume no reuse between frames beyond exact matches and flips. A hand pass can cut the counts (for
  example 8 idle frames in place of 16 halves them, at the cost of smoothness).
- The orange warning palette of the meter is close to hazard colours. It is on the fix layer in the corner, so
  confusion is unlikely, but a white blink is the alternative.
- The plan has two balloons at half gum or more and one below. Neither meter marks the half point; a tick at step 4
  is a small addition if wanted.
- Rival C: the brow placement is automatic (the two largest eye-white areas per frame). 22 frames have no change
  because no eye area passes the size test (blink or turned frames); those frames show the rival without brows.
- The sprites were judged on a still contact sheet and single gif frames, not on the moving gifs.

# Sootling at 32 x 48 with gum design B (drafts, 2026-11-10)

Drafts only. Nothing here is game data and no game code changed. All art is original and drawn by
`draw_sootling_b.py`.

Open `index.html` (dark page, view at 100 percent zoom).

## What was asked

Design B from the previous round (`../2026-11-10-sootling-gum/`) was chosen: one gum membrane with two lobes
blown from the mouth. One lobe pops and the rest pulls round into one bubble. The second pop means fall.
The flier art grows from 16 x 32 to 32 x 48 (2 sprite columns, 3 tile rows). Collision box and physics do
not change: hit box 4 px wide on columns 14..17, feet on row 47.

## The three takes (same concept, different body and membrane rendering)

| Take | Body | Membrane |
|------|------|----------|
| A, Pilot | wide round soot ball, one big ember goggle with strap, visor cap | candy: dark keyline all round, violet inner line on the shadow side, four bands, arc gloss, bounce light |
| B, Bright eyes | tall ball, two big white eyes, goggles pushed up on the cap | glass: dark keyline on the shadow half only, pale inner rim on the lit half, large see-through checker window |
| C, Fuzzball | spiky soot ball, glowing ember eyes, small tilted cap with bobble | thin film: thick saturated rim, pale dithered centre, two small gloss ticks |

Recommended: take A. Its membrane has the cleanest edge on all three moods (on dusk only 6 percent of the
outline has a luminance step under 24) and the solid gum reads at game scale. The eyes of take B have the
most character; A's membrane on B's body is a possible mix.

## Fixes for the weak points of the previous round

- Gum outline contrast: the outer line is now the dark keyline (luminance 10) with the deep gum colour as
  inner line. Mean luminance step against the real backdrop pixels: 64 to 95 (previous round: flat 28 to 47).
- Player pink against the dusk sky: gum ramp moved to a cooler hot pink with violet shadows. Smallest RGB
  distance to the 8 main dusk colours: gum mid 108 (was 86), gum light 131 (was 99).
- Pop droplets: paths that would leave the box are slowed until they fit. Droplets cut by the box: 0.
- Bubble mesh speck: gone. Take A and C have no holes; take B has one large checker window per lobe.
- Cap: back in all three takes.

## Palette

15 colours + transparent, one palette for every frame. Index order 1..15: `o 1 2 3 4 r e f g A B C D E w`
(keyline; fur dark to light; rim; ember dark, mid, light; gum deep line; gum dark to pale; white).
Player to computer is a palette swap of the same tiles: indices 1..14 change colour (gum = 10..14 pink to
lime, fur = 2..6, ember = 7..9, keyline = 1). Index 15 (white) stays.

## Files (per take A, B, C)

- `<take>_sheet_1x.png`: build set, 7 frames (glide2 up2 down2 glide1 up1 glide0 fall), player row then
  computer row, magenta background. `<take>_sheet_4x.png`: presentation copy.
- `<take>_ext_1x.png` / `<take>_ext_2x.png`: extended sheet, 62 frames (flap with two lobes 8, flap with
  one lobe 8, first pop 12, last pop 12, respawn 16, fall 6).
- `<take>_anim_<name>_4x.gif`: flap2, flap1, pop2 (first pop with pull-round), pop1 (last pop), inflate
  (respawn blow-up), fall. Each runs on four crops of the real backdrops.
- `<take>_scene_<mood>_2x.png`: 8 fliers on dusk, moon, storm.
- `compare_old_new_4x.png`: game sheet now (16 x 32), previous round B (16 x 32), the three new takes.
- `numbers.txt`: colours used, unique tiles, dither steps, outline contrast per mood and hazard strip.

## Numbers in short (full list in numbers.txt)

- Colours: 15 of 15 in every take.
- Unique 16 x 16 tiles, flips allowed: build set 36 per take; extended set A 301, B 305, C 304.
- Minimum dither step: A 28.2, B 44.3, C 28.2 (rule: at least 28).
- Membrane never touches the box edge; no droplet is cut.

## Known weak points

Listed per take in `index.html`. The main ones: shapes and shading bands are computed (a hand clean-up
pass is still due), the body fills only the lower third of the box, the tile cost is high, and the dark
keyline is close to the darkest sky patches on clear night and storm.

## Run

    /opt/homebrew/bin/python3.14 -I draw_sootling_b.py [--nogif]

Reads the cached backdrops `bg_<mood>_1x.png` and the previous script from `../2026-11-10-sootling-gum/`,
and `assets/flier/sootling_sheet.png` for the comparison. Writes only into this directory.

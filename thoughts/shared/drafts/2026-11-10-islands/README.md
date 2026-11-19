# Gumbirds islands, draft round 1 (2026-11-10)

Drafts only. Nothing here is in the game, and no file outside this folder was changed.
Open `index.html` in a browser at 100 percent zoom. All files are written by `draw_islands.py`
(run it with `/opt/homebrew/bin/python3.14 -I draw_islands.py`). The measured numbers are in `numbers.txt`.

## The three options

**A, roof chunk.** A piece of brick roof torn loose from a building. A pale stone coping is the standing
line, the brick face below it darkens toward a torn lower edge with rebar stubs. Hard materials only, no
dither. The moving detail is a lantern on a chain under the right end: an 8-frame pendulum, and the lantern
body trails the chain by one pixel at full speed. Mood swaps: terracotta brick (moon), teal slate brick with
warm stone (dusk), ochre sandstone with cold grey stone (storm).

**B, garden slab.** A floating planter. A bright turf line is the standing line, with soil, buried stones
and a rounded root ball below, and grass and blossoms above. Dither is used only in the soil, one row of
teeth between soil shades; every pair is at least 28 apart in luminance (see `numbers.txt`). The moving
detail is 8 frames of hanging vines at both ends, drawn as a wave that travels down the stem and grows
toward the free end, plus the grass on the two end caps bending in the same gust.

**C, airship deck.** A steel deck plate with a hazard band on a see-through truss, held up by a rotor pod
under each end, with a small lamp post above each end. Hard metal, dither only inside the rust blooms. The
moving detail is the two rotors: 8 frames of a two-blade rotor through half a turn, the near blade bright
and thick, the far blade thin and dark, the two pods turning in opposite directions.

## What the files are

- `sheet_<option>_<mood>_1x.png`: build sheet, magenta 255, 0, 255 is transparent. Row 1: left cap,
  middle A, middle B, right cap. Row 2: the eight frames of the left cap. Row 3: the eight frames of the right cap.
- `scene_<option>_<mood>_3x.png`: mock-up of the whole screen. `moods_<option>_1x.png`: the same at true size.
- `zoom_<option>_6x.png`: the centre island on all three backdrops, for close review.
- `anim_<option>_3x.gif`: the eight frames on the moon backdrop, 110 ms a frame.

## Choices I made

- **Box of 32 px height, standing line at row 8.** Rows 0 to 7 hold what stands above the line (grass, lamp
  posts), rows 8 to 15 are the 8 px collision body, rows 16 to 31 are the underside. The art covers
  stage y - 8 to stage y + 23.
- **Real stage table.** The mock-ups place the islands at the eight positions and widths of
  `src/core/stage.c`, camera at 32 px so the two islands on the wrap seam show. The backdrop is the camera 0
  picture from the final background pass, so its parallax offset is not exact.
- **One palette of 15 colours per option on screen**, three in ROM as mood swaps of the same tiles. All
  colours sit on the 5-bit grid.
- **Separation from scenery.** Each option has a near-white standing line and a dark keyline round the solid
  mass; the scenery has neither. The keyline is left off above the standing line so the top stays bright.
- **Light from the upper right**, as in the backgrounds: lit right end, shaded left end.
- **Middle repeats every 32 px** (two middle tiles), caps are 16 px each.

## Findings that need a decision

- **Sprites per scanline.** Each island is one sprite per 16 px of width. With the box two tiles tall the
  centre island (y 140) overlaps the two bottom islands (y 164) on lines 156 to 163: 17 platform sprites on
  one line. With the centre island one tile tall, or moved 8 px up, the worst line has 10. The gameplay
  reserve is 24 a line, and the notes count on 4 spare, so either number needs a change to the reserve or to
  the layout. This is the same for all three options.
- **56 px islands.** The two top islands are 3.5 tiles wide, so the right cap falls off the tile grid and
  needs its own shifted tiles (17 to 28 extra tiles, see `numbers.txt`). A width of 48 or 64 removes that cost.
- **The design document says islands are up to 64 px wide; the stage table has 80, 96 and 112.**

## Weak points that remain

- A: the torn lower edge is an even sawtooth; the brick face is flat at true size; only one end moves.
- B: stones and blossoms repeat every 32 px; most tiles; storm soil is close to the building greys; the
  thin grass above the line is not part of the collision and may mislead by a few pixels.
- C: the open truss lets the backdrop through; closest in material to the scenery; rotors small at true size.
- All: about a fifth to a quarter of the lower edge has less than 24 luminance difference to the backdrop
  below it. The standing line itself is clear everywhere (under 1 percent below 24).
- The page is a dark slate page with plain sans-serif text and amber weak-point lines.

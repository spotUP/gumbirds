# VENT-WARN drafts (2026-11-15)

Drafts only. No game code, asset or build file was changed. Gallery: `index.html`. Rebuild: `/opt/homebrew/bin/python3.14 -I draw_vent_warn.py`.

## Why the current telegraph is missed
The only visual change in ticks 144..215 is the 9x2 px grille on the vent top (body_a frames 1..3, 24 ticks each, `src/core/arc_view.c:13`). The body does not move and keeps its storm-grey colours.

## What is shared by A, B, C
- **Shake**: a hand-written (dx, dy) table, one entry per 2 ticks, 36 entries, three stages (rare tick, steady rattle, hard rattle up to 2 px). Hook: add the offset to `s->x` / `s->y` at `src/core/arc_view.c:15`, indexed by `(t - ARC_VENT_TELEGRAPH) / 2`. Position only: no tiles, no palette words. The hit box does not move (`src/core/arc_elements.c:98-99` uses `e->x`).
- **Red glow**: the vent body gets its own palette line (a copy of storm); entries 1..5 (outline + 4 metal shades) step through 8 hand-picked heat steps (`HEAT` in the script, 5-bit RGB; step 0 is asserted equal to the in-game storm colours). Steps change at warning ticks 0, 14, 26, 36, 45, 53, 60, then flicker 6/7 at 66, 68, 70; cool-down at 40, 50, 60, 70 ticks after launch. **5 palette words on a step frame, 0 otherwise** (budget 112).
  - All vents start at timer 0 and tick together (`src/core/arc_elements.c:24`, `:88`), so one shared line serves every vent on the stage.
  - The storm line itself cannot be cycled: sparks, smoke and the hatch are pinned to it (`tools/import_arcade_sheet.py:42`). So `body_a` moves out of the `storm` pin into a new `vent` group with the same colour order (`tools/import_arcade_sheet.py:42`), `k_arc_anim[ARCV_BODY]` points at it (`src/main.c:557`), the line loads with the others (`src/main.c:1401-1402`), and the step writes go through the same `gfx_pal` call from the arcade element draw (`src/main.c:548` block).
- **Sound**: unchanged, `SC_VENT_WARN` at `src/core/sound_events.c:105`. Timing constants unchanged (`src/core/arc_elements.h:15-17`, `:60`).

## A: shake plus glow
0 new tiles, 0 sprites, 5 words on step frames. Only the two hooks above.

## B: boil bubbles
- 10 frames of 16x16 (10 tiles, `BOIL` grids), frame holds 6,6,6,5,5,5,5,4,4,4,4,3,3,3,3,3,3 ticks (sum 72).
- New piece, built the way the spark is (`src/core/arc_view.c:41-50`): `ARCV_BOIL` in `src/core/arc_view.h:14`, width in `:23`, first frame in `src/main.c:558`, strip row in `tools/import_arcade_sheet.py:20` (pinned to storm, it uses entries 9..12 only).
- Position: x = e->x - 8 + shake dx, y = body top - 15 + shake dy. It is built after the bodies, so it draws behind the body like the spark does: no sprite order change.
- +1 sprite per vent during the warning only.

## C: ember spits (preview of the plume height)
- 6 frames of 16x16 (6 tiles, `EMBER` grids), entries 12..14 of the storm line.
- Three throws at warning ticks 0, 19, 44 reaching 16, 28, 48 px (48 = `ARC_VENT_PLUME_H`, `src/core/arc_elements.h:19`), gravity 0.12 px/tick^2; frame picked by speed. In code this is a 72-entry (frame, height) table generated into `arcade_tables.h`, not maths on the 68k.
- Same piece pattern as B (`ARCV_EMBER`), one ember alive at a time: +1 sprite per vent during the warning only.
- Risk: an ember could be read as a hazard. It is orange and under 6 px; the spark is blue and 10 px.

## Checked against the game art
The script crops body_a and spark_a from `assets/arcade/arcade_sheet.png` and maps every pixel to the storm palette of `arcade_sheet.json` (fails on a miss). Body 32x16, spark 16x16, drawn 1:1 at the positions of `arc_view.c`. New art uses storm entries 9..14 only.

## Not checked
- Free palette line for the vent group and free slots in the `ARC_ELEM_SPRITE` range for the +1 sprite per vent: not measured.
- The GIF runs 2 ticks per frame (30 fps) because browsers clamp shorter delays; the 2-tick shake holds are exact, the loop length is exact.
- The glow tops out orange-yellow rather than pure red; step 4 or 5 as the last step is redder if wanted.

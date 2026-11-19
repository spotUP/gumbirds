---
date: 2026-11-15
topic: Gum burst for the bonus stage nozzles (drafts)
status: draft, waiting for a pick
---

# Gum burst drafts (GUM-BURST)

Drafts only: no game code, no import, nothing committed. Gallery: `index.html`. Source of every pixel: `draw_gum_burst.py`
(hand-typed pixel rows and hand-drawn droplet stamps at hand-chosen positions; no generated shapes, gradients or noise).

## What it replaces

Current effect: `puff_A_1x.png` (thoughts/spot/drafts/2026-11-13-bonus-nozzles), 4 frames of 32x24, 4 ticks each
(`ARC_BONUS_PUFF_FRAMES` 16), drawn by `main.c` at (nozzle x, nozzle top - 24) in 2 sprite columns per nozzle, in front of the nozzle.
It is a flat pink oval that grows and shrinks, with a copy of the collar 9 px above the real one.

## Format (all three variants)

- Frame 32x32 = 2 columns x 2 tiles = 4 tiles per frame (the current 32x24 frame also occupies 2x2 tiles), same 2 sprite columns.
- Drawn at (nozzle x, nozzle top - 24): rows 0-23 above the cap, rows 24-31 overlay the top 8 rows of the cap (same on all 4 nozzles).
  The overlay does the anticipation: gum glow behind the grille, collar lifted 1 then 2 px with an extra rib row.
- Palette: the existing "nozzle" palette (14 colours used) + 1 new gum shadow `#b52984` (5-bit safe) = 15 + transparent. No new palette slot.
  Gum ramp: 180829 outline, 7b1842, b52984 (new), ef4a94, f7a3cd, fff7f0; pop flash fff0a8; sparks ffb02e. Bursts use 12 of the 15.
- Timing at 60 Hz, ticks per frame:

| Variant | Frames | Ticks per frame | Total | Tiles |
|---|---|---|---|---|
| A tight pop | 13 | 3 3 2 2 2 2 3 3 3 3 3 4 4 | 37 (0.62 s) | 52 |
| B big spray | 15 | 3 2 2 2 2 2 2 3 3 3 3 3 3 4 4 | 41 (0.68 s) | 60 |
| C stringy stretch | 14 | 3 3 3 2 2 2 3 3 2 2 3 3 4 4 | 39 (0.65 s) | 56 |

Current puff: 4 frames, 16 tiles. Frames 0-2 (glow, small dome, taut dome) are shared by all variants.

## Variants

- **A tight pop**: dome swells, bursts in a white/yellow star, five droplets fly up in a crown, hang, fall back as teardrops and
  squash on the collar. Centre opens on frame 4, so the rising gum bubble is visible early.
- **B big spray**: a gum jet shoots 20 px up, splits into three big blobs on bowed strands, small droplets fan to the frame edges,
  everything rains back, drips run down the collar sides, the mound in the mouth settles.
- **C stringy stretch**: the gum sticks to the leaving bubble: tent, three strands with windows, hair-thin strands with beads,
  snap with sparks, strands whip outward and fall slack, mound squashes, rebounds and is sucked back in.

## Recommendation: A

A reads at 1x in the first 6 ticks (the star frame is the high-contrast beat), keeps the mouth clear for the bubble, and is the
cheapest (52 tiles, 37 ticks). B is the most spectacular but its jet covers the bubble for 4-6 ticks and it is the longest.
C has the most character but its thin strands are 1 px and get lost against a busy backdrop.

## For the import step (not done here)

- `ARC_BONUS_PUFF_FRAMES` 16 -> total ticks; `main.c` picks the frame with `>> 2`: needs a per-frame tick table
  (like `grabber_frame_ticks`). Draw offset stays top - 24; piece height 24 -> 32.
- `tools/import_arcade_sheet.py` asserts the puff is 128x24 with 4 frames.
- A nozzle that fires again inside the burst restarts it (puff counter is reset on spawn): check the spawn cadence.
- Not checked: the burst over the real bonus backdrop and with the rising bubble sprite (previews use a flat navy background, nozzle 0 only).

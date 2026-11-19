# Gum Trip fix round: rival C brows, rival contrast, gum tube half mark

Drafts only. Nothing under `src/`, `tools/`, `tests/`, `assets/` is touched. Open `index.html` to review.
Every number here comes from `numbers.txt`, which the generator writes.

Regenerate from the repo root:

    /opt/homebrew/bin/python3.14 -I thoughts/shared/drafts/2026-11-10-gum-trip-rival-meter-fix/draw_rival_meter_fix.py

The script reads the Sootling sheet, the fix font palette, the three mood scenes and the storm HUD draft.
It imports no code from other draft folders; the old brow rule and the old tube tile are copied in so that
the "old" side of each comparison is reproduced exactly.

## 1. Rival C Bruiser: brows in all 63 frames

What was wrong: the old rule looked for two open eye whites. It found none in 22 frames (squint and shut
eyes: 17-25, 29-35, 38, 39, 43-45, 49) and only one in frames 26 and 36, where the bubble covers part of
the far eye; there it drew a single brow slanted the wrong way. So 24 frames were wrong.

What changed: one fixed brow shape of 21 pixels (near eye 9, far eye and bridge 12) is placed in every
frame. Columns are fixed (the socket sits on columns 14 to 24 in all frames). The row follows the socket:
the top of the near eye white when the eye is open, two rows above the lid line when the eye is squinted
or shut. The gum bubble and the beak stay in front of the brow.

Checks (read back from `rival_c_sheet_1x.png`):

- Near-eye brow complete, 9 of 9 pixels with the exact index, in 63 of 63 frames.
- Far-eye brow dark or behind gum on at least 11 of 12 pixels in 63 of 63 frames.
- The 39 frames that had correct brows are pixel-identical to the old draft (asserted in the script).
- Largest brow move between neighbouring frames of any clip: 1 px. The brow only moves when the eye does.
- Per-frame table (row, socket state, pixel counts) is in `numbers.txt`.

Cost: 63 of 63 frames differ from the shared Sootling frames, 177 tile references, 156 new unique 16x16
tiles (old draft: 41 frames, 111 tiles).

## 2. Contrast, palette only

Measure: luminance contrast ratio, (lighter + 0.05) / (darker + 0.05), 1.00 is none. Body is fur index 3
(the most used fur colour). Sky is the median pixel of scene rows 16 to 95.

Body contrast against the sky median, old to new:

| Rival | dusk | moon | storm |
|---|---|---|---|
| A Hornet | 1.54 to 2.22 | 1.22 to 2.80 | 1.15 to 2.97 |
| B Bone | 1.95 to 2.05 | 2.46 to 2.59 | 2.61 to 2.75 |
| C Bruiser | 1.50 to 2.11 | 1.19 to 2.66 | 1.12 to 2.82 |

Outline contrast does not move (A 2.81 / 2.23 / 2.10, B and C 2.74 / 2.17 / 2.05). The outline is already
near black; pure black would give 2.96 / 2.34 / 2.21. The gain has to come from the body, and it does.

Rival A against player 1, body tones (CIELAB distance, mean weighted by pixel use): 23.4 to 74.3.
Mid tone alone: 22 to 97. Against the computer flier: 37.1 to 47.9.

Palette changes:

- A Hornet: fur indices 2 to 5 go from blue-grey to charcoal-plum shadow, ochre body, yellow light. Eye
  white (index 6) goes from yellow to cream, because the body is now yellow. Gum (indices 10 to 14) goes
  from amber to orange, so the bubble does not merge with the body.
- B Bone: unchanged. Values only re-expressed in 5 bit units (shifts of at most 7 per channel).
- C Bruiser: only fur indices 2 to 5 change: plum shadow, orchid body, lavender light.

All three palettes hold 15 colours plus transparent, 5 bits per channel, dark bit 0, checked on the sheets.

## 3. Meter A: gum tube with half mark

- 5 fix cells in one row: gum ball icon plus 4 tube cells, 40x8 px.
- 8 fill steps plus empty. Each tube cell holds two 4 px segments. Cell c (0 to 3 from the left) shows
  clamp(step - 2c, 0, 2) filled segments.
- Half mark: a gold bar on the seam between tube cells 2 and 3, 8 px tall (2 px taller than the tube),
  with 3 px caps on top and bottom. It is part of the tiles and always visible. At step 4 the fill ends
  exactly on it.
- At step 2 and below the fill and the icon turn red.
- 13 unique 8x8 tiles: icon 2 (normal, warning), plain cell 5 (empty, half, full, warning half, warning
  full), cell left of the mark 3, cell right of the mark 3.
- 11 colours, all from the `white` palette of `assets/font/fix_font.json` (slots 1, 4 to 11, 13, 15).
  No second palette. No sprites.

## Doubts

- Bruiser's new body is light. It now sits close to the bright dusk clouds in luminance (ratio 1.13
  against the 90th percentile sky pixel; old 3.57). Colour still separates it, but look at the dusk GIF.
  The same holds for Hornet on dusk (1.07).
- Bruiser's body is 20 away from player 1's gum mid tone and 22 from Bone's gum. Those are the closest
  pairs in the set. A more violet body goes to 8 against Bone's gum; a more magenta one to 12 against
  player 1's gum. The chosen colour is the middle.
- Hornet's body against its own orange gum: 44 (old 105). Readable by number, not judged in motion.
- Hornet is now clearly a yellow bird. If the grey hornet look mattered more than the contrast, say so.
- In frames where the bubble covers the far eye (21, 22, 23, 33, 34), only the near-eye brow and part of
  the bridge show.
- Shut-eye frames (20, 32) carry the dark brow wedge above a flat lid. It keeps the brow steady, but the
  face reads heavier than the accepted open frames.
- Brows now cost tiles in every frame: 156 unique tiles for Bruiser alone.
- There is no player 2 palette in the sheet; the computer flier palette stands in for it.
- The warning state uses 5 extra tiles in place of a second palette. If tile space on the fix layer is
  tighter than palette space, swap that back.
- All judgements here are by number. Nobody looked at the GIFs in motion.

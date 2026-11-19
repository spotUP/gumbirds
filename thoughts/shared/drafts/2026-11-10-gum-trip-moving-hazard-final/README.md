# Gum Trip moving hazards: final draft sheets

Final pass on the three moving hazards the user picked ("all of them") from
`../2026-11-10-gum-trip-moving-hazard/`. Drafts only: nothing here is wired into the game, no importer has read
these sheets. Gallery: `index.html`. All measured numbers: `numbers.txt` (written by the script from the sheets).

Regenerate: `/opt/homebrew/bin/python3.14 -I draw_moving_hazard_final.py` (add `--preview` for 4x contact sheets
`preview_*.png`; delete them afterwards). The script reads nothing outside this folder.

## Files

| File | Content |
|---|---|
| `sheet_a_1x.png`, `sheet_a.json` | A Skip-rope squall, 48 x 48, 24 frames x 4 ticks, palette "storm" |
| `sheet_b_1x.png`, `sheet_b.json` | B Flue spinner, 32 x 48, 16 frames x 4 ticks, palette "hot_metal" |
| `sheet_c_1x.png`, `sheet_c.json` | C Cinder, 32 x 32, 24 frames x 3 ticks, palette "hot_metal" |
| `anim_a_3x.gif`, `anim_b_3x.gif`, `anim_c_3x.gif` | Loops at game timing over grey-blue (88, 104, 128) |
| `on_moods_2x.png` | One frame of each kind on the dusk, moon and storm sky colours |

The JSON files follow `assets/flier/sootling_sheet.json`: `source`, `animations` (frame rectangles), `palettes`
(15 RGB triples), `defines`, `tables` (`clip_first`, `clip_count`, `clip_loop`, `frame_ticks`). Added for the hazards:
`defines.HIT_X0/Y0/X1/Y1/W/H`, `defines.LOOP_TICKS` and a `hitbox` object (px relative to the frame). The sheets
have a transparent background (alpha 0), not the magenta key of the first drafts.

## What changed against the first drafts

- Palettes: three private palettes (12 + 12 + 10 colours) became two shared ones of 15 colours. B and C share
  "hot_metal"; A has "storm".
- A: the violet cloud became slate grey with indigo shadows and a warm cream top light. Reason: the moon sky is
  violet (76, 60, 142), the first draft sank into it. Each billow now carries two lumps that overturn around it once
  per loop (outward at the top, down at the flanks). The arc no longer glows all the time: the belly charges blue
  from inside over 13 frames, the rope brightens with it, strikes once under the base, fades in three frames, rests.
  16 frames became 24.
- B: vanes are helical now, so the slots sweep across the globe and the saw fins travel down both silhouettes
  like a barber pole. Foreshortening comes from the sphere (vanes crowd toward the edges). The cap, base ring,
  striped collar with a lit lip and the rust edge are drawn as separate metal parts, no dither anywhere. The chain
  is five links, each a pendulum that lags the link above by 0.55 rad, with the swing growing toward the hook.
- C: the coal is one fixed solid of 16 facets; facets, pits and cracks are stored on the solid and ride with the
  tumble. Cracks sit on facet edges and breathe twice per loop, each with its own phase. The ember ring of the
  first draft is gone; 20 sparks are shed into the wake, cool from pale yellow to red and rise. 16 frames became 24
  at 3 ticks, and the coal grew from about 16 px to about 19 px.
- Outlines: one dark outline colour on the outside of every solid; lightning, glow and sparks have none.
- Loops are closed-form periodic functions instead of the tail of a simulation; the measured seam sits inside the
  range of the other frame steps for all three kinds.

## Weak points still visible

1. A: while the rope crosses the front of the cloud (frames 1 to 6) it is a thin dark blue line over the cloud
   face and reads more like a wire than like lightning.
2. A: in the rest frames the cloud is a plain grey cloud. The danger read then depends on the dark outline and
   the pin sparks. The background cloud planes are also grey; not checked against them in a real scene.
3. B: at 1x the helical slots read as orange and steel diagonal stripes. That is clear as "hot", but one could
   read it as a striped sweet. The globe art repeats after 8 frames (only body rock and chain differ).
4. C: sparks are single pixels and few per frame (2 to 6); on the dusk sky they nearly vanish. A big lit facet
   reads as grey stone for a few frames of the tumble.
5. All three: the shapes come from rendered solids that were then banded and clustered, not from hand-set pixels.
   Edges have some stray single pixels (cloud base, coal rim glow) that a hand clean-up pass would remove.

## Open choices

1. Tile cost of A. Recommended: keep 24 frames (212 unique tiles; the build plan says ROM space is not the
   limit). Other option: 16 frames like the first draft (about 140 tiles), with a shorter charge build.
2. Does the resting rope of A hurt? Recommended: no, only the cloud body hurts (hit box in `numbers.txt`), the
   rope is a warning. Other option: the rope under the base hurts during the strike frame and the fade (4 frames),
   which needs a second hit box in the code.
3. Hand clean-up pass on the three sheets (weak point 5). Recommended: yes, after the first in-game look, so the
   clean-up targets what shows at 1x on the real backgrounds. Other option: import as they are.

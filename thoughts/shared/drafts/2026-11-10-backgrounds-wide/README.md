# Backgrounds, wide arena (plan item C12)

Drafts only. Nothing here is imported into `assets/`. Source of the widths: section 5 of
`thoughts/shared/plans/2026-11-10-wide-arena-camera.md`. Base art: `../2026-11-10-backgrounds-final/` (untouched).

Open `index.html` in a browser at 100 percent zoom.

## What was built

Arena 384 px, camera 0..64 px, plane offset = camera x k / 16. Sway is removed.

| Plane | k | Width final | Width wide | New columns |
|-------|---|-------------|------------|-------------|
| sky | 0 | 320 | 320 | none |
| far | 4 | 336 | 336 | none |
| mid A | 8 | 336 | 352 | 336..351: one art deco house with a roof tank |
| mid B | 12 | 336 | 368 | 336..367: a glass house and an apartment house with a roof tank |
| near | 16 | 320 | 384 | 320..383: a fifth rooftop, cut stone block house, roof tank, antenna, fan, own cast-light table |
| clouds, airship, beams, rain | 0 | unchanged | unchanged | none, own drift |

The widths agree with the plan: "+16 / +32 / +64" are relative to the draft widths 336 / 336 / 320. No contradiction found.

The new houses are drawn by the same building code as the old ones, as new entries at the end of the `MIDA`, `MIDB` and `NB`
tables. They are not mirrored or tiled copies. The stone block material of the fifth near house is new code (`mat == 'block'`).
Animation frame counts and timing are unchanged (8 city frames, 4 sky frames, 16 hazard steps).

## Files

- `plane_<mood>_<plane>_1x.png`: one sheet per plane and mood, transparent colour 255, 0, 255.
- `cams_<mood>_2x.png`: composite at camera 0, 32 and 64.
- `pan_<mood>_3x.gif`: camera 0 to 64 and back with parallax, one pan per loop.
- `numbers.txt`: palettes, tiles, dither steps, sprites per scanline, comparison with the final pass sheets.
- `draw_backgrounds_wide.py`: the generator. Run: `python3 -I draw_backgrounds_wide.py [--nogif] [--only moon,storm,dusk]`.

## Where the old 320 px region is not pixel-identical

- Plane sheets: sky, far, mid B, near, clouds, airship and beams are identical to the final pass sheets over the old width.
- Mid A: 10 pixels differ at x 334..335, sheet rows 38..62, in all three moods. The last old house (x 304..339) had detail that
  the 336 px canvas edge cut off. The wider canvas now draws it complete. Screen x 0..319 at camera 0 is not affected.
- Composites: they are not identical to the final pass scenes. The final pass showed the city planes at plane x 8 plus sway.
  The wide pass shows plane x 0 at camera 0 and has no sway.
- Near cast light: the lit level per 16 px column comes from a percentile over all hazard columns. With 24 columns in place of 20
  the level of an old column can change by one step. This is the dynamic palette choice, not the art.
- Placeholders: islands and fliers are moved (x spread by 1.2).

## Sprite budget (off-screen columns counted, gameplay reserve 24, hazard strip 24 columns, limit 96)

| Mood | Scenery worst | Total worst | Lines | Total with off-screen columns culled |
|------|---------------|-------------|-------|--------------------------------------|
| moon | 65 | 89 of 96 | 128..143 | 84 |
| dusk | 65 | 89 of 96 | 128..143 | 84 |
| storm | 67 | 91 of 96 | 128..143 | 86 |

Storm rain still needs the gap on lines 80..143: without it the worst line is 97 of 96 with every column counted
(92 when off-screen columns are culled).

## Weak points

- The near plane gains one house only. At camera 64 the right fifth of the screen is that single stone house. Its wall is quieter
  than the brick and panel houses.
- Mid A gains 14 visible pixels of one house, so the new house is never seen whole.
- The hazard strip is the accepted 64 px tile repeated 6 times, not new art.
- The planes are not drawn to join at the arena wrap (column 383 next to column 0). The camera range 0..64 never shows that seam.
- Storm has 5 sprites of headroom with every column counted. The rain gap is required.
- The pan GIFs are about 4.6 MB each, because a pan changes every pixel in every frame.
- The budget counts come from this script, not from MAME.

# Gum Trip moving hazards: hand clean-up pass

Draft art only. Nothing here is wired into the game. The sheets in
`../2026-11-10-gum-trip-moving-hazard-final/` are untouched; this folder holds the cleaned-up versions beside them.

Open `index.html` for the gallery (old beside new, animations, sky moods, before and after, numbers).
Rebuild everything with `/opt/homebrew/bin/python3.14 -I draw_moving_hazard_final2.py`
(add `--preview` for contact sheets of every frame; delete them afterwards).

## What changed per fix item

1. **Banding and the rendered look (all three).** No shade is computed per pixel any more. Cloud: every billow is
   three drawn discs (shadow, body, light) placed at half-pixel steps and painted back to front, with a crease where
   one billow sits on another. Globe: every blade is four flat stripes. Coal: one flat tone per facet. Pixel rules
   run after that: no orphan pixels, no 1 px spurs or notches on the silhouette, rim light only on edges that face
   the light. Shadows run to cold indigo, lights to warm cream. Stray pixels per frame fell from 24.5 to 3.5 (cloud),
   67.2 to 37.7 (vent; what is left is rivets, chain links and the collar edge, drawn on purpose) and 12.8 to 6.9
   (coal; what is left is spark pixels). The table `FIXES` in the script takes per-frame pixel corrections; it is
   empty in this pass, the corrections so far are all rules.
2. **Storm cloud.** Darker slate body with a heavy indigo underside, a warm lit rim on the upper left silhouette, a
   near-black outline, and a blue charge glow in the belly that never goes fully out and grows to the strike. The
   rope is now a trail of faint 2 px dashes that travel along it. It hangs only below the base and no longer crosses
   the cloud face. It thickens and turns blue as the charge builds and is a solid white bolt on the strike frame only.
   24 frames kept.
3. **Vent.** Twelve bowed vertical blades on a sphere with true foreshortening (blades narrow toward both edges),
   steel greys only, black slots, a hard highlight that stays fixed to the light and that only the leading edges of
   the blades catch. No dither. Heat is an accent: the torn bottom edge of the collar and one dark red pixel column
   low in the slots. The hazard stripes and the saw fins are gone. The blades advance 5 pitches in 16 frames, so all
   16 globe frames differ (the old sheet repeated after 8). Chain: four links (ring, bar, ring, bar) with a hole in
   each ring; each link lags the one above it.
4. **Coal.** Facets are coal black and cold dark only; grey is left for thin sheen lines on facet edges. More
   cracks, never dimmer than orange red, each with a warm plum or red border. The outline glows red beside a hot
   crack (this replaces the dither halo). Sparks are 2 to 3 px trails (pale core, orange body, red tail) with a dark
   keyline behind and under them.
5. **Kept.** Frame sizes, frame counts, ticks per frame, hit boxes (no change forced), two palettes of 15 colours
   (values changed, see `numbers.txt`), JSON format, one strike frame per loop. Flash numbers are in `numbers.txt`.

## Weak points left

1. The resting trail under the cloud is very faint: 2 px periwinkle dashes. On the moon sky it almost disappears.
   That was the brief (a warning, not a wire), but the warning only reads from about frame 10 of the charge.
2. The cloud top goes flat and boxy in frames 3 to 7 where the upper billows line up. It needs a hand redraw of
   those five frames (the `FIXES` table is the place).
3. The vent globe has no hot rim or sparks any more, so at a glance it is the least "dangerous" of the three. Its
   threat reads from motion and the torn glowing collar only.
4. The coal silhouette is still the convex solid from the first pass. Its tumble is correct but the shape is plain;
   a chipped corner would help.

Not checked: nothing was built, imported or run in MAME, and the animations were judged from contact sheets, not
watched in motion.

## Open choices

1. **Trail at rest: keep it faint (recommended) or make it one step brighter.** Faint keeps the cloud body as the
   only thing that looks solid, which matches the single hit box. One step brighter (colour 9 instead of 15) helps
   on the moon sky but starts to read as a rope again.
2. **Vent heat: steel only (recommended) or a thin hot rim on the base ring.** Steel only keeps it distinct from
   the coal, which shares its palette. A hot ring adds threat and costs no colours.

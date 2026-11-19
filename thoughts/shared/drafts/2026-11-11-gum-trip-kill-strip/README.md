# Gum Trip kill strips: three drafts

Drafts only. Nothing in the build reads this folder. Gallery: `index.html` (A, B and C side by side, then each one in detail). Measured numbers: `numbers.txt`. Source: `draw_kill_strip.py` (run with `/opt/homebrew/bin/python3.14 -I draw_kill_strip.py`; it rewrites every PNG, GIF, `numbers.txt` and `index.html`).

The script paints a test course of 3 chunks of 192 px (576 x 224). Per chunk the window is set by (ceiling, floor) tile rows: (3, 11), (4, 9), (2, 10). This gives a floor step up and a ceiling step down at x 192, and a ceiling step up and a floor step down at x 384, with steps of 1 row and 2 rows. The script then cuts the course into 16 x 16 tiles and deduplicates them, counting horizontal and vertical flips as the same tile. It rebuilds the mock-ups from that tile set and checks that they are pixel-equal to the painted course. Each mock-up is a 320 x 224 crop at camera x 32, so the x 192 join is at screen x 160, on the plain sky tone #161428.

## Variants

| | Idea | Unique tiles | ROM tile cost | Frames | Ceiling |
|---|---|---|---|---|---|
| A Shard ridge | Crimson glass shards on a plum rock crust, outlined. Facets are lit from the upper left. Violet back shards. | 15 (all static) | 15 | static | redrawn natively, so the light stays upper left |
| B Live rail | Steel conduit with amber chevrons and emitter studs on every tile edge. A lime plasma arc crawls stud to stud above the steel. Corner posts with emitters. | 7 (6 animated) | 41 | 8 at 4 ticks; faces 4 | vertical flip of the floor |
| C Boiling gum | Hot pink gum melt. The surface is a damped wave driven by bubble pops. Bubbles rise, dome and pop. The step faces carry a falling film. | 7 (6 animated) | 41 | 8 at 5 ticks; faces 4 | vertical flip of the floor |

ROM tile cost counts a static tile as 1. An 8-frame tile costs 8 (LSPC 3-bit auto-animation). A tile that loops every 4 frames costs 4 (the 2-bit auto-animation bit in the sprite tile map). In B and C the step face tiles use the 4-frame loop. All three variants are under the 48 target.

The rim period is 64 px (4 tile columns) in all three. B and C mirror the rim every 32 px, so the 64 px period costs only 2 rim tiles plus their flips. Every variant uses one palette of at most 15 colours: A uses 15, B uses 13 and C uses 10.

## How the motion is made

- B arc: three pinned, forced, damped strings (two for the top edge, one for the faces). Each string is simulated for 30 loops until it reaches a periodic steady state, so frame 7 leads into frame 0 like any other pair. A per-frame crackle jitter and one forked spark per frame go on top. A lime cast light hits the steel top row where the arc dips low.
- C surface: a 1D damped wave on a 32 px cell with reflecting ends, mirrored to 64 px. Three bubble pops per loop drive it, and it is simulated to a steady state. The body shades follow the surface: 5 bands with checker transitions between neighbours, plus a peach crest and a glint on the wave peaks.

## Hurt line

The hurt line is the window edge. No variant puts an opaque pixel in the window: the measured count is 0, so nothing pokes into the window. The visible art starts slightly below the hurt line. Measured gap from the hurt line to the first opaque pixel on top and bottom edges:

- A: mean 1.8 px, max 4 (between shards)
- B: mean 1.0 px, max 3 (between arc dips)
- C: mean 2.3 px (wave troughs)

## Weak points

- No variant has an inner-corner fillet. Where a face meets the lower rim, the two edge treatments butt together with a small dark crevice.
- B and C step-downs are horizontal flips of the step-ups, and their ceilings are vertical flips. So the steel highlight in B and the gum crest in C are lit symmetrically, not from the upper left. A is redrawn and avoids this, but its ceiling then costs its own tiles: 8 rim tiles in A against 2 in B and C.
- C ceiling bubbles bulge downward (vertical flip). They read as forming drips, not as boiling.
- B leaves the arc zone (the top 0 to 5 px) mostly transparent. The lethal edge is marked by the arc and the glow, not by a solid surface.
- Not viewed by eye. All checks were done by measurement, so the read at game speed and how the colours sit against the three sky moods are unverified.

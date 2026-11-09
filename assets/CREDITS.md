# Credits

## Hero sprites (`assets/hero/guard_sheet.png`, `guard_sheet.json`)

- Source: "Space Police Hero" by Master484 - https://opengameart.org/content/space-police-hero
- Author profile: https://opengameart.org/users/master484
- License: CC-BY 4.0 (also OGA-BY 4.0). Credit line shown in game: "Hero sprites based on Space Police Hero by Master484 (CC-BY 4.0)"
- Source file used: `spacepolice_blue.png` (968x577). The page also offers `spacepolice_red.png` (colour variant) and four preview images; no larger or fuller download exists.

### Changes made (remix for "Roofline")

- Cut a subset of frames out of the source sheet (32 px wide cells): run, run with gun move, run recoil, aim forward + recoil, duck + recoil, jump + recoil, hit, aim diagonal up / up / diagonal down / down.
- Recoloured the whole set to one 14-colour palette (5 bits per channel): blue armour -> dark navy uniform with a cool purple shadow and a lighter rim tone on the upper and right edges, silver armour -> cool steel, inner lines -> near-black ink.
- Cut the shoulder pads down to small fabric epaulettes (pixels removed and recoloured; body drawing unchanged).
- Replaced the helmet with a peaked guard cap with a gold badge and a shaded face on every frame, hit and the four aim angles included.
- Redrew the gun as a chunky police flashlight in every frame that holds it: short tube in the glove, wide head with a steel bezel, cyan-white lens.
- Flashlight re-posed to an overhand grip (run, run shoot, run recoil, aim forward, duck, jump and their recoils): one fist raised by the shoulder, dark tube lying over the fist, steel head and lens forward, no second hand; the free arm swings over the run cycle. Aim angles and hit keep the earlier two-hand hold.
- Added a 1 px near-black outline around every frame (none under the feet).
- Added new sprites (not from the source): a cyan-white laser beam segment and a 4-frame hit flash.

## Obstacle sprites (vent, cable, drone, bot)

- Source: original pixel art by this project, no external asset. Drawn by `tools/draw_obstacle_sheet.py` (Pillow) into `assets/obstacles/obstacle_sheet.png` and `.json`; hand-placed pixel clusters, 15 source colours snapped to 5 bits per channel. No credit line required.

# Logo over three skies

Run `/opt/homebrew/bin/python3.14 -I compose.py`; numbers in `numbers.txt`, gallery in `index.html`.
Sky comes from the camera 0 crop of the wide-background camera sheet (the crop the accepted title used), so it includes islands, fliers and the hazard strip. Logo layer top left at screen x -13, y -8.

Result (still, edge pixels under 1.5 contrast): moon 11.7%, dusk 3.2%, storm 17.9%. Mean ratio about 3.0 / 3.8 / 3.0. Storm is the weakest; it collides with sky colour (28,41,56), moon with (38,37,98), both against the outer line (8,8,24).

Possible fixes (not done):
1. 1 px backing ring in a lighter dark tone (for example violet rim step 115,90,231 is too bright; use a new navy ~ (40,50,90)) around the logo on storm and moon: costs one palette slot (10 of 15 colours used) and about one extra sprite column set; no art change inside.
2. Per-mood logo palette: swap outline colour 8 for a lighter keyline on storm and moon only: costs one extra 16-colour palette entry per mood and a palette swap at mood change; no tile cost.
3. Darken the sky locally behind the logo (a 20 to 30 percent dim band in the sky plane at lines 16..120): costs sky tile changes in two moods and affects the approved backgrounds.

# Logo outline colour per sky mood

Run `/opt/homebrew/bin/python3.14 -I compose_moods.py`; numbers in `numbers.txt`, gallery in `index.html`.
`compose_moods.py` copies the composition and measure code of `../2026-11-10-logo-three-skies/compose.py` unchanged
(the baseline reproduces: storm 17.9%, moon 11.7%, dusk 3.2%) and adds a palette swap, the candidate table, a check over
all 10 animation frames, and the contrast of the new outer line against the logo colours it touches inside.

Palette swap only: same pixels, same 10 palette entries, no tiles. New values are multiples of 8 per channel.

## What the measure showed first

The outer ring of the logo is two palette entries, not one: outer line (8,8,24) is 474 of the 884 edge pixels, drop shadow
(24,8,49) is the other 410. Changing the outer line alone cannot go under about 5 to 6 percent, because the shadow half still
meets dark sky. Mid tones are the worst choice for either entry (30 to 50 percent weak): the sky next to the logo is mid-dark,
so the line must be clearly lighter or stay near black.

## Recommended

| Mood | Pick | Palette change | Weak edge before | after (still) | after (10 frames) |
|---|---|---|---|---|---|
| Storm | S2 grey-green rim, black shadow | outer line (8,8,24) to (160,200,184); drop shadow (24,8,49) to (0,0,0) | 17.9% | 5.0% | 4.4 to 5.8% |
| Moon | M2 moonlight rim, blue-black shadow | outer line (8,8,24) to (160,192,248); drop shadow (24,8,49) to (0,0,16) | 11.7% | 4.5% | 4.5 to 5.6% |
| Dusk | keep current | none | 3.2% | 3.2% | 2.9 to 4.1% |

Reason: the rim takes the mood's own light colour, so it reads as light catching the gum and not as a white sticker line, and
the drop shadow stays dark, so the logo keeps its weight and depth. The keyline (90,16,115) is untouched, so the gum keeps its
dark inner line (contrast rim to keyline 6.5) and the pink ramp is identical on all three moods. The black shadow gains only
about one point over keeping the old shadow (S1 6.1%, M1 5.0%), but it cuts the share of near-invisible edge pixels (under 1.2)
from 3.3% to 1.0% on storm and 3.2% to 0.9% on moon, and it removes the purple shadow tone that sits inside the moon sky hues.
If one changed entry per mood is preferred, S1 and M1 are the fallback.

S3 and M3 have the best numbers (2.4% and 2.8%) but turn the shadow pale too: the logo then sits on a pale slab, loses its
drop shadow and reads like a sticker. Rim against the pale shadow is only 1.5 to 1.7, so the two merge into one blob.

Dusk D1 (apricot rim) measures 1.9% against 3.2%, but the dark line is what makes the pink sit in the warm sky; not worth it.

## Things to know

- The outer line colour is also used for the letter counters (holes in B, R, D, G) and the lines between overlapping letters
  (2891 pixels, only 474 on the outer ring). With a light rim these all turn light: the counters become pale patches. It reads
  fine at 1x in my view but it is the biggest visible change, larger than the rim itself. Fixing it needs a redraw (a separate
  palette index for the counters), which is outside this job.
- Animation: all 10 frames use the same 10 colours; frames differ from the still by at most 716 pixels (the bubble on the I
  grows and shrinks, the drip under the U extends). Width is 303 pixels in every frame, so "widest stretch" is frame 0 by tie.
  Weak edge stays within about one point of the still on every frame. Checked frames 0 and 4 by eye
  (`contact_frames_3x.png`): the rim follows the big bubble and the drip cleanly, nothing breaks.
- The big bubble in frame 4 puts a full light ring next to the moon disc on the moon sky; rim and moon are both pale blue-white
  there. It still separates because of the dark cloud between them, but look at it in the animation.
- Remaining weak pixels after the change are almost all on the shadow side against the darkest cloud bands; no palette value
  fixes those without making the shadow pale.
- The existing logo colours are not multiples of 8 (for example 165, 33, 90); the new ones are, as the brief asks. Whoever
  converts to Neo Geo words should check the converter maps both the same way.
- Gif timing in the gallery is a guess (100 ms per frame).
- Mood change on the title: only 2 colour words change per mood, so the swap can happen in the same blank as the sky palette.

Page design: dark neutral grey page, system sans-serif, flat bordered cards, gold border on the recommended one.

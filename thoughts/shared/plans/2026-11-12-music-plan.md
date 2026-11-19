---
date: 2026-11-12
topic: Gumbirds music plan
status: decided by the user through the question tool (2026-11-12); nothing built yet
related: thoughts/shared/plans/2026-11-09-sound-driver.md
---

# Gumbirds music plan

## Decisions (user, 2026-11-12)

- Source: the user writes every track in DEViLBOX and saves `.dbx` (DEViLBOX's own format). Changed 2026-11-12: no `.fur` step. Pipeline: `tools/dbxtool.py` compiles the `.dbx` into nullsound's stream and instrument data; spec `thoughts/shared/plans/2026-11-12-dbx-neo-geo-export-spec.md`.
- Style: bouncy FM pop with bright leads. Major keys, slap FM bass, bell and brass leads, about 140 to 160 BPM in game, calmer title.
- Channel split: music owns 4 FM, 3 SSG and ADPCM-A channels 3 and 6 (drums: kick and snare on 3, hats on 6). Sound effects keep ADPCM-A channels 1, 2, 4, 5. No effect ever cuts a music voice. ADPCM-B stays unused (free for a later voice sample).
- First step: pipeline proof. One short `.fur` exported from DEViLBOX goes through furtool and a headless sound test before the user writes the full list. DEViLBOX export through furtool is unverified today.

## Track list (all four groups picked)

Loops:
1. Title / attract theme.
2. Arena loop.
3. Gum Trip loop.
4. Name entry loop.
5. Arcade stage loop A (stages 1 to 4), B (5 to 8), C (9 to 12): the mood variants; the stage group picks the loop. Arena may reuse A until its own loop exists.
6. Bonus stage tune.
7. Continue countdown tune (short loop, about 10 seconds of countdown).

Jingles (play once):
8. Round clear (replaces the placeholder WAV "4 Brass fanfare").
9. Game over.
10. Perfect bonus.

Danger variant: a tenser version of the running loop on the last gum or last life. Two ways, to be chosen after the pipeline proof shows what nullsound offers: (a) a second `.fur` per loop with the same length and a switch at a pattern boundary; (b) a tempo change command in the driver. Default until then: (a) for the arena and arcade loops only, and the switch restarts the tune (simplest, no driver change).

Count: 9 loops + 3 jingles + up to 4 danger versions = up to 16 `.fur` files. M1 ROM is 131072 bytes; size per tune is measured in the pipeline proof and the list is cut if it does not fit.

## Open (not asked yet)

- Music start relative to `ROUND nn` / `GO!` (ledger open question). Default: loop starts on `GO!`, round texts play over silence or the tail of the previous jingle.
- Does the title theme play in attract mode with sound off by the MVS soft dip (standard: attract sound is a dip setting)?
- Loop lengths (default: loops 45 to 60 seconds, jingles 2 to 4 seconds).
- Sample set for the two drum channels (user's own samples; 18500 Hz mono for ADPCM-A).

## Work items

- MU1 Pipeline proof: `tools/dbxtool.py` compiles `neo_geo_composer_trial.dbx` (was: user exports one short `.fur`; furtool run); build M1; `test-sound` headless; report size, channel use, any furtool rejects (macro types failed before on converted songs).
- MU2 Music ids and events: one id per track in `music-map.yaml`; events per screen in `src/core/sound_events.h` / `src/sound.c` (title, mode start, name entry, round clear, game over, bonus, continue); stand-in tones until real tracks exist. Own editor, after the current editor order. Collides with the match-end brief (coin sound CS1..CS5, round texts): run after it.
- MU3 Channel rule check: a build step that fails when a `.fur` uses ADPCM-A 1, 2, 4 or 5.
- MU4 Danger variant switch (after MU1 result).
- MU5 Composer sheet for the user: per track length, tempo, key suggestion, channel rule, export steps.

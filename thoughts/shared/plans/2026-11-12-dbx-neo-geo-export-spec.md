---
date: 2026-11-12
topic: Playing DEViLBOX `.dbx` songs on the Neo Geo (Gumbirds) - shared spec for the game side and the DEViLBOX side
status: draft; route proposed by the game session, user picked "spec file, user hands it to the DEViLBOX agent"
related: thoughts/spot/2026-11-12-nullsound-stream-research.md, thoughts/shared/plans/2026-11-12-music-plan.md
---

# `.dbx` on the Neo Geo

## Route

The Neo Geo already has a player: ngdevkit's nullsound (Z80). Furnace songs are not played as `.fur`; two build tools (`nsstool.py -z` for the patterns, `furtool.py --instruments` for the patches) compile the `.fur` into Z80 assembler data that nullsound plays. Evidence with file and line: `thoughts/spot/2026-11-12-nullsound-stream-research.md`.

So no new player is needed. The game build gets its own compiler, `tools/dbxtool.py`, that reads a `.dbx` and writes the same two assembler files. The `.dbx` that DEViLBOX saves today is then the game's music source: "save in DEViLBOX, run `gmake`". There is no `.fur` step and no separate export format to keep in step.

Cost on the console: the same for every route that ends in nullsound (a `.fur` and a `.dbx` of the same song compile to the same kind of stream). An own Z80 player could only win by being smaller or by supporting macros nullsound lacks; that is not measured and would replace a driver whose effects and timing already pass the game's sound test. Not planned.

## What the compiler must map (game side)

- Container: magic `DVBZ`, 9-byte header, zlib stream, JSON `format: devilbox-song`.
- Channels: `.dbx` channels 0..3 to FM 1..4, 4..6 to SSG 1..3. Later: two channels for ADPCM-A 3 and 6 (music drums). ADPCM-A 1, 2, 4, 5 belong to sound effects: the compiler fails the build if a song uses them.
- Timing: nullsound takes a Timer-B tempo from a tick rate in Hz plus a speed (ticks per row). `bpm` and the song's rows-per-beat must map onto that; the mapping is not settled (see questions).
- Order list to per-channel streams; loop point as a jump at an order boundary.
- FM patches: fixed 25-byte block per patch (algorithm, feedback, four operators).
- SSG instruments: per-tick register writes built from the macros. nullsound's tools support volume, waveform/mixer, envelope and arpeggio macros with one loop point; they drop noise-frequency and pitch macros and have no release point.
- Effects: only the ones in use get mapped first; anything unknown fails the build with the pattern, row and channel named.

## Known gaps in the trial song (`neo_geo_composer_trial.dbx`)

- SSG Hat, Snare and Kick use macro codes 0, 2 and 3. If code 2 is the noise frequency (Furnace numbering for the AY family), the stock tools would drop it and the three drums would sound alike. `dbxtool.py` has to write the noise period itself; whether nullsound's SSG instrument format can carry that register is unverified.
- Pattern effect type 12 is the only effect in use (180 rows). Meaning unverified (volume set is the guess).

## Questions for the DEViLBOX agent

1. Field meanings in the row: `effTyp` numbering (what is 12?), `volume` range and the value for "no volume", `note` numbering (which number is C-4?), note-off and empty-row values.
2. Timing: how do `bpm`, speed and rows per beat give the row length in seconds? Is there a tick rate (50/60 Hz) under it?
3. Instrument `furnace` block: is the macro `code` numbering Furnace's (0 volume, 1 arpeggio, 2 duty/noise, 3 wave/mixer, 4 pitch)? What do `loop`, `release`, `mode`, `type` mean when not -1/0? Are operator fields in YM2610 register units?
4. Is the `.dbx` format versioned and stable enough to compile from, or is there a schema file to read?
5. How will ADPCM-A drum channels look in a `.dbx` (sample instruments, sample data inside the file or beside it)?

## Asks for DEViLBOX (none blocks the game side)

- A "Neo Geo (Gumbirds)" check in the editor that warns about what the compiler rejects: channels outside the rule above, macro kinds and effects from the unsupported list, release points on SSG macros.
- A written description of the `.dbx` song JSON (answers to the questions above are enough to start).
- Later, if wanted: the same compiler inside DEViLBOX ("export Neo Geo assembler"). Only worth it once `tools/dbxtool.py` is proven, because two compilers must then stay equal.

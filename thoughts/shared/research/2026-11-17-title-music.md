---
date: 2026-11-17
topic: "Title music missing on integ/beta1 (owner report)"
status: not reproduced
branch: integ/beta1 (c172699)
---

# Title music on integ/beta1: not reproduced

## Verdict
The title music is sent by the 68k, received by the Z80 and played (continuous FM/SSG writes) on integ/beta1 HEAD
in every headless case tried. No code cause found. The owner's MAME window (pid 61717) was started 2026-11-16 23:37,
before the current ROM was built (build/rom/gumbirds-p1.p1 00:24 on 11-17), so it runs an older build.

## Static comparison main vs integ/beta1
- Sound driver, assets/sound, music map and Makefile sound rules: unchanged (`git diff main integ/beta1 --stat`).
  build/rom/gumbirds-m1.m1 and -v1.v1 are byte-identical between the owner's build and a fresh build of HEAD.
- src/sound.c: unchanged. src/core/sound_events.c: only the HUMANS[] refactor (flaps/lives arrays); SE_TITLE line identical.
- main.c: bios_user_mode now stays 2 in FLOW_SAVE_REMINDER (bf483f7); SYSTEM_RETURN paths (main.c:1959-1962, 2044-2047)
  return before sound_frame on the first attract frame, but se_step catches the edge on the next frame.
- No other sound_music/sound_stop caller (grep src): nothing overrides title music.

## Runtime evidence (scratch worktree of integ/beta1, SDL_VIDEODRIVER=dummy, -sound none, Z80 io taps)
Z80 commands as frame:cmd; SND_MUSIC_TITLE = 4, arena = 5, game over = 7, 3 = driver reset.
- `make test-sound` (nullbios + unibios40): PASS, title_music sent, read by Z80, FM writes in the music window.
- Boot, nullbios, 1500 frames: `46:3 48:4`; FM writes every second (146..550/s) to the end.
- Boot, unibios40, fresh nvram: `... 416:3 418:4`; FM writes from 6 s on (228..612/s) to the end.
- Boot, unibios40, copy of the owner's nvram/neogeo_16/saveram: `... 376:3 378:4`; same continuous FM writes.
- Full arcade run -> game over (7) -> name entry -> title (unibios40, probe from tests/mame/title_pause_check.lua):
  BIOS return `4852:1 4852:3 4852:3`, then title music `4898:4` after it; FM writes 77..262 per 30 frames afterwards.
  The BIOS reset comes before the title command, so it does not cut the music.

## Side finding
tests/mame/title_pause_check.lua pokes last_score at g_flow+22; Flow gained `Ai demo_ai` and `last_score[2]` on beta1,
so the poke misses and the run ranks ("FAIL ranked: score poke missed"). make test-title-pause is broken on beta1;
fix: read the offset from the build (offsetof probe / nm) instead of the hard-coded 22.

## Not tested
- Title reached after a coin is in (credit_hold title), after the PARTY how-to demo, after the save reminder return.
- Audible output (all runs -sound none); the owner's live MAME mixer/volume.

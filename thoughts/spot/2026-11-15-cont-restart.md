---
date: 2026-11-15
topic: game restarts by itself after the arcade continue countdown runs out
branch: fix/cont-restart
status: fixed, gates below
---

# Continue countdown runs out, a new game starts with no Start press

## Repro

UniBIOS 4.0, two coins, one Start, lose every life, no press on the continue
screen. New check: `make test-arcade-contout` (tests/mame/arcade_check.lua,
`ARCADE_CONT_OUT=1`, `ARCADE_COINS` default 2, check A7).

Before the fix (BIOS RAM read every frame from the continue screen on):

```
+600 flow 4 (GAME_OVER) credit 01 umode 2 comp 00/00
+780 flow 0 (title)     credit 01 umode 1 comp 00/00
+781 flow 3 (PLAYING)   credit 00 umode 2 comp 00/00
```

One frame after the title shows, the BIOS takes the left-over credit and
forces PLAYER_START. player_start accepts it, so a game starts with no press.

## Cause

The compulsion timer (0x10FDDA seconds / 0x10FDDB frames) reads 00/00 for the
whole game. The BIOS reloads it only when the cart hands control back with
SYSTEM_RETURN. MVS games SYSTEM_RETURN at every game end. This cart never did
(it returned only when backup RAM needed a save). So at the first mode-1
frame with a credit and a timer of 0, the BIOS forced the start at once.

First fix try (set g_bram_unsaved on GAME_OVER, so the existing attract-frame
return runs) did not work: that return is at the loop end after
gfx_wait_vblank, and the BIOS vblank already saw mode 1 with the stale timer
and forced the start in that same vblank.

## Fix

src/main.c game_loop: `g_game_ended` is set while the flow is GAME_OVER. On the
first frame the flow is back in attract (title/table/demo), right after
flow_step and before any vblank, game_loop returns while BIOS_USER_MODE is
still 2. ngdevkit then does SYSTEM_RETURN, the BIOS reloads the timer and
calls USER again, and rom_title resumes the loop (same path as the backup RAM
save). Name entry stays inside the loop, the return comes after it.

After the fix:

```
+780 flow 0 credit 01 umode 2 comp 00/00   (return to the BIOS)
+781 flow 0 credit 01 umode 1 comp 30/3b   (timer reloaded: 30 s)
... title -> table -> demo, timer counts down ...
+2602 flow 3 credit 00 umode 2 comp 00/00  (BIOS compulsion start, 1822 frames = 30.4 s)
```

This now matches the one-coin case test-unibios `d` already accepts: with a
credit and no press the UniBIOS title timer forces a start after about 30 s,
credit and game together. A7 passes only when the timer was reloaded (peak at
least 25 BCD s), the start came at least 1500 frames into attract, and one
credit went with it.

## Open design call (not done)

On MVS the forced start is fair because games show the compulsion countdown
on the title while credits are in. This cart does not: with a credit it keeps
cycling title -> table -> demo and shows no timer, so the forced start still
looks like a surprise to the player, 30 s later instead of at once.

Options:
1. (Recommended) While credits are in, hold the title and show PRESS START plus
   the 0x10FDDA seconds countdown, as MVS games do. Touches flow + title view.
2. Leave as is: 30 s forced start, no countdown shown.
3. Refuse a forced start in player_start (no Start press seen). Not possible
   cleanly: the BIOS has already taken the credit when it calls PLAYER_START,
   so refusing loses the credit (test-unibios `d` note says the same).

## Side effect: coin during attract after a game end

With the game-end return, the BIOS runs attract under USER_REQUEST 2 and a coin
re-enters the cart with USER 3 (the same black re-entry the first coin already
had: 30 black frames, +3..+32). The loop is back and on the title about 44
frames after the coin (was under 8 before). test-unibios `a` now reads the flow
state at +60; the `settle` step now waits up to 2400 frames for the 30 s BIOS
compulsion start (it used to expect a start at once, which was this bug).

## Gates (all on fix/cont-restart, UniBIOS 4.0 where the target uses it)

- host suite: OK
- build: OK
- test-arcade: PASS
- test-unibios: PASS (all verdicts; `d` 29.2 s BIOS title timeout unchanged)
- test-reach: OK
- test-vblank: OK (outside-vblank writes 0)
- test-arcade-contout (new): PASS, compulsion start 1822 frames into attract,
  timer peak 30 BCD s, one credit taken. Before the fix it FAILs (start 1 frame
  into attract, timer 00).
- No host test added: the change is in src/main.c (BIOS glue), not src/core.

## Unverified

- Real MVS hardware and the AES/MVS stock BIOS: only UniBIOS 4.0 in MAME ran.
- The one-coin variant of the contout path (ARCADE_COINS=1, no credit left):
  not run; nothing forces a start there.

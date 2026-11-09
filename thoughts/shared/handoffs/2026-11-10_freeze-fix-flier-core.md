---
date: 2026-11-10
topic: Final-death freeze fix, CRT shader path, flier physics core
tags: [handoff, unibios, flier]
status: draft
---

# Handoff 2026-11-10

## Tasks
- Done (uncommitted): UniBIOS freeze at final death with a credit left. Root cause: hero_and_mode
  (src/main.c ~357) set BIOS_USER_MODE 1 on entering GAME_OVER; UniBIOS then stopped calling the
  VBlank callback and game_loop spun in gfx_wait_vblank. Fix: mode 2 through GAME_OVER, NAME_ENTRY,
  SAVE_REMINDER; 1 only in attract. Regression: make test-unibios two-coin phase (FAIL before:
  0 of 600 frames; PASS after). make test-reach PASS.
- Done (uncommitted, unverified): Makefile ROOFLINE_WINDOW_FLAGS gets -artpath brew share/mame/artwork
  so crt-geom-deluxe finds aperture PNGs. Check the make run log has no "Unable to load chain".
- Done (uncommitted): flier physics core src/core/flier.[ch], tests/host/test_flier.c (2107 checks,
  no div/long multiply on m68k). Not wired into the game.
- Earlier this session (uncommitted): PLAYER_START crash fix, scroll distance base (test-scroll),
  test-sound fix.

## Critical references
- Spec: thoughts/shared/research/2026-11-09_flier-reference-spec.md (reference is the spec; side
  edges bounce, user decision 2026-11-10).
- Ledger: thoughts/spot/todos.md (trust over memory).
- Flier choices: 8-term flap lerp, gravity before flap, knockback along fighter line, max 3
  balloons, no refill, caller passes floor each frame.

## Next steps
1. User human test in a fresh make run: 2 coins, die, game keeps running; CRT shader visible.
2. Wire flier into the game (replace runner in src/core/game.c path), reachability MAME test
   through the real entry point (coin, start, flap, death by water at y=180).
3. Then ask trip mode questions (only once the engine runs).
4. Open: name entry has no timeout (cabinet left stuck on name entry); uneven scroll steps
   (user decision); 120 Hz display hitch theory unverified.
5. Commit only when the user asks.

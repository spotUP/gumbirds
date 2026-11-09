---
date: 2026-11-09
topic: Screen flow state machine and 8-character name entry (P3.2, P3.3, P3.4, P3.5, P4.1)
tags: [core, flow, nameentry, hiscore, attract, tests, knobs]
status: draft
---

# Flow and name entry

Files: src/core/{nameentry,flow}.[ch], new knobs at the end of src/core/tuning.h and in tests/host/knobs.txt, tests/host/test_flow.c, flow section in tests/host/knob_digest.c, run.sh builds and runs test_flow. Existing core behaviour is unchanged (game, rng, hiscore untouched).

## Result

- Host: tests/host/run.sh passes: test_core 3859 checks, test_flow 36171 checks, 59 knobs each proven to move the digest (12 new).
- m68k: nameentry.c and flow.c compile with the required flags, no warnings. Unresolved: __udivsi3 (libgcc), memcpy (struct copy in ranks(); ngdevkit libc), plus core functions.
- Not wired into main.c or the Makefile (other job).

## Decisions

- Direction bits live in nameentry.h: IN_UP 0x10, IN_DOWN 0x20, IN_LEFT 0x40, IN_RIGHT 0x80 (buttons stay IN_A..IN_D from game.h). main.c must map the Neo Geo joystick to these.
- Symbol order: A-Z, 0-9, space, '.', END (39 symbols, wraps). Up goes forward, down goes back. Each position remembers its symbol so B then A keeps the old choice. Up wins if both are held.
- A on a symbol confirms and advances; A on END finishes with the characters confirmed before the cursor; the 8th confirm finishes. B steps back one and blanks that position (not at position 0). Edges come from the raw held byte inside nameentry.
- Auto-repeat: first step on the press, repeat after NAME_REPEAT_DELAY held frames, then every NAME_REPEAT_RATE frames.
- Timeout: NAME_TIMEOUT_FRAMES (1800) of frames with the whole input byte zero. Any held input restarts it, so a stuck button blocks the timeout. It keeps the confirmed characters. If none were confirmed (also END at position 0) the name is "PLAYER  " (NAME_ENTRY_DEFAULT) so the table never gets a blank row.
- Flow input contract: flow_step(f, input, start_pressed, frame_counter). start_pressed is a one-frame event from the BIOS credit path. Seed for a real game and for the demo is the frame counter at start / demo begin.
- Cycle: TITLE (420) -> TABLE (480) -> DEMO (900 or demo game over) -> TITLE. Start works on title, table, demo. Start is ignored on game over, name entry and the reminder.
- Demo: same game_step, scripted input from its own Rng (fire held, random jump presses, duck bursts). It only returns to the title; it has no path to hiscore_insert or dirty, and last_score is not updated. Tested with a demo score forced to 900000.
- Game over: GAMEOVER_FRAMES then name entry if the score ranks, else title. Ranking is decided by trying hiscore_insert on a copy of the table, so the tie and zero rules stay in hiscore.c only.
- After the entry: insert, dirty = 1, SAVE_REMINDER (REMINDER_FRAMES, text "open the MiSTer menu before power-off" is the renderer's job), then the table screen with highlight = new row, cleared when that screen ends or a game starts.
- Save contract: the flow only sets f.dirty. The platform serialises f.table with hiscore_serialise, writes backup RAM, clears dirty. The tests' save path does exactly that and counts saves (sentinel).
- Operator reset (P3.4): on the title screen only, hold A+B+C+D (FLOW_RESET_COMBO) for RESET_HOLD_FRAMES (180 = 3 s). Table goes to defaults, dirty = 1, reset_flash = 1 until the title ends. Fires once per hold; release re-arms. Any state change clears the hold. Start is ignored while all four are held. View exposes reset_progress 0..100 for a progress bar. The hold must stay shorter than ATTRACT_TITLE_FRAMES or the title ends first.
- View: flow_view() fills a FlowView of const pointers (table, game, entry) and scalars. No drawing code.
- New knobs (12): NAME_REPEAT_DELAY, NAME_REPEAT_RATE, NAME_TIMEOUT_FRAMES, ATTRACT_TITLE_FRAMES, ATTRACT_TABLE_FRAMES, ATTRACT_DEMO_FRAMES, DEMO_JUMP_ODDS, DEMO_DUCK_ODDS, DEMO_DUCK_FRAMES, GAMEOVER_FRAMES, REMINDER_FRAMES, RESET_HOLD_FRAMES. The knob digest now also runs a 120000-frame flow session (attract, demo, real runs, mash and idle name entries, reset combo) after the existing game run.

## Open items

- Durations are first guesses (60 fps assumed; the Neo Geo runs about 59.2).
- The Flow struct embeds a Game (about 350 bytes) plus a table copy; fine for work RAM.
- 16-bit modulo in the auto-repeat and 32-bit divide in flow_view (reset_progress) may pull libgcc helpers on the 68000; view runs once per frame at most.
- Reachability through the real entry point (main.c, MAME) is not done; main.c must call flow_step each frame, map joystick bits, pass the BIOS start event and write backup RAM on dirty.

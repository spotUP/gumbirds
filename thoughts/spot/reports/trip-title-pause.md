# Title pause after a Gum Trip run

Measure: `make test-title-pause` (tests/mame/title_pause_check.lua, UniBIOS 4.0), run end = PLAYING -> GAME_OVER.

Before the fix (title->live = frames in state TITLE until the flow timer advances):
- Gum Trip: 104 frames. Arcade: 55 frames.
- Of those, 55 are the BIOS return after a run (SYSTEM_RETURN, backup RAM save; g_frame_counter does not advance, same for both modes,
  known from BLACK-SCREEN-3). The other 49 Gum Trip frames are game frames held.

Cause: the title fades its next mood (game_next_mood in flow.c, each attract loop) through bg_set_mood. `g_bg_paused = g_bg_hold && bg_pending()`
(src/main.c) also froze flow_step on the title: g_bg_hold is BG_HOLD_FRAMES whenever the state is not a world state, and bg_pending() is
true for the whole fade out / swap / fade in. The pause exists for the Start that enters a world (fcbf961), not for an idle title.

Fix: on the title the flow only waits when `start` is set (a Start or A credit taken, including a latched g_start_pending).

After: held game frames 0 for Gum Trip and arcade; over->live 235 both (180 Game Over text + 55 BIOS return).
The test asserts held game frames <= 30.

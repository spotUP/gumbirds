# GAMEOVER-BLACK-GAP

Method: `BRAWL_TRACE=<file> gmake test-black-screen` (tests/mame/black_screen_check.lua) logs distinct colours per frame after Game Over, Gum Trip, UniBIOS. Frames at 60 per second.

## Measured (Gum Trip; frame 0 = flow leaves GAME_OVER)
| Run | BIOS blackout (one colour) | First visible frame | Our part: visible start to title settled (g_bg_mood_busy 0) |
| --- | --- | --- | --- |
| 1 credit left, before | 835..~894 (59 f) | +63 | 45 f (settled +108) |
| 2 credit left, before | 1227..~1286 (59 f) | +64 | 45 f (settled +109) |
| 3 no credit, before | 1764..1811 (47 f) | +51 | 45 f (settled +96) |
| after the fix | unchanged (BIOS) | +63 / +63 / +51 | 12 f (settled +75 / +75 / +63) |

Cause of our part: the BIOS return re-runs init (bg_init), which restores the old mood; the flow already wants the title mood, so bg_set_mood ran a full visible fade: 16 out, tile swap, 16 in. The screen was already black from the BIOS, so that fade was pure wait.

Fix: after bg_init in the init path, `bg_set_mood(g_flow.game.mood, 1)` (cut swap at full colour, planes hidden while the strips are rewritten, 12 frames). The logo stays hidden while bg_dark() (GAMEOVER-LOGO-FLASH unchanged). One init path serves every mode that returns to title (Gum Trip, arcade, arena), so there is no per-mode code.

Not fixable by us: BIOS palette clear / video_init, 47-59 frames (about 1 s). The owner's 1-3 s = ~1 s BIOS + ~0.75 s old fade (gone) + the 3 s Game Over screen itself in play (no credit: 180 f state 4 in test).

Arcade was not frame-measured separately (same resume path, covered by test-arcade as a gate only).

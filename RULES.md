# Roofline - project rules

Original Neo Geo MVS homebrew (ngdevkit, C, SDCC Z80 + m68k gcc). Target: MiSTer Neo Geo core on a cabinet.
Plan: ~/.claude/plans/buzzing-kindling-heron.md. Toolchain notes: thoughts/shared/research/2026-11-09_p0-toolchain.md.

## Commands

Run from the repo root. Use `gmake` (system make is 3.81). First build writes config.mk via tools/gen_config.sh (needs `brew install pillow`).

- Build: `make`  (romset in build/rom/, zip build/roofline.zip)
- Run in MAME (window, MVS, hiscores in nvram/): `make run`  (MAME has no window-title option. Exemption from the window-title rule, user decision 2026-11-09: a session that starts a MAME window says in chat which window it is and what for. Headless test runs have no window.) MAME shows "one or more ROMs ... incorrect" at boot: expected, the BIOS is ngdevkit nullbios and its checksums are fixed inside MAME. Press any key. make run boots UniBIOS 4.0 from UNIBIOS (default ~/Downloads/uni-bios-40.zip, never copied into the repo; falls back to nullbios if missing). make test uses nullbios, except test-reach, which runs on UniBIOS 4.0 (REACH_BIOS_FLAGS): stock nullbios writes backup RAM without REG_SRAMUNLOCK, so no high score saves under it (found 2026-11-09). Headless test MAME runs also need `SDL_VIDEODRIVER=dummy -video none -sound none` (user report 2026-11-09: test runs opened MAME windows). sfix/sm1 still come from nullbios, so the warning stays. User decisions 2026-11-09. Window uses bgfx with CRT shader crt-geom-deluxe (user pick 2026-11-09) and no bilinear filter; switch with `make run MAME_SHADER=crt-geom` (or `unfiltered`, `lcd-grid`, `hlsl`). User report 2026-11-09: image was blurry. Headless test MAME runs use `-window -nomaximize -video none`: on macOS `-video none` alone opens a black fullscreen window over the desktop (user report 2026-11-09). Every hand-run MAME command adds `-window -nomaximize`.
- Test: `make test` = tests/host/run.sh, then headless MAME Lua check (tests/mame/boot_check.lua, ~40 s): frame counter g_frame_counter advances, flow leaves ATTRACT after coin + start, BIOS_USER_MODE is 2 while PLAYING, a second coin mid-play keeps the counter monotonic and the state PLAYING; then tests/mame/check_hero_pixels.py (python3.14 -I, Pillow; arg order hero obs city pre play) checks hero-only palette colours in the flier screen box in the MAME snapshots (none before start). Arena: `make test` runs host tests, test-flier, test-reach, test-vblank, test-scroll, test-sound, then the boot check (laser, hit and obstacle checks were retired with the runner, 2026-11-10); the hero pixel box sits on the middle island at the flier spawn (player and computer fliers draw the Sootling sprite: palette 0 player, palette 1 computer; frame choice src/core/flier_view.c; flier_check.lua asserts Sootling tiles via g_soot_range; check_hero_pixels.py min 100 player-only pixels, attract shows the demo flier so pre-start is unbounded).
- Flier art: assets/flier/sootling_sheet.png (+ .json), built by tools/build_flier_sprites.py (run by make). Swap art from a draft sheet with `python3.14 -I tools/import_flier_sheet.py <sheet_1x.png>` then `gmake` (draft generator: thoughts/shared/drafts/2026-11-10-flier/gen_v5.py, user pick Sootling v5 2026-11-10).
- Sprites: hero and obstacles share tools/sprite_pipeline.py (wrappers tools/build_hero_sprites.py, tools/build_obstacle_sprites.py, run by make). Obstacle art is redrawn by `python3.14 -I tools/draw_obstacle_sheet.py` (writes assets/obstacles/). City background: tools/build_city_sprites.py (run by make) from assets/city/ (redraw with `python3.14 -I assets/city/draw_city.py`); tests/mame/check_bg_pixels.py checks backdrop, layer bands, measured scroll against g_bg_scroll_px and the g_bg_column_writes sentinel (snapshots bg_a.png frame 420, playing.png frame 450). Sprite slot map: src/sprite_slots.h; VRAM tile map: src/vram_layout.h. Snapshots are copied to build/test-snap/. Scratch dirs build/test-run.*
- Flier: `make test-flier` (also run by `make test`, ~40 s): tests/mame/flier_check.lua (layout from tests/mame/flier_probe.c) drives coin, start, flaps with A, steers off the island with left/right and drowns; sentinel Game.flier_steps must track the PLAYING frames (src/core/game.c game_step_arena). Removed with the runner (user decision 2026-11-10): test-laser, test-hit, check_obstacle_pixels.py; no jump, duck, laser or obstacles in play. Attract demo hovers and sweeps (src/core/flow.c demo_input; knobs DEMO_HOVER_Y, DEMO_SWEEP_FRAMES).
- Scroll: `make test-scroll` (also run by `make test`, ~90 s): tests/mame/scroll_check.lua plays coin, start, flaps, walks off the island, game over and a second run, keeps a Lua shadow of LSPC VRAM and asserts every PLAYING frame that each city ring (sprites 26/47/68) shows the scroll the game committed at that vblank (no late ring words, no skipped steps) and that g_bg_scroll_px never changes in play (the city is still in the arena). Sentinel g_bg_rebases dropped (distance is always 0). Per-frame log: `make test-scroll SCROLL_LOG=<file>`.
- Reach: `make test-reach` (also run by `make test`) plays to game over, types a name and checks the save; it also asserts the name entry countdown (sentinel g_name_seconds_shown must follow entry.idle rounded up to seconds and start at NAME_TIMEOUT_FRAMES / 60 = 60; 60 s timeout saves the typed letters, user decision 2026-11-10).
- Test (UniBIOS): `make test-unibios` = headless MAME under UniBIOS 4.0 (tests/mame/unibios_check.lua, ~30 s): palettes (text, hero, city, backdrop entry 4095) survive the real-BIOS coin re-entry (real BIOSes clear palette RAM before USER command 3; nullbios does not, so make test cannot see it). Second phase: with two coins, a hero death and a credit left, g_frame_counter must keep advancing (>=90% of 600 frames, no 60-frame stall), flow must reach attract, and a start press must begin a second game (regression for the BIOS_USER_MODE 1 freeze, 2026-11-10). Needs the UNIBIOS file; run it after any change to the boot/resume path or video setup in src/main.c.
- Sound: `make test-sound` (also run by `make test`, ~40 s): tests/mame/sound_check.lua drives coin, start, a flap (A press edge, SE_FLAP plays the jump sample), walk off the island to game over; asserts 68k sentinels g_sound_sent/g_sound_last, Z80 command port reads and YM2610 key-on/FM writes agree per event (coin, music, flap, stop, game over). Hit and laser samples have no game event in the arena. One clean `gmake` builds nullsound M1/V1 from source (CUSTOM_GENERATE_TARGETS=sound-gen); after changing tools/make_sfx_placeholders.py or tools/make_standin_fur.py run `gmake generate`. Z80 io taps must span 0x0000-0xffff (in/out put register A on A8-A15); key-on bits come from build/snd_commands.inc (yaml channel is 1-based). Protocol notes: thoughts/shared/research/2026-11-09_sound-driver.md.
- Package for MiSTer (.neo cabinet file): `tools/package_mister.sh`  (output build/mister/roofline.neo)
- Clean: `make clean`
- Type-check / lint / format: none (C project; build with -Wall).

Test runners: `nice -n 19`, one at a time (global rule 6a-1).

## URLs

None (no web UI). Live test = MiSTer cabinet, see plan P1.3 / P5.2.

## Layout

- src/ C sources; assets/ art/sound sources; tools/ scripts; tests/ MAME Lua + runners
- thoughts/shared/{research,plans,handoffs,prs}; thoughts/<user>/ is git-ignored
- design/ is draft HTML (owned by the design session, do not edit from toolchain work)

## Rules

- No emojis. Full English words in on-screen labels.
- Reachability: a feature is done only when a headless MAME test drives the real game entry point.

---
date: 2026-11-09
topic: P0 toolchain setup - ngdevkit install, hello-world, MiSTer packaging
tags: [neogeo, ngdevkit, mame, mister, neosdconv, p0]
status: done-except-cabinet
---

# P0 status

- P0.1 DONE (not committed): git init, .gitignore, RULES.md, CLAUDE.md, thoughts layout.
- P0.2 DONE: ngdevkit 0.5+202611061802-1 and ngdevkit-toolchain installed (source build of the cross toolchain, ~35 min). `brew install` exited 1 only after install (trailing Python upgrade notes); packages are present. SDCC is `z80-neogeo-ihx-sdcc`; nullsound at /opt/homebrew/share/ngdevkit/nullsound_driver.ihx and z80-neogeo-ihx/lib/nullsound.lib. Plain `sdcc` is not on PATH.
- Gotchas: examples/Makefile need Python with Pillow. `brew install pillow` puts it in python3.14 only; the framework Python 3.9 has none. tools/gen_config.sh writes config.mk using python3.14 (override with PYTHON=). ./configure from ngdevkit-examples is not needed in the repo. The gngeo hash step fails without gngeo; Makefile sets HASH_GNGEO= to skip it.
- P0.3 DONE: example 01-helloworld built and booted headless; then repo skeleton (Makefile, build.mk, emu.mk, rom.mk, setup/ngdevkit-assets copied from 00-template, src/main.c prints ROOFLINE on the fix layer). `make` builds build/rom/roofline.zip; `make test` boots in MAME. Proof: `Average speed: 1539.81% (9 seconds)` then `[OK] MAME booted roofline headless for 10s`. MAME prints BIOS CRC mismatch warnings (sp-s2.sp1, sm1.sm1, sfix.sfix) because ngdevkit ships its own open-source BIOS in build/rom/neogeo.zip; expected, not an error. Fix-layer text correctness was NOT checked visually (human/snapshot check pending).
- P0.4 DONE for packaging: `tools/package_mister.sh` produced build/mister/roofline.neo (6033408 bytes) with neosdconv 1.0.2 on Node 24. Boot on MiSTer UNVERIFIED.

# MiSTer packaging

- Format: NeoSD `.neo`, via neosdconv 1.0.2 (npm; repo URL in npm metadata is github.com/city41/neosdconv, which returns 404 via the GitHub API today; the npm tarball was fetched and its README and lib read). Last npm modify 2024-07-01.
- neosdconv input dir: files matching `<text>-<p|s|m|v|c><n>.<type><n>` (e.g. `roofline-p1.p1`) or `*<type><n>.rom|.bin`. This matches ngdevkit's rom names (verified by reading lib/buildNeoFile.js).
- Command: `npx --yes neosdconv@1.0.2 -i build/rom -o build/mister/roofline.neo -n Roofline -g Other -y 2026 -m Roofline` (wrapped in tools/package_mister.sh).
- Install location on MiSTer: /media/fat/games/NeoGeo/ (from core README, see 2026-11-09_mister-neogeo-platform.md).
- UNVERIFIED: that neosdconv output from ngdevkit ROMs boots on the MiSTer core; whether a ROM with a 1 MB P is accepted; GitHub availability of city41/neosdconv source (npm package only); behaviour with the core's current version. Test on cabinet (P1.3).
- neosdconv ran fine on Node 24 (verified).

# Update: examples verified, main.c not yet written (agent run)

- Example 01-helloworld and 16-sound-music built (scratchpad copies) and booted headless in MAME 0.286. Proof of boot without snapshots: Lua `manager.machine.screens[":screen"]:pixels()` still works with `-video none` (320x224); distinct colour count was 3 for hello (matches its palette) and 6 for example 16. Palette RAM reads (0x400000) and CURPC are NOT usable as proof.
- MAME run form: `mame -noautosave -skip_gameinfo -hash build/rom -rp build/rom neogeo -cart1 <game> -video none -sound none -seconds_to_run N -autoboot_script x.lua`. Needs `make bios` first (copies neogeo.zip/aes.zip into build/rom), else "Required files are missing".
- Example builds: gngeo hash failure (use HASH_GNGEO=); `-j2` raced on base-sound-driver.ihx link (re-run serially or avoid -j on that step); PYTHON must be a Python with Pillow (python3.14); sox missing for example 16 sfx (brew install sox, or generate the wav with ffmpeg).
- .fur versions: example starship-battle.fur is version 213 and builds. furtool decompresses (zlib), checks magic `-Furnace module-`, reads u16 version; <=240 takes read_module_pre240, >240 takes the INF2/INS2 path. INS2 instruments need version >=127; supported types FM(1), SSG(6), ADPCM-A(37), ADPCM-B(38). Furnace version is not a blocker.
- Input mapping for main.c: BIOS bios_p1current bits are UP=1,DOWN=2,LEFT=4,RIGHT=8,A=0x10,B=0x20,C=0x40,D=0x80. Core wants A..D=0x01..0x08, UP=0x10.. so core_in = ((cur>>4)&0xF) | ((cur&0xF)<<4). Start is in bios_statchange & CNT_START1, not p1current.
- Backup RAM: `u8 _backup_ram buf[HISCORE_IMAGE_SIZE]` (130 bytes) goes to .bss.bram at 0x100000 (example 11 pattern).
- Do not redefine ng_cls/ng_text in main.c: ng-fix.h provides ng_cls, ng_text, ng_center_text; ng-video.h provides ng_wait_vblank.
- OPEN (P0.3 remainder): real src/main.c (input, flow_step per frame, flow_view text, backup RAM), Makefile ELF link of src/core/*.c, `make run` window title "Roofline - P0 dev", `make test` = tests/host/run.sh + MAME Lua check of a RAM frame counter (68k RAM at 0x100000, read with program-space read_u32; address from `nm` on the ELF).

# P0 step 3: real main.c, core linked, make test with MAME Lua (agent run)

Done
- src/main.c rewritten (glue only): vblank loop, BIOS joypad nibble swap, Start from `bios_statchange & CNT_START1`, flow_step per frame, flow_view drawn as fix-layer text (title, state name, score, lives, name entry with cursor, top-10 table, save reminder), hiscore image `u8 _backup_ram g_hiscore_image[130]` at 0x100000, written via hiscore_serialise when `flow.dirty`. Removed the ng_cls/ng_text redefinitions. Fix palettes: 0 white, 1 yellow (highlight) in MMAP_PALBANK1.
- Makefile: ELF links src/core/{rng,game,hiscore,nameentry,flow}.o. Links cleanly with ngdevkit's own libc (memcpy/memset present; no __udivsi3 problem).
- `make test`: tests/host/run.sh, then MAME headless with tests/mame/boot_check.lua. Addresses come from `nm` on the ELF (env vars), so no hardcoded addresses.
- RULES.md Commands updated to match.

Sentinel
- `g_frame_counter` (u32, volatile) at 0x001000a8; `g_flow` at 0x001000ac (state byte at offset 0); `g_hiscore_image` at 0x00100000.

make test result (exact last lines)
```
PASS counter 180 -> 380, state 0 -> 3, coin=true start=true
[OK] make test passed
```
Host part: test_core 3859 checks 0 failures, test_flow 36172 checks 0 failures, knobs 59 checked 0 failed.

Finding: after coin + start the frame counter resets (300 at frame 300, then 30 at frame ~350): the BIOS re-enters main() when the game is started from the title, so BSS/flow is re-initialised. flow_init then runs again from ATTRACT_TITLE, yet state is PLAYING a few frames later because bios_statchange still shows START1. Consequences: the 40 s counter test samples both values after the restart (frames 500 and 700). Whether the hiscore table survives this restart is unchecked (g_hiscore_image is in .bss.bram, which the BIOS should preserve; not tested). Needs a look before P1: either confirm USER-call handling (ngdevkit examples use the same main) or handle the restart deliberately.

Package
- tools/package_mister.sh: build/mister/roofline.neo (see size below). Boot on MiSTer still UNVERIFIED.

Open
- MAME has no window-title option (checked `mame -showusage`: no title flag). `make run` title is MAME's default; a title needs an SDL/OSD patch or a wrapper that sets it after launch.
- Fix-layer text appearance is not visually checked (no screenshots per brief); human check at `make run`.
- Each `make test` leaves build/test-run.XXXXXX (small) because rm of computed paths is blocked by the sandbox; build/ is ignored.
- Persistence of hiscore across a MAME restart untested.

# BIOS USER re-entry (agent run)

Root cause
- The BIOS jumps to the cartridge USER vector again after boot. Measured in MAME: at frame 321 (the coin-insert frame) `BIOS_USER_REQUEST` (0x10fdae) = 3 (title), `BIOS_USER_MODE` = 1, and `g_frame_counter` drops 320 -> 0. So it is the coin, not the start press, that re-enters.
- ngdevkit crt0 (`/opt/homebrew/Cellar/ngdevkit/0.5+202611061802-1/m68k-neogeo-elf/lib/ngdevkit-crt0.o`, disassembled): `USER` (0x122) jumps to `wrapper_user` (0x35c), which reads 0x10fdae, indexes the table at 0x34c [rom_mvs_startup_init, rom_eye_catcher, rom_game, rom_title] and jsr's the entry, then jumps to SYSTEM_RETURN (0xc00444).
- `rom_title_default` (0x2ec) and `rom_game_default` (0x31c, same address as `rom_eye_catcher_default`) both do: SR=0x2700, IRQ ack, watchdog, `jsr init_c_runtime` (0x270: clears .bss from `__bss_start_in_ram`, copies .data), SR=0x2000, `_init`, REG_CRTFIX=1, then `jsr main_mvs_title` / `jsr main`. So every command 2/3 wipes all RAM globals and runs main() again.
- `ngdevkit.ld` lines 74-80: `rom_game`, `rom_title`, `rom_mvs_startup_init`, `rom_eye_catcher`, `main_mvs_title` are link-time hooks that fall back to the crt0 defaults. Roofline did not define them.
- Backup RAM: `.bss.bram` (0x100000) sits before `__bss_start_in_ram`, so init_c_runtime does not clear `g_hiscore_image`; the harm was flow_init re-running (state, unsaved table) and the counter. Measured: image bytes unchanged across the window both before and after the fix.
- ngdevkit examples: not installed locally (only neogeo.zip/aes.zip/nullsound in share/ngdevkit); not checked.

Fix (src/main.c)
- Define `rom_game` and `rom_title`. First entry after power-on: call the ngdevkit default (one C runtime init, then main). main() sets `g_boot_magic` (a .bss u32, cleared by that init) after flow_init and enters `game_loop()`. Every later command 2/3: same hardware prologue as crt0 (SR 0x2700, IRQ ack, watchdog, SR 0x2000, REG_CRTFIX=1) without the runtime init, then `game_loop()` with RAM intact. The flow state machine owns title/attract/play, so commands 2/3 need no separate screens. Command 0 keeps the default (flow_init falls back to defaults on a bad image); command 1 never comes (rom_eye_catcher_mode 0).
- Verified from the linked ELF (structure, not grep): dispatch table at 0x34c = `00000268 0000031c 0000102a 00001042` = startup default, eye-catcher default, our rom_game, our rom_title.
- Open: a soft reset must not leave `g_boot_magic` set (relies on the BIOS work RAM test/clear at boot). Unverified in MAME and on hardware; a MAME `soft_reset()` check would settle it.
- Open: the game never sets `BIOS_USER_MODE` = 2 when PLAYING (MVS convention); BIOS then still treats coins as attract-mode coins. Not changed here.

Regression test (tests/mame/boot_check.lua via `make test`)
- Samples `g_frame_counter` every frame 290..420 (coin 320, start 360) and fails on any decrease (logs user_request/mode at that frame); compares the hiscore image (`g_hiscore_image`, address and size from `nm`/`nm -S`, new env vars in the Makefile) at frame 300 vs 700; still requires state attract -> playing.
- Before fix: `FAIL counter not monotonic at frame 321: 320 -> 0 (user_request=3 user_mode=1); counter 290 -> 100 over frames 290..420, state 0 -> 3, image unchanged, coin=true start=true`
- After fix: `PASS counter 290 -> 421 over frames 290..420, state 0 -> 3, image unchanged, coin=true start=true` / `[OK] make test passed`. Host: test_core 3859 checks 0 failures, test_flow 36172 checks 0 failures, knobs 59 checked 0 failed.
- The image check is a guard only: with fresh nvram the image is invalid and never rewritten, so it passed before the fix too.

# Real BIOS clears palettes on re-entry (2026-11-09)

Symptom (user, UniBIOS 4.0 in `make run`): screen goes black after pressing coin; game keeps running.

Measured (headless MAME, UniBIOS, coin at frame 900): before the coin, palette RAM held
text palette 0 colour 1 = 0fff and hero slot 2 colour 1 = 3102. From the first frame after
BIOS_USER_REQUEST changed 2 -> 3, both read 0000 and stayed 0000, while g_frame_counter kept
counting and g_flow advanced. So UniBIOS clears palette RAM before it re-enters the cartridge
with USER command 3. nullbios does not, which is why make test missed it. Assume the SNK MVS
BIOS on the cabinet behaves like UniBIOS (unverified on hardware).

Fix: src/main.c `video_init()` (fix layer clear, text palettes, hero palettes, hero hide,
force draw() to clear) runs on first boot and in `resume_game_loop()` on every later USER
entry. Regression test: tests/mame/unibios_check.lua via `make test-unibios` (fails before
the fix with "palettes lost after coin: text 0000 (was 0fff) hero 0000 (was 3102)").
Rule for new video state (backgrounds, enemy palettes): load it in video_init(), never only
in main().

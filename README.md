# Gumbirds

Gumbirds is an original Neo Geo MVS arcade game written in C with ngdevkit. Sooty birds called Sootlings float under bubble gum bubbles above a city roofline, in a flap-to-float arena built for a high-score competition on an office cabinet.

Status: work in progress. This is not a finished game. Art, sound and game rules are still changing, and the sound currently uses placeholder effects and a stand-in music file.

## The game

The game takes place on one screen with a wrapping camera and a city backdrop that stays behind the action. Your Sootling starts on an island. Press A to flap and stay in the air, and steer with the stick left and right. Walking off the island without flapping ends in a drowning and a game over. Computer-controlled fliers share the arena. Scores go into a high-score table, and a name entry screen follows a finished run, with a 60 second timeout that saves the letters typed so far. Scores are kept in backup RAM (the `nvram/` folder when run in MAME).

Controls, as used by the tests: coin and start to begin, A to flap, stick left and right to steer. The B, C and D buttons and stick up and down have no function in the arena according to the design document.

## Requirements

- ngdevkit (the toolchain and its tools, including the sound tooling the build calls).
- GNU make, run as `gmake` on macOS because the system make is too old.
- Python 3 with Pillow (the build writes `config.mk` through `tools/gen_config.sh`, which needs it), run in isolated mode by the Makefile.
- MAME, to run the game and the emulator tests.
- A Neo Geo BIOS set for MAME. It is not included in this repository. The build uses the ngdevkit null BIOS, which makes MAME print a ROM checksum warning at boot; this is expected. `make run` can boot a UniBIOS 4.0 zip you supply through the `UNIBIOS` variable, and falls back to the null BIOS if it is missing. The UniBIOS file is never copied into the repository.

The Makefile and `RULES.md` are written around macOS with Homebrew (the run target locates MAME's shader and artwork folders with `brew --prefix`).

## Build, run and test

Run all commands from the repository root.

- `gmake` builds the ROM set into `build/rom/` and a zip, `build/brawl.zip`. The game's internal ROM name is still `brawl` (see Known leftovers below).
- `gmake run` starts the game in a MAME window as an MVS machine, with high scores kept in `nvram/`. Pick another screen filter with, for example, `gmake run MAME_SHADER=crt-geom`.
- `gmake test` runs the host tests and then the emulator checks (see Tests).
- `gmake clean` removes build output.
- `tools/package_mister.sh` packages a `.neo` file for an FPGA-based cabinet.

There is no type-check, lint or format step; the C code is built with `-Wall`.

## Tests

Host tests are plain C programs in `tests/host/`, started by `tests/host/run.sh`. They cover the core logic in `src/core/`: flier physics, arena, AI, flow, stages, camera, object pool, sprite budget, VRAM queue, sound queue and background scroll.

MAME tests are Lua scripts in `tests/mame/`, run headless against the built ROM. `gmake test` runs the host tests plus these targets: `test-flier`, `test-reach`, `test-vblank`, `test-scroll`, `test-sound` and a boot check. Further targets, run on their own: `test-crom`, `test-slots`, `test-hazard`, `test-camera`, `test-sprite-peak` and `test-unibios` (the last one needs the UniBIOS file). Each one launches MAME, so run them one at a time.

## Repository layout

- `src/` - game code: the Neo Geo glue in `main.c`, graphics, background and hazard code, and the sound driver glue.
- `src/core/` - hardware-independent game logic (flier, arena, AI, flow, stages, camera, high scores, name entry, queues), so it can be tested on the host.
- `assets/` - sprite sheets and other art and sound sources.
- `tools/` - Python and shell scripts that build sprite tables, placeholder sounds and the cabinet package.
- `tests/` - host tests in `tests/host/` and MAME Lua checks in `tests/mame/`.
- `setup/`, `cfg/`, `build.mk`, `config.mk`, `emu.mk`, `rom.mk`, `Makefile` - build configuration.
- `design/` - draft design pages in HTML.
- `thoughts/` - plans, research notes, handoffs and art drafts.

## Known leftovers

The project was renamed from an earlier working title. The build still uses the old name in places: the Makefile sets `GAMEROM=brawl` and `GAMETITLE=Bubblegum Brawl`, and the MiSTer package is named `bubblegum-brawl.neo`.

## License

The source code, build scripts, tools and tests are under the MIT License (Copyright (c) 2026 spotUP); see `LICENSE`. Art, music and sound under `assets/`, and the design material under `thoughts/` and `design/`, are not covered by it. All rights in them are reserved by their authors, except third-party items, which keep the license named in their own files.

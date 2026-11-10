# Copyright (c) 2015-2025 Damien Ciabrini
# This file is part of ngdevkit
#
# ngdevkit is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# ngdevkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with ngdevkit.  If not, see <http://www.gnu.org/licenses/>.



all: cart bios

# These are various variables that you might want to customize
# based on your liking or your requirements.
# location of generated and compiled content
BUILDDIR=build
# all directories that contain source to be compiled
SRCDIRS=assets src
# default build flags, can be overriden per target
CFLAGS=-I$(BUILDDIR) -std=c99 -fomit-frame-pointer -O2 -g -MMD -MP
LDFLAGS=
Z80FLAGS=
Z80LDFLAGS=

# This is an autoconf-generated configuration for your environment
# (ngdevkit path, OS-specific configs...)
config.mk:
	tools/gen_config.sh $@

include config.mk

# This defines the layout of your game cartridge
# You can customize it to match your requirements
# Name of the rom file created
GAMEROM=roofline
# Game title, long description
GAMETITLE=Roofline
HASH_GNGEO=
include rom.mk

# All the generic build targets (68k, Z80, assets, run)
include build.mk

# Some default targets for running your project via emulators
include emu.mk



# program ROM: your main program
# Add your dependencies below to compile your sources into an ELF binary
# that is used as the content of the program ROM (referenced by symbol PROM1)
# 
# Note: build rules (%.c -> %.o -> %.elf) are defined in Makefile.build
ELF=$(BUILDDIR)/rom.elf
CORE_SRCS=rng game hiscore nameentry flow obstacle_view bg_scroll flier_view vram_queue obj_pool sound_queue sound_events flier stage ai
$(ELF):	$(BUILDDIR)/src/main.o $(BUILDDIR)/gen/sootling_sprites.o $(BUILDDIR)/gen/obs_sprites.o $(BUILDDIR)/gen/city_sprites.o $(BUILDDIR)/src/bg.o $(BUILDDIR)/src/gfx.o $(BUILDDIR)/src/sound.o $(CORE_SRCS:%=$(BUILDDIR)/src/core/%.o)
$(PROM1): $(ELF)



# fixed tiles ROM: all your 8x8 pixel tiles for the fixed layer
# Add your dependencies below to convert images to fixed tile binary data
# and pack it into the fixed tile ROM (referenced by symbol SROM1)
# 
# By default, this makefile creates a tileset ROM with small and tall
# latin characters for printing ASCII string, and tiles that are
# displayed during the attract mode.
# Note: build rules (%.gif -> %.fix) are defined in Makefile.build
$(SROM1): $(BUILDDIR)/assets/base-srom-text-shadow.fix



# sprite ROM: all your 16x16 pixel tiles for sprites
# Add your dependencies below to convert images to fixed sprite binary data
# and pack it into two separate sprite ROMs that hold odd and even bits of
# color information (referenced by symbols CROM1 and CROM2)
#
# By default, this makefile creates CROMs with tiles for displaying a ngdevkit
# logo during the attract mode.
# Note: build rules (%.gif -> %.c<1,2>) are defined in Makefile.build
# Obstacle tiles come after the logo (256 tiles = OBS_TILE_BASE in src/vram_layout.h), city tiles after the obstacles (bases in src/vram_layout.h, from the generated headers); prerequisite order = cat order.
CROM_SETS=assets/base-crom-logo gen/obs gen/city gen/sootling
CROM_LAYOUT=$(BUILDDIR)/gen/crom-layout.stamp
$(CROM1): $(CROM_SETS:%=$(BUILDDIR)/%.c1) $(CROM_LAYOUT)
$(CROM2): $(CROM_SETS:%=$(BUILDDIR)/%.c2) $(CROM_LAYOUT)
# The stamp holds the set list and changes only when the list does. Without it, dropping or reordering a set
# leaves the old C-ROM in place (no prerequisite is newer) while the program ROM gets the new tile bases:
# every sprite then draws the wrong tiles. build.mk leaves %.stamp out of the cat.
.PHONY: crom-layout-check
$(CROM_LAYOUT): crom-layout-check
	@mkdir -p $(@D); echo '$(CROM_SETS)' | cmp -s - $@ || echo '$(CROM_SETS)' > $@
# Flier (Sootling) sprite pipeline (tools/build_flier_sprites.py). The sheet is imported from a draft PNG by
# tools/import_flier_sheet.py and committed under assets/flier/; re-importing a new draft is the whole art swap.
$(BUILDDIR)/gen/sootling.c1 $(BUILDDIR)/gen/sootling.c2 $(BUILDDIR)/gen/sootling_sprites.c $(BUILDDIR)/gen/sootling_sprites.h: assets/flier/sootling_sheet.png assets/flier/sootling_sheet.json tools/build_flier_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_flier_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/sootling_sprites.o: $(BUILDDIR)/gen/sootling_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Obstacle sprite pipeline (tools/build_obstacle_sprites.py, shared module tools/sprite_pipeline.py).
# The sheet itself is drawn by tools/draw_obstacle_sheet.py and committed under assets/obstacles/.
$(BUILDDIR)/gen/obs.c1 $(BUILDDIR)/gen/obs.c2 $(BUILDDIR)/gen/obs_sprites.c $(BUILDDIR)/gen/obs_sprites.h: assets/obstacles/obstacle_sheet.png assets/obstacles/obstacle_sheet.json tools/build_obstacle_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_obstacle_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/obs_sprites.o: $(BUILDDIR)/gen/obs_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# City background sprite pipeline (tools/build_city_sprites.py over tools/sprite_pipeline.py).
# The sheet is drawn by assets/city/draw_city.py and committed under assets/city/.
$(BUILDDIR)/gen/city.c1 $(BUILDDIR)/gen/city.c2 $(BUILDDIR)/gen/city_sprites.c $(BUILDDIR)/gen/city_sprites.h: assets/city/city_sheet.png assets/city/city_sheet.json tools/build_city_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_city_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/city_sprites.o: $(BUILDDIR)/gen/city_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@

$(BUILDDIR)/src/main.o $(BUILDDIR)/src/bg.o $(BUILDDIR)/src/gfx.o: $(BUILDDIR)/gen/obs_sprites.h $(BUILDDIR)/gen/city_sprites.h $(BUILDDIR)/gen/sootling_sprites.h src/core/flier_view.h src/vram_layout.h src/sprite_slots.h src/bg.h src/gfx.h src/core/vram_queue.h



# sound driver ROM: nullsound (Z80) + generated command table, built from source by gmake.
# Plan: thoughts/shared/plans/2026-11-09-sound-driver.md. Nothing under build/sound is committed.
#   assets/sound/*.yaml            music and sample maps (soundtool.py)
#   tools/make_standin_fur.py      stand-in music (no upstream asset copied, licence unclear)
#   tools/make_sfx_placeholders.py placeholder SFX WAVs (replaced by real samples later)
# Generation order: `gmake` runs the sound-gen target (CUSTOM_GENERATE_TARGETS) before anything is
# compiled, so build/snd_commands.h exists for the 68k and nss-deps.mk exists for the include below.
SOUND_DIR=$(BUILDDIR)/sound
SOUND_YAMLS=assets/sound/music-map.yaml assets/sound/sample-map.yaml
SFX_NAMES=jump hit game_over coin
SFX_WAVS=$(SFX_NAMES:%=$(SOUND_DIR)/sfx/%.wav)
SOUND_DRIVER=$(SOUND_DIR)/driver.ihx

$(SOUND_DIR)/ingame.fur: tools/make_standin_fur.py
	mkdir -p $(@D)
	$(PYTHON) -I tools/make_standin_fur.py $@
$(SFX_WAVS): tools/make_sfx_placeholders.py
	mkdir -p $(@D)
	$(PYTHON) -I tools/make_sfx_placeholders.py $(SOUND_DIR)/sfx
SOUND_ASSETS=$(SOUND_DIR)/ingame.fur $(SFX_WAVS)

# build.mk recipes read the maps through $^, so the generated assets are order-only prerequisites
# (they exist before soundtool/vromtool run). After changing a generator script run `gmake generate`.
$(VROM1) $(Z80_SAMPLES_IN_VROM) $(Z80_SOUND_COMMANDS) $(SOUND_COMMANDS): $(SOUND_YAMLS) | $(SOUND_ASSETS)
$(SOUND_DIR)/nss-deps.mk: $(SOUND_YAMLS)
	mkdir -p $(@D)
	$(SOUNDTOOL) -m -s $^ > $@
-include $(SOUND_DIR)/nss-deps.mk

$(BUILDDIR)/src/sound/user_commands.rel: src/sound/user_commands.s $(Z80_SAMPLES_IN_VROM) $(Z80_SOUND_COMMANDS)
	mkdir -p $(@D)
	$(Z80SDAS) -g -l -p -u -I$(NGZ80INCLUDEDIR)/nullsound -I$(BUILDDIR) -o $@ $<
$(SOUND_DRIVER): $(BUILDDIR)/src/sound/user_commands.rel
	mkdir -p $(@D)
	$(Z80SDLD) -m -b DATA=0xf800 -i $@ $(NGZ80LIBDIR)/nullsound.lib $^
$(MROM1): $(SOUND_DRIVER)
$(BUILDDIR)/src/main.o $(BUILDDIR)/src/sound.o: $(SOUND_COMMANDS) src/sound.h src/core/sound_queue.h src/core/sound_events.h

sound-gen: $(Z80_SAMPLES_IN_VROM) $(Z80_SOUND_COMMANDS) $(SOUND_COMMANDS) $(SOUND_DIR)/nss-deps.mk
.PHONY: sound-gen



# sound FX ROM: ADPCM-A samples, packed by vromtool from the sample map (VROMTEMPLATE in rom.mk)
# Note: build rules (%.wav-> %.adpcm<a,b>) are defined in Makefile.build



# One-time asset preprocessing
# Various assets may have to be processed before they can be used to
# build your ROM, for example:
#   . the ngdevkit assets must be converted to sprite and text tiles
#   . converting your SFX assets from .mp3 into .wav so they can be
#     processed by ngdevkit tools
# To handle these pre-processing requirements, `make` automatically
# runs into all subdirectories under ./setup/, so you get a chance
# to preprocess what you need before anything is built.
#
# Other assets must be processed only once to generate source files
# that gets built into your ROM, for example:
#   . converting your musics from .fur to z80 code and data files
#   . generating make dependencies to pack gfx or sound assets into
#     the right ROM bank based on your input assets
# Those actions can be achieved by creating custom make targets
# that get invoked automatically when added to the variable below.
CUSTOM_GENERATE_TARGETS=sound-gen



# a default `clean` target removes .o .elf and .ihx from the builddir
# a default `distclean` target removes the build directory entirely
# you can customize clean up by adding dependencies to those targets


# ---- Roofline targets (see RULES.md) ----
.DEFAULT_GOAL := all

# Window run, MVS BIOS, backup RAM kept in nvram/
# Windowed, 3x native 320x224, so dev runs never grab the whole screen. -artpath: the crt-geom
# chains load their aperture PNGs from artwork/bgfx/...; the default artpath is ./artwork, so
# without it MAME logged "Unable to load chain ... falling back to no post processing".
MAME_SHADER?=crt-geom-deluxe
ROOFLINE_WINDOW_FLAGS=-window -nomaximize -resolution 960x672 -nofilter -video bgfx -bgfx_path $(shell brew --prefix)/share/mame/bgfx -bgfx_screen_chains $(MAME_SHADER) -artpath $(shell brew --prefix)/share/mame/artwork
# UniBIOS 4.0 for make run only (user decision 2026-11-09). The zip is never copied into the
# repo: build/unibios/neogeo.zip = nullbios files + uni-bios_4_0.rom, searched before $(ROM).
# Missing UNIBIOS file: make run falls back to nullbios. make test uses nullbios except test-reach (UniBIOS).
UNIBIOS?=$(HOME)/Downloads/uni-bios-40.zip
UNIBIOS_DIR=$(BUILDDIR)/unibios
$(UNIBIOS_DIR)/neogeo.zip: $(UNIBIOS) $(ROM)/neogeo.zip
	rm -rf $(UNIBIOS_DIR); mkdir -p $(UNIBIOS_DIR)/x
	unzip -q -o $(ROM)/neogeo.zip -d $(UNIBIOS_DIR)/x
	unzip -q -p $(UNIBIOS) uni-bios.rom > $(UNIBIOS_DIR)/x/uni-bios_4_0.rom
	cd $(UNIBIOS_DIR)/x && zip -q ../neogeo.zip *
	rm -rf $(UNIBIOS_DIR)/x
ifneq ($(wildcard $(UNIBIOS)),)
RUN_BIOS_DEPS=$(UNIBIOS_DIR)/neogeo.zip
RUN_BIOS_FLAGS=-rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40
else
RUN_BIOS_DEPS=
RUN_BIOS_FLAGS=-rp $(ROM)
endif
run: cart bios $(RUN_BIOS_DEPS)
	mkdir -p nvram
	$(MAME) $(ROOFLINE_WINDOW_FLAGS) -noautosave -skip_gameinfo -hash $(ROM) $(RUN_BIOS_FLAGS) -nvram_directory nvram neogeo -cart1 $(GAMEROM)


# Test: host core tests, then headless MAME Lua check (tests/mame/boot_check.lua) that the
# frame counter sentinel advances and the flow leaves ATTRACT after coin + start.
# Addresses come from nm on the ELF. Fresh nvram dir and result file per run. Non-zero on fail.
TEST_SECONDS?=40
NM=$(M68KGCC:%gcc=%nm)
# The C-ROMs must start with their sets in CROM_SETS order (the tile bases in src/vram_layout.h assume it).
.PHONY: test-crom
test-crom: cart
	@for n in 1 2; do f=$(ROM)/$(GAMEROM)-c$$n.c$$n; cat $(CROM_SETS:%=$(BUILDDIR)/%.c$$n) > $(BUILDDIR)/crom-expect.bin; \
	  head -c `wc -c < $(BUILDDIR)/crom-expect.bin` $$f | cmp -s - $(BUILDDIR)/crom-expect.bin || { echo "[FAIL] test-crom: $$f does not match its sets"; rm -f $(BUILDDIR)/crom-expect.bin; exit 1; }; done; \
	rm -f $(BUILDDIR)/crom-expect.bin; echo "[OK] test-crom: C-ROMs match their sets"
test: cart
	nice -n 19 tests/host/run.sh
	@$(MAKE) --no-print-directory test-crom
	@$(MAKE) --no-print-directory test-flier
	@$(MAKE) --no-print-directory test-reach
	@$(MAKE) --no-print-directory test-vblank
	@$(MAKE) --no-print-directory test-scroll
	@$(MAKE) --no-print-directory test-sound
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_HISCORE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_image"{print $$1}') \
	ROOFLINE_HISCORE_SIZE=$$($(NM) -S $(ELF) | awk '$$4=="g_hiscore_image"{print $$2}') \
	ROOFLINE_BG_SCROLL_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_scroll_px"{print $$1}') \
	ROOFLINE_BG_WRITES_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_column_writes"{print $$1}') \
	ROOFLINE_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -snapshot_directory $$T/snap -autoboot_script tests/mame/boot_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	mkdir -p $(BUILDDIR)/test-snap; cp $$T/snap/*.png $(BUILDDIR)/test-snap/ 2>/dev/null || true; \
	grep -q '^PASS' $$T/result.txt && $(PYTHON) -I tests/mame/check_hero_pixels.py build/gen/sootling_sprites.c build/gen/obs_sprites.c build/gen/city_sprites.c $$T/snap/pre_start.png $$T/snap/playing.png && $(PYTHON) -I tests/mame/check_bg_pixels.py build/gen/city_sprites.c build/gen/obs_sprites.c $$T/snap/pre_start.png $$T/snap/bg_a.png $$T/snap/playing.png $$T/result.txt.bg || echo "[FAIL] pixel check" >> $$T/result.txt; \
	if ! grep -q 'FAIL' $$T/result.txt; then rm -rf $$T; echo "[OK] make test passed"; else echo "[FAIL] make test, log kept in $$T"; exit 1; fi

# Flier reachability (tests/mame/flier_check.lua): coin, start, flap with A, steer, drown, game over. Sentinel:
# Game.flier_steps (src/core/game.c game_step_arena) must track the PLAYING frames.
test-flier: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_SOOT_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_soot_range"{print $$1}') \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	ROOFLINE_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/flier_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from flier Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-flier passed"; else echo "[FAIL] make test-flier, log kept in $$T"; exit 1; fi

# High score reachability, plan P5.1 (tests/mame/hiscore_reach.lua): boot 1 plays to game over, types the name
# REACHTST through the real name entry screen and checks the save sentinel g_hiscore_saves and backup RAM; boot 2
# on the same nvram dir checks the table holds that name and score at the same row. Run by make test.
# Runs under UniBIOS 4.0 (cabinet BIOS class): the BIOS copies .bss.bram to backup RAM after the game returns
# through SYSTEM_RETURN. Stock ngdevkit nullbios writes backup RAM without REG_SRAMUNLOCK, so nothing persists
# there (see thoughts/shared/research/2026-11-09_p51-reachability.md). Needs the UNIBIOS file.
REACH_SECONDS?=300
REACH_BIOS_FLAGS?=-rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40
test-reach: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	for PH in 1 2; do \
	ROOFLINE_PHASE=$$PH \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	ROOFLINE_HISCORE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_image"{print $$1}') \
	ROOFLINE_SAVES_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_saves"{print $$1}') \
	ROOFLINE_NAMESEC_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_name_seconds_shown"{print $$1}') \
	ROOFLINE_REACH_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/reach_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result$$PH.txt ROOFLINE_EXPECT=$$T/expect.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(REACH_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) $(REACH_BIOS_FLAGS) -nvram_directory $$T/nvram -autoboot_script tests/mame/hiscore_reach.lua neogeo -cart1 $(GAMEROM) > $$T/mame$$PH.log 2>&1 || true; \
	if [ ! -f $$T/result$$PH.txt ]; then tail -n 15 $$T/mame$$PH.log 2>/dev/null || echo "[ERROR] $$T/mame$$PH.log missing: the scratch dir was deleted during the run (another session cleaning build/test-run.*?)"; echo "[FAIL] test-reach boot $$PH: no result from Lua script"; exit 1; fi; \
	cat $$T/result$$PH.txt; \
	grep -q '^PASS' $$T/result$$PH.txt || { echo "[FAIL] make test-reach boot $$PH, log kept in $$T"; exit 1; }; \
	done; rm -rf $$T; echo "[OK] make test-reach passed"

# Vblank write reachability (tests/mame/vblank_check.lua): taps the LSPC VRAM registers and palette RAM during
# a real run (attract, coin, start, scrolling) and asserts every write after boot lands in vblank.
# Run by make test; `make test-vblank` alone re-runs only this check.
test-vblank: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	ROOFLINE_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/vblank_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from vblank Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if ! grep -q 'FAIL' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-vblank passed"; else echo "[FAIL] make test-vblank, log kept in $$T"; exit 1; fi

# Background scroll reachability (tests/mame/scroll_check.lua): coin, start, play with jumps and fire, restart after
# game over; a Lua VRAM shadow asserts every PLAYING frame each city ring shows the g_bg_scroll_px the game committed
# for it (no late or skipped scroll writes), sentinel g_bg_scroll_flushes. Run by make test; `make test-scroll`
# alone re-runs only this check. SCROLL_LOG=<file> keeps the per-frame log.
test-scroll: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result.txt ROOFLINE_SCROLL_LOG=$(SCROLL_LOG) \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 90 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/scroll_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from scroll Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if ! grep -q 'FAIL' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-scroll passed"; else echo "[FAIL] make test-scroll, log kept in $$T"; exit 1; fi

# Sound driver reachability (tests/mame/sound_check.lua): coin, start, jump, fire, idle to game over. Asserts the 68k
# sentinels g_sound_sent/g_sound_last, the Z80 command port reads and the YM2610 key-on/FM writes agree for every
# game sound event. Run by make test; `make test-sound` alone re-runs only this check.
test-sound: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/sound_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from sound Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if ! grep -q 'FAIL' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-sound passed"; else echo "[FAIL] make test-sound, log kept in $$T"; exit 1; fi

# UniBIOS check (tests/mame/unibios_check.lua): palettes survive the real-BIOS coin re-entry.
# Separate from make test, because it needs the UNIBIOS file from outside the repo.
test-unibios: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	ROOFLINE_BG_PAL_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_pal_first_entry"{print $$1}') \
	ROOFLINE_SOOT_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_soot_range"{print $$1}') \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_REACH_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/reach_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 120 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/unibios_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-unibios passed"; else echo "[FAIL] make test-unibios, log kept in $$T"; exit 1; fi

.PHONY: run test test-flier test-reach test-vblank test-scroll test-sound test-unibios

# Header dependencies from -MMD (build/**/*.d): a changed header rebuilds every object that includes it.
-include $(shell find $(BUILDDIR) -name '*.d' 2>/dev/null)

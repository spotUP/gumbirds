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
CFLAGS=-I$(BUILDDIR) -std=c99 -fomit-frame-pointer -O2 -g
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
CORE_SRCS=rng game hiscore nameentry flow obstacle_view bg_scroll laser_view hero_view vram_queue
$(ELF):	$(BUILDDIR)/src/main.o $(BUILDDIR)/gen/hero_sprites.o $(BUILDDIR)/gen/obs_sprites.o $(BUILDDIR)/gen/city_sprites.o $(BUILDDIR)/gen/heat_sprites.o $(BUILDDIR)/src/bg.o $(BUILDDIR)/src/gfx.o $(CORE_SRCS:%=$(BUILDDIR)/src/core/%.o)
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
# Hero tiles come after the logo (256 tiles = HERO_TILE_BASE in src/main.c), obstacle tiles after the
# hero tiles, city tiles after the obstacles (bases in src/vram_layout.h, from the generated headers); prerequisite order = cat order.
$(CROM1): $(BUILDDIR)/assets/base-crom-logo.c1 $(BUILDDIR)/gen/hero.c1 $(BUILDDIR)/gen/obs.c1 $(BUILDDIR)/gen/city.c1 $(BUILDDIR)/gen/heat.c1
$(CROM2): $(BUILDDIR)/assets/base-crom-logo.c2 $(BUILDDIR)/gen/hero.c2 $(BUILDDIR)/gen/obs.c2 $(BUILDDIR)/gen/city.c2 $(BUILDDIR)/gen/heat.c2

# Hero sprite pipeline (tools/build_hero_sprites.py); one run makes all four files.
$(BUILDDIR)/gen/hero.c1 $(BUILDDIR)/gen/hero.c2 $(BUILDDIR)/gen/hero_sprites.c $(BUILDDIR)/gen/hero_sprites.h: assets/hero/guard_sheet.png assets/hero/guard_sheet.json tools/build_hero_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_hero_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/hero_sprites.o: $(BUILDDIR)/gen/hero_sprites.c
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

# Heat bar sprite pipeline (tools/build_laser_sprites.py). The sheet is drawn by tools/draw_heat_sheet.py
# and committed under assets/laser/. The beam and the kill flash are frames of the hero set.
$(BUILDDIR)/gen/heat.c1 $(BUILDDIR)/gen/heat.c2 $(BUILDDIR)/gen/heat_sprites.c $(BUILDDIR)/gen/heat_sprites.h: assets/laser/heat_sheet.png assets/laser/heat_sheet.json tools/build_laser_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_laser_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/heat_sprites.o: $(BUILDDIR)/gen/heat_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
$(BUILDDIR)/src/main.o $(BUILDDIR)/src/bg.o $(BUILDDIR)/src/gfx.o: $(BUILDDIR)/gen/hero_sprites.h $(BUILDDIR)/gen/obs_sprites.h $(BUILDDIR)/gen/city_sprites.h $(BUILDDIR)/gen/heat_sprites.h src/core/laser_view.h src/core/hero_view.h src/vram_layout.h src/sprite_slots.h src/bg.h src/gfx.h src/core/vram_queue.h



# sound driver ROM: nullsound + your configured sound commands
# Add your dependencies below to compile your z80 sources into a HEX binary
# that is used as the sound driver ROM (referenced by symbol MROM1)
#
# By default, this makefile uses the empty sound driver provided by ngdevkit
# Note: build rules (%.s -> %.o -> %.ihx) are defined in Makefile.build
SOUND_DRIVER=$(BUILDDIR)/assets/base-sound-driver.ihx
$(MROM1): $(SOUND_DRIVER)



# sound FX ROM: all your ADPCM samples
# Add your dependencies below to convert your samples into suitable
# ADPCM data and pack it into the sound ROM (referenced by symbol VROM1)
#
# Music and SFX assets can be managed with <> rather to generate
# the dependencies automatically.
# By default, no sample is used, so the VROM is empty
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
CUSTOM_GENERATE_TARGETS=



# a default `clean` target removes .o .elf and .ihx from the builddir
# a default `distclean` target removes the build directory entirely
# you can customize clean up by adding dependencies to those targets


# ---- Roofline targets (see RULES.md) ----
.DEFAULT_GOAL := all

# Window run, MVS BIOS, backup RAM kept in nvram/
# Windowed, 3x native 320x224, so dev runs never grab the whole screen.
MAME_SHADER?=crt-geom-deluxe
ROOFLINE_WINDOW_FLAGS=-window -nomaximize -resolution 960x672 -nofilter -video bgfx -bgfx_path $(shell brew --prefix)/share/mame/bgfx -bgfx_screen_chains $(MAME_SHADER)
# UniBIOS 4.0 for make run only (user decision 2026-11-09). The zip is never copied into the
# repo: build/unibios/neogeo.zip = nullbios files + uni-bios_4_0.rom, searched before $(ROM).
# Missing UNIBIOS file: make run falls back to nullbios. make test always uses nullbios.
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
test: cart
	nice -n 19 tests/host/run.sh
	@$(MAKE) --no-print-directory test-laser
	@$(MAKE) --no-print-directory test-hit
	@$(MAKE) --no-print-directory test-vblank
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_HISCORE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_image"{print $$1}') \
	ROOFLINE_HISCORE_SIZE=$$($(NM) -S $(ELF) | awk '$$4=="g_hiscore_image"{print $$2}') \
	ROOFLINE_BG_SCROLL_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_scroll_px"{print $$1}') \
	ROOFLINE_BG_WRITES_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_column_writes"{print $$1}') \
	ROOFLINE_OBS_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/layout_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result.txt \
	nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -snapshot_directory $$T/snap -autoboot_script tests/mame/boot_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	mkdir -p $(BUILDDIR)/test-snap; cp $$T/snap/*.png $(BUILDDIR)/test-snap/ 2>/dev/null || true; \
	grep -q '^PASS' $$T/result.txt && $(PYTHON) -I tests/mame/check_hero_pixels.py build/gen/hero_sprites.c build/gen/obs_sprites.c build/gen/city_sprites.c $$T/snap/pre_start.png $$T/snap/playing.png && $(PYTHON) -I tests/mame/check_obstacle_pixels.py build/gen/hero_sprites.c build/gen/obs_sprites.c build/gen/city_sprites.c $$T/snap/pre_start.png $$T/snap/obstacles.png $$T/result.txt.obs && $(PYTHON) -I tests/mame/check_bg_pixels.py build/gen/city_sprites.c build/gen/hero_sprites.c build/gen/obs_sprites.c $$T/snap/pre_start.png $$T/snap/bg_a.png $$T/snap/playing.png $$T/result.txt.bg || echo "[FAIL] pixel check" >> $$T/result.txt; \
	if ! grep -q 'FAIL' $$T/result.txt; then rm -rf $$T; echo "[OK] make test passed"; else echo "[FAIL] make test, log kept in $$T"; exit 1; fi

# Laser reachability (tests/mame/laser_check.lua + check_laser_pixels.py): sentinel-driven timeline (coin
# once the game loop runs, start until PLAYING, fire while a drone or bot is ahead, jump/duck the rest),
# snapshots the beam, the heat bar and the hit flash, reads kill counter and bonus from RAM.
# Run by make test; `make test-laser` alone re-runs only this check.
test-laser: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	ROOFLINE_LASER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/laser_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result.txt \
	nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -snapshot_directory $$T/snap -autoboot_script tests/mame/laser_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from laser Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	mkdir -p $(BUILDDIR)/test-snap; for f in heat_zero beam kill; do cp $$T/snap/$$f.png $(BUILDDIR)/test-snap/laser_$$f.png 2>/dev/null || true; done; \
	grep -q '^PASS' $$T/result.txt && $(PYTHON) -I tests/mame/check_laser_pixels.py build/gen/hero_sprites.c build/gen/obs_sprites.c build/gen/city_sprites.c build/gen/heat_sprites.c $$T/snap/heat_zero.png $$T/snap/beam.png $$T/snap/kill.png $$T/result.txt.laser || echo "[FAIL] laser check" >> $$T/result.txt; \
	if ! grep -q 'FAIL' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-laser passed"; else echo "[FAIL] make test-laser, log kept in $$T"; exit 1; fi

# Hit look reachability (tests/mame/hit_check.lua): idle hero, first obstacle hit; reads the hero animation
# sentinels the game wrote with the sprite registers. Run by make test; `make test-hit` alone re-runs only this.
test-hit: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_HERO_ANIM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hero_shown_anim"{print $$1}') \
	ROOFLINE_HERO_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hero_shown_frame"{print $$1}') \
	ROOFLINE_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result.txt \
	nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/hit_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from hit Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if ! grep -q 'FAIL' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-hit passed"; else echo "[FAIL] make test-hit, log kept in $$T"; exit 1; fi

# Vblank write reachability (tests/mame/vblank_check.lua): taps the LSPC VRAM registers and palette RAM during
# a real run (attract, coin, start, scrolling) and asserts every write after boot lands in vblank.
# Run by make test; `make test-vblank` alone re-runs only this check.
test-vblank: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	ROOFLINE_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	ROOFLINE_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	ROOFLINE_RESULT=$$T/result.txt \
	nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/vblank_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from vblank Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if ! grep -q 'FAIL' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-vblank passed"; else echo "[FAIL] make test-vblank, log kept in $$T"; exit 1; fi

# UniBIOS check (tests/mame/unibios_check.lua): palettes survive the real-BIOS coin re-entry.
# Separate from make test, because it needs the UNIBIOS file from outside the repo.
test-unibios: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ROOFLINE_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	ROOFLINE_BG_PAL_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_pal_first_entry"{print $$1}') \
	ROOFLINE_RESULT=$$T/result.txt \
	nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 30 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/unibios_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-unibios passed"; else echo "[FAIL] make test-unibios, log kept in $$T"; exit 1; fi

.PHONY: run test test-laser test-hit test-vblank test-unibios

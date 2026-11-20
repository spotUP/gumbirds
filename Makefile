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
# DEBUG_HEADER=1 builds the GUMBIRDS / state name header back in (src/main.c draw); off in the normal build. Objects do not track
# the flag: gmake clean (or touch src/main.c) when switching.
DEBUG_HEADER ?=
CFLAGS=-I$(BUILDDIR) -std=c99 -fomit-frame-pointer -O2 -g -MMD -MP $(if $(DEBUG_HEADER),-DGUMBIRDS_DEBUG_HEADER) -include $(BUILDDIR)/prof_cfg.h
# PROF=1 / release switch as a force-included header: -MMD records it, so switching PROF rebuilds every object (before this, a PROF build
# silently reused release objects and every mark read 0.0). Rewritten only when the value changes.
HASH:=\#
PROF_CFG:=$(if $(PROF),$(HASH)define GUMBIRDS_PROF 1,/* release */)
$(shell mkdir -p $(BUILDDIR); echo '$(PROF_CFG)' | cmp -s - $(BUILDDIR)/prof_cfg.h || echo '$(PROF_CFG)' > $(BUILDDIR)/prof_cfg.h)
# Cartridge header eyecatcher mode (ngdevkit.ld rom_eye_catcher_mode: 0 BIOS draws it, 1 game, 2 none). 2 keeps UniBIOS from
# drawing its eyecatcher text with tile codes that collide with the game's fix ROM (thoughts/spot/2026-11-12-u3-eyecatcher-hunt.md).
LDFLAGS=-Wl,--defsym,rom_eye_catcher_mode=2
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
GAMEROM=gumbirds
# Game title, long description
GAMETITLE=Gumbirds
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
CORE_SRCS=rng game hiscore nameentry flow attract_overlay obstacle_view bg_scroll flier_view gum_view vram_queue obj_pool sound_queue sound_events flier stage island_layout ai camera trip trip_gen trip_cave trip_hit trip_rival score_table gumgames gg_flapdash gg_popdrop gg_poop gg_fling gg_toss trip_view trip_pickup_fx banner splash_view arcade arc_elements arc_view result result_view stadium
$(ELF):	$(BUILDDIR)/src/main.o $(BUILDDIR)/gen/sootling_sprites.o $(BUILDDIR)/gen/hazard_sprites.o $(BUILDDIR)/gen/island_sprites.o $(BUILDDIR)/gen/island_garden_sprites.o $(BUILDDIR)/gen/island_deck_sprites.o $(BUILDDIR)/gen/tripstrip_sprites.o $(BUILDDIR)/gen/trippickup_sprites.o $(BUILDDIR)/gen/triphaz_sprites.o $(BUILDDIR)/gen/gum_sprites.o $(BUILDDIR)/gen/splash_sprites.o $(BUILDDIR)/gen/arcade_sprites.o $(BUILDDIR)/gen/resfx_sprites.o $(BUILDDIR)/gen/chute_sprites.o $(BUILDDIR)/gen/gumbubble_sprites.o $(BUILDDIR)/gen/tosspose_sprites.o $(BUILDDIR)/gen/gumleak_sprites.o $(BUILDDIR)/gen/countdown_sprites.o $(BUILDDIR)/gen/rulecard_sprites.o $(BUILDDIR)/gen/popdrop_sprites.o $(BUILDDIR)/gen/popdropsky_sprites.o $(BUILDDIR)/gen/poop_sprites.o $(BUILDDIR)/gen/flfield_sprites.o $(BUILDDIR)/gen/stadium_sprites.o $(BUILDDIR)/gen/obs_sprites.o $(BUILDDIR)/gen/city_sprites.o $(BUILDDIR)/gen/dusk_sprites.o $(BUILDDIR)/gen/storm_sprites.o $(BUILDDIR)/src/bg.o $(BUILDDIR)/src/gfx.o $(BUILDDIR)/src/hazard.o $(BUILDDIR)/src/island.o $(BUILDDIR)/src/trip_strip.o $(BUILDDIR)/src/fling_field.o $(BUILDDIR)/src/stadium_hw.o $(BUILDDIR)/src/trip_pickup.o $(BUILDDIR)/src/gum.o $(BUILDDIR)/src/logo.o $(BUILDDIR)/src/splash.o $(BUILDDIR)/src/sound.o $(CORE_SRCS:%=$(BUILDDIR)/src/core/%.o)
$(PROM1): $(ELF)



# fixed tiles ROM: all your 8x8 pixel tiles for the fixed layer
# Add your dependencies below to convert images to fixed tile binary data
# and pack it into the fixed tile ROM (referenced by symbol SROM1)
# 
# The S-ROM is the Gumdrop font (tools/build_fix_font.py from assets/font/, imported by tools/import_font_sheet.py): 256 tiles,
# tile index = sheet index, tile 255 blank (user decision 2026-11-10 replaced the ngdevkit ASCII font). The char to tile maps and the
# five fix palettes come with it in build/gen/fix_font.h (src/gfx.c prints through the maps).
# The Gum Trip gum meter tiles (assets/tripmeter, 13 tiles) are pasted into the font at tile 186; tripmeter.h holds the cell table.
# The attract overlay icons (59 fix tiles) sit in the S-ROM right after the font (tile 0x400); the S-ROM rule below concatenates both.
$(BUILDDIR)/gen/attract_icons.h $(BUILDDIR)/gen/attract_icons.fix &: assets/attract/attract_icons.json assets/attract/attract_icons.png tools/build_attract_icons.py tools/sprite_pipeline.py tools/attract_layout.py
	$(PYTHON) -I tools/build_attract_icons.py --out $(BUILDDIR)/gen/attract_icons.h --fix-base 0x400
$(BUILDDIR)/gen/tripmeter.fix $(BUILDDIR)/gen/tripmeter.h &: assets/tripmeter/tripmeter_sheet.png assets/tripmeter/tripmeter_sheet.json assets/font/fix_font.json tools/build_tripmeter_tiles.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_tripmeter_tiles.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/fix_font.fix $(BUILDDIR)/gen/fix_font.h &: assets/font/fix_font_sheet.png assets/font/fix_font.json tools/build_fix_font.py tools/sprite_pipeline.py assets/tripmeter/tripmeter_sheet.png assets/font/pop_burst.png assets/font/aim_caret.png assets/result/result_palettes.json $(BUILDDIR)/gen/tripmeter.fix
	$(PYTHON) -I tools/build_fix_font.py --out $(BUILDDIR)/gen --overlay assets/tripmeter/tripmeter_sheet.png@186 --overlay assets/font/pop_burst.png@75 --overlay assets/font/aim_caret.png@76 --extra-pal assets/result/result_palettes.json
	dd if=$(BUILDDIR)/gen/fix_font.fix bs=32 skip=954 count=13 2>/dev/null | cmp -s - $(BUILDDIR)/gen/tripmeter.fix || { echo "[FAIL] fix_font.fix tiles 954..966 differ from tripmeter.fix"; exit 1; }
$(SROM1): $(BUILDDIR)/gen/fix_font.fix $(BUILDDIR)/gen/attract_icons.fix $(BUILDDIR)/gen/result_scene.fix $(BUILDDIR)/gen/rulecard_tiles.fix $(BUILDDIR)/gen/flingmeter_tiles.fix



# sprite ROM: all your 16x16 pixel tiles for sprites
# Add your dependencies below to convert images to fixed sprite binary data
# and pack it into two separate sprite ROMs that hold odd and even bits of
# color information (referenced by symbols CROM1 and CROM2)
#
# By default, this makefile creates CROMs with tiles for displaying a ngdevkit
# logo during the attract mode.
# Note: build rules (%.gif -> %.c<1,2>) are defined in Makefile.build
# Obstacle tiles come after the logo (256 tiles = OBS_TILE_BASE in src/vram_layout.h), city tiles after the obstacles (bases in src/vram_layout.h, from the generated headers); prerequisite order = cat order.
CROM_SETS=assets/base-crom-logo gen/obs gen/city gen/dusk gen/storm gen/sootling gen/hazard gen/island gen/island_garden gen/island_deck gen/tripstrip gen/trippickup gen/triphaz gen/gum gen/logo gen/splash gen/arcade gen/resfx gen/chute gen/gumbubble gen/gumleak gen/countdown gen/rulecard gen/flfield gen/tosspose gen/stadium gen/popdrop gen/popdropsky gen/poop
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
$(BUILDDIR)/gen/sootling.c1 $(BUILDDIR)/gen/sootling.c2 $(BUILDDIR)/gen/sootling_sprites.c $(BUILDDIR)/gen/sootling_sprites.h $(BUILDDIR)/gen/sootling_tables.h &: assets/flier/sootling_sheet.png assets/flier/sootling_sheet.json tools/build_flier_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_flier_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/sootling_sprites.o: $(BUILDDIR)/gen/sootling_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Obstacle sprite pipeline (tools/build_obstacle_sprites.py, shared module tools/sprite_pipeline.py).
# The sheet itself is drawn by tools/draw_obstacle_sheet.py and committed under assets/obstacles/.
$(BUILDDIR)/gen/obs.c1 $(BUILDDIR)/gen/obs.c2 $(BUILDDIR)/gen/obs_sprites.c $(BUILDDIR)/gen/obs_sprites.h &: assets/obstacles/obstacle_sheet.png assets/obstacles/obstacle_sheet.json tools/build_obstacle_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_obstacle_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/obs_sprites.o: $(BUILDDIR)/gen/obs_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# City background sprite pipeline (tools/build_city_sprites.py over tools/sprite_pipeline.py).
# The sheet is stacked from the draft planes by tools/import_bg_sheet.py and committed under assets/city/.
$(BUILDDIR)/gen/city.c1 $(BUILDDIR)/gen/city.c2 $(BUILDDIR)/gen/city_sprites.c $(BUILDDIR)/gen/city_sprites.h $(BUILDDIR)/gen/city_tables.h &: assets/city/city_sheet.png assets/city/city_sheet.json tools/build_city_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_city_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/city_sprites.o: $(BUILDDIR)/gen/city_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Dusk mood planes: same importer (tools/import_bg_sheet.py dusk), same plane layout as the moon, own tiles and palettes.
$(BUILDDIR)/gen/dusk.c1 $(BUILDDIR)/gen/dusk.c2 $(BUILDDIR)/gen/dusk_sprites.c $(BUILDDIR)/gen/dusk_sprites.h $(BUILDDIR)/gen/dusk_tables.h &: assets/dusk/dusk_sheet.png assets/dusk/dusk_sheet.json tools/build_dusk_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_dusk_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/dusk_sprites.o: $(BUILDDIR)/gen/dusk_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Storm mood planes: same importer (tools/import_bg_sheet.py storm), same plane layout as the moon, own tiles and palettes (STORM-1).
$(BUILDDIR)/gen/storm.c1 $(BUILDDIR)/gen/storm.c2 $(BUILDDIR)/gen/storm_sprites.c $(BUILDDIR)/gen/storm_sprites.h $(BUILDDIR)/gen/storm_tables.h &: assets/storm/storm_sheet.png assets/storm/storm_sheet.json tools/build_storm_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_storm_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/storm_sprites.o: $(BUILDDIR)/gen/storm_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@

# Hazard strip sprite set (tools/build_hazard_sprites.py over tools/sprite_pipeline.py). The sheet is cut from
# assets/hazard/frames_*_1x.png by assets/hazard/build_sheet.py and committed under assets/hazard/.
$(BUILDDIR)/gen/hazard.c1 $(BUILDDIR)/gen/hazard.c2 $(BUILDDIR)/gen/hazard_sprites.c $(BUILDDIR)/gen/hazard_sprites.h $(BUILDDIR)/gen/hazard_tables.h &: assets/hazard/hazard_sheet.png assets/hazard/hazard_sheet.json tools/build_hazard_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_hazard_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/hazard_sprites.o: $(BUILDDIR)/gen/hazard_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@

# Floating island sprite set (tools/build_island_sprites.py over tools/sprite_pipeline.py). The sheet is imported from the
# island drawing by tools/import_islands_sheet.py and committed under assets/islands/. C-ROM position: after the hazard set.
$(BUILDDIR)/gen/island.c1 $(BUILDDIR)/gen/island.c2 $(BUILDDIR)/gen/island_sprites.c $(BUILDDIR)/gen/island_sprites.h $(BUILDDIR)/gen/island_tables.h &: assets/islands/island_sheet.png assets/islands/island_sheet.json tools/build_island_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_island_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/island_sprites.o: $(BUILDDIR)/gen/island_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# The garden and deck looks: same pipeline, one set each, placed directly after the roof set (24 tiles and one palette each).
$(BUILDDIR)/gen/island_%.c1 $(BUILDDIR)/gen/island_%.c2 $(BUILDDIR)/gen/island_%_sprites.c $(BUILDDIR)/gen/island_%_sprites.h $(BUILDDIR)/gen/island_%_tables.h: assets/islands/island_%_sheet.png assets/islands/island_%_sheet.json tools/build_island_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_island_sprites.py --look $* --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/island_garden_sprites.o: $(BUILDDIR)/gen/island_garden_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
$(BUILDDIR)/gen/island_deck_sprites.o: $(BUILDDIR)/gen/island_deck_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@

# Gum Trip kill strip sprite set (tools/build_tripstrip_sprites.py over tools/sprite_pipeline.py). Sheet imported from
# thoughts/shared/drafts/2026-11-11-gum-trip-import/ and committed under assets/tripstrip/. C-ROM position: after the island set.
$(BUILDDIR)/gen/tripstrip.c1 $(BUILDDIR)/gen/tripstrip.c2 $(BUILDDIR)/gen/tripstrip_sprites.c $(BUILDDIR)/gen/tripstrip_sprites.h $(BUILDDIR)/gen/tripstrip_tables.h &: assets/tripstrip/tripstrip_sheet.png assets/tripstrip/tripstrip_sheet.json tools/build_tripstrip_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_tripstrip_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/tripstrip_sprites.o: $(BUILDDIR)/gen/tripstrip_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Gum Trip pickup sprite set (step V3): idle and collect animations, one palette. C-ROM position: after the kill strip set.
$(BUILDDIR)/gen/trippickup.c1 $(BUILDDIR)/gen/trippickup.c2 $(BUILDDIR)/gen/trippickup_sprites.c $(BUILDDIR)/gen/trippickup_sprites.h $(BUILDDIR)/gen/trippickup_tables.h &: assets/trippickup/trippickup_sheet.png assets/trippickup/trippickup_sheet.json tools/build_trippickup_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_trippickup_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/trippickup_sprites.o: $(BUILDDIR)/gen/trippickup_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
$(BUILDDIR)/gen/triphaz.c1 $(BUILDDIR)/gen/triphaz.c2 $(BUILDDIR)/gen/triphaz_sprites.c $(BUILDDIR)/gen/triphaz_sprites.h $(BUILDDIR)/gen/triphaz_tables.h &: assets/triphaz/triphaz_sheet.png assets/triphaz/triphaz_sheet.json tools/build_triphaz_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_triphaz_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/triphaz_sprites.o: $(BUILDDIR)/gen/triphaz_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
$(BUILDDIR)/gen/gum.c1 $(BUILDDIR)/gen/gum.c2 $(BUILDDIR)/gen/gum_sprites.c $(BUILDDIR)/gen/gum_sprites.h $(BUILDDIR)/gen/gum_tables.h &: assets/gum/gum_sheet.png assets/gum/gum_sheet.json tools/build_gum_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_gum_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/gum_sprites.o: $(BUILDDIR)/gen/gum_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Splash of a flier in water or lava: both strips stacked into one sheet by the build script. C-ROM position: last, after the logo.
$(BUILDDIR)/gen/splash.c1 $(BUILDDIR)/gen/splash.c2 $(BUILDDIR)/gen/splash_sprites.c $(BUILDDIR)/gen/splash_sprites.h $(BUILDDIR)/gen/splash_tables.h &: assets/splash/splash_water_1x.png assets/splash/splash_lava_1x.png assets/splash/splash_gum_1x.png assets/splash/splash.json tools/build_splash_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_splash_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/splash_sprites.o: $(BUILDDIR)/gen/splash_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Arcade stage elements (tools/build_arcade_sprites.py over assets/arcade/, made by tools/import_arcade_sheet.py). C-ROM position: last, after the splash.
$(BUILDDIR)/gen/arcade.c1 $(BUILDDIR)/gen/arcade.c2 $(BUILDDIR)/gen/arcade_sprites.c $(BUILDDIR)/gen/arcade_sprites.h $(BUILDDIR)/gen/arcade_tables.h &: assets/arcade/arcade_sheet.png assets/arcade/arcade_sheet.json tools/build_arcade_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_arcade_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/arcade_sprites.o: $(BUILDDIR)/gen/arcade_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Bonus result screen (tools/build_result_art.py paints all of it): the still scene for the S-ROM (after the attract icons), the baked bubble
# paths, and the moving parts as the resfx sprite set. C-ROM position: last, after the arcade set.
$(BUILDDIR)/gen/resfx.c1 $(BUILDDIR)/gen/resfx.c2 $(BUILDDIR)/gen/resfx_sprites.c $(BUILDDIR)/gen/resfx_sprites.h $(BUILDDIR)/gen/resfx_tables.h $(BUILDDIR)/gen/result_scene.fix $(BUILDDIR)/gen/result_scene.h $(BUILDDIR)/gen/result_paths.h &: assets/result/result_palettes.json tools/build_result_art.py tools/build_attract_icons.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_result_art.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/resfx_sprites.o: $(BUILDDIR)/gen/resfx_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Parachute (variant C, both palettes) over a flier in state PARACHUTE. C-ROM position: last, after the result sprites, so no earlier tile base moves.
$(BUILDDIR)/gen/chute.c1 $(BUILDDIR)/gen/chute.c2 $(BUILDDIR)/gen/chute_sprites.c $(BUILDDIR)/gen/chute_sprites.h $(BUILDDIR)/gen/chute_tables.h &: assets/chute/chute_sheet.png assets/chute/chute_sheet.json tools/build_chute_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_chute_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/chute_sprites.o: $(BUILDDIR)/gen/chute_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Gum bubble B (Hot Gum, not drawn in play yet): 7 cells 16x16 + the frame sequence in gumbubble_tables.h. C-ROM position: last, after the parachute, so no earlier tile base moves.
$(BUILDDIR)/gen/gumbubble.c1 $(BUILDDIR)/gen/gumbubble.c2 $(BUILDDIR)/gen/gumbubble_sprites.c $(BUILDDIR)/gen/gumbubble_sprites.h $(BUILDDIR)/gen/gumbubble_tables.h &: assets/gum_bubble/gum_bubble_sheet.png assets/gum_bubble/gum_bubble_sheet.json tools/build_gumbubble_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_gumbubble_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/gumbubble_sprites.o: $(BUILDDIR)/gen/gumbubble_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Toss Gum poses: 8 cells 32x32 (tools/make_toss_sheet.py) + the gum anchor per pose in tosspose_tables.h. C-ROM position: last, so no earlier tile base moves.
$(BUILDDIR)/gen/tosspose.c1 $(BUILDDIR)/gen/tosspose.c2 $(BUILDDIR)/gen/tosspose_sprites.c $(BUILDDIR)/gen/tosspose_sprites.h $(BUILDDIR)/gen/tosspose_tables.h &: assets/toss/toss_sheet.png assets/toss/toss_sheet.json tools/build_tosspose_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_tosspose_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/tosspose_sprites.o: $(BUILDDIR)/gen/tosspose_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Gum leak (air jet + hole over a damaged bubble, 12 frames of 32x16). C-ROM position: last, after the gum bubble set, so no earlier tile base moves.
$(BUILDDIR)/gen/gumleak.c1 $(BUILDDIR)/gen/gumleak.c2 $(BUILDDIR)/gen/gumleak_sprites.c $(BUILDDIR)/gen/gumleak_sprites.h $(BUILDDIR)/gen/gumleak_tables.h &: assets/gum_leak/gum_leak_sheet.png assets/gum_leak/gum_leak_sheet.json tools/build_gumleak_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_gumleak_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/gumleak_sprites.o: $(BUILDDIR)/gen/gumleak_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Countdown GET SET / GO! (A2, Pink Gum + Hot Gum swap, not drawn yet): 6 + 3 glyph frames in whole 16x32 columns + glyph x tables in countdown_tables.h. C-ROM position: last, after the gum leak, so no earlier tile base moves.
$(BUILDDIR)/gen/countdown.c1 $(BUILDDIR)/gen/countdown.c2 $(BUILDDIR)/gen/countdown_sprites.c $(BUILDDIR)/gen/countdown_sprites.h $(BUILDDIR)/gen/countdown_tables.h &: assets/countdown/countdown_sheet.png assets/countdown/countdown_sheet.json tools/build_countdown_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_countdown_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/countdown_sprites.o: $(BUILDDIR)/gen/countdown_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Gum Games rules card (layout A): 12 fix tiles (button A up / down, bar segments) after the result scene in the S-ROM, and 5 example props (slab, needles, gum, dot) last in the C-ROM, so no earlier tile base moves. Art: tools/draw_rulecard_art.py.
$(BUILDDIR)/gen/rulecard_tiles.h $(BUILDDIR)/gen/rulecard_tiles.fix &: assets/rulecard/rulecard_fix.png tools/build_rulecard_tiles.py tools/build_attract_icons.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_rulecard_tiles.py --out $(BUILDDIR)/gen/rulecard_tiles.h

$(BUILDDIR)/gen/flingmeter_tiles.h $(BUILDDIR)/gen/flingmeter_tiles.fix &: tools/build_flingmeter_tiles.py tools/flingmeter_art.py tools/build_attract_icons.py tools/sprite_pipeline.py $(BUILDDIR)/gen/rulecard_tiles.h
	$(PYTHON) -I tools/build_flingmeter_tiles.py --out $(BUILDDIR)/gen/flingmeter_tiles.h
$(BUILDDIR)/gen/rulecard.c1 $(BUILDDIR)/gen/rulecard.c2 $(BUILDDIR)/gen/rulecard_sprites.c $(BUILDDIR)/gen/rulecard_sprites.h &: assets/rulecard/rulecard_sheet.png assets/rulecard/rulecard_sheet.json tools/build_rulecard_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_rulecard_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/rulecard_sprites.o: $(BUILDDIR)/gen/rulecard_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Gum Fling field (turf, chalk line, distance boards, dust puff; hand-pixeled grids in tools/draw_fling_field.py, 3 mood palettes), last in the C-ROM.
$(BUILDDIR)/gen/flfield.c1 $(BUILDDIR)/gen/flfield.c2 $(BUILDDIR)/gen/flfield_sprites.c $(BUILDDIR)/gen/flfield_sprites.h $(BUILDDIR)/gen/flfield_tables.h &: tools/draw_fling_field.py tools/build_flfield_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_flfield_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/flfield_sprites.o: $(BUILDDIR)/gen/flfield_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Stadium stands for the ground events (every unique tile of the hand-pixeled stand art in assets/stadium/, 3 mood palettes x teams), after the Fling field.
$(BUILDDIR)/gen/stadium.c1 $(BUILDDIR)/gen/stadium.c2 $(BUILDDIR)/gen/stadium_sprites.c $(BUILDDIR)/gen/stadium_sprites.h $(BUILDDIR)/gen/stadium_tables.h $(BUILDDIR)/gen/stadium_motion.h $(BUILDDIR)/gen/stadium_layout.h &: assets/stadium/draw_stadium.py assets/stadium/draw_polish.py tools/draw_fling_field.py tools/build_stadium_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_stadium_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/src/core/stadium.o: $(BUILDDIR)/gen/stadium_motion.h src/core/stadium.h
$(BUILDDIR)/gen/stadium_sprites.o: $(BUILDDIR)/gen/stadium_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
$(BUILDDIR)/gen/popdrop.c1 $(BUILDDIR)/gen/popdrop.c2 $(BUILDDIR)/gen/popdrop_sprites.c $(BUILDDIR)/gen/popdrop_sprites.h $(BUILDDIR)/gen/popdrop_tables.h &: assets/popdrop/popdrop_sheet.png assets/popdrop/popdrop_sheet.json tools/build_popdrop_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_popdrop_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/popdrop_sprites.o: $(BUILDDIR)/gen/popdrop_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Pop Drop summer sky (draft v3 take B: 13-blue line-dither sky tiles and 8 clouds, assets/popdropsky), last in CROM_SETS.
$(BUILDDIR)/gen/popdropsky.c1 $(BUILDDIR)/gen/popdropsky.c2 $(BUILDDIR)/gen/popdropsky_sprites.c $(BUILDDIR)/gen/popdropsky_sprites.h $(BUILDDIR)/gen/popdropsky_tables.h &: assets/popdropsky/popdropsky_sheet.png assets/popdropsky/popdropsky_sheet.json tools/build_popdropsky_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_popdropsky_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/popdropsky_sprites.o: $(BUILDDIR)/gen/popdropsky_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Poop the Man walkers, umbrellas, poop, splats, shoes, berry (assets/poop, cut by tools/import_poop_sheet.py), last in CROM_SETS.
$(BUILDDIR)/gen/poop.c1 $(BUILDDIR)/gen/poop.c2 $(BUILDDIR)/gen/poop_sprites.c $(BUILDDIR)/gen/poop_sprites.h $(BUILDDIR)/gen/poop_tables.h &: assets/poop/poop_sheet.png assets/poop/poop_sheet.json tools/build_poop_sprites.py tools/sprite_pipeline.py
	$(PYTHON) -I tools/build_poop_sprites.py --out $(BUILDDIR)/gen
$(BUILDDIR)/gen/poop_sprites.o: $(BUILDDIR)/gen/poop_sprites.c
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@
# Title logo (tools/build_logo_sprites.py over assets/logo/): animated strips and free pieces, no .c file (macros only in logo_sprites.h). C-ROM position: after the gum set, so no earlier tile base moves.
$(BUILDDIR)/gen/logo.c1 $(BUILDDIR)/gen/logo.c2 $(BUILDDIR)/gen/logo_sprites.h &: assets/logo/logo_rim.json assets/logo/logo_rim_frames_1x.png assets/logo/logo_rim_pieces_1x.png assets/logo/logo_pieces.json tools/build_logo_sprites.py
	$(PYTHON) -I tools/build_logo_sprites.py --out $(BUILDDIR)/gen

$(BUILDDIR)/src/main.o $(BUILDDIR)/src/bg.o $(BUILDDIR)/src/gfx.o $(BUILDDIR)/src/hazard.o $(BUILDDIR)/src/island.o $(BUILDDIR)/src/trip_strip.o $(BUILDDIR)/src/fling_field.o $(BUILDDIR)/src/stadium_hw.o $(BUILDDIR)/src/trip_pickup.o $(BUILDDIR)/src/gum.o $(BUILDDIR)/src/logo.o $(BUILDDIR)/src/splash.o $(BUILDDIR)/src/core/sprite_budget.o $(BUILDDIR)/src/core/island_layout.o $(BUILDDIR)/src/core/banner.o $(BUILDDIR)/src/core/result_view.o $(BUILDDIR)/src/core/result.o: $(BUILDDIR)/gen/result_scene.h $(BUILDDIR)/gen/result_paths.h $(BUILDDIR)/gen/resfx_sprites.h $(BUILDDIR)/gen/chute_sprites.h $(BUILDDIR)/gen/gumbubble_sprites.h $(BUILDDIR)/gen/tosspose_sprites.h $(BUILDDIR)/gen/gumleak_sprites.h $(BUILDDIR)/gen/gumleak_tables.h $(BUILDDIR)/gen/countdown_sprites.h $(BUILDDIR)/gen/countdown_tables.h $(BUILDDIR)/gen/rulecard_sprites.h $(BUILDDIR)/gen/popdrop_sprites.h $(BUILDDIR)/gen/popdropsky_sprites.h $(BUILDDIR)/gen/poop_sprites.h $(BUILDDIR)/gen/flfield_sprites.h $(BUILDDIR)/gen/stadium_sprites.h $(BUILDDIR)/gen/stadium_layout.h src/stadium_hw.h $(BUILDDIR)/gen/rulecard_tiles.h $(BUILDDIR)/gen/flingmeter_tiles.h $(BUILDDIR)/gen/fix_font.h $(BUILDDIR)/gen/attract_icons.h src/core/attract_overlay.h $(BUILDDIR)/gen/tripmeter.h $(BUILDDIR)/gen/island_tables.h $(BUILDDIR)/gen/city_tables.h $(BUILDDIR)/gen/dusk_tables.h $(BUILDDIR)/gen/storm_tables.h $(BUILDDIR)/gen/island_sprites.h $(BUILDDIR)/gen/island_garden_sprites.h $(BUILDDIR)/gen/island_deck_sprites.h $(BUILDDIR)/gen/tripstrip_sprites.h $(BUILDDIR)/gen/tripstrip_tables.h $(BUILDDIR)/gen/trippickup_sprites.h $(BUILDDIR)/gen/trippickup_tables.h $(BUILDDIR)/gen/triphaz_sprites.h $(BUILDDIR)/gen/triphaz_tables.h $(BUILDDIR)/gen/gum_sprites.h $(BUILDDIR)/gen/gum_tables.h $(BUILDDIR)/gen/logo_sprites.h src/logo.h $(BUILDDIR)/gen/splash_sprites.h $(BUILDDIR)/gen/splash_tables.h $(BUILDDIR)/gen/arcade_sprites.h $(BUILDDIR)/gen/arcade_tables.h src/splash.h src/core/splash_view.h $(BUILDDIR)/gen/hazard_sprites.h $(BUILDDIR)/gen/obs_sprites.h $(BUILDDIR)/gen/city_sprites.h $(BUILDDIR)/gen/dusk_sprites.h $(BUILDDIR)/gen/storm_sprites.h $(BUILDDIR)/gen/sootling_sprites.h src/core/flier_view.h src/core/gum_view.h src/vram_layout.h src/sprite_slots.h src/bg.h src/gfx.h src/hazard.h src/island.h src/core/island_layout.h src/core/vram_queue.h



# sound driver ROM: nullsound (Z80) + generated command table, built from source by gmake.
# Plan: thoughts/shared/plans/2026-11-09-sound-driver.md. Nothing under build/sound is committed.
#   assets/sound/*.yaml            music and sample maps (soundtool.py)
#   tools/make_standin_fur.py      stand-in music (no upstream asset copied, licence unclear)
#   tools/make_sfx.py              sound effect WAVs (offline synthesis, needs numpy; about one minute)
# Generation order: `gmake` runs the sound-gen target (CUSTOM_GENERATE_TARGETS) before anything is
# compiled, so build/snd_commands.h exists for the 68k and nss-deps.mk exists for the include below.
SOUND_DIR=$(BUILDDIR)/sound
SOUND_YAMLS=assets/sound/music-map.yaml assets/sound/sample-map.yaml
SFX_NAMES=splosh spike sizzle vent_warn vent_burst grab_rise grab_bite grate flipper pop_a pop_b pop_c bubble_puff bump die life_lost chute perfect gum_low hit pump_a pump_b rival_launch defeat rival_warn flap_a flap_b flap_c fall coin start round_go banner_in tally_tick tally_bonus continue_tick continue_yes ne_move ne_confirm ne_done pickup pickup_streak
SFX_WAVS=$(SFX_NAMES:%=$(SOUND_DIR)/sfx/%.wav)
SOUND_DRIVER=$(SOUND_DIR)/driver.ihx

# grouped target (&:): one run writes every WAV
$(SFX_WAVS) &: tools/make_sfx.py
	mkdir -p $(@D)
	$(PYTHON) -I tools/make_sfx.py $(SOUND_DIR)/sfx $(SFX_NAMES)
SOUND_ASSETS=$(SFX_WAVS)

# build.mk recipes read the maps through $^, so the generated assets are order-only prerequisites
# (they exist before soundtool/vromtool run). After changing a generator script run `gmake generate`.
$(VROM1) $(Z80_SAMPLES_IN_VROM) $(Z80_SOUND_COMMANDS) $(SOUND_COMMANDS): $(SOUND_YAMLS) | $(SOUND_ASSETS)
# On a fresh clone this first runs while config.mk is still being generated (SOUNDTOOL empty; -include ignores the error).
# Write via a temp file so a failed run leaves no empty nss-deps.mk hiding the nss_<name> rules; the restarted make rebuilds it.
$(SOUND_DIR)/nss-deps.mk: $(SOUND_YAMLS)
	mkdir -p $(@D)
	$(SOUNDTOOL) -m -s $^ > $@.tmp && mv $@.tmp $@
-include $(SOUND_DIR)/nss-deps.mk

$(BUILDDIR)/src/sound/user_commands.rel: src/sound/user_commands.s $(Z80_SAMPLES_IN_VROM) $(Z80_SOUND_COMMANDS)
	mkdir -p $(@D)
	$(Z80SDAS) -g -l -p -u -I$(NGZ80INCLUDEDIR)/nullsound -I$(BUILDDIR) -o $@ $<
# Patched SSG driver (noise period byte for furtool_noise.py): linked before nullsound.lib so the lib member is not pulled.
SSG_NOISE_REL=$(BUILDDIR)/src/sound/nss-ssg.rel
SSG_NOISE_LIB=$(SOUND_DIR)/nullsound-noise.lib
$(SSG_NOISE_REL): tools/nullsound/nss-ssg.s
	mkdir -p $(@D)
	$(Z80SDAS) -a -g -l -p -s -u -Itools/nullsound -I$(NGZ80INCLUDEDIR)/nullsound -o $@ $<
# nullsound.lib is linked whole (concatenated objects), so the stock SSG module is cut out of a copy.
$(SSG_NOISE_LIB): tools/patch_nullsound_lib.py
	mkdir -p $(@D)
	$(PYTHON) -I tools/patch_nullsound_lib.py $(NGZ80LIBDIR)/nullsound.lib $@
# link order matters: the lib declares the CODE area first (at 0); with nss-ssg.rel first the struct area landed at 0 and CODE at 0xff99
$(SOUND_DRIVER): $(SSG_NOISE_REL) $(SSG_NOISE_LIB) $(BUILDDIR)/src/sound/user_commands.rel
	mkdir -p $(@D)
	$(Z80SDLD) -m -b DATA=0xf800 -i $@ $(SSG_NOISE_LIB) $(SSG_NOISE_REL) $(filter-out $(SSG_NOISE_REL) $(SSG_NOISE_LIB),$^)
	grep -q "src/sound/nss-ssg.rel" $(@:.ihx=.map) || { echo "patched nss-ssg not linked"; exit 1; }
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


# ---- Gumbirds targets (see RULES.md) ----
.DEFAULT_GOAL := all

# Window run, MVS BIOS, backup RAM kept in nvram/
# Windowed, 3x native 320x224, so dev runs never grab the whole screen. -artpath: the crt-geom
# chains load their aperture PNGs from artwork/bgfx/...; the default artpath is ./artwork, so
# without it MAME logged "Unable to load chain ... falling back to no post processing".
MAME_SHADER?=crt-geom-deluxe
BRAWL_WINDOW_FLAGS=-window -nomaximize -resolution 960x672 -nofilter -video bgfx -bgfx_path $(shell brew --prefix)/share/mame/bgfx -bgfx_screen_chains $(MAME_SHADER) -artpath $(shell brew --prefix)/share/mame/artwork
# UniBIOS 4.0 for make run only (user decision 2026-11-09). The zip is never copied into the
# repo: build/unibios/neogeo.zip = nullbios files + uni-bios_4_0.rom, searched before $(ROM).
# Missing UNIBIOS file: make run falls back to nullbios. make test uses nullbios except test-reach (UniBIOS).
# Project copy bios/uni-bios-40.zip (git-ignored by *.zip, never committed) wins; else the download dir.
UNIBIOS?=$(firstword $(wildcard bios/uni-bios-40.zip) $(HOME)/Downloads/uni-bios-40.zip)
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
	$(MAME) $(BRAWL_WINDOW_FLAGS) -noautosave -skip_gameinfo -hash $(ROM) $(RUN_BIOS_FLAGS) -nvram_directory nvram neogeo -cart1 $(GAMEROM)


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
# The S-ROM must start with the generated font (FIXFONT_SROM_TILES tiles) and be SROMSIZE bytes (the rest zero); UniBIOS prints ASCII
# codes (tile = code, 0x100 + code, 0x200 + code), so the glyphs of "A" on all three pages must be drawn and tile 0xFF blank.
.PHONY: test-srom
test-srom: cart
	@f=$(ROM)/$(GAMEROM)-s1.s1; \
	[ `wc -c < $$f` -eq $(SROMSIZE) ] || { echo "[FAIL] test-srom: $$f is not $(SROMSIZE) bytes"; exit 1; }; \
	head -c `wc -c < $(BUILDDIR)/gen/fix_font.fix` $$f | cmp -s - $(BUILDDIR)/gen/fix_font.fix || { echo "[FAIL] test-srom: $$f does not start with fix_font.fix"; exit 1; }; \
	blank() { dd if=$$f bs=32 skip=$$1 count=1 2>/dev/null | tr -d '\000' | wc -c | tr -d ' '; }; \
	for t in 65 321 577; do [ `blank $$t` -ne 0 ] || { echo "[FAIL] test-srom: ASCII tile $$t (0x41 / 0x141 / 0x241) is blank, UniBIOS text needs it"; exit 1; }; done; \
	for t in `seq 512 543` 576 606; do [ `blank $$t` -eq 0 ] || { echo "[FAIL] test-srom: UniBIOS boot slot $$t must stay blank (tiles 0x200-0x21F, 0x240, 0x25E)"; exit 1; }; done; \
	for t in 278 279 320 350 752; do [ `blank $$t` -ne 0 ] || { echo "[FAIL] test-srom: tile $$t (0x116/0x117 rule, tall '@'/'^' top 0x140/0x15E, moved @ bottom 0x2F0) is blank"; exit 1; }; done; \
	[ `blank 255` -eq 0 ] || { echo "[FAIL] test-srom: tile 0xFF is not blank"; exit 1; }; \
	echo "[OK] test-srom: S-ROM is the Gumdrop font at tile 0x300, ASCII pages 0..2 and blank 0xFF, $(SROMSIZE) bytes"
# Compile-only check of the debug header build (DEBUG_HEADER=1): src/main.c with -DGUMBIRDS_DEBUG_HEADER into its own object dir,
# so the normal objects are untouched and no gmake clean is needed. A compile error fails the target.
test-debug-header: cart
	@mkdir -p $(BUILDDIR)/debug-header
	@$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -DGUMBIRDS_DEBUG_HEADER -c src/main.c -o $(BUILDDIR)/debug-header/main.o && echo "[OK] test-debug-header: src/main.c compiles with GUMBIRDS_DEBUG_HEADER"
test: cart
	nice -n 19 tests/host/run.sh
	@$(MAKE) --no-print-directory test-debug-header
	@$(MAKE) --no-print-directory test-crom
	@$(MAKE) --no-print-directory test-srom
	@$(MAKE) --no-print-directory test-flier
	@$(MAKE) --no-print-directory test-arcade
	@$(MAKE) --no-print-directory test-small-sootling
	@$(MAKE) --no-print-directory test-reach
	@$(MAKE) --no-print-directory test-vblank
	@$(MAKE) --no-print-directory test-left-column
	@$(MAKE) --no-print-directory test-scroll
	@$(MAKE) --no-print-directory test-slots
	@$(MAKE) --no-print-directory test-hazard
	@$(MAKE) --no-print-directory test-score
	@$(MAKE) --no-print-directory test-hazard-kill
	@$(MAKE) --no-print-directory test-soft-reset
	@$(MAKE) --no-print-directory test-ring
	@$(MAKE) --no-print-directory test-logo
	@$(MAKE) --no-print-directory test-solid
	@$(MAKE) --no-print-directory test-trip
	@$(MAKE) --no-print-directory test-title-pause
	@$(MAKE) --no-print-directory test-arena-join
	@$(MAKE) --no-print-directory test-party
	@$(MAKE) --no-print-directory test-party-toss
	@$(MAKE) --no-print-directory test-gum-big-blow
	@$(MAKE) --no-print-directory test-gum-visible
	@$(MAKE) --no-print-directory test-gum-burst-race
	@$(MAKE) --no-print-directory test-gum-burst-race-2p
	@$(MAKE) --no-print-directory test-gum-flap-dash
	@$(MAKE) --no-print-directory test-gum-bubble-gather
	@$(MAKE) --no-print-directory test-gum-bubble-gather-fail
	@$(MAKE) --no-print-directory test-gum-pop-drop
	@$(MAKE) --no-print-directory test-gum-fling
	@$(MAKE) --no-print-directory test-party-roost
	@$(MAKE) --no-print-directory test-party-name
	@$(MAKE) --no-print-directory test-coop
	@$(MAKE) --no-print-directory test-sound
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_HISCORE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_image"{print $$1}') \
	BRAWL_HISCORE_SIZE=$$($(NM) -S $(ELF) | awk '$$4=="g_hiscore_image"{print $$2}') \
	BRAWL_BG_X_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_plane_x"{print $$1}') \
	BRAWL_BG_WRITES_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_x_writes"{print $$1}') \
	BRAWL_MOOD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood"{print $$1}') \
	BRAWL_FIXFONT_H=$(BUILDDIR)/gen/fix_font.h \
	BRAWL_RESULT=$$T/result.txt \
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
	BRAWL_PAIR_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flier_pair_calls"{print $$1}') \
	BRAWL_SENT_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_sound_sent"{print $$1}') \
	BRAWL_LAST_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_sound_last"{print $$1}') \
	BRAWL_BLOCKED_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flier_pair_blocked"{print $$1}') \
	BRAWL_CEIL_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flier_ceiling_hits"{print $$1}') \
	BRAWL_CEILRIVAL_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flier_ceiling_rival_hits"{print $$1}') \
	BRAWL_SOOT_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_soot_range"{print $$1}') \
	BRAWL_SOOTVIEW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_soot_view"{print $$1}') \
	BRAWL_RE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_round_end_s"{print $$1}') \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_STAGE_ADDR=$$($(NM) $(ELF) | awk '$$3=="stage_platforms"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_SOOT_TABLES=$(BUILDDIR)/gen/sootling_tables.h \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/flier_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from flier Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-flier passed"; else echo "[FAIL] make test-flier, log kept in $$T"; exit 1; fi

# Gum leak jets exist at one balloon and draw above their bubble (tests/mame/leak_check.lua). Run by `make test-leak` alone.
test-leak: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_POOL_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_pool"{print $$1}') \
	BRAWL_LEAKIDX_ADDR=$$($(NM) $(ELF) | awk '$$3=="gumleak_tile_index"{print $$1}') \
	BRAWL_PUMP_FIRST=$$(awk '/SOOTLING_TABLE_CLIP_FIRST/{print $$8+0}' $(BUILDDIR)/gen/sootling_tables.h) \
	BRAWL_PUMP_COUNT=$$(awk '/SOOTLING_TABLE_CLIP_COUNT/{print $$8+0}' $(BUILDDIR)/gen/sootling_tables.h) \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/leak_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from leak Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-leak passed"; else echo "[FAIL] make test-leak, log kept in $$T"; exit 1; fi

# Arcade mode reachability (tests/mame/arcade_check.lua): coin, ARCADE on the title select, Start, stage 1, forced stage clear to stage 2
# (island VRAM words change), forced deaths to the continue state, A to continue. Run by `make test-arcade` alone.
test-arcade: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_MOOD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood"{print $$1}') \
	BRAWL_HAZARD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hazard_kind"{print $$1}') \
	BRAWL_ARCADE_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/arcade_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/arcade_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from arcade Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-arcade passed"; else echo "[FAIL] make test-arcade, log kept in $$T"; exit 1; fi

# Continue countdown out under UniBIOS (ARCADE_CONT_OUT=1, tests/mame/arcade_check.lua A7): one coin, Start, forced deaths,
# no press on the continue screen; GAME OVER, attract, the PRESS START title holds 5 minutes with no game and no credit
# taken (never force start), then one Start plays. `make test-arcade-contout` alone.
test-arcade-contout: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	ARCADE_CONT_OUT=1 \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_MOOD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood"{print $$1}') \
	BRAWL_HAZARD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hazard_kind"{print $$1}') \
	BRAWL_ARCADE_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/arcade_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 600 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/arcade_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from arcade Lua script"; exit 1; fi; \
	cat $$T/result.txt; grep -h "^BRAWL_LOG" $$T/mame.log | tail -n 40 || true; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-arcade-contout passed"; else echo "[FAIL] make test-arcade-contout, log kept in $$T"; exit 1; fi

# Attract demos (tests/mame/attract_check.lua): no input for three attract cycles; the demo phases play arena, Gum Trip, arcade in turn,
# the frame counter never stalls, a coin during the fourth demo goes to the title. About 100 s of emulated time.
test-attract: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_ATTRACT_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/attract_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 160 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/attract_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from attract Lua script"; exit 1; fi; \
	cat $$T/result.txt; grep -h "^BRAWL_TEST demo" $$T/mame.log || true; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-attract passed"; else echo "[FAIL] make test-attract, log kept in $$T"; exit 1; fi

# Per-stage frame cost walk (ARCADE_WALK=1, ~2-4 min, not in `make test`): stages 1..12, 300 frames each, prints ARC_STAGE / ARC_TOP lines in mame.log.
test-arcade-walk: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_MOOD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood"{print $$1}') \
	BRAWL_HAZARD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hazard_kind"{print $$1}') \
	BRAWL_ARCADE_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/arcade_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_round_end_s"{print $$1}') \
	BRAWL_RESULT=$$T/result.txt ARCADE_WALK=1 \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 900 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/arcade_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from arcade Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then grep -h "^ARC_\|BRAWL_TEST" $$T/mame.log; rm -rf $$T; echo "[OK] make test-arcade-walk passed"; else echo "[FAIL] make test-arcade-walk, log kept in $$T"; exit 1; fi

# RESULT_DUMP=<absolute directory> also writes every second result screen frame there as res_NNN.png.
# Bonus stage cost (ARCADE_BONUS=1): clears stages 1..3, then measures the bonus stage with 8+ bubbles alive (logic end under 224); not in `make test`.
test-arcade-bonus: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_MOOD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood"{print $$1}') \
	BRAWL_HAZARD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hazard_kind"{print $$1}') \
	BRAWL_ARCADE_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/arcade_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt ARCADE_BONUS=1 \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 600 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T $(if $(RESULT_DUMP),-snapshot_directory $(RESULT_DUMP)) -autoboot_script tests/mame/arcade_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from arcade Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then cat $$T/result.txt; grep -h "^ARC_" $$T/mame.log || true; rm -rf $$T; echo "[OK] make test-arcade-bonus passed"; else echo "[FAIL] make test-arcade-bonus, log kept in $$T"; exit 1; fi

# Small Sootling reachability (tests/mame/small_sootling_check.lua): the 24 x 32 sheet is what the real ROM draws for the
# player (art size, tile count, SCB3 height, SCB1 tiles in range, frame-select sentinel, sprite top and x from the flier
# position). Spec numbers are written in the Lua; a stale sheet fails. Run by make test; `make test-small-sootling` alone.
test-small-sootling: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_BLINK_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_blink_pool"{print $$1}') \
	BRAWL_SOOT_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_soot_range"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_SOOT_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/small_sootling_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/small_sootling_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from small Sootling Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-small-sootling passed"; else echo "[FAIL] make test-small-sootling, log kept in $$T"; exit 1; fi

# High score reachability, plan P5.1 (tests/mame/hiscore_reach.lua): boot 1 plays to game over, types the name
# REACHTST through the real name entry screen and checks the save sentinel g_hiscore_saves and backup RAM; boot 2
# on the same nvram dir checks the table holds that name and score at the same row. Run by make test.
# Runs under UniBIOS 4.0 (cabinet BIOS class): the BIOS copies .bss.bram to backup RAM after the game returns
# through SYSTEM_RETURN. Stock ngdevkit nullbios writes backup RAM without REG_SRAMUNLOCK, so nothing persists
# there (see thoughts/shared/research/2026-11-09_p51-reachability.md). Needs the UNIBIOS file.
REACH_SECONDS?=300
REACH_PARTY?=0
REACH_BIOS_FLAGS?=-rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40
test-reach: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[SKIP] UNIBIOS file not found: $(UNIBIOS)"; exit 0; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	for PH in 1 2; do \
	BRAWL_PHASE=$$PH BRAWL_PARTY=$(REACH_PARTY) \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_HISCORE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_image"{print $$1}') \
	BRAWL_SAVES_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_saves"{print $$1}') \
	BRAWL_NAMESEC_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_name_seconds_shown"{print $$1}') \
	BRAWL_REACH_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/reach_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result$$PH.txt BRAWL_EXPECT=$$T/expect.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(REACH_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) $(REACH_BIOS_FLAGS) -nvram_directory $$T/nvram -autoboot_script tests/mame/hiscore_reach.lua neogeo -cart1 $(GAMEROM) > $$T/mame$$PH.log 2>&1 || true; \
	if [ ! -f $$T/result$$PH.txt ]; then tail -n 15 $$T/mame$$PH.log 2>/dev/null || echo "[ERROR] $$T/mame$$PH.log missing: the scratch dir was deleted during the run (another session cleaning build/test-run.*?)"; echo "[FAIL] test-reach boot $$PH: no result from Lua script"; exit 1; fi; \
	cat $$T/result$$PH.txt; \
	grep -q '^PASS' $$T/result$$PH.txt || { echo "[FAIL] make test-reach boot $$PH, log kept in $$T"; exit 1; }; \
	done; rm -rf $$T; echo "[OK] make test-reach passed"

# Same run as test-reach with the run scored as a PARTY run (name entry into the party table, then the BIOS save and return).
test-reach-party:
	@$(MAKE) --no-print-directory test-reach REACH_PARTY=1

# Vblank write reachability (tests/mame/vblank_check.lua): taps the LSPC VRAM registers and palette RAM during
# a real run (attract, coin, start, scrolling) and asserts every write after boot lands in vblank.
# Run by make test; `make test-vblank` alone re-runs only this check.
test-vblank: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_PALMAX_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_pal_words_frame_max"{print $$1}') \
	BRAWL_VQ_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/vq_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/vblank_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_PALMAX_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_pal_words_frame_max"{print $$1}') \
	BRAWL_VQ_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/vq_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_DEMO=1 BRAWL_RESULT=$$T/result-demo.txt \
	BRAWL_ATTRACT_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/attract_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 160 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/vblank_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame-demo.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ] || [ ! -f $$T/result-demo.txt ]; then tail -n 15 $$T/mame.log $$T/mame-demo.log; echo "[FAIL] no result from vblank Lua script"; exit 1; fi; \
	cat $$T/result.txt $$T/result-demo.txt; \
	if ! grep -q 'FAIL' $$T/result.txt $$T/result-demo.txt; then rm -rf $$T; echo "[OK] make test-vblank passed"; else echo "[FAIL] make test-vblank, log kept in $$T"; exit 1; fi

# Background scroll reachability (tests/mame/scroll_check.lua): coin, start, play with jumps and fire, restart after
# game over; a Lua VRAM shadow asserts every PLAYING frame each of the five background planes shows the g_cam_px the
# game committed for it (no late or skipped scroll writes), sentinel: camera changes counted. Run by make test; `make test-scroll`
# alone re-runs only this check. SCROLL_LOG=<file> keeps the per-frame log.
test-scroll: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_STAGE_ADDR=$$($(NM) $(ELF) | awk '$$3=="stage_platforms"{print $$1}') \
	BRAWL_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_CAMERA_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/camera_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt BRAWL_SCROLL_LOG=$(SCROLL_LOG) \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 90 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/scroll_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from scroll Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if ! grep -q 'FAIL' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-scroll passed"; else echo "[FAIL] make test-scroll, log kept in $$T"; exit 1; fi

# Sprite draw-order proof (tests/mame/slot_order_check.lua): a copy of a live pool sprite in a background plane slot
# is hidden by the pool, a copy in a slot above the hero covers it (src/sprite_slots.h). Run by make test;
# `make test-slots` alone re-runs only this check.
test-slots: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_ISLAND_DRAWS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_island_draws"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_STAGE_PLATFORMS="$$(sed -n 's/^#define R01_PLAT//p' src/core/stage.c | grep -o '[0-9][0-9]*' | tr '\n' ' ')" \
	BRAWL_SLOT_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/slot_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 30 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/slot_order_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from slot order Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-slots passed"; else echo "[FAIL] make test-slots, log kept in $$T"; exit 1; fi

# Hazard strip (tests/mame/hazard_check.lua, build plan G3): the strip is on lines 192..223, shows 16 distinct frames over
# its two banks at the active hazard's speed, the CPU writes no SCB1 word while it runs (only the bank swap writes
# SCB3), nothing is written outside vblank, and the palette stays within its limit. `make test-hazard` alone re-runs it.
test-hazard: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_STAGE_ADDR=$$($(NM) $(ELF) | awk '$$3=="stage_platforms"{print $$1}') \
	BRAWL_KIND_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hazard_kind"{print $$1}') \
	BRAWL_SPEED_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_autoanim_frames"{print $$1}') \
	BRAWL_SWAPS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_swap_count"{print $$1}') \
	BRAWL_MATCHES_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hazard_matches"{print $$1}') \
	BRAWL_PALMAX_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_pal_words_frame_max"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_LASTUS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_last_us"{print $$1}') \
	BRAWL_RE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_round_end_s"{print $$1}') \
	BRAWL_ISLAND_STEP="$$(sed -n 's/^.define ISLAND_STEP_FRAMES *\([0-9]*\).*/\1/p' $(BUILDDIR)/gen/island_tables.h)" \
	BRAWL_HAZARD_STEPS="$$(sed -n 's/.*HAZARD_TABLE_STEP_FRAMES *{\(.*\)}.*/\1/p' $(BUILDDIR)/gen/hazard_tables.h)" \
	BRAWL_HAZARD_VARIANTS="$$(sed -n 's/.*HAZARD_TABLE_VARIANTS *{\(.*\)}.*/\1/p' $(BUILDDIR)/gen/hazard_tables.h)" \
	BRAWL_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_HAZARD_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/hazard_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 150 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/hazard_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from hazard Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-hazard passed"; else echo "[FAIL] make test-hazard, log kept in $$T"; exit 1; fi

# Hazard kill lines (tests/mame/hazard_kill_check.lua, build plan P6-4/P6-5): four plays in a row show spikes, fire, water
# and lava; per kind Game.hazard_kind equals g_hazard_kind, the flier lives with its feet 1 px above the spec kill line and
# drowns on it, and the hero slots sit below the hazard slots (hero drawn behind the strip). `make test-hazard-kill` alone.
test-hazard-kill: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_KIND_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hazard_kind"{print $$1}') \
	BRAWL_STAGE_ADDR=$$($(NM) $(ELF) | awk '$$3=="stage_platforms"{print $$1}') \
	BRAWL_RE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_round_end_s"{print $$1}') \
	BRAWL_SENT_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_sound_sent"{print $$1}') \
	BRAWL_LAST_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_sound_last"{print $$1}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_KILL_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/hazard_kill_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 900 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/hazard_kill_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from hazard kill Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-hazard-kill passed"; else echo "[FAIL] make test-hazard-kill, log kept in $$T"; exit 1; fi

# Round clear banner (tests/mame/banner_check.lua): g_banner_calls stays 0 through attract (title, table, one demo phase);
# in a real game a round won by RAM poke raises calls and cells during the hold and both stop rising right after it.
# `make test-banner` alone runs it.
test-banner: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_CALLS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_banner_calls"{print $$1}') \
	BRAWL_CELLS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_banner_cells"{print $$1}') \
	BRAWL_RE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_round_end_s"{print $$1}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 120 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/banner_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from banner Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-banner passed"; else echo "[FAIL] make test-banner, log kept in $$T"; exit 1; fi

# Background mood (tests/mame/mood_check.lua, DUSK-1): in a real game, rounds won by RAM poke until match_start picks the
# other mood; g_bg_mood takes both values, backdrop entry 4095 differs, and palette RAM holds the generated dusk palette.
# STORM-1: then storm is forced by poking Game mood (no game code picks it yet): palette RAM holds the storm palette and the
# worst line of every sprite in VRAM is at most SB_LIMIT 90.
# `make test-mood` alone runs it.
test-mood: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_RE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_round_end_s"{print $$1}') \
	BRAWL_MOOD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood"{print $$1}') \
	BRAWL_BUSY_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood_busy"{print $$1}') \
	BRAWL_CHANGES_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood_changes"{print $$1}') \
	BRAWL_FIRST_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_dusk_pal_first_entry"{print $$1}') \
	BRAWL_PAL_ADDR=$$($(NM) -S $(ELF) | awk '$$4=="dusk_palettes"{print $$1}') \
	BRAWL_PAL_SIZE=$$($(NM) -S $(ELF) | awk '$$4=="dusk_palettes"{print $$2}') \
	BRAWL_STORM_FIRST_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_storm_pal_first_entry"{print $$1}') \
	BRAWL_STORM_PAL_ADDR=$$($(NM) -S $(ELF) | awk '$$4=="storm_palettes"{print $$1}') \
	BRAWL_STORM_PAL_SIZE=$$($(NM) -S $(ELF) | awk '$$4=="storm_palettes"{print $$2}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 200 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/mood_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from mood Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-mood passed"; else echo "[FAIL] make test-mood, log kept in $$T"; exit 1; fi

# Camera view (tests/mame/camera_check.lua): drives the human right until the camera pixel sentinel g_cam_px goes
# past 64 and the human crosses the arena seam; asserts the hero sprite x against camera_screen_x, at most 2 px camera
# movement per frame, island columns and every hazard column (both banks) at their ring x, hazard SCB4 written only when the camera moved, zero VRAM writes outside vblank.
# `make test-camera` alone runs it.
test-camera: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_BGX_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_x_writes"{print $$1}') \
	BRAWL_RAMP_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_vq_ramp_ops"{print $$1}') \
	BRAWL_CAMU_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_unwrapped"{print $$1}') \
	BRAWL_STAGE_ADDR=$$($(NM) $(ELF) | awk '$$3=="stage_platforms"{print $$1}') \
	BRAWL_POOL_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_pool"{print $$1}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_CAMERA_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/camera_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 90 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/camera_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from camera Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-camera passed"; else echo "[FAIL] make test-camera, log kept in $$T"; exit 1; fi

# Gameplay sprites per scanline (tests/mame/sprite_peak_check.lua): forces 6 computer fliers, reads the sprite control
# blocks of the gameplay slot range every frame and records the maximum per line against SB_GAMEPLAY_PER_LINE.
# `make test-sprite-peak` alone runs it; not part of make test.
PEAK_FRAMES?=6000
PEAK_SECONDS?=240
test-sprite-peak: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_PEAK_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/peak_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_PEAK_FRAMES=$(PEAK_FRAMES) \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(PEAK_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/sprite_peak_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from sprite peak Lua script"; exit 1; fi; \
	cat $$T/result.txt; grep BRAWL_PROFILE $$T/mame.log || true; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-sprite-peak passed"; else echo "[FAIL] make test-sprite-peak, log kept in $$T"; exit 1; fi

# Sound driver reachability (tests/mame/sound_check.lua): coin, start, jump, fire, idle to game over. Asserts the 68k
# sentinels g_sound_sent/g_sound_last, the Z80 command port reads and the YM2610 key-on/FM writes agree for every
# game sound event. Run by make test; `make test-sound` alone re-runs only this check.
SOUND_LEGS?=nullbios unibios40
test-sound: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	for LEG in $(SOUND_LEGS); do \
	if [ $$LEG = unibios40 ]; then \
	if [ ! -f "$(UNIBIOS)" ]; then echo "[SKIP] test-sound UniBIOS leg: UNIBIOS file not found: $(UNIBIOS)"; continue; fi; \
	$(MAKE) --no-print-directory bios $(UNIBIOS_DIR)/neogeo.zip; \
	RP="$(UNIBIOS_DIR);$(ROM)"; BIOSFLAG="-bios unibios40"; else RP="$(ROM)"; BIOSFLAG=""; fi; \
	BRAWL_LABEL=$$LEG \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_STAGE_ADDR=$$($(NM) $(ELF) | awk '$$3=="stage_platforms"{print $$1}') \
	BRAWL_HIT_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/hit_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result-$$LEG.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp "$$RP" $$BIOSFLAG -nvram_directory $$T/nvram-$$LEG -autoboot_script tests/mame/sound_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame-$$LEG.log 2>&1 || true; \
	if [ ! -f $$T/result-$$LEG.txt ]; then tail -n 15 $$T/mame-$$LEG.log; echo "[FAIL] test-sound $$LEG: no result from Lua script"; exit 1; fi; \
	echo "[$$LEG]"; cat $$T/result-$$LEG.txt; \
	if grep -q 'FAIL' $$T/result-$$LEG.txt; then echo "[FAIL] make test-sound $$LEG, log kept in $$T"; exit 1; fi; \
	done; rm -rf $$T; echo "[OK] make test-sound passed"

# Black screen between Gum Trip runs (tests/mame/black_screen_check.lua, UniBIOS 4.0): five runs that die with no rank, with a coin at
# Game Over, a coin on the title, Start from the title and a coin in the demo between them; the screen never stays black, the entry
# hold never sticks. `make test-black-screen`.
.PHONY: test-black-screen
test-black-screen: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_BGHELD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_held"{print $$1}') \
	BRAWL_BUSY_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood_busy"{print $$1}') \
	BRAWL_MOOD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_mood"{print $$1}') \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 1500 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/black_screen_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from black screen Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-black-screen passed"; else echo "[FAIL] make test-black-screen, log kept in $$T"; exit 1; fi

# UniBIOS check (tests/mame/unibios_check.lua): palettes survive the real-BIOS coin re-entry.
# Separate from make test, because it needs the UNIBIOS file from outside the repo.
test-unibios: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_FIXFONT_H=$(BUILDDIR)/gen/fix_font.h \
	BRAWL_BG_PAL_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_pal_first_entry"{print $$1}') \
	BRAWL_BG_PAL_BYTES=$$($(NM) -S $(ELF) | awk '$$4=="city_palettes"{print $$2}') \
	BRAWL_SOOT_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_soot_range"{print $$1}') \
	BRAWL_COINCALLS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_coin_calls"{print $$1}') \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_REACH_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/reach_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 700 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/unibios_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-unibios passed"; else echo "[FAIL] make test-unibios, log kept in $$T"; exit 1; fi

# Co-op join (tests/mame/coop_check.lua): UniBIOS, two coins, P1 Start, then P2 Start in play takes the BIOS credit and drops
# hero[1] in on the parachute; refused Starts keep the credit. `make test-coop` alone.
test-coop: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_COOP_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/coop_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/coop_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from coop Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-coop passed"; else echo "[FAIL] make test-coop, log kept in $$T"; exit 1; fi

# Arena instant join (tests/mame/arena_join_check.lua): UniBIOS, two coins, Arena 1P Start, P2 Start in play restarts the whole match
# (scores and rounds 0, both heroes in) and the CREDITS plate shows in play. `make test-arena-join` alone.
test-arena-join: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_JOIN_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/arena_join_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/arena_join_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from arena join Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-arena-join passed"; else echo "[FAIL] make test-arena-join, log kept in $$T"; exit 1; fi

# Party Rule of the Round (tests/mame/party_check.lua): UniBIOS, one coin, Up to the PARTY row, Start: the title goal line, the round-start banner
# (twist name and goal line on fix rows 11..13), its clearing at GO and the round playing. `make test-party` alone.
test-party: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_PARTY_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/party_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/party_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from party Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-party passed"; else echo "[FAIL] make test-party, log kept in $$T"; exit 1; fi

# PARTY Toss Gum (tests/mame/party_toss_check.lua): UniBIOS, Arena 1P Start, rule set to Toss, P2 join restarts into Toss Gum; four birds, a toss in flight,
# a burst and a winner, and the held gum knot sits on the drawn wing gum point of the carrier's pose. `make test-party-toss TOSS_SNAP=<dir>` also writes toss_mid.png and toss_burst.png there.
test-party-toss: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_WING_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_toss_wing"{print $$1}') BRAWL_KNOT_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_toss_knot"{print $$1}') \
	BRAWL_SNAP=$(TOSS_SNAP) BRAWL_TOSS_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/party_toss_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 400 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T $(if $(TOSS_SNAP),-snapshot_directory $(TOSS_SNAP)) -autoboot_script tests/mame/party_toss_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from party toss Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-party-toss passed"; else echo "[FAIL] make test-party-toss, log kept in $$T"; exit 1; fi

# Gum visibility (tests/mame/gum_visible_check.lua): Big Blow and Toss Gum each must show the hero on screen and a lit bubble sprite.
test-gum-visible: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; for SC in blow toss; do T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_SCEN=$$SC BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_VIS_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_visible_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 400 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_visible_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from gum visible Lua script ($$SC)"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; else echo "[FAIL] make test-gum-visible ($$SC), log kept in $$T"; exit 1; fi; done; echo "[OK] make test-gum-visible passed"

# PARTY Roost Rule (tests/mame/party_roost_check.lua): UniBIOS, Arena 1P Start, rule set to Roost, P2 join restarts the match; the island is picked,
# the round timer runs and a sole standing human is paid ticks. `make test-party-roost` alone.
test-party-roost: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_PLAT_ADDR=$$($(NM) $(ELF) | awk '$$3=="stage_platforms"{print $$1}') \
	BRAWL_ROOST_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/party_roost_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/party_roost_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from party roost Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-party-roost passed"; else echo "[FAIL] make test-party-roost, log kept in $$T"; exit 1; fi

# PARTY two-player name entry (tests/mame/party_name_check.lua): UniBIOS, 2P PARTY game over with both scores ranking, both players type a name;
# both names reach the saved table, the game loop keeps running and the screen is not blank afterwards. `make test-party-name` alone.
test-party-name: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_HISCORE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_image"{print $$1}') \
	BRAWL_NAME_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/party_name_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 400 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $${PN_NVRAM:-$$T} -autoboot_script tests/mame/party_name_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from party name Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-party-name passed"; else echo "[FAIL] make test-party-name, log kept in $$T"; exit 1; fi

# Gum Games Big Blow (tests/mame/gum_big_blow_check.lua): UniBIOS, one coin, Up to the GUM GAMES row, Start: A/B mashing grows the bubble and the power bar,
# the result shows a qualifying mark, the score and a spent ticket. `make test-gum-big-blow` alone.
test-gum-big-blow: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_big_blow_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_big_blow_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Big Blow Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-big-blow passed"; else echo "[FAIL] make test-gum-big-blow, log kept in $$T"; exit 1; fi

# Gum Games Burst Race (tests/mame/gum_burst_race_check.lua): UniBIOS, one coin, Up to the GUM GAMES row, Right picks the event, Start: A/B mashing grows the bubble and both power bars,
# the player bursts first and scores 900. `make test-gum-burst-race` alone.
test-gum-burst-race: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_SNAP=$(RACE_SNAP) BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_burst_race_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T $(if $(RACE_SNAP),-snapshot_directory $(RACE_SNAP)) -autoboot_script tests/mame/gum_burst_race_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Burst Race Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-burst-race passed"; else echo "[FAIL] make test-gum-burst-race, log kept in $$T"; exit 1; fi

# Gum Games Flap Dash (tests/mame/gum_flap_dash_check.lua): UniBIOS, one coin, Up to the GUM GAMES row, Left once (wraps) picks the event, Start: A/B mashing flies three laps,
# the HUD, the lap count, the score and the saved record are checked. `make test-gum-flap-dash` alone.
test-gum-flap-dash: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_flap_dash_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_flap_dash_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Flap Dash Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-flap-dash passed"; else echo "[FAIL] make test-gum-flap-dash, log kept in $$T"; exit 1; fi

# Gum Games Bubble Gather (tests/mame/gum_bubble_gather_check.lua): UniBIOS, one coin, Up to the GUM GAMES row, Right twice picks the event, Start: the hero is parked on live bubbles;
# the HUD, the caught count, the score and the saved record are checked. `make test-gum-bubble-gather` alone.
test-gum-bubble-gather: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_bubble_gather_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_bubble_gather_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Bubble Gather Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-bubble-gather passed"; else echo "[FAIL] make test-gum-bubble-gather, log kept in $$T"; exit 1; fi

# Gum Games Burst Race 2P (gum_burst_race_2p_check.lua): see the header of the Lua file. `make test-gum-burst-race-2p` alone.
test-gum-burst-race-2p: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_burst_race_2p_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_burst_race_2p_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Burst Race 2P Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-burst-race-2p passed"; else echo "[FAIL] make test-gum-burst-race-2p, log kept in $$T"; exit 1; fi

# Gum Games Bubble Gather not qualified (gum_bubble_gather_fail_check.lua): see the header of the Lua file. `make test-gum-bubble-gather-fail` alone.
test-gum-bubble-gather-fail: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_bubble_gather_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_bubble_gather_fail_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Bubble Gather not qualified Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-bubble-gather-fail passed"; else echo "[FAIL] make test-gum-bubble-gather-fail, log kept in $$T"; exit 1; fi

# Gum Games Pop Drop (tests/mame/gum_pop_drop_check.lua): UniBIOS, one coin, Up to the GUM GAMES row, Right three times picks the event, Start: a platform is parked on the bird (three hits crash it);
# the HUD, the crash, the depth score and the saved record are checked. `make test-gum-pop-drop` alone.
test-gum-pop-drop: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_LASTUS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_last_us"{print $$1}') \
	BRAWL_DEFER_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_defer_last"{print $$1}') \
	BRAWL_FLUSHN_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_flush_n"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_pop_drop_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_pop_drop_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Pop Drop Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-pop-drop passed"; else echo "[FAIL] make test-gum-pop-drop, log kept in $$T"; exit 1; fi

# Pop Drop pool finish (same Lua, BRAWL_POOL=1): the fall is moved to the pool; water, flop bird, splash and score cards are checked in SCB RAM.
test-gum-pop-drop-pool: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_LASTUS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_last_us"{print $$1}') \
	BRAWL_DEFER_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_defer_last"{print $$1}') \
	BRAWL_FLUSHN_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_flush_n"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_pop_drop_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_POOL=1 BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_pop_drop_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Pop Drop Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-pop-drop-pool passed"; else echo "[FAIL] make test-gum-pop-drop-pool, log kept in $$T"; exit 1; fi

# Gum Games Pop Drop 2P (tests/mame/gum_pop_drop_2p_check.lua): 1P Pop Drop start, then a second coin and P2 Start in the countdown;
# both birds fall at once, a platform parked on P1 crashes it and its ghost floats on with P2 alive. `make test-gum-pop-drop-2p` alone.
test-gum-pop-drop-2p: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_LASTUS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_last_us"{print $$1}') \
	BRAWL_DEFER_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_defer_last"{print $$1}') \
	BRAWL_FLUSHN_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_flush_n"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_pop_drop_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_pop_drop_2p_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Pop Drop 2P Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-pop-drop-2p passed"; else echo "[FAIL] make test-gum-pop-drop-2p, log kept in $$T"; exit 1; fi

# Arena flush saturation baseline (measurement only, tests/mame/flush_arena_baseline.lua): prints the FLUSH line for 1500 PLAYING frames of the default mode.
test-flush-arena: cart bios
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_LASTUS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_last_us"{print $$1}') \
	BRAWL_DEFER_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_defer_last"{print $$1}') \
	BRAWL_FLUSHN_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_flush_n"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_pop_drop_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 200 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/flush_arena_baseline.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result"; exit 1; fi; cat $$T/result.txt

# Gum Games Gum Fling (tests/mame/gum_fling_check.lua): UniBIOS, one coin, Up to the GUM GAMES row, Left once wraps to the event, Start: A/B mashed, C held and released;
# the TRIP flight, the best distance, the score and the saved record are checked. `make test-gum-fling` alone.
test-gum-fling: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_BLOW_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_fling_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_fling_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Gum Fling Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-fling passed"; else echo "[FAIL] make test-gum-fling, log kept in $$T"; exit 1; fi

# Gum Games Poop the Man (tests/mame/gum_poop_check.lua): UniBIOS, Down x6 to the last event, Start; A drops poops; HUD, record, sprite and flush budgets.
test-gum-poop: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_LASTUS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_last_us"{print $$1}') \
	BRAWL_DEFER_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_defer_last"{print $$1}') \
	BRAWL_FLUSHN_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_gfx_flush_n"{print $$1}') \
	BRAWL_POOP_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/gum_poop_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 300 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/gum_poop_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from Poop the Man Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-gum-poop passed"; else echo "[FAIL] make test-gum-poop, log kept in $$T"; exit 1; fi

# Ring reachability (tests/mame/ring_check.lua): holds Left until the player's world x wraps across the seam, then Right
# back; every PLAYING frame the flier is on screen (ring maths with g_cam_px), the hero SCB3 height is non-zero, the
# camera moves at most CAM_MAX_STEP_PX per frame (ring distance), and both seam crossings happened. `make test-ring` alone.
test-ring: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_CAM_SIZE=$$($(NM) -S $(ELF) | awk '$$4=="g_cam_px"{print $$2}') \
	BRAWL_BGHELD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_held"{print $$1}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RING_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/ring_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 90 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/ring_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from ring Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-ring passed"; else echo "[FAIL] make test-ring, log kept in $$T"; exit 1; fi

# Solid platforms (tests/mame/solid_check.lua): the hero rises into an island underside and flies into an island side; the
# hero box never overlaps the solid box from the ROM table, the velocity flips, g_flier_solid_hits rises. `make test-solid` alone.
test-solid: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_STAGE_ADDR=$$($(NM) $(ELF) | awk '$$3=="stage_platforms"{print $$1}') \
	BRAWL_HITS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flier_solid_hits"{print $$1}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_SOLID_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/solid_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 90 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/solid_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from solid Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-solid passed"; else echo "[FAIL] make test-solid, log kept in $$T"; exit 1; fi

# Title pause after a run (tests/mame/title_pause_check.lua, UniBIOS 4.0): frames from the run end to a live title, Gum Trip and arcade;
# the title must start running within 30 frames of being reached. `make test-title-pause`.
.PHONY: test-title-pause
test-title-pause: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	for MODE in trip arcade; do \
	BRAWL_MODE=$$MODE \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_SCORE_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/score_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result-$$MODE.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 600 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/title_pause_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame-$$MODE.log 2>&1 || true; \
	if [ ! -f $$T/result-$$MODE.txt ]; then tail -n 15 $$T/mame-$$MODE.log; echo "[FAIL] no result from title pause Lua script ($$MODE)"; exit 1; fi; \
	cat $$T/result-$$MODE.txt; \
	if ! grep -q '^PASS' $$T/result-$$MODE.txt; then echo "[FAIL] make test-title-pause ($$MODE), log kept in $$T"; exit 1; fi; \
	done; rm -rf $$T; echo "[OK] make test-title-pause passed"

# Gum Trip view (tests/mame/trip_check.lua): coin, Down on the title, Start; over 500 PLAYING frames the mode is TRIP, the distance grows
# by the scroll speed (49152 raw at distance 0), the camera changes every frame or every second frame, the flier stays on screen,
# zero game steps are missed and the frame logic ends before the visible lines end. `make test-trip` alone.
# `make test-trip TRIP_PC_LOG=<file>` also samples the 68000 PC once per scan line and writes lines per function per frame to <file> (opt-in, no assert).
test-trip: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	export BRAWL_PC_LOG=$(TRIP_PC_LOG) BRAWL_PC_SYMS=$$T/syms.txt; \
	if [ -n "$(TRIP_PC_LOG)" ]; then $(NM) -n -S --defined-only $(ELF) > $$T/syms.txt; fi; \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_TRIPDRAWS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_island_trip_draws"{print $$1}') \
	BRAWL_BGHELD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_bg_held"{print $$1}') \
	BRAWL_ISLANDDRAWS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_island_draws"{print $$1}') \
	BRAWL_STRIPDRAWS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_trip_strip_draws"{print $$1}') \
	BRAWL_WINCALLS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_trip_window_calls"{print $$1}') \
	BRAWL_WINCLAMP_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_trip_window_clamps"{print $$1}') \
	BRAWL_PICKUPDRAWS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_trip_pickup_draws"{print $$1}') \
	BRAWL_PICKUPTILES_ADDR=$$($(NM) $(ELF) | awk '$$3=="trippickup_tile_index"{print $$1}') \
	BRAWL_PICKUPFRAMES_ADDR=$$($(NM) $(ELF) | awk '$$3=="trippickup_frames"{print $$1}') \
	BRAWL_HAZDRAWS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_trip_haz_draws"{print $$1}') \
	BRAWL_METERDRAWS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_meter_draws"{print $$1}') \
	BRAWL_METERTAB_ADDR=$$($(NM) $(ELF) | awk '$$3=="tripmeter_cell"{print $$1}') \
	BRAWL_CAM_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_cam_px"{print $$1}') \
	BRAWL_CAM_SIZE=$$($(NM) -S $(ELF) | awk '$$4=="g_cam_px"{print $$2}') \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_TRIP_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/trip_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RIVAL_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/rival_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_LASTUS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_last_us"{print $$1}') \
	BRAWL_VQ_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/vq_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 90 -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/trip_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from trip Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-trip passed"; else echo "[FAIL] make test-trip, log kept in $$T"; exit 1; fi

# Score tables (tests/mame/score_check.lua): two boots under UniBIOS (backup RAM persists only there, see test-reach). Boot 1 plays a
# Gum Trip run and an arena run through the real name entry, checks fix layer captions and rows, each score lands in its own table,
# the save counter and the backup RAM image (magic, version, FNV-1a, both tables); boot 2 checks the tables came back and nothing
# was re-saved. `make test-score` alone.
SCORE_SECONDS?=300
test-score: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[FAIL] test-score needs UniBIOS: UNIBIOS file not found: $(UNIBIOS)"; exit 1; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	for PH in 1 2; do \
	BRAWL_PHASE=$$PH \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_STAGE_ADDR=$$($(NM) $(ELF) | awk '$$3=="stage_platforms"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_HISCORE_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_image"{print $$1}') \
	BRAWL_SAVES_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_hiscore_saves"{print $$1}') \
	BRAWL_TABLEDRAWS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_table_mode_draws"{print $$1}') \
	BRAWL_FIXFONT_H=$(BUILDDIR)/gen/fix_font.h \
	BRAWL_SCORE_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/score_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_REACH_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/reach_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_FLIER_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/flier_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result$$PH.txt BRAWL_EXPECT=$$T/expect.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(SCORE_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) $(REACH_BIOS_FLAGS) -nvram_directory $$T/nvram -autoboot_script tests/mame/score_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame$$PH.log 2>&1 || true; \
	if [ ! -f $$T/result$$PH.txt ]; then tail -n 15 $$T/mame$$PH.log 2>/dev/null; echo "[FAIL] test-score boot $$PH: no result from Lua script"; exit 1; fi; \
	cat $$T/result$$PH.txt; \
	grep -q '^PASS' $$T/result$$PH.txt || { echo "[FAIL] make test-score boot $$PH, log kept in $$T"; exit 1; }; \
	done; rm -rf $$T; echo "[OK] make test-score passed"

# Soft reset (tests/mame/soft_reset_check.lua, plan thoughts/spot/2026-11-10-soft-reset-test-plan.md): a MAME soft reset in play must
# reboot the game (frame counter drops, g_boot_magic re-armed only afterwards), come back to attract with score 0 and a valid
# score table, keep the game loop running and start a new play. Two legs: nullbios, then UniBIOS (skipped with a [SKIP] line,
# not a pass, when the UNIBIOS file is missing). `make test-soft-reset` alone.
SOFT_RESET_LEGS?=nullbios unibios40
test-soft-reset: cart
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	for LEG in $(SOFT_RESET_LEGS); do \
	if [ $$LEG = unibios40 ]; then \
	if [ ! -f "$(UNIBIOS)" ]; then echo "[SKIP] test-soft-reset UniBIOS leg: UNIBIOS file not found: $(UNIBIOS)"; continue; fi; \
	$(MAKE) --no-print-directory bios $(UNIBIOS_DIR)/neogeo.zip; \
	RP="$(UNIBIOS_DIR);$(ROM)"; BIOSFLAG="-bios unibios40"; else RP="$(ROM)"; BIOSFLAG=""; fi; \
	BRAWL_LABEL=$$LEG \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_MAGIC_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_boot_magic"{print $$1}') \
	BRAWL_REACH_LAYOUT="$$($(M68KGCC) -std=c99 -S -o - tests/mame/reach_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result-$$LEG.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 120 -noautosave -skip_gameinfo -hash $(ROM) -rp "$$RP" $$BIOSFLAG -nvram_directory $$T/nvram-$$LEG -autoboot_script tests/mame/soft_reset_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame-$$LEG.log 2>&1 || true; \
	if [ ! -f $$T/result-$$LEG.txt ]; then tail -n 15 $$T/mame-$$LEG.log; echo "[FAIL] test-soft-reset $$LEG: no result from Lua script"; exit 1; fi; \
	cat $$T/result-$$LEG.txt; \
	grep -q '^PASS' $$T/result-$$LEG.txt || { echo "[FAIL] make test-soft-reset $$LEG, log kept in $$T"; exit 1; }; \
	done; rm -rf $$T; echo "[OK] make test-soft-reset passed"

# Left column (tests/mame/left_column_check.lua): a test sprite at x 0, y 60 must draw as well as one at x 16, and slot 0 must carry no
# sprite while PLAYING. Arena and Gum Trip. `make test-left-column` alone.
test-left-column: cart
	@set -e; for M in arena trip; do T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_FRAME_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_frame_counter"{print $$1}') \
	BRAWL_MOOD_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_want"{print $$1}') \
	BRAWL_BACKDROP_ADDR=$$($(NM) $(ELF) | awk -v T=$$([ $$M = trip ] && echo TRIP_BACKDROP || echo BACKDROP) '$$3==T{print $$1}') \
	BRAWL_LC_MODE=$$M BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run $(TEST_SECONDS) -noautosave -skip_gameinfo -hash $(ROM) -rp $(ROM) -nvram_directory $$T -autoboot_script tests/mame/left_column_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from left column Lua script ($$M)"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; else echo "[FAIL] make test-left-column ($$M), log kept in $$T"; exit 1; fi; done; echo "[OK] make test-left-column passed"

# Title screen (tests/mame/logo_check.lua, UniBIOS 4.0 for coins): logo sprites active, PRESS START absent at 0 credits and present
# after a coin, credit byte 0x10FE00, kill strips (slots shared with the logo) correct over title, Gum Trip, title, Gum Trip. `make test-logo` alone.
test-logo: cart bios
	@if [ ! -f "$(UNIBIOS)" ]; then echo "[SKIP] test-logo needs UNIBIOS (coins); not found: $(UNIBIOS)"; exit 0; fi
	@$(MAKE) --no-print-directory $(UNIBIOS_DIR)/neogeo.zip
	@set -e; T=$$(mktemp -d $(BUILDDIR)/test-run.XXXXXX); \
	BRAWL_FLOW_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_flow"{print $$1}') \
	BRAWL_LOGODRAWS_ADDR=$$($(NM) $(ELF) | awk '$$3=="g_logo_draws"{print $$1}') \
	BRAWL_FIXFONT_H=$(BUILDDIR)/gen/fix_font.h \
	BRAWL_LOGO_LAYOUT="$$($(M68KGCC) $(NGCFLAGS) -Ibuild -std=c99 -S -o - tests/mame/logo_probe.c | awk '/^probe:/{f=1;next} f&&/\.long/{print $$2} f&&/\.size/{exit}')" \
	BRAWL_RESULT=$$T/result.txt \
	SDL_VIDEODRIVER=dummy nice -n 19 $(MAME) -window -nomaximize -video none -sound none -nothrottle -seconds_to_run 120 -noautosave -skip_gameinfo -hash $(ROM) -rp "$(UNIBIOS_DIR);$(ROM)" -bios unibios40 -nvram_directory $$T -autoboot_script tests/mame/logo_check.lua neogeo -cart1 $(GAMEROM) > $$T/mame.log 2>&1 || true; \
	if [ ! -f $$T/result.txt ]; then tail -n 15 $$T/mame.log; echo "[FAIL] no result from logo Lua script"; exit 1; fi; \
	cat $$T/result.txt; \
	if grep -q '^PASS' $$T/result.txt; then rm -rf $$T; echo "[OK] make test-logo passed"; else echo "[FAIL] make test-logo, log kept in $$T"; exit 1; fi

.PHONY: run test test-mood test-arcade test-arcade-walk test-arcade-bonus test-crom test-srom test-debug-header test-camera test-sprite-peak test-left-column test-flier test-small-sootling test-reach test-vblank test-scroll test-slots test-hazard test-hazard-kill test-soft-reset test-ring test-solid test-trip test-score test-sound test-unibios test-coop test-arena-join test-party test-party-toss test-party-roost test-party-name test-gum-big-blow test-gum-visible test-gum-burst-race test-gum-burst-race-2p test-gum-bubble-gather-fail test-gum-flap-dash test-gum-bubble-gather test-gum-pop-drop test-gum-pop-drop-2p test-gum-pop-drop-pool test-gum-fling test-logo

# Header dependencies from -MMD (build/**/*.d): a changed header rebuilds every object that includes it.
-include $(shell find $(BUILDDIR) -name '*.d' 2>/dev/null)

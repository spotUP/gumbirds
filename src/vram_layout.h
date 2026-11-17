#ifndef VRAM_LAYOUT_H
#define VRAM_LAYOUT_H
/*
 * C-ROM tile bases and palette slots (bank 1). C-ROM order is the Makefile cat order:
 * logo (256 tiles), obstacles, city, Sootling (the fliers), hazard strip, floating islands. Every base is derived from the generated headers,
 * never typed. Palette slots 0..FIX_PAL_COUNT-1 are the fix layer.
 */
#include "gen/fix_font.h"
#include "gen/obs_sprites.h"
#include "gen/city_sprites.h"
#include "gen/dusk_sprites.h"
#include "gen/storm_sprites.h"
#include "gen/sootling_sprites.h"
#include "gen/hazard_sprites.h"
#include "gen/island_sprites.h"
#include "gen/island_garden_sprites.h"
#include "gen/island_deck_sprites.h"
#include "gen/tripstrip_sprites.h"
#include "gen/trippickup_sprites.h"
#include "gen/triphaz_sprites.h"
#include "gen/gum_sprites.h"
#include "gen/logo_sprites.h"
#include "gen/splash_sprites.h"
#include "gen/arcade_sprites.h"
#include "gen/resfx_sprites.h"
#include "gen/chute_sprites.h"
#include "gen/gumbubble_sprites.h"
#include "gen/gumleak_sprites.h"
#include "gen/countdown_sprites.h"

/* The ngdevkit logo tile block that opens the C-ROM (assets/base-crom-logo); the title logo (gen/logo_sprites.h, LOGO_TILE_COUNT) sits last. */
#define BASE_LOGO_TILE_COUNT 256
#define OBS_TILE_BASE BASE_LOGO_TILE_COUNT
#define CITY_TILE_BASE (OBS_TILE_BASE + OBS_TILE_COUNT)

#define DUSK_TILE_BASE (CITY_TILE_BASE + CITY_TILE_COUNT) /* dusk mood planes (src/bg.c) */
#define STORM_TILE_BASE (DUSK_TILE_BASE + DUSK_TILE_COUNT) /* storm mood planes (src/bg.c, STORM-1) */
#define SOOT_TILE_BASE (STORM_TILE_BASE + STORM_TILE_COUNT)
/* A Sootling frame is drawn as SOOT_COLUMNS hardware strips of 16 px: the pipeline pads the art to whole tiles, centred
   (tools/sprite_pipeline.py), so the sprite is wider than the art when ART_W is not a multiple of 16 (24 px art: 32 px
   sprite, 4 px left pad). SOOT_BOX_DX is the hit box's first column inside the sprite: art column plus the left pad. */
#define SOOT_COLUMNS SOOTLING_MAX_COLUMNS
#define SOOT_SPRITE_W (SOOT_COLUMNS * 16)
#define SOOT_BOX_DX ((SOOT_SPRITE_W - SOOTLING_ART_W) / 2 + SOOTLING_BOX_FIRST_COL)
#define HAZARD_TILE_BASE (SOOT_TILE_BASE + SOOTLING_TILE_COUNT)
/* Auto-animation replaces the low 3 bits of the tile number: the hazard base must be a multiple of 8. */
_Static_assert((HAZARD_TILE_BASE & 7) == 0, "hazard tile base is not 8-aligned");
/* The sprite pipeline pads every set to a multiple of 8 tiles, so the island base stays aligned; its swap groups are
   8-aligned inside the set (asserted by tests/host/test_islands.py). */
#define ISLAND_TILE_BASE (HAZARD_TILE_BASE + HAZARD_TILE_COUNT)
_Static_assert((ISLAND_TILE_BASE & 7) == 0, "island tile base is not 8-aligned");
/* Gum Trip kill strips: the rim uses 8 frame auto-animation, so the set base must be a multiple of 8 (the rim runs sit at
   multiples of 8 inside the set, see tools/sprite_pipeline.py). */
/* The three island looks (roof, garden, deck: island.c1, island_garden.c1, island_deck.c1) sit one after the other, ISLAND_TILE_COUNT
   tiles each; look k starts at ISLAND_TILE_BASE + k * ISLAND_TILE_COUNT. Each look has one palette (ISLAND_PAL_SLOT + k). */
_Static_assert(ISLAND_GARDEN_TILE_COUNT == ISLAND_TILE_COUNT && ISLAND_DECK_TILE_COUNT == ISLAND_TILE_COUNT, "island looks differ in tile count");
_Static_assert(ISLAND_GARDEN_PALETTE_COUNT == ISLAND_PALETTE_COUNT && ISLAND_DECK_PALETTE_COUNT == ISLAND_PALETTE_COUNT, "island looks differ in palette count");
#define ISLAND_LOOK_COUNT 3
#define ISLAND_LOOK_TILE_BASE(look) (ISLAND_TILE_BASE + (look) * ISLAND_TILE_COUNT)
#define TRIPSTRIP_TILE_BASE (ISLAND_TILE_BASE + ISLAND_LOOK_COUNT * ISLAND_TILE_COUNT)
_Static_assert((TRIPSTRIP_TILE_BASE & 7) == 0, "trip strip tile base is not 8-aligned");
/* Gum Trip pickup (step V3), appended after the strip set so no earlier base moves. */
#define TRIPPICKUP_TILE_BASE (TRIPSTRIP_TILE_BASE + TRIPSTRIP_TILE_COUNT)
_Static_assert((TRIPPICKUP_TILE_BASE & 7) == 0, "trip pickup tile base is not 8-aligned");
/* Gum Trip hazards (step V4), appended after the pickup set. */
#define TRIPHAZ_TILE_BASE (TRIPPICKUP_TILE_BASE + TRIPPICKUP_TILE_COUNT)
_Static_assert((TRIPHAZ_TILE_BASE & 7) == 0, "trip hazard tile base is not 8-aligned");
/* The player's gum bubble (Gum Trip), appended after the hazard set. */
#define GUM_TILE_BASE (TRIPHAZ_TILE_BASE + TRIPHAZ_TILE_COUNT)
_Static_assert((GUM_TILE_BASE & 7) == 0, "gum tile base is not 8-aligned");
/* The title logo (strips and pieces, one palette), appended after the gum set. */
#define LOGO_TILE_BASE (GUM_TILE_BASE + GUM_TILE_COUNT)
_Static_assert((LOGO_TILE_BASE & 7) == 0 && (LOGO_TILE_COUNT & 7) == 0, "logo tile base or count is not 8-aligned");
/* The water and lava splash, appended after the logo set. */
#define SPLASH_TILE_BASE (LOGO_TILE_BASE + LOGO_TILE_COUNT)
_Static_assert((SPLASH_TILE_BASE & 7) == 0, "splash tile base is not 8-aligned");

/* Arcade stage elements (vent, flipper, grabber, hatch), appended last. The island looks sit directly after the roof island tiles
   and moved this base: it is chained, never a literal. */
#define ARCADE_TILE_BASE (SPLASH_TILE_BASE + SPLASH_TILE_COUNT)
_Static_assert((ARCADE_TILE_BASE & 7) == 0, "arcade tile base is not 8-aligned");
#define RESFX_TILE_BASE (ARCADE_TILE_BASE + ARCADE_TILE_COUNT) /* bonus result screen sprites (tools/build_result_art.py) */
_Static_assert((RESFX_TILE_BASE & 7) == 0, "result sprite tile base is not 8-aligned");
#define CHUTE_TILE_BASE (RESFX_TILE_BASE + RESFX_TILE_COUNT) /* parachute sprites (tools/make_chute_sheet.py), last in CROM_SETS */
_Static_assert((CHUTE_TILE_BASE & 7) == 0, "parachute tile base is not 8-aligned");
#define GUMBUBBLE_TILE_BASE (CHUTE_TILE_BASE + CHUTE_TILE_COUNT) /* Hot Gum bubble B (assets/gum_bubble), last in CROM_SETS */
_Static_assert((GUMBUBBLE_TILE_BASE & 7) == 0, "gum bubble tile base is not 8-aligned");
#define GUMLEAK_TILE_BASE (GUMBUBBLE_TILE_BASE + GUMBUBBLE_TILE_COUNT) /* gum leak (assets/gum_leak), last in CROM_SETS */
_Static_assert((GUMLEAK_TILE_BASE & 7) == 0, "gum leak tile base is not 8-aligned");
#define COUNTDOWN_TILE_BASE (GUMLEAK_TILE_BASE + GUMLEAK_TILE_COUNT) /* countdown GET SET / GO! (assets/countdown), last in CROM_SETS */
_Static_assert((COUNTDOWN_TILE_BASE & 7) == 0, "countdown tile base is not 8-aligned");

#define FIX_PAL_COUNT FIXFONT_PAL_COUNT /* fix palettes 0..4: white, pink, lime, gold, dim (build/gen/fix_font.h) */
#define ATTRACT_PAL_SLOT FIX_PAL_COUNT /* one palette: the attract overlay icons (build/gen/attract_icons.h). Fix tiles hold a 4-bit palette, so it must sit in slots 0..15, never after the sprite palettes */
_Static_assert(ATTRACT_PAL_SLOT < 16, "fix layer palettes are 4 bits: the overlay palette must be slot 0..15");
#define OBS_PAL_SLOT (ATTRACT_PAL_SLOT + 1)
#define CITY_PAL_SLOT (OBS_PAL_SLOT + OBS_PALETTE_COUNT)
#define DUSK_PAL_SLOT (CITY_PAL_SLOT + CITY_PALETTE_COUNT) /* dusk mood planes; both moods stay loaded, a mood change rewrites only the strips (src/bg.c) */
#define STORM_PAL_SLOT (DUSK_PAL_SLOT + DUSK_PALETTE_COUNT) /* storm mood planes, resident like dusk */
#define SOOT_PAL_SLOT (STORM_PAL_SLOT + STORM_PALETTE_COUNT) /* palette 0: player, palette 1: computer fliers (red balloons) */

#define HAZARD_PAL_SLOT (SOOT_PAL_SLOT + SOOTLING_PALETTE_COUNT) /* palette p = hazard p: spikes, fire, water, lava */
#define ISLAND_PAL_SLOT (HAZARD_PAL_SLOT + HAZARD_PALETTE_COUNT) /* one palette per look */
#define TRIPSTRIP_PAL_SLOT (ISLAND_PAL_SLOT + ISLAND_LOOK_COUNT * ISLAND_PALETTE_COUNT) /* one palette: the gum strip */
#define TRIPPICKUP_PAL_SLOT (TRIPSTRIP_PAL_SLOT + TRIPSTRIP_PALETTE_COUNT) /* one palette: the pickup */
#define TRIPHAZ_PAL_SLOT (TRIPPICKUP_PAL_SLOT + TRIPPICKUP_PALETTE_COUNT) /* palette 0 cloud, 1 vent, 2 coal, as tools/build_triphaz_sprites.py assigns */
#define GUM_PAL_SLOT (TRIPHAZ_PAL_SLOT + TRIPHAZ_PALETTE_COUNT) /* one palette: the bubble */
#define LOGO_PAL_SLOT (GUM_PAL_SLOT + GUM_PALETTE_COUNT) /* one palette: the moon logo (entries 1..15) */
#define SPLASH_PAL_SLOT (LOGO_PAL_SLOT + 1) /* palette 0 water, 1 lava (animation order) */
#define ARCADE_PAL_SLOT (SPLASH_PAL_SLOT + SPLASH_PALETTE_COUNT) /* palette p = arcade palette p (ARCADE_ANIM_* order: storm, player, computer, roof, nozzle, vent; the vent line glows, main.c arcade_elems_step) */
#define ATTRACT_FIX_BASE 0x400 /* first fix tile of the overlay icons: right after the 1024-tile font in the S-ROM (tools/build_attract_icons.py --fix-base) */
#define RESFX_PAL_SLOT (ARCADE_PAL_SLOT + ARCADE_PALETTE_COUNT) /* palette p = resfx palette p (RESFX_ANIM_* order: bubble, wheel, crank, glass, ticket) */
#define CHUTE_PAL_SLOT (RESFX_PAL_SLOT + RESFX_PALETTE_COUNT) /* palette p = chute palette p (0 player, 1 computer) */
#define SOOT_P2_PAL_SLOT (CHUTE_PAL_SLOT + CHUTE_PALETTE_COUNT) /* player 2: sootling_extra_palettes[0], the sun yellow swap of the player palette (hero shading kept) */
#define CHUTE_P2_PAL_SLOT (SOOT_P2_PAL_SLOT + 1) /* player 2 parachute: chute_extra_palettes[0] */
#define GUMBUBBLE_PAL_SLOT (CHUTE_P2_PAL_SLOT + 1) /* one palette: gum bubble B */
#define COUNTDOWN_PAL_SLOT (GUMBUBBLE_PAL_SLOT + GUMBUBBLE_PALETTE_COUNT) /* countdown GET SET: Pink Gum */
#define COUNTDOWN_HOT_PAL_SLOT (COUNTDOWN_PAL_SLOT + COUNTDOWN_PALETTE_COUNT) /* countdown GO!: the Hot Gum swap, same tiles */
_Static_assert(COUNTDOWN_HOT_PAL_SLOT + COUNTDOWN_EXTRA_PALETTE_COUNT <= 256, "palette slots exceed the 256 the hardware has");

#endif

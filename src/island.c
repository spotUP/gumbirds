#include "island.h"
#include "gfx.h"
#include "hazard.h"
#include "sprite_slots.h"
#include "vram_layout.h"
#include "core/camera.h"
#include "core/island_layout.h"
#include "core/stage.h"
#include "core/trip_view.h"
#include "gen/island_tables.h"

_Static_assert(ISLAND_SPRITE + ISLAND_COUNT <= POOL_SPRITE_BASE, "island sprites overlap the object pool");
_Static_assert(BG_SPRITE_END <= ISLAND_SPRITE, "island sprites overlap the background planes");
_Static_assert(TRIP_GEN_RING * TRIP_VIEW_ISLAND_BLOCK <= ISLAND_COUNT, "trip island blocks exceed the island sprites");
_Static_assert(STAGE_LOOK_COUNT == ISLAND_LOOK_COUNT, "stage looks and island art looks differ in count");
_Static_assert(ISLAND_PIECE_W == 16, "islands are drawn one 16 px sprite per column");

volatile u16 g_island_draws;
volatile u16 g_island_trip_draws;
static u8 g_shown, g_loaded;
static s16 g_col_x[ISLAND_COUNT]; /* last x sent per column slot, or CAMERA_COL_HIDDEN: only changes reach VRAM */
static int g_placed_cam = -1;     /* camera the columns were last placed for: place() is a pure function of it, so the same camera costs nothing (-1: unknown) */
static u16 g_scb4[ISLAND_COUNT];  /* SCB4 word of every column slot, sent as one run (a hidden column keeps its last x) */
static u16 g_tiles[ISLAND_COUNT]; /* tile of each column, relative to ISLAND_TILE_BASE; the queue dedupes by this pointer */

/* The stage table never changes, so the first sprite and the column count of every island are computed once (load()) and
 * place() reads them: no search per frame. Filled by init_layout(), which load() and hide() call before use. */
static u16 g_first[STAGE_PLATFORM_COUNT]; /* first sprite of island i: the columns of the islands before it */
static u8 g_cols[STAGE_PLATFORM_COUNT];
static u8 g_layout_ready;

static void init_layout(void) {
    u16 s = ISLAND_SPRITE;
    if (g_layout_ready) return;
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        g_first[i] = s;
        g_cols[i] = (u8)island_platform_columns(stage_platforms[i].w);
        s = (u16)(s + g_cols[i]);
    }
    g_layout_ready = 1;
}

/* Tiles and size words go to VRAM once, on the first call (attract): a 41 column burst on the first PLAYING frame made the
   first camera scroll write late (tests/mame/scroll_check.lua). Columns are not chained (an island may straddle the screen
   edge or the ring seam, so each column has its own x); the height stays 0, so nothing shows until place().
   One call loads one island (g_load_i), not all of them: a new layout writes up to 41 columns, and the whole burst held the main loop
   for 7 frames (tests/mame/hazard_kill_check.lua measures it); place() waits for g_loaded. */
static u8 g_load_i;
static u8 g_look; /* look (stage.h STAGE_LOOK_*) the arena islands are loaded with: read from the stage at the first island of a load */

static void load_step(void) {
    if (g_load_i == 0) {
        init_layout();
        g_look = (u8)stage_look();
        g_placed_cam = -1;
        for (int s = 0; s < ISLAND_COUNT; s++) { g_col_x[s] = CAMERA_COL_HIDDEN; g_scb4[s] = gfx_scb4_word(SCREEN_W); }
        gfx_scb_run((u16)(ADDR_SCB4 + ISLAND_SPRITE), 1, g_scb4, ISLAND_COUNT); /* parked off screen once, so place() sends only changes */
    }
    {
        int i = g_load_i;
        u16 first = g_first[i];
        int cols = g_cols[i];
        for (int c = 0; c < cols; c++) {
            int anim = island_piece_anim(stage_platforms[i].w, c);
            const IslandFrame *f = &island_frames[island_anims[anim].first_frame];
            /* a swapping piece starts its run of 8 consecutive tiles at its first frame (the 8-aligned tile) */
            u16 attr = (u16)((ISLAND_PAL_SLOT + g_look * ISLAND_PALETTE_COUNT + f->palette) << 8);
            if (island_anim_swaps(anim)) attr |= 0x08; /* bit 3: 8-frame auto-animation, as hazard.c */
            g_tiles[first - ISLAND_SPRITE + c] = island_tile_index[f->tile_offset];
            gfx_sprite_strips((u16)(first + c), 1, 1, &g_tiles[first - ISLAND_SPRITE + c], ISLAND_LOOK_TILE_BASE(g_look), attr);
        }
        if (cols) gfx_sprite_unchained(first, (u8)cols); /* the size words never change: sent once here, not per frame (frame logic budget) */
    }
    g_load_i++;
    if (g_load_i == STAGE_PLATFORM_COUNT) { g_load_i = 0; g_loaded = 1; if (!hazard_owns_anim()) island_autoanim_baseline(); /* a shown strip or Gum Trip owns the counter speed: a reload at a round or trip start finishes after it was set */ }
}

static const u16 k_hidden[ISLAND_COUNT]; /* SCB3 height 0 hides a column */
/* One run op over the layout's columns (they are adjacent from ISLAND_SPRITE), not one gfx_word each: the per-word loop took
 * 33 raster lines on the arcade stage-entry frame and ran logic past vblank (arc-spike, thoughts/spot/2026-11-13-arc-spike.md). */
static void hide(void) {
    const int last = STAGE_PLATFORM_COUNT - 1;
    int n;
    g_placed_cam = -1;
    init_layout();
    n = g_first[last] + g_cols[last] - ISLAND_SPRITE;
    if (n) gfx_scb_run((u16)(ADDR_SCB3 + ISLAND_SPRITE), 1, k_hidden, (u8)n);
    for (int s = 0; s < n; s++) g_col_x[s] = CAMERA_COL_HIDDEN;
}

/* The top of an island sprite is the stage y minus the line row of the art (ISLAND_LINE_ROW): the drawn line is the floor.
   Each 16 px column is placed on its own on the ring; VRAM gets a word only when the column's x or visibility changed.
   Camera dependent: the screen x of each platform's first column (one camera_screen_x per platform) and, from it, one add and one
   wrap test per column (camera_strip_x). Static: first sprite and column count (g_first, g_cols), the platform's world x and y. */
static void place(int cam_px) {
    u8 moved = 0;
    if (cam_px == g_placed_cam) return;
    g_placed_cam = cam_px;
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) {
        const StagePlatform *p = &stage_platforms[i];
        u16 slot = g_first[i];
        int cols = g_cols[i];
        int sx0 = camera_screen_x(p->x, cam_px, 16);
        for (int c = 0; c < cols; c++, slot++, sx0 += 16) {
            int sx = camera_strip_x(sx0);
            s16 *last = &g_col_x[slot - ISLAND_SPRITE];
            if (sx == *last) continue;
            if (sx == CAMERA_COL_HIDDEN) {
                gfx_word((u16)(ADDR_SCB3 + slot), 0); /* SCB4 keeps its last value */
            } else {
                if (*last == CAMERA_COL_HIDDEN) gfx_word((u16)(ADDR_SCB3 + slot), gfx_scb3_word(1, p->y - ISLAND_LINE_ROW));
                g_scb4[slot - ISLAND_SPRITE] = gfx_scb4_word(sx);
                moved = 1;
            }
            *last = (s16)sx;
        }
    }
    if (moved) gfx_scb_run((u16)(ADDR_SCB4 + ISLAND_SPRITE), 1, g_scb4, ISLAND_COUNT); /* one run op, not one per word */
}

void island_autoanim_baseline(void) { gfx_autoanim_speed(ISLAND_STEP_FRAMES); }

/* The stage layout changed (stage_select, at a round start under the frozen ROUND banner): the next island_step recomputes the columns and rewrites the tiles. */
static u8 g_relayout_hold; /* set by island_relayout: the frame match_start runs in (rivals, stage copy) writes no island yet */
void island_relayout(void) { g_layout_ready = 0; g_loaded = 0; g_load_i = 0; g_relayout_hold = 1; }

void island_step(u8 playing, int cam_px) {
    /* The stage change frame overran vblank with match_start and island 0 together (stage-spike), and in arcade with the hide
     * of the old layout (arc-spike): that frame writes no island at all; the old columns stay one more frame under the frozen
     * banner and are hidden on the next one. */
    if (g_relayout_hold) { g_relayout_hold = 0; return; }
    if (!g_loaded) load_step();
    if (playing && g_loaded) {
        place(cam_px);
        g_island_draws++;
    } else if (g_shown) {
        hide();
    }
    g_shown = playing && g_loaded; /* shown only once placed: hide() runs once per relayout, not on every load frame */
}

/* Gum Trip always draws the roof look (look 0: ISLAND_TILE_BASE, ISLAND_PAL_SLOT). */
/* ---- Gum Trip: islands of the generated course (plan step V1) ----
 * Ring slot r of the course owns sprite columns ISLAND_SPRITE + r * TRIP_VIEW_ISLAND_BLOCK ..: a chunk keeps its columns while
 * it is held. The tiles are written when a slot takes a new island, then only x (and visibility) of columns that changed. */
#define TRIP_ISLAND_SLOTS (TRIP_GEN_RING * TRIP_VIEW_ISLAND_BLOCK)
static u32 g_trip_key[TRIP_GEN_RING]; /* chunk index + 1 whose island the block holds, 0 none */
static u32 g_trip_px;
static u8 g_trip_on, g_trip_px_valid;

static void trip_block_hide(int r) {
    for (int c = 0; c < TRIP_VIEW_ISLAND_BLOCK; c++) {
        u16 i = (u16)(r * TRIP_VIEW_ISLAND_BLOCK + c);
        if (g_col_x[i] != CAMERA_COL_HIDDEN) {
            gfx_word((u16)(ADDR_SCB3 + ISLAND_SPRITE + i), 0);
            g_col_x[i] = CAMERA_COL_HIDDEN;
        }
    }
}

static void trip_block_load(int r, const TripChunk *ch) {
    int w = ch->island.w, cols = trip_view_island_cols(w);
    for (int c = 0; c < cols; c++) {
        u16 i = (u16)(r * TRIP_VIEW_ISLAND_BLOCK + c);
        int anim = island_piece_anim(w, c);
        const IslandFrame *f = &island_frames[island_anims[anim].first_frame];
        u16 attr = (u16)((ISLAND_PAL_SLOT + f->palette) << 8);
        if (island_anim_swaps(anim)) attr |= 0x08;
        g_tiles[i] = island_tile_index[f->tile_offset];
        gfx_sprite_strips((u16)(ISLAND_SPRITE + i), 1, 1, &g_tiles[i], ISLAND_TILE_BASE, attr);
    }
}

void island_trip_step(const TripGen *g, uint32_t scroll_px, int ready) {
    u8 changed = 0, moved = 0;
    if (!g) {
        if (g_trip_on) {
            for (int r = 0; r < TRIP_GEN_RING; r++) { trip_block_hide(r); g_trip_key[r] = 0; }
            g_trip_on = 0; g_trip_px_valid = 0;
            g_loaded = 0; /* island_step loads the arena tiles into these sprites again */
        }
        return;
    }
    g_trip_on = 1;
    if (!ready) { /* a new run holds here while the course is built: the previous run's islands must not stay on screen */
        for (int r = 0; r < TRIP_GEN_RING; r++) {
            if (!g_trip_key[r]) continue;
            trip_block_hide(r); g_trip_key[r] = 0; g_trip_px_valid = 0;
        }
        return;
    }
    if (!g_loaded) return;
    for (int r = 0; r < TRIP_GEN_RING; r++) {
        const TripChunk *ch = trip_view_ring_chunk(g, r, ready);
        u32 key = (ch && ch->island.present) ? ch->index + 1 : 0;
        if (key == g_trip_key[r]) continue;
        trip_block_hide(r);
        if (key) trip_block_load(r, ch);
        g_trip_key[r] = key;
        changed = 1;
    }
    if (!changed && g_trip_px_valid && scroll_px == g_trip_px) return;
    g_trip_px = scroll_px; g_trip_px_valid = 1;
    for (int r = 0; r < TRIP_GEN_RING; r++) {
        const TripChunk *ch;
        int cols;
        if (!g_trip_key[r]) continue;
        ch = trip_view_ring_chunk(g, r, ready);
        cols = trip_view_island_cols(ch->island.w);
        for (int c = 0; c < cols; c++) {
            u16 i = (u16)(r * TRIP_VIEW_ISLAND_BLOCK + c);
            int sx = trip_view_island_col_x(ch, c, scroll_px);
            if (sx == g_col_x[i]) continue;
            if (sx == CAMERA_COL_HIDDEN) {
                gfx_word((u16)(ADDR_SCB3 + ISLAND_SPRITE + i), 0);
            } else {
                if (g_col_x[i] == CAMERA_COL_HIDDEN) gfx_word((u16)(ADDR_SCB3 + ISLAND_SPRITE + i), gfx_scb3_word(1, ch->island.y - ISLAND_LINE_ROW));
                g_scb4[i] = gfx_scb4_word(sx);
                moved = 1;
            }
            g_col_x[i] = (s16)sx;
        }
    }
    if (moved) gfx_scb_run((u16)(ADDR_SCB4 + ISLAND_SPRITE), 1, g_scb4, TRIP_ISLAND_SLOTS);
    g_island_trip_draws++;
}

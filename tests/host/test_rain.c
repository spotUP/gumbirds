/* test_rain.c - storm rain: spawn, drop cap, HUD rows and text kept, lightning timer and flash, palette slot. */
#include <stdio.h>
#include <string.h>
#include "../../src/core/rain.h"
#include "../../src/vram_layout.h"
#include "gen/rain_tiles.h"

static int fails;
#define CHECK(c, msg) do { if (!(c)) { printf("[FAIL] %s\n", msg); fails++; } } while (0)

static VramQueue q;
static Rain r;

static int rain_cells(void) {
    int n = 0;
    for (int x = 0; x < 40; x++) for (int y = 0; y < 32; y++) { uint16_t w = q.fix_want[x * VQ_FIX_ROWS + y]; if ((w >> 12) == RAIN_PAL_SLOT) n++; }
    return n;
}

int main(void) {
    /* palette slot: below 16 (4-bit fix palette), not the font's 0..4, not the attract slot 5, and the sprite chain moved up by one */
    CHECK(RAIN_PAL_SLOT == 6, "rain slot 6 (the test-rain target passes it to the Lua check)");
    CHECK(RAIN_PAL_SLOT < 16, "rain slot below 16");
    CHECK(RAIN_PAL_SLOT >= FIX_PAL_COUNT && RAIN_PAL_SLOT != ATTRACT_PAL_SLOT, "rain slot is its own");
    CHECK(OBS_PAL_SLOT == RAIN_PAL_SLOT + 1, "obstacle palettes follow the rain slot");
    CHECK(RAIN_FIX_BASE + RAIN_FIX_TILES <= 0x1000, "rain tiles inside the 12-bit code range");

    vq_init(&q);
    vq_fix_fill(&q, FIXFONT_BLANK);
    rain_init(&r, RAIN_PAL_SLOT);
    /* spawn: drops appear, never above the cap, cells only on blank non-HUD cells */
    int peak = 0, max_cells = 0, hud_hit = 0;
    for (int f = 0; f < 1200; f++) {
        rain_step(&r, &q, 1, RAIN_MODE_ARENA, 0);
        if (r.n > peak) peak = r.n;
        int c = rain_cells();
        if (c > max_cells) max_cells = c;
        for (int x = 0; x < 40; x++) for (int row = 0; row < 28; row++)
            if ((rain_hud_rows[RAIN_MODE_ARENA] >> row & 1u) && (q.fix_want[x * VQ_FIX_ROWS + row + 2] >> 12) == RAIN_PAL_SLOT) hud_hit++;
    }
    CHECK(peak > 10, "drops spawn");
    CHECK(peak <= RAIN_MAX_DROPS, "drop cap");
    CHECK(max_cells > 20, "rain cells reach the fix layer");
    CHECK(hud_hit == 0, "no rain on HUD rows");
    printf("[INFO] peak drops %d, peak cells %d\n", peak, max_cells);
    /* text is never overwritten and never blanked by the rain */
    vq_fix_put(&q, 10, 14, (uint16_t)((1 << 12) | 'A'));
    for (int f = 0; f < 600; f++) rain_step(&r, &q, 1, RAIN_MODE_ARENA, 0);
    CHECK(q.fix_want[10 * VQ_FIX_ROWS + 14] == (uint16_t)((1 << 12) | 'A'), "text cell kept");
    /* inactive: every cell it owned is blank again */
    rain_step(&r, &q, 0, RAIN_MODE_ARENA, 0);
    CHECK(rain_cells() == 0, "rain cells released when inactive");
    /* lightning: first flash after the first gap, then the typed gaps, flash levels 1..4, burst palette */
    rain_init(&r, RAIN_PAL_SLOT);
    int first = -1, second = -1, seen[5] = { 0 }, flashes = 0, burst_pal = 0;
    for (int f = 1; f < 60 * 40; f++) {
        rain_step(&r, &q, 1, RAIN_MODE_ARENA, 0);
        if (r.flash_t == 1) { flashes++; if (first < 0) first = f; else if (second < 0) second = f; }
        seen[rain_flash_index(&r)]++;
        if (rain_burst_palette(&r)) burst_pal++;
    }
    CHECK(first == 7 * 60, "first flash after 7 s");
    CHECK(second - first >= 11 * 60, "second gap 11 s after the flash");
    CHECK(seen[1] >= 4 && seen[2] >= 4 && seen[3] >= 4 && seen[4] >= 4, "flash levels 1..4 shown");
    CHECK(burst_pal >= RAIN_BURST_PAL_FRAMES, "burst palette shown");
    CHECK(flashes >= 3, "flashes repeat");
    CHECK(rain_flash_color(0x0000, 1) != 0 && rain_flash_color(0x1234, 0) == 0x1234, "flash colour lifts toward white");
    printf("%s\n", fails ? "[FAIL] test_rain" : "[OK] test_rain");
    return fails != 0;
}

#include "island_layout.h"
#include "stage.h"
#include "gen/island_tables.h"

static const unsigned char k_width[ISLAND_WIDTH_COUNT] = ISLAND_TABLE_WIDTH;
static const unsigned char k_count[ISLAND_WIDTH_COUNT] = ISLAND_TABLE_PIECE_COUNT;
static const unsigned char k_pieces[] = ISLAND_TABLE_PIECES;
static const unsigned char k_swap[] = ISLAND_TABLE_SWAP;

int island_columns(int w) {
    for (int i = 0; i < ISLAND_WIDTH_COUNT; i++)
        if (k_width[i] == w) return k_count[i];
    return 0;
}

int island_piece_anim(int w, int col) {
    int first = 0;
    for (int i = 0; i < ISLAND_WIDTH_COUNT; i++) {
        if (k_width[i] == w) return (col >= 0 && col < k_count[i]) ? k_pieces[first + col] : -1;
        first += k_count[i];
    }
    return -1;
}

int island_anim_swaps(int anim) {
    return anim >= 0 && anim < (int)sizeof k_swap && k_swap[anim];
}

int island_total_columns(void) {
    int n = 0;
    for (int i = 0; i < STAGE_PLATFORM_COUNT; i++) n += island_columns(stage_platforms[i].w);
    return n;
}

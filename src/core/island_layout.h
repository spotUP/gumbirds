/*
 * island_layout.h - which sprite piece draws which 16 px column of a stage platform (the floating islands).
 * Pure C99. The piece tables are generated (build/gen/island_tables.h, tools/import_islands_sheet.py): per island width a
 * list of animation indices (cap, mids, cap), and per animation whether it swaps (the two cap pieces use the hardware
 * 8-frame auto-animation). The widths come from the stage table (stage.c), the one source of the island positions.
 */
#ifndef BRAWL_ISLAND_LAYOUT_H
#define BRAWL_ISLAND_LAYOUT_H

/* Sprite columns of an island of width w (pixels), 0 when the generated tables have no piece list for that width. */
int island_columns(int w);
/* Animation index (ISLAND_ANIM_*) of column col of an island of width w, -1 when out of range or width unknown. */
int island_piece_anim(int w, int col);
/* 1 when the animation index swaps tiles by hardware auto-animation (an 8-frame run), else 0. */
int island_anim_swaps(int anim);
/* Sprite columns of all stage platforms together: the size of the island sprite range (ISLAND_COUNT, sprite_slots.h). */
int island_total_columns(void);

#endif

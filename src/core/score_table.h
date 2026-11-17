/*
 * score_table.h - one high score table per game mode (plan T-B8). Portable C99, no libc
 * beyond stdint/stddef. Pure logic: no hardware, no malloc, no division in per-frame paths.
 *
 * Layered on hiscore.h: each mode owns one HiscoreTable (10 rows, 8 character names, name
 * entry already exists in flow.c), so hiscore_insert / hiscore_defaults are reused, not
 * duplicated. Link hiscore.c with score_table.c.
 *
 * Backup RAM image v5 (v4 = four tables + tags, 500 bytes, still loads; v3 and v2 below also load) (v2 = first two tables, 250 bytes, still loads), big endian (explicit, like hiscore.h):
 *   offset  size  field
 *      0     4    magic 'R' 'O' 'O' 'F' (HISCORE_MAGIC, same as v1)
 *      4     2    version (3)
 *      6   120    arena table: 10 x (8 name bytes + u32 score)
 *    126   120    trip table, same layout
 *    246   120    arcade table, same layout
 *    366   120    party table, same layout
 *    486    10    party rule tag per party row (PARTY_*)
 *    496   120    Gum Games table (v5 only; v4 ends here with the checksum at 496)
 *    616    24    Gum Games event records, 6 x u32 big endian (v5 only; 0 = no record)
 *    640     4    checksum: FNV-1a 32 bit over bytes 0..639
 * Total SCORE_IMAGE_SIZE = 644 bytes (the checksum of v4 sits at 496; v3 = 370 bytes, no party table: loads with party defaults). A v1 image (130 bytes) loads as the arena table with
 * the trip defaults.
 */
#ifndef BRAWL_SCORE_TABLE_H
#define BRAWL_SCORE_TABLE_H

#include <stdint.h>
#include <stddef.h>
#include "hiscore.h"
#include "tuning.h"

#define SCORE_MODES 5u           /* index = GameMode: 0 arena, 1 trip, 2 arcade, 3 party, 4 gum games */
#define SCORE_GG_EVENTS 6u       /* Gum Games events with a saved record (gumgames.h GG_EVENT_COUNT) */
#define SCORE_CAP 999999u        /* display fact (6 digits): clamp, never wrap */
#define SCORE_VERSION 5u
#define SCORE_IMAGE_SIZE 644u     /* 6 + 5 x 120 + 10 party rule tags + 6 x 4 records + 4 checksum (tags sit after the party table, records after the Gum Games table) */
#define SCORE_VERSION_4 4u        /* load path only: four tables + tags, 500 bytes; Gum Games defaults */
#define SCORE_IMAGE_SIZE_4 500u
#define SCORE_VERSION_3 3u        /* load path only: arena + trip + arcade, 370 bytes; party defaults */
#define SCORE_IMAGE_SIZE_3 370u
#define SCORE_VERSION_2 2u        /* load path only: arena + trip, 250 bytes */
#define SCORE_IMAGE_SIZE_2 250u
#define SCORE_ARCADE_DEFAULT_TOP 10000u
#define SCORE_ARCADE_DEFAULT_STEP 1000u

/* Trip default rows (agent default): 3000 down to 300 in steps of 300, name "GUMTRIP",
 * lower than the arena defaults so the first run ranks. */
#define SCORE_TRIP_DEFAULT_TOP 3000u
#define SCORE_TRIP_DEFAULT_STEP 300u

typedef struct {
    HiscoreTable t[SCORE_MODES];
    uint32_t gg_record[SCORE_GG_EVENTS]; /* best mark per Gum Games event (gumgames.h gg_record_better decides what better means); 0 = none */
    uint8_t party_rule[HISCORE_ENTRIES]; /* PARTY_* tag of each row of the party table (t[GAME_MODE_PARTY]); 0 = none */
} ScoreTables;

/* Factory rows for both modes. */
void score_tables_defaults(ScoreTables *s);

/* 1 when mode is valid, every row sorted descending and every score <= SCORE_CAP. */
int score_tables_valid(const ScoreTables *s);

/* Would this score enter mode's table? 0 for score 0, a bad mode, or a score that does not
 * beat the last row (a tie with the last row does not qualify: earlier entry stays above). */
int score_qualifies(const ScoreTables *s, unsigned mode, uint32_t score);

/* Insert (score clamped to SCORE_CAP first). Returns the 0 based row or -1. Only mode's table
 * changes. */
int score_insert(ScoreTables *s, unsigned mode, const char *name, uint32_t score);
/* Same, and for the party table the new row carries rule (the tags shift with the rows). */
int score_insert_rule(ScoreTables *s, unsigned mode, const char *name, uint32_t score, uint8_t rule);

/* Read a row. Returns 1 and fills name (8 chars, space padded, NOT terminated) and score;
 * 0 for a bad mode or row (outputs untouched). Either output pointer may be NULL. */
int score_entry(const ScoreTables *s, unsigned mode, unsigned row, char *name8, uint32_t *score);

/* Image round trip. Serialise returns SCORE_IMAGE_SIZE or 0 when cap is too small.
 * Load returns 1 (valid v5), 5 (valid v4: Gum Games defaults), 4 (valid v3: party defaults), 3 (valid v2: arena + trip, arcade defaults), 2 (valid v1: arena from the image, others defaults) or 0 (anything
 * else, including a corrupt block or unsorted rows: both tables set to defaults). */
size_t score_serialise(const ScoreTables *s, uint8_t *buf, size_t cap);
int score_load(ScoreTables *s, const uint8_t *buf, size_t len);

/* Which mode's table to draw. FlowState values from flow.h:
 *   ATTRACT_TITLE            highlighted (the mode picked on the title)
 *   ATTRACT_TABLE            alternates: arena for swap_frames, trip for swap_frames, ...
 *                            driven by the state timer; swap_frames 0 gives arena
 *   everything else          run_mode (the table of the run being scored / entered)
 * No division: repeated subtraction, at most timer / (2 * swap_frames) steps (2 at the
 * default knob and the default table screen length). */
unsigned score_shown_mode(unsigned flow_state, unsigned highlighted, unsigned run_mode,
                          uint16_t timer, uint16_t swap_frames);

#endif

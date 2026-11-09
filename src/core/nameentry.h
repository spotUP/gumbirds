/*
 * nameentry.h - 8 character name entry state machine. Portable C99, no libc.
 *
 * Controls: joystick up/down cycles the character under the cursor (with auto-repeat while
 * held), A confirms it and moves to the next position, B goes back one position. The
 * character set is A-Z, 0-9, space, '.', and an END glyph. Choosing END with A, or confirming
 * the 8th position, finishes. No new button press for NAME_TIMEOUT_FRAMES also finishes and keeps
 * what was confirmed so far. Inputs are raw held bits; edges are detected here.
 *
 * Result: name[8], space padded, valid when done is 1. If nothing was confirmed the name is
 * NAME_ENTRY_DEFAULT.
 */
#ifndef ROOFLINE_NAMEENTRY_H
#define ROOFLINE_NAMEENTRY_H

#include <stdint.h>
#include "tuning.h"
#include "game.h" /* IN_A..IN_D */

/* Direction bits share the input byte with the buttons (IN_A..IN_D are bits 0..3). */
#define IN_UP 0x10u
#define IN_DOWN 0x20u
#define IN_LEFT 0x40u
#define IN_RIGHT 0x80u

#define NAME_LEN 8
#define NAME_SYMBOLS 39                 /* A-Z, 0-9, space, '.', END */
#define NAME_SYMBOL_END (NAME_SYMBOLS - 1)
#define NAME_ENTRY_DEFAULT "PLAYER  "

typedef struct {
    char name[NAME_LEN];       /* space padded; only [0, pos) is confirmed while editing */
    uint8_t sym[NAME_LEN];     /* symbol index under the cursor for each position */
    uint8_t pos;               /* cursor position 0..7 */
    uint8_t done;              /* 1 when finished; name is final */
    uint8_t prev_in;           /* previous raw input, for edge detection */
    uint8_t held_dir;          /* IN_UP or IN_DOWN being held, else 0 */
    uint16_t held_frames;      /* frames the direction has been held */
    uint16_t idle;             /* frames since the last input */
} NameEntry;

void nameentry_init(NameEntry *e);
/* One frame. input is the raw held bits. Does nothing once done. */
void nameentry_step(NameEntry *e, uint8_t input);
/* The character a symbol index draws as. END returns 0: the renderer draws the END glyph. */
char nameentry_symbol_char(uint8_t sym);

#endif

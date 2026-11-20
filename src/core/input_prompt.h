#ifndef INPUT_PROMPT_H
#define INPUT_PROMPT_H
#include <stdint.h>

/* On-screen input prompts (owner pick A, "cabinet caps"): the buttons a player needs right now, drawn as fix layer caps in the screen corners.
 * Pure logic. An event reports only its own phase; this table says what to show and how the caps move.
 *   MASH   caps press down one after the other (a single cap pulses)
 *   PRESS  caps glow together, press once
 * The stick item (left right sweep) comes first when the event steers. */
enum { IP_BLOW, IP_RACE, IP_GATHER, IP_DASH, IP_POP, IP_FLING, IP_TOSS, IP_EVENTS };
enum { IP_STYLE_NONE, IP_STYLE_MASH, IP_STYLE_PRESS };
#define IP_PHASE_PLAY 0u   /* Gather and Dash have no phase enum: PLAY while the run is on, OFF once it is over */
#define IP_PHASE_OFF 1u
#define IP_MAX_ITEMS 3u    /* stick + 2 caps, or 3 caps: never more */

typedef struct { uint8_t buttons;   /* IN_A | IN_B | IN_C bits */
                 uint8_t style;     /* IP_STYLE_* */
                 uint8_t stick; } InputPrompt;

/* What `event` shows in its phase (the event's own phase enum, see gumgames.h, gg_fling.h, gg_popdrop.h, gg_toss.h). */
InputPrompt input_prompt_for(uint8_t event, uint8_t phase);

/* Item list of a prompt: item codes in draw order. Returns the item count. */
enum { IP_ITEM_CAP_A, IP_ITEM_CAP_B, IP_ITEM_CAP_C, IP_ITEM_STICK, IP_ITEM_NONE = 0xFF };
enum { IP_CAP_UP, IP_CAP_DOWN, IP_CAP_GLOW, IP_STICK_NEUTRAL, IP_STICK_LEFT, IP_STICK_RIGHT };
/* State of item i (0 .. count-1) at animation tick: kind = IP_ITEM_*, state = IP_CAP_* or IP_STICK_*. */
uint8_t input_prompt_items(const InputPrompt *p, uint8_t *kind);
uint8_t input_prompt_state(const InputPrompt *p, uint8_t kind, uint16_t tick);
#endif

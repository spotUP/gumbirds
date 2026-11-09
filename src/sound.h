#ifndef SOUND_H
#define SOUND_H
/*
 * 68k side of the sound driver (nullsound on the Z80, see thoughts/shared/plans/2026-11-09-sound-driver.md).
 * Ids come from build/snd_commands.h (generated from assets/sound/*.yaml): SND_SFX_*, SND_MUSIC_*.
 * Commands are queued and written to REG_SOUND one per frame by sound_tick().
 */
#include <stdint.h>
#include "core/flow.h"

void sound_init(void);                  /* queue reset_driver (command 3) */
void sound_play_sfx(uint8_t id);        /* id = SND_SFX_* */
void sound_music(uint8_t id);           /* id = SND_MUSIC_*, restarts */
void sound_stop(void);                  /* stop_music (command 2) */
void sound_frame(const FlowView *v);    /* game events -> sound calls, once per frame */
void sound_tick(void);                  /* pops one queued command to REG_SOUND, once per frame */

extern volatile uint16_t g_sound_sent;  /* test sentinel: commands written to REG_SOUND */
extern volatile uint8_t g_sound_last;   /* test sentinel: last command byte written */

#endif

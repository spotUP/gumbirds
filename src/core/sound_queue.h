#ifndef SOUND_QUEUE_H
#define SOUND_QUEUE_H
/*
 * Pure model of the 68k -> Z80 command path. Game code pushes sound command bytes; sound.c (the single
 * owner of REG_SOUND) pops at most one per frame, so the Z80 NMI handler never sees two bytes back to back.
 * Overflow policy: the newest push is dropped (an old music command is worth more than a late blip) and counted.
 */
#include <stdint.h>

#define SQ_CAP 16

typedef struct {
    uint8_t buf[SQ_CAP];
    uint8_t head, count;
    uint16_t dropped;
} SoundQueue;

void sq_init(SoundQueue *q);
int sq_push(SoundQueue *q, uint8_t cmd);   /* 1 = queued, 0 = full and dropped */
int sq_pop(SoundQueue *q, uint8_t *cmd);   /* 1 = got a command, 0 = empty */

#endif

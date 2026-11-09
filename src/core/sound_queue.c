#include "sound_queue.h"

void sq_init(SoundQueue *q) { q->head = 0; q->count = 0; q->dropped = 0; }

int sq_push(SoundQueue *q, uint8_t cmd)
{
    if (q->count >= SQ_CAP) { q->dropped++; return 0; }
    q->buf[(q->head + q->count) % SQ_CAP] = cmd;
    q->count++;
    return 1;
}

int sq_pop(SoundQueue *q, uint8_t *cmd)
{
    if (!q->count) return 0;
    *cmd = q->buf[q->head];
    q->head = (uint8_t)((q->head + 1) % SQ_CAP);
    q->count--;
    return 1;
}

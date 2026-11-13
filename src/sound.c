#include "sound.h"
#include "core/sound_queue.h"
#include "core/sound_events.h"
#include "snd_commands.h"

#define REG_SOUND_ADDR ((volatile uint8_t *)0x320000)
#define CMD_STOP_MUSIC 2
#define CMD_RESET_DRIVER 3

volatile uint16_t g_sound_sent;
volatile uint8_t g_sound_last;
static SoundQueue g_queue;
static SoundEvents g_events;

void sound_init(void)
{
    sq_init(&g_queue);
    se_init(&g_events);
    sq_push(&g_queue, CMD_RESET_DRIVER);
}

void sound_play_sfx(uint8_t id) { sq_push(&g_queue, id); }
void sound_music(uint8_t id) { sq_push(&g_queue, id); }
void sound_stop(void) { sq_push(&g_queue, CMD_STOP_MUSIC); }

const SoundEvents *sound_events(void) { return &g_events; }

void sound_frame(const FlowView *v)
{
    uint16_t ev = se_step(&g_events, v);
    uint8_t n;
    if (ev & SE_START) sound_music(SND_MUSIC_INGAME);
    if (ev & SE_FLAP) sound_play_sfx(SND_SFX_JUMP);
    if (ev & SE_HIT) sound_play_sfx(SND_SFX_HIT);
    if (ev & SE_SIZZLE) sound_play_sfx(SND_SFX_SIZZLE);
    /* several fliers can die in one frame: one request each; sound_tick sends one per frame, so they play one after the other (queue holds SQ_CAP) */
    /* pop first, then die: a last-balloon burst plays both through the queue */
    for (n = 0; n < g_events.n_pop; n++) sound_play_sfx(SND_SFX_POP);
    for (n = 0; n < g_events.n_die; n++) sound_play_sfx(SND_SFX_DIE);
    for (n = 0; n < g_events.n_fall; n++) sound_play_sfx(SND_SFX_FALL);
    for (n = 0; n < g_events.n_splosh; n++) sound_play_sfx(SND_SFX_SPLOSH);
    for (n = 0; n < g_events.n_spike; n++) sound_play_sfx(SND_SFX_SPIKE);
    if (ev & SE_GAME_OVER) { sound_stop(); sound_play_sfx(SND_SFX_GAME_OVER); }
}

void sound_tick(void)
{
    uint8_t cmd;
    if (!sq_pop(&g_queue, &cmd)) return;
    *REG_SOUND_ADDR = cmd;
    g_sound_last = cmd;
    g_sound_sent++;
}

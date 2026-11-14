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
/* Frames of round_clear (48 rows x speed 5, derived by hand from the .fur): then the arena loop restarts. */
#define ROUND_CLEAR_FRAMES 240
static uint16_t g_resume;
static uint8_t g_flap_i, g_pop_i;   /* variant rotation: repeated flaps and pops do not sound stamped */
static const uint8_t FLAPS[3] = { SND_SFX_FLAP_A, SND_SFX_FLAP_B, SND_SFX_FLAP_C };
static const uint8_t POPS[3] = { SND_SFX_POP_A, SND_SFX_POP_B, SND_SFX_POP_C };
static const uint8_t CUE_SFX[SC_COUNT] = {
    [SC_GO] = SND_SFX_ROUND_GO, [SC_BANNER] = SND_SFX_BANNER_IN,
    [SC_PUMP_A] = SND_SFX_PUMP_A, [SC_PUMP_B] = SND_SFX_PUMP_B, [SC_RIVAL_LAUNCH] = SND_SFX_RIVAL_LAUNCH, [SC_DEFEAT] = SND_SFX_DEFEAT,
    [SC_BUMP] = SND_SFX_BUMP, [SC_CHUTE] = SND_SFX_CHUTE,
    [SC_VENT_WARN] = SND_SFX_VENT_WARN, [SC_VENT_BURST] = SND_SFX_VENT_BURST, [SC_FLIPPER] = SND_SFX_FLIPPER, [SC_GRATE] = SND_SFX_GRATE,
    [SC_GRAB_RISE] = SND_SFX_GRAB_RISE, [SC_GRAB_BITE] = SND_SFX_GRAB_BITE, [SC_BUBBLE_PUFF] = SND_SFX_BUBBLE_PUFF,
    [SC_PICKUP] = SND_SFX_PICKUP, [SC_PICKUP_STREAK] = SND_SFX_PICKUP_STREAK, [SC_RIVAL_WARN] = SND_SFX_RIVAL_WARN, [SC_GUM_LOW] = SND_SFX_GUM_LOW,
    [SC_LIFE_LOST] = SND_SFX_LIFE_LOST, [SC_CONTINUE_TICK] = SND_SFX_CONTINUE_TICK, [SC_CONTINUE_YES] = SND_SFX_CONTINUE_YES,
    [SC_NE_MOVE] = SND_SFX_NE_MOVE, [SC_NE_CONFIRM] = SND_SFX_NE_CONFIRM, [SC_NE_DONE] = SND_SFX_NE_DONE,
};

void sound_init(void)
{
    sq_init(&g_queue);
    se_init(&g_events);
    sq_push(&g_queue, CMD_RESET_DRIVER);
}

void sound_play_sfx(uint8_t id) { sq_push(&g_queue, id); }
void sound_play_pop(void) { sound_play_sfx(POPS[g_pop_i]); g_pop_i = (uint8_t)(g_pop_i == 2 ? 0 : g_pop_i + 1); }
void sound_music(uint8_t id) { sq_push(&g_queue, id); }
void sound_stop(void) { sq_push(&g_queue, CMD_STOP_MUSIC); }

const SoundEvents *sound_events(void) { return &g_events; }

void sound_frame(const FlowView *v)
{
    uint16_t ev = se_step(&g_events, v);
    uint8_t n;
    uint32_t c;
    if (g_resume && !--g_resume) sound_music(SND_MUSIC_ARENA);
    if (ev & SE_TITLE) sound_music(SND_MUSIC_TITLE);
    if (ev & SE_START) { g_resume = 0; sound_music(SND_MUSIC_ARENA); sound_play_sfx(SND_SFX_START); }
    if (ev & SE_ROUND) { sound_music(SND_MUSIC_ROUND_CLEAR); g_resume = ROUND_CLEAR_FRAMES; }
    if (ev & SE_FLAP) { sound_play_sfx(FLAPS[g_flap_i]); g_flap_i = (uint8_t)(g_flap_i == 2 ? 0 : g_flap_i + 1); }
    if (ev & SE_HIT) sound_play_sfx(SND_SFX_HIT);
    if (ev & SE_SIZZLE) sound_play_sfx(SND_SFX_SIZZLE);
    /* several fliers can die in one frame: one request each; sound_tick sends one per frame, so they play one after the other (queue holds SQ_CAP) */
    /* pop first, then die: a last-balloon burst plays both through the queue */
    for (n = 0; n < g_events.n_pop; n++) sound_play_pop();
    for (n = 0; n < g_events.n_die; n++) sound_play_sfx(SND_SFX_DIE);
    for (n = 0; n < g_events.n_fall; n++) sound_play_sfx(SND_SFX_FALL);
    for (n = 0; n < g_events.n_splosh; n++) sound_play_sfx(SND_SFX_SPLOSH);
    for (n = 0; n < g_events.n_spike; n++) sound_play_sfx(SND_SFX_SPIKE);
    for (c = g_events.cues, n = 0; c; c >>= 1, n++) if (c & 1) sound_play_sfx(CUE_SFX[n]);
    if (ev & SE_GAME_OVER) { g_resume = 0; sound_music(SND_MUSIC_GAME_OVER); }
}

void sound_tick(void)
{
    uint8_t cmd;
    if (!sq_pop(&g_queue, &cmd)) return;
    *REG_SOUND_ADDR = cmd;
    g_sound_last = cmd;
    g_sound_sent++;
}

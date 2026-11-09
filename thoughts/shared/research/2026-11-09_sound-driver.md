---
date: 2026-11-09
topic: sound driver phase 2 (build integration, 68k API, test-sound)
status: test-sound green (2026-11-09)
---
# Sound driver phase 2: state

## Done
- Clean one-command `gmake` builds nullsound M1 and V1 from source (verified in a copy of the repo without build/).
  Ordering fix: `CUSTOM_GENERATE_TARGETS=sound-gen` (Makefile) makes build.mk's `cart` run the generation
  (samples.inc, snd_commands.inc, snd_commands.h, build/sound/nss-deps.mk) before compiling; nss-deps.mk is a
  remade `-include`. Generated assets (stand-in music, SFX WAVs) are ORDER-ONLY prerequisites of the generated
  files because build.mk recipes read the maps through `$^`. After changing a generator script run `gmake generate`.
- Music file must be named after the yaml entry: nss-deps.mk derives labels from the .fur basename
  (`ingame.fur` -> `nss_ingame`); `standin.fur` gave undefined `nss_ingame`.
- Licence of ngdevkit-examples assets unclear: nothing copied. `tools/make_standin_fur.py` writes a minimal
  Furnace v213 module, `tools/make_sfx_placeholders.py` writes the five SFX WAVs, both into build/sound.
- Linker map: `build/sound/driver.map` (sdld `-m`).
- 68k: `src/sound.c/.h` (sound_init, sound_play_sfx, sound_music, sound_stop, sound_frame, sound_tick; sentinels
  g_sound_sent u16, g_sound_last u8), `src/core/sound_queue.c/.h` (16 deep, newest dropped, one pop per frame),
  `src/core/sound_events.c/.h` (edge detection: start, jump, hit, laser, game over; demo silent; coin blip is
  played on run start because the flow has no coin event). Hooks in src/main.c: sound_init after video_init,
  sound_frame + sound_tick after flow_view. Host test `tests/host/test_sound_queue.c` (in run.sh): all host tests pass.
- rom.mk: VROMTEMPLATE enabled.

## test-sound failure: root cause (fixed 2026-11-09)
- Violated invariant: the test must see every command the Z80 receives and every ADPCM-A key-on. Root level:
  the test decode (tests/mame/sound_check.lua), not the 68k send path or the driver. Two decode bugs:
  1. Z80 io addresses are 16-bit: `in a,(n)` / `out (n),a` drive A8-A15 with register A. The taps covered only
     0x0000-0x00ff (cmd) and 0x0004-0x0007 (YM), so they saw an access only when A happened to be 0 (hence
     "3 of 10 commands", 0 key-ons). Taps now span 0x0000-0xffff and decode the port from the low byte.
  2. sample-map.yaml `channel` is 1-based: soundtool.py does `channel = data.get('channel', 6) - 1`, bit
     `1 << channel`. The test hardcoded bit = 1 << yaml value. Masks now come from build/snd_commands.inc
     (`.db 0xNN ; channel (bit)`), the driver's own table. Yaml comment corrected.
- nullsound command protocol (read from the linked M1 with the MAME debugger `dasm`, no sources installed):
  NMI at 0x66 reads port 0x00 once; 1 (rom switch), 2 (stop: re-inits the driver, clears the FIFO, then
  stream_stop) and 3 (reset) run inside the NMI. Any other command jumps to 0x159, reads port 0x00 again,
  pushes it into the 64-entry FIFO at 0xF800 (indices 0xF840/0xF841) and acks `cmd | 0x80` on port 0x0C.
  No 68k handshake is required; one command per frame is safe. The test counts one command per NMI: a port
  0x00 read of 1-3, or a port 0x0C write with bit 7 set.
- Consequence for the 68k: command 2 drops any not-yet-processed FIFO entries. With one command per frame the
  FIFO is drained before the next arrives, so nothing is lost today.
- Measured: 68k sent 10 (reset, coin, music, jump, laser x2, hit x2, stop, game_over), Z80 received the same
  10, 7 key-ons on the right channels, 268 FM/SSG writes. Revert check (sound_play_sfx stubbed): FAIL
  "68k never sent coin (id 9)".
- UniBIOS 4.0 boot (probe, 900 frames, no input): command 1 at frames 73 and 80, then 3 at 367, 3 x2 at 369,
  2 at 376, 3 at 836 and 854. Which of the 2/3 are BIOS and which the game's sound_init is unverified
  (no 68k sentinel in the probe).

## Open
- Stand-in music and placeholder SFX are to be replaced by DEViLBOX exports.

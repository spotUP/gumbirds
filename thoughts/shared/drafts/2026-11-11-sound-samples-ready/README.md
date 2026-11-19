# Sound samples ready for the ADPCM-A pipeline (2026-11-11)

- `pop_wet_smack_adpcma.wav` (gum pop, from pop_2_wet_smack): 3031 frames, 0.164 s, 6106 bytes, ADPCM-A 1536 bytes in V ROM. Planned channel 3.
- `jingle_brass_fanfare_adpcma.wav` (round clear, from jingle_4_brass_fanfare): 32683 frames, 1.767 s, 65410 bytes, ADPCM-A 16384 bytes. Planned channel 6.

Format of both: RIFF WAV, PCM, mono, 16-bit signed, 18500 Hz (what adpcmtool.py expects for ADPCM-A; it does not resample).
Leading and trailing silence trimmed (1 percent of peak), short linear fade-out (4 ms pop, 40 ms jingle), peak -1.00 dBFS.
The drafts were already 18500 Hz mono, so no resampling was needed. Notes: thoughts/spot/2026-11-11-sound-sample-prep.md

"""Slice a Furnace render of assets/sound/sfx/fling_sfx.fur into the committed Gum Fling sfx WAVs (18500 Hz mono).

Render: /Applications/Furnace.app/Contents/MacOS/Furnace -loops 0 -output render.wav assets/sound/sfx/fling_sfx.fur
Slice:  python3 -I tools/slice_fling_sfx.py render.wav assets/sound/sfx   (needs numpy and ffmpeg)
"""
import subprocess, sys, wave
import numpy as np

ROW = 0.06  # speed 3 at 50 Hz
# name, first row, row count
CUTS = [("fling_runup_1", 0, 4), ("fling_runup_2", 4, 4), ("fling_runup_3", 8, 4), ("fling_runup_4", 12, 4),
        ("fling_throw", 16, 8), ("fling_land", 24, 6), ("fling_foul", 32, 10), ("fling_win", 44, 33),
        ("fling_lose", 80, 25)]
src, out = sys.argv[1], sys.argv[2]
for name, row, rows in CUTS:
    d = rows * ROW
    path = f"{out}/{name}.wav"
    subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-v", "error", "-ss", f"{row * ROW:.3f}", "-t", f"{d:.3f}",
                    "-i", src, "-af", f"afade=t=out:st={d - 0.03:.3f}:d=0.03", "-ac", "1", "-ar", "18500",
                    "-c:a", "pcm_s16le", path], check=True)
    w = wave.open(path)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    w.close()
    assert np.abs(a).max() > 1000, f"{name} is silent"
    a *= 0.9 * 32767 / np.abs(a).max()  # peak 0.9, the level tools/make_sfx.py masters to
    w = wave.open(path, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(18500)
    w.writeframes(np.round(a).astype("<i2").tobytes())
    w.close()
    print(f"{name} {d:.2f}s frames {len(a)} rms {20 * np.log10(np.sqrt((a * a).mean()) / 32768):.1f} dB")

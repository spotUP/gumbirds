#!/usr/bin/env python3
"""Attract overlay palette slot. Run: $PYTHON -I tests/host/test_attract_pal.py
Fix tiles hold a 4-bit palette, so the overlay icon palette (ATTRACT_PAL_SLOT) must be a fix slot 0..15 that no font palette uses
(slots 0..FIXFONT_PAL_COUNT-1) and that no sprite palette range starts on: the sprite chain in src/vram_layout.h begins after it."""
import os, re, sys
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
lay = open(os.path.join(ROOT, "src/vram_layout.h")).read()
fonts = int(re.search(r"#define FIXFONT_PAL_COUNT (\d+)", open(os.path.join(ROOT, "build/gen/fix_font.h")).read()).group(1))
att = re.search(r"#define ATTRACT_PAL_SLOT (.+?) /\*", lay).group(1)
obs = re.search(r"#define OBS_PAL_SLOT (.+?)(?: /\*|\n)", lay).group(1)
fails = []
if att != "FIX_PAL_COUNT": fails.append("ATTRACT_PAL_SLOT is '%s', expected FIX_PAL_COUNT (first slot after the font palettes)" % att)
if fonts + 1 > 16: fails.append("%d font palettes leave no fix slot for the overlay" % fonts)
if "ATTRACT_PAL_SLOT" not in obs: fails.append("OBS_PAL_SLOT '%s' does not start after the overlay slot" % obs)
if re.search(r"#define \w+_PAL_SLOT \(ATTRACT_PAL_SLOT", lay.replace("#define OBS_PAL_SLOT", "")): fails.append("another palette range is chained from ATTRACT_PAL_SLOT")
print("\n".join("[FAIL] " + f for f in fails) if fails else "[OK] overlay palette slot %d is a fix slot outside every other range" % fonts)
sys.exit(1 if fails else 0)

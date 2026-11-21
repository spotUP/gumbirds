#!/usr/bin/env python3
"""Tug Gum sprite set (tools/make_tug_sheet.py): assets/tug/tug_sheet.png + .json -> build/gen/tugpose.c1/.c2, tugpose_sprites.h/.c, tugpose_tables.h.
Usage: $PYTHON -I tools/build_tugpose_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py. Strand piece frame numbers are in the json defines."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("tugpose", "assets/tug/tug_sheet.png", "assets/tug/tug_sheet.json")

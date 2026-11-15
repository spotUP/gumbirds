#!/usr/bin/env python3
"""Storm mood background sprite set: assets/storm/storm_sheet.png + .json -> build/gen/storm.c1/.c2, storm_sprites.h/.c.
Usage: $PYTHON -I tools/build_storm_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is stacked by tools/import_bg_sheet.py storm."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("storm", "assets/storm/storm_sheet.png", "assets/storm/storm_sheet.json")

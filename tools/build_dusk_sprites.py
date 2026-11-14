#!/usr/bin/env python3
"""Dusk mood background sprite set: assets/dusk/dusk_sheet.png + .json -> build/gen/dusk.c1/.c2, dusk_sprites.h/.c.
Usage: $PYTHON -I tools/build_dusk_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is stacked by tools/import_bg_sheet.py dusk."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("dusk", "assets/dusk/dusk_sheet.png", "assets/dusk/dusk_sheet.json")

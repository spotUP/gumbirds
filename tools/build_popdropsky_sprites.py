#!/usr/bin/env python3
"""Pop Drop sky sprite set: assets/popdropsky/popdropsky_sheet.png + .json -> build/gen/popdropsky.c1/.c2, popdropsky_sprites.h/.c.
Usage: $PYTHON -I tools/build_popdropsky_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is cut from the approved draft by tools/import_popdropsky_sheet.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("popdropsky", "assets/popdropsky/popdropsky_sheet.png", "assets/popdropsky/popdropsky_sheet.json")

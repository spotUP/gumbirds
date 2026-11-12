#!/usr/bin/env python3
"""Trip kill strip sprite set: assets/tripstrip/tripstrip_sheet.png + .json -> build/gen/tripstrip.c1/.c2, tripstrip_sprites.h/.c.
Usage: $PYTHON -I tools/build_tripstrip_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is cut from the draft by
thoughts/shared/drafts/2026-11-11-gum-trip-import/make_import_sheets.py (TILE_COUNT renamed ROLE_COUNT: it clashed with the pipeline's TRIPSTRIP_TILE_COUNT)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("tripstrip", "assets/tripstrip/tripstrip_sheet.png", "assets/tripstrip/tripstrip_sheet.json")

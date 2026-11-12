#!/usr/bin/env python3
"""Trip hazard sprite set: assets/triphaz/triphaz_sheet.png + .json -> build/gen/triphaz.c1/.c2, triphaz_sprites.h/.c.
Usage: $PYTHON -I tools/build_triphaz_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is cut from the draft by
thoughts/shared/drafts/2026-11-11-gum-trip-import/make_import_sheets.py (assets/triphaz/triphaz_sheet.png is its hazards_sheet.png)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("triphaz", "assets/triphaz/triphaz_sheet.png", "assets/triphaz/triphaz_sheet.json")

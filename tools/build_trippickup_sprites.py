#!/usr/bin/env python3
"""Trip pickup sprite set: assets/trippickup/trippickup_sheet.png + .json -> build/gen/trippickup.c1/.c2, trippickup_sprites.h/.c.
Usage: $PYTHON -I tools/build_trippickup_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is cut from the draft by
thoughts/shared/drafts/2026-11-11-gum-trip-import/make_import_sheets.py (assets/trippickup/trippickup_sheet.png is its pickup_sheet.png)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("trippickup", "assets/trippickup/trippickup_sheet.png", "assets/trippickup/trippickup_sheet.json")

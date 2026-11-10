#!/usr/bin/env python3
"""Flier sprite set (name "sootling"): assets/flier/sootling_sheet.png + .json -> build/gen/sootling.c1/.c2,
sootling_sprites.h/.c. Usage: $PYTHON -I tools/build_flier_sprites.py [--out build/gen] [--scratch DIR] [--no-verify]
All logic is in tools/sprite_pipeline.py. The sheet is imported from a draft by tools/import_flier_sheet.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("sootling", "assets/flier/sootling_sheet.png", "assets/flier/sootling_sheet.json")

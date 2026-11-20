#!/usr/bin/env python3
"""Poop the Man sprite set: assets/poop/poop_sheet.png + .json -> build/gen/poop.c1/.c2, poop_sprites.h/.c.
Usage: $PYTHON -I tools/build_poop_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is cut from the approved draft by tools/import_poop_sheet.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("poop", "assets/poop/poop_sheet.png", "assets/poop/poop_sheet.json")

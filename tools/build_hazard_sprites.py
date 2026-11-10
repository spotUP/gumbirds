#!/usr/bin/env python3
"""Hazard strip sprite set: assets/hazard/hazard_sheet.png + .json -> build/gen/hazard.c1/.c2, hazard_sprites.h/.c.
Usage: $PYTHON -I tools/build_hazard_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is drawn by assets/hazard/draw_hazard.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("hazard", "assets/hazard/hazard_sheet.png", "assets/hazard/hazard_sheet.json")

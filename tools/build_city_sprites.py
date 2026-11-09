#!/usr/bin/env python3
"""City background sprite set: assets/city/city_sheet.png + .json -> build/gen/city.c1/.c2, city_sprites.h/.c.
Usage: $PYTHON -I tools/build_city_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py; the sheet is drawn by assets/city/draw_city.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("city", "assets/city/city_sheet.png", "assets/city/city_sheet.json")

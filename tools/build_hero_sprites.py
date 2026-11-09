#!/usr/bin/env python3
"""Hero sprite set: assets/hero/guard_sheet.png + .json -> build/gen/hero.c1/.c2, hero_sprites.h/.c.
Usage: $PYTHON -I tools/build_hero_sprites.py [--out build/gen] [--scratch DIR] [--no-verify]
All logic is in tools/sprite_pipeline.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("hero", "assets/hero/guard_sheet.png", "assets/hero/guard_sheet.json")

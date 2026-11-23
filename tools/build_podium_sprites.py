#!/usr/bin/env python3
"""Event result podium (blocks in two team colours, crown, chunky digits gold and blue): assets/podium/podium_sheet.png + .json -> build/gen/podium.c1/.c2, podium_sprites.h/.c.
Usage: $PYTHON -I tools/build_podium_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("podium", "assets/podium/podium_sheet.png", "assets/podium/podium_sheet.json")

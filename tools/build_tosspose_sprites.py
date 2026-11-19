#!/usr/bin/env python3
"""Toss Gum pose sprite set (tools/make_toss_sheet.py): assets/toss/toss_sheet.png + .json -> build/gen/tosspose.c1/.c2, tosspose_sprites.h/.c, tosspose_tables.h.
Usage: $PYTHON -I tools/build_tosspose_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py. The gum anchor per pose is in the json tables."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("tosspose", "assets/toss/toss_sheet.png", "assets/toss/toss_sheet.json")

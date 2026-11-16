#!/usr/bin/env python3
"""Gum bubble B sprite set (Hot Gum): assets/gum_bubble/gum_bubble_sheet.png + .json -> build/gen/gumbubble.c1/.c2, gumbubble_sprites.h/.c, gumbubble_tables.h.
Usage: $PYTHON -I tools/build_gumbubble_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py. The frame sequence (cell, dx, dy, ticks) is in the json tables."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("gumbubble", "assets/gum_bubble/gum_bubble_sheet.png", "assets/gum_bubble/gum_bubble_sheet.json")

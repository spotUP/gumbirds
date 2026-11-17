#!/usr/bin/env python3
"""Rules card example props (slab, two needles, gum, trail dot): assets/rulecard/rulecard_sheet.png + .json -> build/gen/rulecard.c1/.c2, rulecard_sprites.h/.c.
Usage: $PYTHON -I tools/build_rulecard_sprites.py [--out build/gen] [--no-verify]
All logic is in tools/sprite_pipeline.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_pipeline

if __name__ == "__main__":
    sprite_pipeline.main("rulecard", "assets/rulecard/rulecard_sheet.png", "assets/rulecard/rulecard_sheet.json")

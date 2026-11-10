#!/bin/sh
# Package the Bubblegum Brawl romset as a NeoSD .neo file for the MiSTer Neo Geo core.
# Input : build/rom/brawl-{p1,s1,m1,v1,c1,c2}.* (raw ROMs from `make`)
# Output: build/mister/bubblegum-brawl.neo  -> copy to /media/fat/games/NeoGeo/ on the MiSTer SD card
# UNVERIFIED: that an ngdevkit-built .neo boots on the MiSTer core (test on hardware, plan P1.3).
set -eu
cd "$(dirname "$0")/.."
ROMDIR=build/rom
OUT=build/mister
[ -f "$ROMDIR/brawl-p1.p1" ] || { echo "[ERROR] no ROMs in $ROMDIR; run 'make' first" >&2; exit 1; }
command -v npx >/dev/null || { echo "[ERROR] node/npx required for neosdconv" >&2; exit 1; }
mkdir -p "$OUT"
# neosdconv pinned; name is read from the file by the core, keep it short ASCII.
npx --yes neosdconv@1.0.2 -i "$ROMDIR" -o "$OUT/bubblegum-brawl.neo" -n "Bubblegum Brawl" -g Other -y 2026 -m "Bubblegum Brawl"
ls -l "$OUT/bubblegum-brawl.neo"
echo "[OK] copy $OUT/bubblegum-brawl.neo to /media/fat/games/NeoGeo/ (no stray .xml files there)"

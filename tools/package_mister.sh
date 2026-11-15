#!/bin/sh
# Package the Gumbirds romset as a NeoSD .neo file for the MiSTer Neo Geo core.
# Input : build/rom/gumbirds-{p1,s1,m1,v1,c1,c2}.* (raw ROMs from `make`)
# Output: build/mister/gumbirds.neo  -> copy to /media/fat/games/NeoGeo/ on the MiSTer SD card
# UNVERIFIED: that an ngdevkit-built .neo boots on the MiSTer core (test on hardware, plan P1.3).
set -eu
cd "$(dirname "$0")/.."
ROMDIR=build/rom
OUT=build/mister
[ -f "$ROMDIR/gumbirds-p1.p1" ] || { echo "[ERROR] no ROMs in $ROMDIR; run 'make' first" >&2; exit 1; }
command -v npx >/dev/null || { echo "[ERROR] node/npx required for neosdconv" >&2; exit 1; }
mkdir -p "$OUT"
# neosdconv pinned; name is read from the file by the core, keep it short ASCII.
# neosdconv reads every ROM file in its input dir; stage only this game's set so stale sets (old names) never double the .neo.
SET=$(mktemp -d); trap 'rm -rf "$SET"' EXIT
cp "$ROMDIR"/gumbirds-*.[pscmv]1 "$ROMDIR"/gumbirds-c2.c2 "$SET"/
npx --yes neosdconv@1.0.2 -i "$SET" -o "$OUT/gumbirds.neo" -n "Gumbirds" -g Other -y 2026 -m "Gumbirds"
ls -l "$OUT/gumbirds.neo"
echo "[OK] copy $OUT/gumbirds.neo to /media/fat/games/NeoGeo/ (no stray .xml files there)"

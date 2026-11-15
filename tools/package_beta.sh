#!/bin/sh
# Pack a beta archive for testers: MiSTer .neo plus MAME romset and hash file, with a README.
# Input : build/rom from `gmake` (run this from the tree that built it).
# Output: build/beta/bubblegum-brawl-beta-<date>-<sha>.zip
# No BIOS goes in the archive: testers supply their own neogeo.zip / MiSTer BIOS.
set -eu
cd "$(dirname "$0")/.."
ROMDIR=build/rom
for f in brawl.zip neogeo.xml; do
    [ -f "$ROMDIR/$f" ] || { echo "[ERROR] $ROMDIR/$f missing; run 'gmake' first" >&2; exit 1; }
done
sh tools/package_mister.sh >/dev/null
VER="$(date +%Y%m%d)-$(git rev-parse --short HEAD)"
git diff --quiet HEAD -- src tools assets || VER="$VER-dirty"
NAME="bubblegum-brawl-beta-$VER"
STAGE="build/beta/$NAME"
rm -rf "$STAGE"
mkdir -p "$STAGE/MiSTer/games/NeoGeo" "$STAGE/MAME/roms" "$STAGE/MAME/hash"
cp build/mister/bubblegum-brawl.neo "$STAGE/MiSTer/games/NeoGeo/"
cp "$ROMDIR/brawl.zip" "$STAGE/MAME/roms/"
# Only our cart in the hash file, so it never shadows the tester's own neogeo.xml.
cp "$ROMDIR/neogeo.xml" "$STAGE/MAME/hash/neogeo.xml"
sed "s/@VER@/$VER/" tools/beta_readme.txt > "$STAGE/README.txt"
(cd build/beta && rm -f "$NAME.zip" && zip -qr "$NAME.zip" "$NAME")
rm -rf "$STAGE"
ls -l "build/beta/$NAME.zip"

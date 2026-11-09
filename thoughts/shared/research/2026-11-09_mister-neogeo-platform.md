---
date: 2026-11-09
topic: MiSTer Neo Geo core - backup RAM persistence, homebrew loading, ngdevkit toolchain
tags: [neogeo, mister, ngdevkit, backup-ram, neosdconv]
status: draft
---

# MiSTer Neo Geo platform research

## 1. Backup RAM / memory card persistence

Answer: YES (from core source), with open details.

- Core README lists "Supports memory card saving"; AES mode: all saves go to memory card only; MVS mode: some games/UniBIOS store settings in battery-backed RAM, game data can still go to memory card. https://github.com/MiSTer-devel/NeoGeo_MiSTer (README, "Saving and Loading")
- The README does NOT mention file names, autosave or OSD save. Details below come from the core source, https://github.com/MiSTer-devel/NeoGeo_MiSTer/blob/master/neogeo.sv:
  - OSD entries: "Save Memory Card" (line ~145), "Reload Memory Card", and "Autosave,OFF,ON" (status[24]). Header comment line 96: "Save memory card & backup RAM".
  - One save image holds both: 64 KB backup RAM (sectors with lba[7]=0) + 8 KB memory card (lba[7]=1), 0x90 sectors, "regardless the selected system" (lines ~627, 1281-1285). So backup RAM is saved in MVS and AES mode alike.
  - Change tracking: `bk_change = sram_slot_we | CARD_WE`; comment says backup RAM writes carry "cab settings, dates, timer, high scores, saves, & bookkeeping" in MVS (line ~565). A pending flag lights the user LED.
  - Trigger: manual OSD Save (status[12]) writes only if pending; with Autosave ON, `bk_save = status[12] | (bk_autosave & OSD_STATUS)` - i.e. autosave fires when the OSD is OPENED, not on a timer. Autosave default is OFF. Power-off without opening OSD (autosave on) or pressing Save loses data. => Cabinet risk. 
  - Save is loaded automatically after ROM load ("always load backup so it will erase the memory if doesn't exist").
- File name/location: standard MiSTer framework save slot (VD 0), expected `/media/fat/saves/NEOGEO/<romname>.sav`. A forum post reports a per-game save in saves/NEOGEO working in AES and MVS: https://www.misterfpga.org/viewtopic.php?p=10410 (via search snippet only). UNVERIFIED: exact filename and folder (framework-derived, not in core source). 
- UNVERIFIED: whether current core versions or a newer MiSTer Main build adds a periodic/exit autosave; no source seen. Forum claim that memory card option is greyed in MVS mode: UNVERIFIED, forum snippet only.
- Dev notes (backup RAM at 0x000000-0xFFFF, card at 0x10000): https://git.eaw.app/mister-devel/NeoGeo_MiSTer/src/branch/master/DEV_NOTES.md (search snippet; mirror, not fetched).

## 2. Homebrew load formats

Answer: .neo (preferred) or romset folder + romsets.xml.

- Core accepts decrypted .neo sets, decrypted MAME sets with user XML, Darksoft sets with provided XML; ROMs live in `games/NeoGeo`; `romsets.xml` tells the core where sets are and how to load them. BIOS needed: 000-lo.lo, sfix.sfix, uni-bios.rom, sp-s2.sp1 (MVS) or neo-epo.sp1 (AES). https://github.com/MiSTer-devel/NeoGeo_MiSTer (README)
- Core OSD loads via "Load ROM set" (`FS1,*`), neogeo.sv line 122.
- Conversion tool: neosdconv (homebrew-oriented, NeoSD .neo). Usage: `npm install -g neosdconv`, then `neosdconv -i <dir with raw P,S,M,V,C ROM files> -o ./mygame.neo -n 'Name' -g <Genre> -y <year> -m <maker>`; leave NGH/screenshot unset for homebrew. https://github.com/city41/neosdconv (README text read from the fork https://github.com/InquisitiveCoder/neosdconv; the city41 URL returned 404 to the API but is the one linked by the core README). NodeJS 8.9.4 was the author's version.
- NeoBuilder: not mentioned in core README; UNVERIFIED.
- Forum caveats: stray XML files in the Neo Geo folder broke some homebrew .neo; renaming a .neo changes the displayed name (name is read from the file): https://www.misterfpga.org/viewtopic.php?p=68130 and https://mail.misterfpga.org/viewtopic.php?p=40659 (search snippets only).

## 3. ngdevkit on macOS

Answer: YES, via Homebrew; Z80 toolchain bundled; nullsound included in source.

- Commands: `brew tap dciabrin/ngdevkit`, `brew trust dciabrin/ngdevkit`, `brew install ngdevkit`; for examples also `brew install pkg-config autoconf automake rsync zip imagemagick sox ngdevkit-gngeo`; use brew python3 and gmake. https://github.com/dciabrin/ngdevkit (README) ; tap repo https://github.com/dciabrin/homebrew-ngdevkit
- Bottles for last two macOS versions on ARM only; Intel/older build from source.
- Z80: README lists "A C and ASM cross-compiler for the z80 (SDCC 4.4)"; the formula depends on `ngdevkit-toolchain` (GNU toolchain, newlib, SDCC, GDB). https://github.com/dciabrin/homebrew-ngdevkit/blob/master/Formula/ngdevkit.rb
- nullsound: a `nullsound` directory exists in the ngdevkit repo (Z80 sound driver sources: adpcm.s, fx-*.s ...), built with the devkit. https://github.com/dciabrin/ngdevkit/tree/master/nullsound . Not described in README; that it is installed by the brew package is UNVERIFIED (likely, same repo).
- Includes a backup-RAM example: https://github.com/dciabrin/ngdevkit-examples/tree/master/11-backup-ram and `18-memory-card`.

## 4. ngdevkit output -> MiSTer

Answer: UNCLEAR - plausible path, no documented confirmation.

- ngdevkit examples build a romset (MAME-style P/S/M/V/C files, zip) and run via `make gngeo`, `make gngeo-mvs`, `make mame`, `make mame-mvs`: https://github.com/dciabrin/ngdevkit-examples (README). Neither README mentions MiSTer or .neo.
- Plausible path: take the raw ROM files from the example's build, run neosdconv, put .neo in `games/NeoGeo`. neosdconv README says it should convert any homebrew ROM. No confirmed report of an ngdevkit-built .neo running on MiSTer found - UNVERIFIED. Test early on real hardware, including backup RAM write/power-cycle.

## Decision (2026-11-09, user)

Score persistence: set Autosave ON in the MiSTer Neo Geo core. Whoever shuts the cabinet down
first opens the OSD menu (MiSTer button), which triggers the save. No core fork.
Known risk: a forgotten OSD open loses that session's new scores.
Mitigation in the game: after a new top 10 entry, the name entry screen shows a short reminder
line to open the menu before power-off. A printed note on the cabinet does the same job.

Gumbirds - beta build @VER@
==================================

Neo Geo MVS cartridge game. Beta: please do not pass this archive on.
No BIOS is included. Use your own Neo Geo BIOS.

MiSTer (Neo Geo core)
---------------------
1. Copy MiSTer/games/NeoGeo/gumbirds.neo to /media/fat/games/NeoGeo/ on the SD card.
2. Start the NeoGeo core, open the OSD, load gumbirds.neo.
3. Set the system type to MVS (arcade) in the OSD.

MAME
----
1. Put your Neo Geo BIOS set (neogeo.zip) in MAME/roms/ or in your usual roms folder.
2. From the MAME folder of this archive, run:
     mame neogeo -hash hash -rp roms -cart1 gumbirds
   (Add your usual roms folder to -rp, separated by ';', if the BIOS lives there.)

Controls
--------
Insert a coin, then press Start. Button A flaps, stick left and right steers.

Reporting bugs
--------------
Please send: the build name above, MiSTer or MAME, the game mode, the stage,
and what you did just before the bug. A photo or a short video helps a lot.

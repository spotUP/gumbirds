#!/bin/sh
# Write config.mk (tool paths) from the Homebrew ngdevkit install. Replaces ngdevkit-examples' ./configure.
# Needs python with Pillow: brew install pillow; PYTHON overrides the default.
set -eu
P=$(brew --prefix)
PY=${PYTHON:-$P/bin/python3.14}
cat > "${1:-config.mk}" <<EOF
PKGCONFIG=$P/bin/pkg-config
PYTHON=$PY
ZIP=/usr/bin/zip
M68KAR=$P/bin/m68k-neogeo-elf-ar
M68KAS=$P/bin/m68k-neogeo-elf-as
M68KGCC=$P/bin/m68k-neogeo-elf-gcc
M68KGXX=$P/bin/m68k-neogeo-elf-g++
M68KLD=$P/bin/m68k-neogeo-elf-ld
M68KOBJCOPY=$P/bin/m68k-neogeo-elf-objcopy
M68KRANLIB=$P/bin/m68k-neogeo-elf-ranlib
Z80SDAR=$P/bin/z80-neogeo-ihx-sdar
Z80SDAS=$P/bin/z80-neogeo-ihx-sdasz80
Z80SDCC=$P/bin/z80-neogeo-ihx-sdcc
Z80SDLD=$P/bin/z80-neogeo-ihx-sdldz80
Z80SDOBJCOPY=$P/bin/z80-neogeo-ihx-sdobjcopy
Z80SDRANLIB=$P/bin/z80-neogeo-ihx-sdranlib
PALTOOL=$P/bin/paltool.py
TILETOOL=$P/bin/tiletool.py
ADPCMTOOL=$P/bin/adpcmtool.py
VROMTOOL=$P/bin/vromtool.py
FURTOOL=$P/bin/furtool.py
NSSTOOL=$P/bin/nsstool.py
SOUNDTOOL=$P/bin/soundtool.py
ROMTOOL=$P/bin/romtool.py
NGCFLAGS=\`\$(PKGCONFIG) --cflags ngdevkit\`
NGLDFLAGS=\`\$(PKGCONFIG) --libs ngdevkit\`
NGLIBDIR=\`\$(PKGCONFIG) --variable=libdir ngdevkit\`
NGZ80INCLUDEDIR=\`\$(PKGCONFIG) --variable=z80includedir ngdevkit\`
NGZ80LIBDIR=\`\$(PKGCONFIG) --variable=z80libdir ngdevkit\`
NGSHAREDIR=\$(shell \$(PKGCONFIG) --variable=sharedir ngdevkit)
AES_BIOS=\$(NGSHAREDIR)/aes.zip
MVS_BIOS=\$(NGSHAREDIR)/neogeo.zip
CONVERT=$P/bin/magick
SOX=
RSYNC=$P/bin/rsync
GNGEO=
GNGEO_DATA=
GNGEO_GLSL=
GNGEO_SHADER_PATH=
GLSL_SHADER_PATH=
SHADER_PATH=
SHADER=noop.glslp
ENABLE_MSYS2=
ENABLE_MINGW=no
GNGEO_INSTALL_PATH=
EOF

#!/bin/sh
# Fail the link when the work RAM left for the 68000 stack (from the end of .data/.bss up to the reset SP 0x10f300) is under MIN bytes.
# The merge of Tug Gum and Poop the Man with storm rain left 948 bytes; rain_step plus the vblank handler ran past it and overwrote .data.
# Usage: check_stack_room.sh <nm> <elf> <min bytes>
set -eu
end=$("$1" -n -S "$2" | awk '{ a = $1; s = (NF == 4) ? $2 : 0 }
  function h(x,  i, v) { v = 0; for (i = 1; i <= length(x); i++) v = v * 16 + index("0123456789abcdef", substr(x, i, 1)) - 1; return v }
  { v = h(a); if (v >= 1048576 && v < 1110784) { e = v + h(s); if (e > m) m = e } } END { print m }')
room=$((0x10f300 - end))
if [ "$room" -lt "$3" ]; then echo "[FAIL] $2: stack room $room bytes (RAM used up to $(printf %x "$end")), need $3"; exit 1; fi
echo "[OK] stack room $room bytes (need $3)"

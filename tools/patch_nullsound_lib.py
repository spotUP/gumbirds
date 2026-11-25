"""Copy nullsound.lib without its SSG module (the one defining state_ssg_pipeline), so the patched
tools/nullsound/nss-ssg.s replaces it, and with its stream module (the one defining nss_opcodes) replaced in
place by the patched tools/nullsound/stream.s object. The lib is concatenated .rel objects, each starting with
an XL3 line.
The stream module must keep its place: its DATA area ends with 70 bytes of padding that put the next module's
DATA (timer, then FM state at 0xf940) where the FM code's 8-bit address arithmetic expects it. Linked after the
lib instead, the FM state moved to 0xf85c and the FM channels went silent (gumbirds-title: 0 of 426 note starts).
usage: patch_nullsound_lib.py <in.lib> <out.lib> <stream.rel>"""
import sys
lines = open(sys.argv[1]).read().split("\n")
stream = open(sys.argv[3]).read().rstrip("\n").split("\n")
assert stream[0] == "XL3", "not a .rel object: %s" % sys.argv[3]
starts = [i for i, l in enumerate(lines) if l == "XL3"] + [len(lines)]
syms = lambda b: [l.split(" ")[1] for l in b if l.startswith("S ") and " Def" in l]
mods = [lines[a:z] for a, z in zip(starts, starts[1:])]
out = []
dropped = replaced = 0
for b in mods:
    if "state_ssg_pipeline" in syms(b):
        dropped += 1
    elif "nss_opcodes" in syms(b):
        out.append(stream)
        replaced += 1
    else:
        out.append(b)
assert (dropped, replaced) == (1, 1), "expected one SSG and one stream module, got %d and %d" % (dropped, replaced)
open(sys.argv[2], "w").write("\n".join(l for b in out for l in b))

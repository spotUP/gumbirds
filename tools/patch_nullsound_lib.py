"""Copy nullsound.lib without its SSG module (the one defining state_ssg_pipeline) and its stream module
(the one defining nss_opcodes), so the patched tools/nullsound/nss-ssg.s and tools/nullsound/stream.s replace them. The lib is concatenated .rel objects, each starting with an XL3 line.
usage: patch_nullsound_lib.py <in.lib> <out.lib>"""
import sys
lines = open(sys.argv[1]).read().split("\n")
starts = [i for i, l in enumerate(lines) if l == "XL3"] + [len(lines)]
DROP = ("state_ssg_pipeline", "nss_opcodes")
syms = lambda b: [l.split(" ")[1] for l in b if l.startswith("S ") and " Def" in l]
keep = [b for b in (lines[a:z] for a, z in zip(starts, starts[1:])) if not any(d in syms(b) for d in DROP)]
assert len(keep) == len(starts) - 1 - len(DROP), "expected one SSG and one stream module, dropped %d" % (len(starts) - 1 - len(keep))
open(sys.argv[2], "w").write("\n".join(l for b in keep for l in b))

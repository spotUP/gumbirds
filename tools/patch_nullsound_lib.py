"""Copy nullsound.lib without its SSG module (the one defining state_ssg_pipeline), so the patched
tools/nullsound/nss-ssg.s replaces it. The lib is concatenated .rel objects, each starting with an XL3 line.
usage: patch_nullsound_lib.py <in.lib> <out.lib>"""
import sys
lines = open(sys.argv[1]).read().split("\n")
starts = [i for i, l in enumerate(lines) if l == "XL3"] + [len(lines)]
keep = [b for b in (lines[a:z] for a, z in zip(starts, starts[1:])) if "S state_ssg_pipeline Def" not in " ".join(l[:26] + "|" for l in b if l.startswith("S "))]
assert len(keep) == len(starts) - 2, "expected exactly one SSG module, dropped %d" % (len(starts) - 1 - len(keep))
open(sys.argv[2], "w").write("\n".join(l for b in keep for l in b))

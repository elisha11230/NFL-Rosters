"""
Chips are not circles. A chip's ink runs from 28px above its centre (top of the
disc) down to about 75px below it (disc + name + "+N" depth count), and 68px wide
once the jersey and Top 100 badges overhang the disc.

This models each chip as that rectangle and reports any overlapping pair, at the
smallest field box the CSS allows. Run it after moving anything in FORMS.
"""
import re
import sys
import itertools

# Chip footprint in px, relative to the coordinate point.
HALF_W = 36          # 56px disc + ~8px badge overhang each side
UP = 28              # top of disc
DOWN = 75            # disc bottom + name + depth count

# Smallest box the field can be: min-height from CSS, and a narrow desktop split.
FIELD_W = 900
FIELD_H = 520


def load_forms(path):
    blk = open(path).read().split("const FORMS = {")[1].split("\n};")[0]
    forms = {}
    for m in re.finditer(r'"([^"]+)":\s*\{.*?coords:\s*\{(.*?)\}\s*\}', blk, re.S):
        pts = {int(a): (float(b), float(c))
               for a, b, c in re.findall(r"(\d+):\s*\[([\d.]+),\s*([\d.]+)\]", m.group(2))}
        forms[m.group(1)] = pts
    return forms


def box(x, y):
    cx, cy = x / 100 * FIELD_W, y / 100 * FIELD_H
    return (cx - HALF_W, cy - UP, cx + HALF_W, cy + DOWN)


def overlap(a, b):
    ox = min(a[2], b[2]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[1], b[1])
    return (ox, oy) if ox > 0 and oy > 0 else None


bad = 0
for name, pts in load_forms(sys.argv[1] if len(sys.argv) > 1 else "app_template.html").items():
    hits = []
    for (s1, p1), (s2, p2) in itertools.combinations(pts.items(), 2):
        ov = overlap(box(*p1), box(*p2))
        if ov:
            hits.append((s1, s2, ov))
    # also flag anything whose labels run off the bottom of the field
    off = [s for s, (x, y) in pts.items() if box(x, y)[3] > FIELD_H]
    status = "OK" if not hits and not off else "COLLIDE"
    print(f"{status:<8} {name}")
    for s1, s2, (ox, oy) in hits:
        print(f"           slots {s1} & {s2} overlap {ox:.0f}x{oy:.0f}px")
    for s in off:
        print(f"           slot {s} label runs {box(*pts[s])[3]-FIELD_H:.0f}px past the bottom")
    bad += len(hits) + len(off)

print("\nclean" if not bad else f"\n{bad} problem(s)")
sys.exit(1 if bad else 0)

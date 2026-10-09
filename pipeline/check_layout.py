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


def load_forms(path, const="FORMS"):
    src = open(path).read()
    if ("const " + const + " = {") not in src:
        return {}
    blk = src.split("const " + const + " = {")[1].split("\n};")[0]
    forms = {}
    for m in re.finditer(r'"([^"]+)":\s*\{.*?coords:\s*\{(.*?)\}\s*\}', blk, re.S):
        pts = {int(a): (float(b), float(c))
               for a, b, c in re.findall(r"(\d+):\s*\[([\d.]+),\s*([\d.]+)\]", m.group(2))}
        forms[m.group(1)] = pts
    return forms


# Phones get their own layout where they need one (FORMS_NARROW), and compact
# chips: 46px wide, about 66px tall, 78px on game days with a live stat line.
# Tested at 360px wide, a smaller phone than most, and the shortest height the
# CSS allows there (clamp(440px, 125vw, ...) gives 450px at 360px).
# Half width 23: names are capped at 12.4% of the screen on phones (44px at
# 360px) and the movement tag hangs only 3px off the disc. The layouts are also
# checked chip by chip in a real browser across all 32 teams.
NARROW = dict(W=360, H=450, HALF_W=23, UP=39, DOWN=39)
WIDE = dict(W=FIELD_W, H=FIELD_H, HALF_W=HALF_W, UP=UP, DOWN=DOWN)


def box(x, y, m=None):
    m = m or WIDE
    cx, cy = x / 100 * m["W"], y / 100 * m["H"]
    return (cx - m["HALF_W"], cy - m["UP"], cx + m["HALF_W"], cy + m["DOWN"])


def overlap(a, b):
    ox = min(a[2], b[2]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[1], b[1])
    return (ox, oy) if ox > 0 and oy > 0 else None


bad = 0
path = sys.argv[1] if len(sys.argv) > 1 else "app_template.html"
wide = load_forms(path)
narrow_over = load_forms(path, "FORMS_NARROW")
for mode, m in (("desktop", WIDE), ("phone", NARROW)):
    print(f"-- {mode} ({m['W']}x{m['H']}px)")
    for name, base in wide.items():
        pts = narrow_over.get(name, base) if mode == "phone" else base
        hits = []
        for (s1, p1), (s2, p2) in itertools.combinations(pts.items(), 2):
            ov = overlap(box(*p1, m), box(*p2, m))
            if ov:
                hits.append((s1, s2, ov))
        # anything whose labels run off the field, top or bottom, or off a side
        off = [s for s, (x, y) in pts.items()
               if box(x, y, m)[3] > m["H"] or box(x, y, m)[1] < 0
               or box(x, y, m)[0] < -6 or box(x, y, m)[2] > m["W"] + 6]
        status = "OK" if not hits and not off else "COLLIDE"
        print(f"{status:<8} {name}")
        for s1, s2, (ox, oy) in hits:
            print(f"           slots {s1} & {s2} overlap {ox:.0f}x{oy:.0f}px")
        for s in off:
            print(f"           slot {s} runs off the field")
        bad += len(hits) + len(off)

print("\nclean" if not bad else f"\n{bad} problem(s)")
sys.exit(1 if bad else 0)

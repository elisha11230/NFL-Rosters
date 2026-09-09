"""
Generates the app icon at every size the browser and Android ask for.

The mark is the app in miniature: a dark field, one dashed line of scrimmage,
a bright chip sitting on it (the starter) and a dimmer chip behind and below
(the backup). That is literally what the app shows, and it stays legible when
Android renders it at 48px on a home screen.

Outputs base64 PNGs ready to paste into the HTML head as data URIs.
"""
import base64
import io
from PIL import Image, ImageDraw

FIELD = (22, 36, 31)        # --field
INK = (14, 20, 23)          # --ink
CHALK = (221, 230, 225)
BRASS = (201, 162, 39)      # Top 100 gold
TEAL = (74, 124, 111)

S = 1024                    # render big, downsample for clean edges


def render():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # rounded field
    r = int(S * 0.22)
    d.rounded_rectangle([0, 0, S, S], radius=r, fill=FIELD)

    # two yard lines only. Hash marks and a four-line grid turn to noise once
    # Android renders this at 48px, so they are deliberately left out.
    for frac in (0.24, 0.76):
        y = int(S * frac)
        d.line([(int(S * .12), y), (int(S * .88), y)],
               fill=CHALK + (30,), width=int(S * .014))

    # line of scrimmage, dashed
    y = int(S * 0.52)
    dash, gap, x = int(S * .06), int(S * .042), int(S * .09)
    while x < S * .91:
        d.line([(x, y), (min(x + dash, int(S * .91)), y)],
               fill=TEAL + (210,), width=int(S * .020))
        x += dash + gap

    # Two chips stacked with a clear overlap. The stack is what reads as "depth"
    # at small sizes -- far better than two separate circles, which merge.
    back = (int(S * .38), int(S * .60), int(S * .19))
    front = (int(S * .60), int(S * .44), int(S * .245))

    bx, by, br = back
    d.ellipse([bx - br, by - br, bx + br, by + br], fill=INK)
    d.ellipse([bx - br, by - br, bx + br, by + br],
              outline=TEAL + (255,), width=int(S * .026))

    # knock the field colour out behind the front chip so the overlap is crisp
    cx, cy, cr = front
    pad = int(S * .030)
    d.ellipse([cx - cr - pad, cy - cr - pad, cx + cr + pad, cy + cr + pad],
              fill=FIELD)
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=INK)
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr],
              outline=CHALK + (255,), width=int(S * .036))

    # brass dot, the Top 100 marker
    gr = int(S * .075)
    gx, gy = cx + int(cr * .70), cy - int(cr * .70)
    d.ellipse([gx - gr - int(S * .012), gy - gr - int(S * .012),
               gx + gr + int(S * .012), gy + gr + int(S * .012)], fill=FIELD)
    d.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=BRASS)
    return img


def b64(img, size):
    out = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), len(buf.getvalue())


def maskable(base):
    """Android crops home screen icons to whatever shape the launcher uses
    (circle, squircle, teardrop). A maskable icon must therefore bleed to the
    edges and keep everything important inside the middle ~80%."""
    m = Image.new("RGBA", (S, S), FIELD + (255,))
    inner = int(S * 0.78)
    shrunk = base.resize((inner, inner), Image.LANCZOS)
    off = (S - inner) // 2
    m.paste(shrunk, (off, off), shrunk)
    return m


def svg_favicon():
    """A tiny hand-written SVG for the browser tab. Vector stays crisp at 16px
    and costs a fraction of what a PNG data URI would."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#16241F"/>'
        '<g stroke="#4A7C6F" stroke-width="1.6" stroke-linecap="round" opacity=".9">'
        '<path d="M6 33h5M15 33h5M24 33h5M33 33h5M42 33h5M51 33h4"/></g>'
        '<circle cx="24" cy="39" r="10.5" fill="#0E1417" stroke="#4A7C6F" stroke-width="3"/>'
        '<circle cx="39" cy="28" r="15.5" fill="#16241F"/>'
        '<circle cx="39" cy="28" r="13" fill="#0E1417" stroke="#DDE6E1" stroke-width="4"/>'
        '<circle cx="48" cy="19" r="6" fill="#16241F"/>'
        '<circle cx="48" cy="19" r="4.4" fill="#C9A227"/></svg>'
    )


if __name__ == "__main__":
    base = render()
    base.save("icon-preview-512.png")
    base.resize((96, 96), Image.LANCZOS).save("icon-preview-96.png")
    base.resize((48, 48), Image.LANCZOS).save("icon-preview-48.png")
    mask = maskable(base)
    mask.resize((192, 192), Image.LANCZOS).save("icon-preview-maskable.png")

    out = {}
    for label, img, sizes in (("any", base, (192, 512)),
                              ("maskable", mask, (192, 512))):
        for s in sizes:
            enc, nbytes = b64(img, s)
            out[f"{label}-{s}"] = enc
            print(f"{label:<9}{s}x{s}: {nbytes/1024:.1f} KB")

    with open("icons_b64.txt", "w") as f:
        for k, v in out.items():
            f.write(f"### {k}\n{v}\n")
    with open("favicon.svg", "w") as f:
        f.write(svg_favicon())
    print("wrote icons_b64.txt and favicon.svg")

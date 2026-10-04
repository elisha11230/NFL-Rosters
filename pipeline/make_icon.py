"""
Generates the app icon at every size the browser and Android ask for.

A football: brown leather, white laces, tilted the way a ball is usually drawn,
on the app's dark green. Leather is shaded with a soft highlight so it reads as
a solid ball rather than a flat brown lens, and the laces are thick enough to
survive Android rendering the icon at 48px on a home screen.

Outputs base64 PNGs ready to paste into the HTML head as data URIs.
"""
import base64
import io
import math
from PIL import Image, ImageDraw, ImageFilter, ImageChops

FIELD = (22, 36, 31)        # --field, the background
LEATHER = (139, 74, 33)
LEATHER_HI = (184, 108, 52)
LEATHER_LO = (82, 38, 14)
LACE = (246, 242, 234)

S = 1024                    # render big, downsample for clean edges


def ball_mask(L, H, q=1.0):
    """The football's outline: a parabola either side of the long axis,
    y = H(1 - u^2)^q. Fuller in the middle than two circular arcs, with
    pointed ends (the arcs met at a blunt 125 degrees and looked squared off
    once tilted). The points are softened afterwards so they are not needles."""
    top, bot = [], []
    for i in range(601):
        u = -1 + 2 * i / 600
        y = H * max(0.0, 1 - u * u) ** q
        top.append((u * L, -y)); bot.append((u * L, y))
    return top + bot[::-1]


def football(size):
    """The ball on its own transparent layer, lying flat, before it is tilted."""
    W = size
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    L, H = W * 0.43, W * 0.245
    cx, cy = W / 2, W / 2
    outline = [(cx + x, cy + y) for x, y in ball_mask(L, H)]

    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).polygon(outline, fill=255)
    # soften the two points slightly: blur, then re-threshold
    mask = mask.filter(ImageFilter.GaussianBlur(W * 0.012)).point(lambda v: 255 if v > 140 else (v * 2 if v > 70 else 0))

    # Leather: a highlight up and to the left, darkening to the edges.
    shade = Image.new("RGBA", (W, W), LEATHER + (255,))
    g = Image.new("L", (W, W), 0)
    gd = ImageDraw.Draw(g)
    hx, hy = cx - L * 0.28, cy - H * 0.42
    for r in range(int(L * 1.25), 0, -6):
        v = int(255 * (1 - r / (L * 1.25)) ** 1.6)
        gd.ellipse([hx - r, hy - r * 0.7, hx + r, hy + r * 0.7], fill=v)
    hi = Image.new("RGBA", (W, W), LEATHER_HI + (255,))
    shade = Image.composite(hi, shade, g)
    # a darker rim, from a blurred inset of the outline
    inner = mask.filter(ImageFilter.GaussianBlur(W * 0.035))
    rim = ImageChops.invert(inner)
    lo = Image.new("RGBA", (W, W), LEATHER_LO + (255,))
    shade = Image.composite(lo, shade, rim.point(lambda v: int(v * 0.85)))
    img.paste(shade, (0, 0), mask)

    d = ImageDraw.Draw(img)
    # seam from tip to tip along the middle, under the laces
    d.line([(cx - L * 0.86, cy), (cx + L * 0.86, cy)], fill=LEATHER_LO + (200,), width=int(W * 0.012))
    # laces: a spine and eight stitches across it
    lw = int(W * 0.026)
    d.line([(cx - L * 0.36, cy), (cx + L * 0.36, cy)], fill=LACE + (255,), width=lw)
    n = 8
    for i in range(n):
        x = cx - L * 0.32 + (L * 0.64) * i / (n - 1)
        d.rounded_rectangle([x - lw * 0.5, cy - H * 0.30, x + lw * 0.5, cy + H * 0.30],
                            radius=lw // 2, fill=LACE + (255,))
    return img


def render():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, S, S], radius=int(S * 0.22), fill=FIELD)
    ball = football(S).rotate(30, resample=Image.BICUBIC, center=(S / 2, S / 2))
    # a soft shadow under it
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh.paste((0, 0, 0, 110), (0, 0), ball.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(S * 0.02))
    img.alpha_composite(sh, (int(S * 0.012), int(S * 0.03)))
    img.alpha_composite(ball)
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
    """A tiny hand-written SVG football for the browser tab. Vector stays crisp
    at 16px and costs a fraction of what a PNG data URI would."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#16241F"/>'
        '<g transform="rotate(-30 32 32)">'
        # a quadratic curve is a parabola: the same outline as the big icon
        '<path d="M5 32Q32 3 59 32Q32 61 5 32Z" fill="#8B4A21" stroke="#52260E" stroke-width="1.4" stroke-linejoin="round"/>'
        '<path d="M22 32H42" stroke="#F6F2EA" stroke-width="2.6" stroke-linecap="round"/>'
        '<path d="M23.5 28.5v7M27.7 28.5v7M32 28.5v7M36.3 28.5v7M40.5 28.5v7" '
        'stroke="#F6F2EA" stroke-width="2.2" stroke-linecap="round"/></g></svg>'
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

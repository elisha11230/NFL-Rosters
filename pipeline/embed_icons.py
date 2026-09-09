"""
Injects the favicon, home screen icon and web app manifest into the template's
<!--ICONS--> slot, all as data URIs so the app stays a single portable file.

Run make_icon.py first; this reads icons_b64.txt and favicon.svg.
"""
import base64
import json
import urllib.parse


def load_icons(path="icons_b64.txt"):
    out, key = {}, None
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("### "):
            key = line[4:]
        elif key and line:
            out[key] = line
            key = None
    return out


def build_head():
    ic = load_icons()
    svg = open("favicon.svg").read()

    # SVG stays as a percent-encoded data URI. Vector is crisp at 16px and far
    # smaller than a PNG would be at the same fidelity.
    svg_uri = "data:image/svg+xml," + urllib.parse.quote(svg, safe="")

    png192 = "data:image/png;base64," + ic["any-192"]
    mask512 = "data:image/png;base64," + ic["maskable-512"]

    manifest = {
        "name": "NFL Depth Charts",
        "short_name": "Depth Chart",
        "description": "Every NFL roster laid out in formation.",
        "start_url": ".",
        "scope": ".",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#0E1417",
        "theme_color": "#0E1417",
        "icons": [
            {"src": png192, "sizes": "192x192", "type": "image/png",
             "purpose": "any"},
            {"src": mask512, "sizes": "512x512", "type": "image/png",
             "purpose": "maskable"},
        ],
    }
    man_uri = ("data:application/manifest+json;base64,"
               + base64.b64encode(json.dumps(manifest,
                                             separators=(",", ":")).encode()).decode())

    return (
        f'<link rel="icon" href="{svg_uri}">\n'
        f'<link rel="apple-touch-icon" sizes="192x192" href="{png192}">\n'
        f'<link rel="manifest" href="{man_uri}">'
    )


if __name__ == "__main__":
    head = build_head()
    tpl = open("app_template.html").read()
    assert "<!--ICONS-->" in tpl, "template is missing the <!--ICONS--> slot"
    open("app_template.html", "w").write(tpl.replace("<!--ICONS-->", head))
    print(f"injected {len(head)/1024:.0f} KB of icon data into the head")

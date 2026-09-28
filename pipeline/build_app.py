"""
Final assembly. Injects the icons and the data payload into the template and
writes the single distributable HTML file.

    python3 make_icon.py     # regenerate icon art (only if you change it)
    python3 build_data.py    # regenerate nfl_data.json
    python3 build_app.py     # produce nfl-depth-chart.html

The template is never modified, so it stays readable and editable.
"""
import os

from embed_icons import build_head

# site_config.py is yours and is deliberately NOT shipped with the pipeline, so
# that handing over a new copy of these files cannot overwrite your settings.
# Absent, everything falls back to relative links, which is a working default.
try:
    import site_config
except ImportError:
    site_config = None
    print("note: no site_config.py found, using defaults")


def setting(name, default=""):
    """Read one setting, tolerating an older site_config.py that predates it.

    The page config used to be produced by a function inside site_config.py
    itself, which meant a new setting needed a new copy of your file. Reading
    each value here instead means a new setting is one added line, and a file
    without that line still builds."""
    return getattr(site_config, name, default) if site_config else default


def config_js():
    import json
    return json.dumps({
        "streamBase": str(setting("STREAM_BASE")).rstrip("/"),
        "embedBase": str(setting("EMBED_BASE")).rstrip("/"),
        "proxy": setting("PROXY"),
        "youtubeKey": str(setting("YOUTUBE_API_KEY")).strip(),
    }, indent=2)

TPL = "app_template.html"
DATA = "nfl_data.json"
OUT = "index.html"          # the name GitHub Pages serves by default

tpl = open(TPL).read()
assert "<!--ICONS-->" in tpl, "template lost its <!--ICONS--> slot"
assert "/*__DATA__*/" in tpl, "template lost its /*__DATA__*/ slot"
assert "/*__CONFIG__*/" in tpl, "template lost its /*__CONFIG__*/ slot"

html = tpl.replace("<!--ICONS-->", build_head())
html = html.replace("/*__DATA__*/", open(DATA).read())
# Settings come from site_config.py, which is never overwritten by a template
# update. Before this they lived in the template and were lost on every change.
html = html.replace("/*__CONFIG__*/", config_js())
open(OUT, "w").write(html)

kb = os.path.getsize(OUT) / 1024
print(f"wrote {OUT}  ({kb/1024:.2f} MB)")
for label, val in (("stream", setting("STREAM_BASE")),
                   ("embed", setting("EMBED_BASE")),
                   ("proxy", setting("PROXY")),
                   ("youtube", "set" if setting("YOUTUBE_API_KEY") else "")):
    print(f"  {label:<8}{val or '(relative / unset)'}")

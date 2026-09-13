"""
Final assembly. Injects the icons and the data payload into the template and
writes the single distributable HTML file.

    python3 make_icon.py     # regenerate icon art (only if you change it)
    python3 build_data.py    # regenerate nfl_data.json
    python3 build_app.py     # produce nfl-depth-chart.html

The template is never modified, so it stays readable and editable.
"""
import os

import site_config
from embed_icons import build_head

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
html = html.replace("/*__CONFIG__*/", site_config.as_js())
open(OUT, "w").write(html)

kb = os.path.getsize(OUT) / 1024
print(f"wrote {OUT}  ({kb/1024:.2f} MB)")
for label, val in (("stream", site_config.STREAM_BASE),
                   ("embed", site_config.EMBED_BASE),
                   ("proxy", site_config.PROXY)):
    print(f"  {label:<7}{val or '(relative / unset)'}")

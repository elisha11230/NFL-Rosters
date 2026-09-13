"""
Your settings. This file is yours -- nothing in the pipeline overwrites it, and
neither do I when handing over a new app_template.html.

That was the whole reason for splitting it out. These values used to live at the
top of the template, so every time the app's code changed the settings went with
it and had to be typed again. Code and configuration belong in different files.

Edit, commit, done: the push rebuilds the site and the values are baked in.
"""

# Where the "Stream" button on a scorecard points.
#   "" leaves links relative:  /live/nfl/2026-09-13/tb-cin
#   a host makes them absolute: https://example.com/live/nfl/2026-09-13/tb-cin
# No trailing slash.
STREAM_BASE = ""

# Where the embedded player on a live game loads from. Separate from the above
# because the page and the player are often not on the same host.
#   /embed/nfl/2026-09-13/nyj-ten
EMBED_BASE = ""

# Optional. A Cloudflare Worker (or similar) that fetches an ESPN URL and returns
# it with CORS headers. Only needed if direct browser access to ESPN is ever
# blocked; leave empty to call ESPN directly, which currently works.
PROXY = ""


def as_js():
    """Emitted into the page as one object, so the template reads settings from a
    single place rather than having values scattered through it."""
    import json
    return json.dumps({
        "streamBase": STREAM_BASE.rstrip("/"),
        "embedBase": EMBED_BASE.rstrip("/"),
        "proxy": PROXY,
    }, indent=2)

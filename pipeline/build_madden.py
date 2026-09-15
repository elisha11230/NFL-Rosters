"""
Madden player ratings: an overall number per player, ranked within position, and
how it moved since last week.

Why this and not an analytics grade: EA rates every player on every roster,
including the linemen and backups that statistics never reach, and refreshes
weekly through the season. It is a game designer's assessment rather than a
measurement of play, and the app labels it that way -- but as a per-position
ranking with breadth, nothing else free comes close.

Two things worth knowing about how this is built:

  * The endpoint is tried, not assumed. I could not reach EA from where this was
    written, so several known URL shapes are attempted and the response is parsed
    by looking for plausible field names rather than trusting one layout. If none
    of it works the module returns nothing and the build carries on.

  * Movement needs memory. EA publishes the current ratings and no history, so
    each run records what it saw in madden_history.json, which the workflow
    commits. Week-on-week movement is this week against the last week stored.
"""
import json
import os
import re
import unicodedata
import urllib.request

SEASON = 2026
HISTORY = "madden_history.json"
PAGE = 200
MAX_PAGES = 20

# Tried in order. EA has moved this more than once, so do not rely on one.
ENDPOINTS = [
    "https://ratings-api.ea.com/v2/entity/madden-player-ratings?limit={limit}&offset={offset}",
    "https://ratings-api.ea.com/v2/entity/madden-nfl-26-player-ratings?limit={limit}&offset={offset}",
    "https://drop-api.ea.com/rating/madden-nfl?limit={limit}&offset={offset}&locale=en",
]

# Field names seen across versions of the payload, most specific first.
NAME_KEYS = ["fullNameForSearch", "fullName", "name", "playerName"]
FIRST_KEYS = ["firstName", "first_name"]
LAST_KEYS = ["lastName", "last_name"]
OVR_KEYS = ["overall_rating", "overallRating", "overall", "ovr", "rating"]
POS_KEYS = ["position", "pos", "primaryPosition"]
TEAM_KEYS = ["teamName", "team", "team_name", "club"]

# The handful of attributes worth surfacing, by the names they go under.
ATTRS = [
    ("speed", ["speed", "spd"], "Speed"),
    ("acceleration", ["acceleration", "acc"], "Acceleration"),
    ("awareness", ["awareness", "awr"], "Awareness"),
    ("strength", ["strength", "str"], "Strength"),
    ("agility", ["agility", "agi"], "Agility"),
    ("catching", ["catching", "cth"], "Catching"),
    ("throwPower", ["throwPower", "throw_power", "thp"], "Throw power"),
    ("throwAccuracyShort", ["throwAccuracyShort", "tas"], "Short accuracy"),
    ("manCoverage", ["manCoverage", "man_coverage", "mcv"], "Man coverage"),
    ("zoneCoverage", ["zoneCoverage", "zone_coverage", "zcv"], "Zone coverage"),
    ("passBlock", ["passBlock", "pass_block", "pbk"], "Pass block"),
    ("runBlock", ["runBlock", "run_block", "rbk"], "Run block"),
    ("powerMoves", ["powerMoves", "power_moves", "pmv"], "Power moves"),
    ("finesseMoves", ["finesseMoves", "finesse_moves", "fmv"], "Finesse moves"),
    ("tackle", ["tackle", "tak"], "Tackle"),
    ("playRecognition", ["playRecognition", "play_recognition", "prc"], "Play recognition"),
]


def _pick(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    # Payloads sometimes nest the value under {"value": n}.
    for k in keys:
        v = d.get(k)
        if isinstance(v, dict) and "value" in v:
            return v["value"]
    return None


def norm(n):
    if not n:
        return ""
    n = unicodedata.normalize("NFKD", str(n)).encode("ascii", "ignore").decode()
    n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", n.lower())
    return re.sub(r"[^a-z]", "", n)


def _get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; depth-chart-app)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _rows(payload):
    """Find the list of players wherever this version of the payload keeps it."""
    if isinstance(payload, list):
        return payload
    for key in ("docs", "items", "data", "results", "players", "entries"):
        v = payload.get(key)
        if isinstance(v, list) and v:
            return v
    # Last resort: the longest list of dicts anywhere in the object.
    best = []
    for v in payload.values():
        if isinstance(v, list) and len(v) > len(best) and v and isinstance(v[0], dict):
            best = v
    return best


def fetch_all():
    for tpl in ENDPOINTS:
        rows, offset = [], 0
        try:
            for _ in range(MAX_PAGES):
                page = _rows(_get(tpl.format(limit=PAGE, offset=offset)))
                if not page:
                    break
                rows.extend(page)
                if len(page) < PAGE:
                    break
                offset += PAGE
        except Exception:
            continue
        # A real response has hundreds of players with an overall rating.
        if len(rows) > 200 and any(_pick(r, OVR_KEYS) for r in rows[:20]):
            return rows
    return None


def build(players, team_names):
    """players: {pid: {name, pos, team}}; team_names: {full club name: abbr}"""
    rows = fetch_all()
    if not rows:
        return {}, {"live": False, "season": SEASON,
                    "note": "Madden ratings not reachable"}

    by_name = {}
    for pid, p in players.items():
        by_name.setdefault(norm(p["name"]), []).append(pid)

    found = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        ovr = _pick(r, OVR_KEYS)
        if ovr is None:
            continue
        name = _pick(r, NAME_KEYS)
        if not name:
            first, last = _pick(r, FIRST_KEYS), _pick(r, LAST_KEYS)
            name = f"{first} {last}" if first and last else None
        if not name:
            continue
        cands = by_name.get(norm(name))
        if not cands:
            continue
        pid = cands[0]
        if len(cands) > 1:
            # Shared name: prefer the club that matches.
            club = _pick(r, TEAM_KEYS)
            ab = team_names.get(str(club).strip()) if club else None
            match = [c for c in cands if players[c].get("team") == ab]
            if match:
                pid = match[0]
            elif ab:
                continue          # a name collision we cannot resolve; skip it
        attrs = []
        for _key, names, label in ATTRS:
            v = _pick(r, names)
            if isinstance(v, (int, float)) and v:
                attrs.append({"l": label, "v": int(v)})
        found[pid] = {"ovr": int(ovr), "attrs": attrs[:8]}

    if not found:
        return {}, {"live": False, "season": SEASON,
                    "note": "Madden ratings fetched but matched nobody"}

    # Rank within position, which is the only ranking that means anything here:
    # a 78 guard and a 78 receiver are not the same statement.
    bypos = {}
    for pid, v in found.items():
        bypos.setdefault(players[pid]["pos"], []).append(pid)
    for pos, ids in bypos.items():
        ids.sort(key=lambda p: -found[p]["ovr"])
        n = len(ids)
        rank = 0
        last = None
        for i, p in enumerate(ids, 1):
            # Standard competition ranking, so ties share a place.
            if found[p]["ovr"] != last:
                rank = i
                last = found[p]["ovr"]
            found[p]["rank"] = rank
            found[p]["n"] = n
            found[p]["pos"] = pos

    # ---- movement, against the last run we recorded
    hist = {}
    if os.path.exists(HISTORY):
        try:
            hist = json.load(open(HISTORY))
        except Exception:
            hist = {}
    snapshots = hist.get("snapshots", [])
    prev = snapshots[-1] if snapshots else None

    moved = 0
    for pid, v in found.items():
        was = (prev or {}).get("data", {}).get(pid)
        if was:
            if was.get("ovr") != v["ovr"]:
                v["dovr"] = v["ovr"] - was["ovr"]
            if was.get("rank") and v.get("rank"):
                # Rank numbers fall as a player climbs.
                d = was["rank"] - v["rank"]
                if d:
                    v["drank"] = d
            if v.get("dovr") or v.get("drank"):
                moved += 1

    # Record this run, keeping a short tail rather than the whole season.
    stamp = {"at": __import__("datetime").date.today().isoformat(),
             "data": {p: {"ovr": v["ovr"], "rank": v.get("rank")}
                      for p, v in found.items()}}
    if not prev or prev["data"] != stamp["data"]:
        snapshots.append(stamp)
    hist["snapshots"] = snapshots[-6:]
    try:
        with open(HISTORY, "w") as f:
            json.dump(hist, f, separators=(",", ":"))
    except Exception:
        pass

    return found, {
        "live": True, "season": SEASON,
        "players": len(found),
        "positions": len(bypos),
        "moved": moved,
        "hasMovement": bool(prev),
        "since": (prev or {}).get("at"),
    }

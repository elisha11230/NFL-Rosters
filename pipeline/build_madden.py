"""
Madden player ratings: an overall number per player, ranked within position, and
how it moved since last week.

Why this and not an analytics grade: EA rates every player on every roster,
including the linemen and backups that statistics never reach, and refreshes
weekly through the season. It is a game designer's assessment rather than a
measurement of play, and the app labels it that way -- but as a per-position
ranking with breadth, nothing else free comes close.

Two things worth knowing about how this is built:

  * There is no EA ratings API. An independent audit of EA's hosts in September
    2026 found no public contract anywhere -- the endpoints this module first
    tried were guesses and all of them were wrong. Projects that have this data
    scrape EA's website through its build id, which is fragile and a terms
    question, so this does not.

    It reads a committed CSV in a public repository instead. That is a real
    dependency on somebody else's housekeeping, which is worth saying plainly,
    but it is a stable URL rather than a scrape.

  * Movement needs memory. The source carries current ratings and no history, so
    each run records what it saw in madden_history.json, which the workflow
    commits. Movement is this run against the last one stored -- which means it
    only appears when the upstream file actually changes. At the time of writing
    it holds launch ratings, so movement will stay empty until it is refreshed.
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

SOURCES = [
    "https://raw.githubusercontent.com/zachxwalton/madden-ratings-breakdown/"
    "main/scraper/output/madden27_ratings.csv",
    "https://raw.githubusercontent.com/zachxwalton/madden-ratings-breakdown/"
    "master/scraper/output/madden27_ratings.csv",
]

# Madden uses its own position names. Mapped onto the ones the rest of the app
# uses so that "4th of 75" counts the right pool -- an edge rusher listed as REDG
# should be ranked against LEDG too, not against a separate pool of one side.
POS_MAP = {
    "HB": "RB", "FB": "FB", "QB": "QB", "WR": "WR", "TE": "TE",
    "LT": "T", "RT": "T", "LG": "G", "RG": "G", "C": "C",
    "LEDG": "EDGE", "REDG": "EDGE", "DT": "DT",
    "MIKE": "LB", "SAM": "LB", "WILL": "LB",
    "CB": "CB", "FS": "S", "SS": "S", "K": "K", "P": "P", "LS": "LS",
}

# Field names seen across versions of the payload, most specific first.
# Attribute columns worth surfacing, by the position they matter for.
ATTR_ALL = [("speed_rating", "Speed"), ("accel_rating", "Acceleration"),
            ("agility_rating", "Agility"), ("strength_rating", "Strength"),
            ("awareness_rating", "Awareness")]
ATTR_BY_POS = {
    "QB": [("throw_power_ratin", "Throw power"), ("throw_acc_deep_ra", "Deep accuracy"),
           ("throw_under_press", "Under pressure"), ("play_action_ratin", "Play action")],
    "RB": [("break_tackle_rati", "Break tackle"), ("carry_rating", "Carrying"),
           ("juke_move_rating", "Juke"), ("bcv_rating", "Vision")],
    "WR": [("catch_rating", "Catching"), ("route_run_deep_ra", "Deep routes"),
           ("route_run_short_r", "Short routes"), ("release_rating", "Release")],
    "TE": [("catch_rating", "Catching"), ("run_block_rating", "Run block"),
           ("route_run_med_rat", "Routes"), ("cit_rating", "Catch in traffic")],
    "T": [("pass_block_rating", "Pass block"), ("run_block_rating", "Run block"),
          ("pass_block_power_", "Anchor")],
    "G": [("run_block_rating", "Run block"), ("pass_block_rating", "Pass block"),
          ("impact_block_rati", "Impact block")],
    "C": [("run_block_rating", "Run block"), ("pass_block_rating", "Pass block"),
          ("awareness_rating", "Awareness")],
    "EDGE": [("power_moves_ratin", "Power moves"), ("finesse_moves_rat", "Finesse moves"),
             ("block_shed_rating", "Block shedding"), ("pursuit_rating", "Pursuit")],
    "DT": [("power_moves_ratin", "Power moves"), ("block_shed_rating", "Block shedding"),
           ("tackle_rating", "Tackle")],
    "LB": [("tackle_rating", "Tackle"), ("play_rec_rating", "Play recognition"),
           ("zone_cover_rating", "Zone coverage"), ("pursuit_rating", "Pursuit")],
    "CB": [("man_cover_rating", "Man coverage"), ("zone_cover_rating", "Zone coverage"),
           ("press_rating", "Press"), ("play_rec_rating", "Play recognition")],
    "S": [("zone_cover_rating", "Zone coverage"), ("play_rec_rating", "Play recognition"),
          ("tackle_rating", "Tackle"), ("hit_power_rating", "Hit power")],
    "K": [("kick_power_rating", "Kick power"), ("kick_acc_rating", "Kick accuracy")],
    "P": [("kick_power_rating", "Punt power"), ("kick_acc_rating", "Punt accuracy")],
}


def norm(n):
    if not n:
        return ""
    n = unicodedata.normalize("NFKD", str(n)).encode("ascii", "ignore").decode()
    n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", n.lower())
    return re.sub(r"[^a-z]", "", n)


def fetch_all():
    import io
    import pandas as pd
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "depth-chart-app"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            if len(raw) < 50_000:
                continue
            return pd.read_csv(io.BytesIO(raw), low_memory=False)
        except Exception:
            continue
    return None


def build(players, team_names):
    """players: {pid: {name, pos, team}}; team_names unused, kept for the caller"""
    import pandas as pd
    df = fetch_all()
    if df is None or df.empty:
        return {}, {"live": False, "season": SEASON,
                    "note": "Madden ratings source unreachable"}

    by_name = {}
    for pid, p in players.items():
        by_name.setdefault(norm(p["name"]), []).append(pid)

    found = {}
    for _, r in df.iterrows():
        cands = by_name.get(norm(r.get("full_name")))
        if not cands:
            continue
        pid = cands[0]
        if len(cands) > 1:
            # Shared name: prefer the club whose nickname matches.
            club = str(r.get("team_short") or "").strip()
            match = [c for c in cands
                     if (team_names.get(club) and players[c].get("team") == team_names[club])]
            if match:
                pid = match[0]
            elif club:
                continue
        try:
            ovr = int(r["overall"])
        except Exception:
            continue

        mpos = str(r.get("position") or "").strip()
        pos = POS_MAP.get(mpos, mpos)
        attrs = []
        for col, label in ATTR_ALL + ATTR_BY_POS.get(pos, []):
            if col in df.columns and pd.notna(r.get(col)):
                try:
                    attrs.append({"l": label, "v": int(r[col])})
                except Exception:
                    pass
        # Drop repeats where a position list names a general attribute again.
        seen_l, uniq = set(), []
        for a in attrs:
            if a["l"] in seen_l:
                continue
            seen_l.add(a["l"])
            uniq.append(a)

        found[pid] = {"ovr": ovr, "attrs": uniq[:9], "pos": pos}
        arch = r.get("archetype")
        if isinstance(arch, str) and arch.strip():
            # "Deep Threat - WR" reads better as just the role.
            found[pid]["arch"] = arch.split(" - ")[0].strip()

    if not found:
        return {}, {"live": False, "season": SEASON,
                    "note": "Madden ratings fetched but matched nobody"}

    # Rank within position, the only ranking that means anything here: a 78 guard
    # and a 78 receiver are not the same statement.
    bypos = {}
    for pid, v in found.items():
        bypos.setdefault(v["pos"], []).append(pid)
    for pos, ids in bypos.items():
        ids.sort(key=lambda p: -found[p]["ovr"])
        n = len(ids)
        rank, last = 0, None
        for i, p in enumerate(ids, 1):
            # Standard competition ranking, so ties share a place.
            if found[p]["ovr"] != last:
                rank, last = i, found[p]["ovr"]
            found[p]["rank"] = rank
            found[p]["n"] = n

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

"""
ESPN's Total QBR, weekly, for the current season.

Worth having because it is not another yards total. QBR is on a 0-100 scale
adjusted for down, distance and opponent, and it decomposes: the points a
quarterback added, split by what he did passing, running, taking sacks and
through penalties. A quarterback with 300 yards in garbage time and one with 220
in a tight game look similar in a box score and nothing alike here.

Joined on ESPN athlete id, which every player in the payload already carries.
"""
import os
import urllib.request

import pandas as pd

SEASON = 2026
PATH = "qbr_week.csv"
URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
       "espn_data/qbr_week_level.csv")
MIN_BYTES = 50_000

# column, label, and whether a bigger number is better
FIELDS = [
    ("qbr_total", "QBR", True),
    ("pts_added", "Points added", True),
    ("epa_total", "EPA", True),
    ("qb_plays", "Plays", None),
]
# The decomposition: where that value actually came from.
PARTS = [("pass", "Passing"), ("run", "Running"),
         ("exp_sack", "Sacks"), ("penalty", "Penalties")]


def fetch():
    if os.path.exists(PATH) and os.path.getsize(PATH) > MIN_BYTES:
        return PATH
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "depth-chart-app"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except Exception:
        return None
    if len(data) < MIN_BYTES:
        return None
    with open(PATH, "wb") as f:
        f.write(data)
    return PATH


def build(espn_ids):
    """espn_ids: {espn_athlete_id: our_player_id}"""
    path = fetch()
    if not path:
        return {}, {"live": False, "season": SEASON}

    d = pd.read_csv(path, low_memory=False)
    d = d[d.season == SEASON]
    if "season_type" in d.columns:
        d = d[d.season_type.astype(str).str.contains("Regular", case=False, na=True)]
    if d.empty:
        return {}, {"live": False, "season": SEASON}

    d["pid"] = d.player_id.astype("Int64").astype(str).map(espn_ids)
    d = d[d.pid.notna()]
    if d.empty:
        return {}, {"live": False, "season": SEASON}

    out = {}
    for pid, grp in d.groupby("pid"):
        grp = grp.sort_values("game_week")
        weeks = []
        for _, r in grp.iterrows():
            weeks.append({
                "w": int(r.game_week),
                "qbr": round(float(r.qbr_total), 1) if pd.notna(r.qbr_total) else None,
                "pts": round(float(r.pts_added), 1) if pd.notna(r.pts_added) else None,
                "plays": int(r.qb_plays) if pd.notna(r.qb_plays) else None,
            })
        # A season figure weighted by plays, which is how QBR is meant to combine.
        plays = grp.qb_plays.fillna(0)
        total_plays = float(plays.sum())
        season_qbr = (float((grp.qbr_total.fillna(0) * plays).sum()) / total_plays
                      if total_plays else None)
        parts = []
        for col, label in PARTS:
            if col in grp.columns and grp[col].notna().any():
                parts.append({"l": label, "v": round(float(grp[col].fillna(0).sum()), 1)})
        out[pid] = {
            "qbr": round(season_qbr, 1) if season_qbr is not None else None,
            "pts": round(float(grp.pts_added.fillna(0).sum()), 1),
            "plays": int(total_plays),
            "weeks": weeks,
            "parts": parts,
        }

    # Rank on the season figure, but only among quarterbacks with real volume --
    # a backup with nine plays should not appear above a starter.
    real = {p: v for p, v in out.items() if v["plays"] >= 20 and v["qbr"] is not None}
    order = sorted(real, key=lambda p: -real[p]["qbr"])
    for i, p in enumerate(order, 1):
        out[p]["rank"] = i
        out[p]["n"] = len(order)

    return out, {"live": True, "season": SEASON, "players": len(out),
                 "ranked": len(order)}

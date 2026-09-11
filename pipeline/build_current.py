"""
Current-season player stats.

Everything else in this app describes 2025, which was correct all offseason and
stops being correct the moment real games are played. This module pulls the
current season when it exists and leaves the app untouched when it does not, so
it switches itself on a few days after week 1 without anyone editing anything.

Two guards worth keeping:

  * a season file appears before it is worth reading. One week of football ranks
    nobody meaningfully, so ranks are withheld until MIN_WEEKS have been played.
  * the file is 404 until the first Tuesday of the season. A missing file is a
    normal state here, not an error, unlike every other source in the pipeline.
"""
import os
import urllib.request

import pandas as pd

SEASON = 2026
MIN_WEEKS = 2                 # before this, show totals but do not rank
PATH = "stats_2026.csv"
URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
       "stats_player/stats_player_reg_{year}.csv")

# Same shape as the baseline season so the app can render either with one path.
STAT_SETS = {
    "QB": [("passing_yards", "Pass yds"), ("passing_tds", "Pass TD"),
           ("passing_interceptions", "INT"), ("rushing_yards", "Rush yds"),
           ("rushing_tds", "Rush TD")],
    "RB": [("rushing_yards", "Rush yds"), ("rushing_tds", "Rush TD"),
           ("carries", "Carries"), ("receptions", "Rec"),
           ("receiving_yards", "Rec yds")],
    "WR": [("receptions", "Rec"), ("receiving_yards", "Rec yds"),
           ("receiving_tds", "Rec TD"), ("targets", "Targets")],
    "DL": [("def_sacks", "Sacks"), ("def_tackles_solo", "Solo tkl"),
           ("def_qb_hits", "QB hits"), ("def_tackles_for_loss", "TFL")],
    "LB": [("def_tackles_solo", "Solo tkl"), ("def_sacks", "Sacks"),
           ("def_tackles_for_loss", "TFL"), ("def_pass_defended", "PD")],
    "DB": [("def_tackles_solo", "Solo tkl"), ("def_pass_defended", "PD"),
           ("def_interceptions", "INT"), ("def_tackles_for_loss", "TFL")],
    "K":  [("fg_made", "FG made"), ("fg_att", "FG att"), ("fg_pct", "FG%")],
}
STAT_SETS["TE"] = STAT_SETS["WR"]
LOWER_IS_BETTER = {"passing_interceptions"}


# A week-1 file is roughly 30KB and a full season nearer a megabyte, while a
# 404 page saved to disk is 9 bytes. The floor separates those, nothing more.
MIN_BYTES = 2_000


def fetch(year=SEASON):
    """Returns a path, or None if the season has not started producing yet."""
    if os.path.exists(PATH) and os.path.getsize(PATH) > MIN_BYTES:
        return PATH
    try:
        req = urllib.request.Request(URL.format(year=year),
                                     headers={"User-Agent": "depth-chart-app"})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
    except Exception:
        return None
    if len(data) < MIN_BYTES or data[:9] == b"Not Found":
        return None
    with open(PATH, "wb") as f:
        f.write(data)
    return PATH


def build(player_ids, buckets):
    path = fetch()
    if not path:
        return {}, {"live": False, "season": SEASON}

    s = pd.read_csv(path, low_memory=False)
    s = s[s.player_id.isin(player_ids)]
    if s.empty:
        return {}, {"live": False, "season": SEASON}

    weeks = int(s.games.max()) if "games" in s.columns else 0
    rankable = weeks >= MIN_WEEKS

    ranks = {}
    if rankable:
        s = s.copy()
        s["bucket"] = s.player_id.map(buckets)
        for bucket, spec in STAT_SETS.items():
            pool = s[s.bucket == bucket]
            if len(pool) < 8:
                continue
            for col, _label in spec:
                if col not in pool.columns:
                    continue
                sub = pool[pool[col].notna()]
                if len(sub) < 8:
                    continue
                asc = col in LOWER_IS_BETTER
                rk = sub[col].rank(ascending=asc, method="min").astype(int)
                for pid, v in zip(sub.player_id, rk):
                    ranks[(pid, col)] = (int(v), len(sub))

    out = {}
    for _, r in s.iterrows():
        b = buckets.get(r.player_id)
        if b not in STAT_SETS:
            continue
        items = []
        for col, label in STAT_SETS[b]:
            if col not in r or pd.isna(r[col]):
                continue
            v = float(r[col])
            entry = {"l": label, "v": round(v, 1) if col == "fg_pct" else int(v)}
            if (r.player_id, col) in ranks:
                entry["r"], entry["n"] = ranks[(r.player_id, col)]
            items.append(entry)
        if items:
            out[r.player_id] = {
                "games": int(r.get("games") or 0),
                # The season files call this recent_team, not team.
                "team": (r.get("recent_team")
                         if isinstance(r.get("recent_team"), str) else None),
                "items": items,
            }

    return out, {"live": True, "season": SEASON, "weeks": weeks,
                 "ranked": rankable, "players": len(out)}

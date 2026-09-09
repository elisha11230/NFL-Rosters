"""
League leaders for the last five seasons, with each name's move from the year
before.

Computed from the per-season stat files rather than the current payload, because
a 2021 leaderboard must include whoever actually led that year — most of them are
retired or out of the league now, and filtering to the current 2,956 players
would quietly rewrite history.

Six seasons are ranked (one more than is displayed) so that every name on the
2021 board has a 2020 rank to be compared against.

Only box score stats are covered. The charting and play-by-play numbers behind
the advanced and situational leaderboards would need a separate download per
season for a much smaller payoff.
"""
import os
import urllib.request

import pandas as pd

SHOW_FROM = 2021          # first season displayed
LAST = 2025
TOP_N = 15
CACHE = "career"
URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
       "stats_player/stats_player_reg_{year}.csv")

POS_BUCKET = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
    "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
    "CB": "DB", "S": "DB", "SS": "DB", "FS": "DB", "DB": "DB",
    "K": "K", "PK": "K",
}

# bucket -> [(column, label)]. Deliberately the headline numbers only; a
# leaderboard of every column would be a wall nobody reads.
STATS = {
    "QB": [("passing_yards", "Pass yds"), ("passing_tds", "Pass TD"),
           ("rushing_yards", "Rush yds")],
    "RB": [("rushing_yards", "Rush yds"), ("rushing_tds", "Rush TD"),
           ("carries", "Carries")],
    "WR": [("receiving_yards", "Rec yds"), ("receptions", "Rec"),
           ("receiving_tds", "Rec TD")],
    "TE": [("receiving_yards", "Rec yds"), ("receptions", "Rec"),
           ("receiving_tds", "Rec TD")],
    "DL": [("def_sacks", "Sacks"), ("def_tackles_solo", "Solo tkl"),
           ("def_tackles_for_loss", "TFL")],
    "LB": [("def_tackles_solo", "Solo tkl"), ("def_sacks", "Sacks"),
           ("def_tackles_for_loss", "TFL")],
    "DB": [("def_tackles_solo", "Solo tkl"), ("def_interceptions", "INT"),
           ("def_pass_defended", "PD")],
    "K":  [("fg_made", "FG made")],
}

# Minimum volume to appear, so a two-game cameo cannot top a rate-free list.
GATE = {"QB": ("attempts", 100), "RB": ("carries", 40), "WR": ("targets", 25),
        "TE": ("targets", 18), "DL": ("games", 6), "LB": ("games", 6),
        "DB": ("games", 6), "K": ("fg_att", 8)}


def _fetch(year):
    path = os.path.join(CACHE, f"{year}.csv")
    if os.path.exists(path) and os.path.getsize(path) > 100_000:
        return path
    os.makedirs(CACHE, exist_ok=True)
    req = urllib.request.Request(URL.format(year=year),
                                 headers={"User-Agent": "depth-chart-app"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 100_000:
        raise SystemExit(f"season stats for {year} look wrong ({len(data)} bytes)")
    with open(path, "wb") as f:
        f.write(data)
    return path


def _rank_season(year):
    """Returns ((bucket, label) -> {player_id: (rank, value, name, team)},
    and the set of every player who appeared at all that season)."""
    df = pd.read_csv(_fetch(year), low_memory=False).copy()
    df["bucket"] = df.position.map(POS_BUCKET)
    present = set(df.player_id.dropna())
    out = {}
    for bucket, cols in STATS.items():
        pool = df[df.bucket == bucket].copy()
        gcol, gmin = GATE.get(bucket, ("games", 1))
        if gcol in pool.columns:
            pool = pool[pool[gcol].fillna(0) >= gmin]
        if len(pool) < 10:
            continue
        for col, label in cols:
            if col not in pool.columns:
                continue
            sub = pool[pool[col].notna()]
            if len(sub) < 10:
                continue
            ranked = sub[col].rank(ascending=False, method="min").astype(int)
            entry = {}
            for pid, rk, val, nm, tm in zip(sub.player_id, ranked, sub[col],
                                            sub.player_display_name,
                                            sub.get("recent_team", sub.get("team"))):
                entry[pid] = (int(rk), float(val), nm, tm)
            out[(bucket, label)] = entry
    return out, present


def build():
    years = list(range(SHOW_FROM - 1, LAST + 1))
    ranked, present = {}, {}
    for y in years:
        ranked[y], present[y] = _rank_season(y)

    out = {}
    for year in range(SHOW_FROM, LAST + 1):
        cur, prev = ranked[year], ranked.get(year - 1, {})
        for key, entries in cur.items():
            bucket, label = key
            top = sorted(entries.items(), key=lambda kv: kv[1][0])[:TOP_N]
            rows = []
            for pid, (rk, val, nm, tm) in top:
                was = prev.get(key, {}).get(pid)
                row = {"id": pid, "n": nm, "t": tm if isinstance(tm, str) else None,
                       "r": rk, "v": int(val) if float(val).is_integer() else round(val, 1)}
                if was:
                    # Rank numbers fall as a player climbs, so invert the sign.
                    row["d"] = was[0] - rk
                elif pid in present.get(year - 1, set()):
                    # Played but did not clear the volume gate. Usually injury,
                    # not a debut -- calling this "new" would be wrong.
                    row["unranked"] = True
                else:
                    row["new"] = True          # did not appear at all
                rows.append(row)
            out.setdefault(f"{bucket}|{label}", {})[str(year)] = rows
    return out

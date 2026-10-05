"""
Next Gen Stats: the NFL's player tracking numbers, season to date.

From nflverse's copy of the NFL's Next Gen Stats (ngs_passing, ngs_receiving,
ngs_rushing), keyed by the same gsis ids as every player in the app. These are
measurements of the play rather than results of it: how long a quarterback held
the ball, how open a receiver was when the ball arrived, how many yards a runner
gained beyond what his blocking and the defence in front of him predicted.

Each player gets the current season's numbers (week 0 in the files is the
season to date). A league rank is given only among players with enough volume,
with the bar scaled to the weeks played so far, so a backup's six attempts do
not top a board. The ranks say which way is better where there is a better
way; neutral measures such as time to throw rank in a stated direction and the
app words them accordingly.
"""
import os

import pandas as pd

SEASON = 2026

# key: (file column, higher is better?)  -- None means rank by "most", neutral
PASS = {
    "cpoe": ("completion_percentage_above_expectation", True),
    "ttt":  ("avg_time_to_throw", False),          # quickest first
    "agg":  ("aggressiveness", None),
    "iay":  ("avg_intended_air_yards", None),
    "ayts": ("avg_air_yards_to_sticks", None),
}
REC = {
    "sep":   ("avg_separation", True),
    "yacoe": ("avg_yac_above_expectation", True),
    "cush":  ("avg_cushion", None),
    "share": ("percent_share_of_intended_air_yards", None),
    "iay":   ("avg_intended_air_yards", None),
}
RUSH = {
    "ryoe":  ("rush_yards_over_expected", True),
    "ryoep": ("rush_yards_over_expected_per_att", True),
    "roe":   ("rush_pct_over_expected", True),
    "box8":  ("percent_attempts_gte_eight_defenders", None),
    "tlos":  ("avg_time_to_los", False),           # quickest to the line first
}
# Volume to qualify for a rank, per week of the season so far.
PER_WEEK = {"pass": ("attempts", 12), "rec": ("targets", 3.5), "rush": ("rush_attempts", 6)}


def _r(v, nd=2):
    return None if pd.isna(v) else round(float(v), nd)


def _section(df, spec, vol_col, per_week, weeks):
    need = per_week * max(weeks, 1)
    qual = df[df[vol_col] >= need]
    out = {}
    for _, row in df.iterrows():
        pid = row.player_gsis_id
        m = {}
        for key, (col, better) in spec.items():
            v = row.get(col)
            if pd.isna(v):
                continue
            r = n = None
            if row[vol_col] >= need and len(qual) >= 8:
                vals = qual[col].dropna()
                asc = better is False
                r = int((vals < v).sum() + 1) if asc else int((vals > v).sum() + 1)
                n = int(len(vals))
            m[key] = [_r(v), r, n]
        out[pid] = {"vol": int(row[vol_col]), "m": m}
    return out


def build(players):
    files = {k: f"ngs_{k}.parquet" for k in ("passing", "receiving", "rushing")}
    if not all(os.path.exists(f) and os.path.getsize(f) > 10_000 for f in files.values()):
        return {}, {"live": False}
    data = {k: pd.read_parquet(f) for k, f in files.items()}
    rows = {k: d[(d.season == SEASON) & (d.season_type == "REG")] for k, d in data.items()}
    weeks = int(max((r.week.max() if len(r) else 0) for r in rows.values()) or 0)
    if not weeks:
        return {}, {"live": False}

    out = {}
    for name, key, spec in (("pass", "passing", PASS), ("rec", "receiving", REC), ("rush", "rushing", RUSH)):
        d = rows[key]
        d = d[(d.week == 0) & d.player_gsis_id.isin(players)]
        vol_col, per_week = PER_WEEK[name]
        for pid, sec in _section(d, spec, vol_col, per_week, weeks).items():
            out.setdefault(pid, {"s": SEASON})[name] = sec
    meta = {"live": True, "season": SEASON, "weeks": weeks, "players": len(out),
            "need": {k: round(v[1] * weeks) for k, v in PER_WEEK.items()}}
    return out, meta

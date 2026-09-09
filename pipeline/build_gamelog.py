"""
Week-by-week game logs for last season.

nflverse publishes weekly player stats, which is a smaller and cleaner source than
deriving from play-by-play. Only skill positions and defenders with a real box
score get a log; linemen would be seventeen rows of zeroes.

Keys are short and match build_career.py's schema so the app can render both with
the same code:
  w week, o opponent, h home, g started/played
"""
import os
import urllib.request

import pandas as pd

SEASON = 2025
PATH = "stats_week_2025.csv"
URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
       "stats_player/stats_player_week_{year}.csv")

FIELDS = {
    "QB": [("passing_yards", "py"), ("passing_tds", "pt"),
           ("passing_interceptions", "in"), ("rushing_yards", "ry"),
           ("rushing_tds", "rt")],
    "RB": [("carries", "ca"), ("rushing_yards", "ry"), ("rushing_tds", "rt"),
           ("receptions", "re"), ("receiving_yards", "cy")],
    "WR": [("receptions", "re"), ("receiving_yards", "cy"),
           ("receiving_tds", "ct"), ("targets", "tg")],
    "DL": [("def_sacks", "sk"), ("def_tackles_solo", "tk"),
           ("def_tackles_for_loss", "tl"), ("def_qb_hits", "qh")],
    "LB": [("def_tackles_solo", "tk"), ("def_sacks", "sk"),
           ("def_tackles_for_loss", "tl"), ("def_pass_defended", "pd")],
    "DB": [("def_tackles_solo", "tk"), ("def_pass_defended", "pd"),
           ("def_interceptions", "ix"), ("def_tackles_for_loss", "tl")],
    "K":  [("fg_made", "fm"), ("fg_att", "fa")],
}
FIELDS["TE"] = FIELDS["WR"]


def _fetch():
    if os.path.exists(PATH) and os.path.getsize(PATH) > 500_000:
        return PATH
    req = urllib.request.Request(URL.format(year=SEASON),
                                 headers={"User-Agent": "depth-chart-app"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 500_000:
        raise SystemExit(f"weekly stats look wrong ({len(data)} bytes)")
    with open(PATH, "wb") as f:
        f.write(data)
    return PATH


def build(player_ids, buckets):
    s = pd.read_csv(_fetch(), low_memory=False)
    if "season_type" in s.columns:
        s = s[s.season_type == "REG"]
    s = s[s.player_id.isin(player_ids)]

    out = {}
    for _, r in s.iterrows():
        b = buckets.get(r.player_id)
        if b not in FIELDS:
            continue
        row = {"w": int(r.week)}
        opp = r.get("opponent_team")
        if isinstance(opp, str):
            row["o"] = opp
        has = False
        for col, key in FIELDS[b]:
            if col in r and pd.notna(r[col]):
                v = float(r[col])
                row[key] = int(v)
                has = has or v != 0
        if has:
            out.setdefault(r.player_id, []).append(row)

    for pid in out:
        out[pid].sort(key=lambda x: x["w"])
    # A single game is not a log; the season line already says that.
    return {k: v for k, v in out.items() if len(v) >= 2}

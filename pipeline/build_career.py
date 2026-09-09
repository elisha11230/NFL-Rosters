"""
Season-by-season career stats.

nflverse publishes one file per season back to 1999. Coverage of players who are
still on a 2026 depth chart falls off a cliff before 2016 -- twelve rows in 2010,
against 1,763 in 2025 -- so the history starts there. That span covers a complete
career for every active player except a handful of long-serving veterans, whose
earliest seasons are noted as truncated rather than silently dropped.

Do NOT use the master table's `rookie_season` to decide how far back to look. It
carries name collisions: eight players on current charts inherit an older player's
record, including a "1976 rookie season". Everything here joins on player_id, so
those bad rows cannot leak in.

Keys are short because this is the largest single block in the payload:
  y year, t team, g games. Stat keys are abbreviated per position group.
"""
import os
import urllib.request

import pandas as pd

FIRST = 2016
LAST = 2025
CACHE = "career"
URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
       "stats_player/stats_player_reg_{year}.csv")

# bucket -> [(source column, short key, label)]
FIELDS = {
    "QB": [("passing_yards", "py", "Pass yds"), ("passing_tds", "pt", "Pass TD"),
           ("passing_interceptions", "in", "INT"),
           ("rushing_yards", "ry", "Rush yds"), ("rushing_tds", "rt", "Rush TD")],
    "RB": [("carries", "ca", "Carries"), ("rushing_yards", "ry", "Rush yds"),
           ("rushing_tds", "rt", "Rush TD"), ("receptions", "re", "Rec"),
           ("receiving_yards", "cy", "Rec yds")],
    "WR": [("receptions", "re", "Rec"), ("receiving_yards", "cy", "Rec yds"),
           ("receiving_tds", "ct", "Rec TD"), ("targets", "tg", "Targets")],
    "DL": [("def_sacks", "sk", "Sacks"), ("def_tackles_solo", "tk", "Solo tkl"),
           ("def_tackles_for_loss", "tl", "TFL"), ("def_qb_hits", "qh", "QB hits")],
    "LB": [("def_tackles_solo", "tk", "Solo tkl"), ("def_sacks", "sk", "Sacks"),
           ("def_tackles_for_loss", "tl", "TFL"),
           ("def_pass_defended", "pd", "PD")],
    "DB": [("def_tackles_solo", "tk", "Solo tkl"),
           ("def_pass_defended", "pd", "PD"),
           ("def_interceptions", "ix", "INT"),
           ("def_tackles_for_loss", "tl", "TFL")],
    "K":  [("fg_made", "fm", "FG made"), ("fg_att", "fa", "FG att"),
           ("fg_pct", "fp", "FG%")],
}
FIELDS["TE"] = FIELDS["WR"]

# The app needs to know what the short keys mean without hardcoding it twice.
SCHEMA = {b: [{"k": k, "l": lab} for _c, k, lab in f] for b, f in FIELDS.items()}


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
        raise SystemExit(f"career stats for {year} look wrong ({len(data)} bytes)")
    with open(path, "wb") as f:
        f.write(data)
    return path


def build(player_ids, buckets):
    out = {}
    for year in range(FIRST, LAST + 1):
        s = pd.read_csv(_fetch(year), low_memory=False)
        s = s[s.player_id.isin(player_ids)]
        for _, r in s.iterrows():
            b = buckets.get(r.player_id)
            if b not in FIELDS:
                continue
            row = {"y": year}
            team = r.get("team") if "team" in r else r.get("recent_team")
            if isinstance(team, str):
                row["t"] = team
            g = r.get("games")
            if pd.notna(g):
                row["g"] = int(g)
            has = False
            for col, key, _lab in FIELDS[b]:
                if col in r and pd.notna(r[col]):
                    v = float(r[col])
                    row[key] = round(v, 1) if key == "fp" else int(v)
                    has = has or v != 0
            if has:
                out.setdefault(r.player_id, []).append(row)

    for pid in out:
        out[pid].sort(key=lambda x: x["y"])
    return out


def truncated(career, master, player_ids):
    """Players whose first pro season predates our window, so the app can say so
    rather than implying the list is a full career."""
    flags = {}
    for pid, rows in career.items():
        if not rows or rows[0]["y"] > FIRST:
            continue
        # Only trust the master table when it is plausible; see the module note.
        rookie = master.rookie_season.get(pid)
        exp = master.years_of_experience.get(pid)
        est = None
        if pd.notna(rookie) and 1999 <= float(rookie) < FIRST:
            est = int(rookie)
        elif pd.notna(exp) and 2026 - int(exp) < FIRST:
            est = 2026 - int(exp)
        if est:
            flags[pid] = est
    return flags

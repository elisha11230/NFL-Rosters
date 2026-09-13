"""
The best individual performances of each week.

Built from the weekly stats file rather than fetched live. Assembling this in the
browser would mean pulling a box score for every game on the slate — sixteen
requests to answer one question — and the answer stops changing once the games
are over, so it belongs in the payload.

Categories are grouped into offence, defence and special teams because a flat
list of fifteen leaderboards is not something anyone reads. Two are derived
rather than read straight out of a column: scrimmage yards and total touchdowns,
both of which answer "who had the biggest day" better than any single column
does, since they do not care how a player got there.
"""
import os

import pandas as pd

SEASON = 2026
PATH = "stats_week_2026.csv"
TAKE = 10

# group, label, column, unit shown under the number, supporting columns
CATEGORIES = [
    # ---- offence
    ("Offence", "Passing yards", "passing_yards", "Pass yds",
     [("completions", "of"), ("attempts", "att"), ("passing_tds", "TD")]),
    ("Offence", "Passing TDs", "passing_tds", "Pass TD",
     [("passing_yards", "yds"), ("passing_interceptions", "INT")]),
    ("Offence", "Rushing yards", "rushing_yards", "Rush yds",
     [("carries", "car"), ("rushing_tds", "TD")]),
    ("Offence", "Rushing TDs", "rushing_tds", "Rush TD",
     [("carries", "car"), ("rushing_yards", "yds")]),
    ("Offence", "Receiving yards", "receiving_yards", "Rec yds",
     [("receptions", "rec"), ("targets", "tgt"), ("receiving_tds", "TD")]),
    ("Offence", "Receptions", "receptions", "Rec",
     [("targets", "tgt"), ("receiving_yards", "yds")]),
    ("Offence", "Receiving TDs", "receiving_tds", "Rec TD",
     [("receptions", "rec"), ("receiving_yards", "yds")]),
    # Derived below.
    ("Offence", "Scrimmage yards", "_scrimmage", "Yards",
     [("rushing_yards", "rush"), ("receiving_yards", "rec")]),
    # Passing has to be in here: a quarterback's three touchdowns were otherwise
    # listed with nothing to explain where they came from.
    ("Offence", "Touchdowns", "_total_tds", "TDs",
     [("passing_tds", "pass"), ("rushing_tds", "rush"), ("receiving_tds", "rec")]),
    ("Offence", "First downs", "_first_downs", "1st downs",
     [("rushing_first_downs", "rush"), ("receiving_first_downs", "rec")]),
    # ---- defence
    ("Defence", "Sacks", "def_sacks", "Sacks",
     [("def_tackles_solo", "tkl"), ("def_tackles_for_loss", "TFL")]),
    ("Defence", "Tackles", "def_tackles_solo", "Solo tkl",
     [("def_tackles_for_loss", "TFL"), ("def_sacks", "sacks")]),
    ("Defence", "Tackles for loss", "def_tackles_for_loss", "TFL",
     [("def_tackles_solo", "tkl"), ("def_sacks", "sacks")]),
    ("Defence", "Interceptions", "def_interceptions", "INT",
     [("def_pass_defended", "PD"), ("def_tackles_solo", "tkl")]),
    ("Defence", "Passes defended", "def_pass_defended", "PD",
     [("def_interceptions", "INT"), ("def_tackles_solo", "tkl")]),
    ("Defence", "QB hits", "def_qb_hits", "QB hits",
     [("def_sacks", "sacks"), ("def_tackles_for_loss", "TFL")]),
    ("Defence", "Forced fumbles", "def_fumbles_forced", "FF",
     [("def_tackles_solo", "tkl"), ("def_sacks", "sacks")]),
    # ---- special teams
    ("Special teams", "Field goals", "fg_made", "FG made",
     [("fg_att", "att"), ("pat_made", "PAT")]),
]

DERIVED = {
    "_scrimmage": ["rushing_yards", "receiving_yards"],
    "_total_tds": ["rushing_tds", "receiving_tds", "passing_tds", "special_teams_tds"],
    "_first_downs": ["rushing_first_downs", "receiving_first_downs"],
}


def build(player_ids):
    if not os.path.exists(PATH) or os.path.getsize(PATH) < 2_000:
        return {}, {"live": False, "season": SEASON}

    d = pd.read_csv(PATH, low_memory=False)
    if "season_type" in d.columns:
        d = d[d.season_type == "REG"]
    if d.empty:
        return {}, {"live": False, "season": SEASON}

    # Sums of other columns, computed once so the loop can treat them normally.
    # Built as one frame and joined, rather than inserted one at a time, which
    # fragments the frame and makes pandas complain.
    extra = {}
    for name, parts in DERIVED.items():
        cols = [c for c in parts if c in d.columns]
        extra[name] = d[cols].fillna(0).sum(axis=1) if cols else 0
    d = pd.concat([d, pd.DataFrame(extra, index=d.index)], axis=1)

    out = {}
    for week, wk in d.groupby("week"):
        cats = []
        for group, name, col, label, extras in CATEGORIES:
            if col not in wk.columns:
                continue
            pool = wk[wk[col].notna() & (wk[col] > 0)]
            if pool.empty:
                continue
            rows = []
            for _, r in pool.nlargest(TAKE, col).iterrows():
                bits = []
                for ecol, elab in extras:
                    if ecol in r and pd.notna(r[ecol]) and r[ecol]:
                        v = float(r[ecol])
                        bits.append(f"{int(v) if v.is_integer() else v} {elab}")
                v = float(r[col])
                rows.append({
                    "pid": r.player_id if r.player_id in player_ids else None,
                    "n": r.player_display_name,
                    "t": r.team if isinstance(r.get("team"), str) else None,
                    "o": r.opponent_team if isinstance(r.get("opponent_team"), str) else None,
                    "p": r.position if isinstance(r.get("position"), str) else None,
                    "v": int(v) if v.is_integer() else round(v, 1),
                    "x": "  ".join(bits),
                })
            if rows:
                cats.append({"g": group, "name": name, "label": label, "rows": rows})
        if cats:
            out[str(int(week))] = cats

    weeks = sorted(int(w) for w in out)
    return out, {"live": bool(out), "season": SEASON,
                 "weeks": weeks, "latest": weeks[-1] if weeks else None,
                 "groups": ["Offence", "Defence", "Special teams"]}

"""
The best individual performances of each week.

Built from the weekly stats file rather than fetched live. Assembling this in the
browser would mean pulling a box score for every game on the slate — sixteen
requests to answer one question — and the answer does not change once the games
are over, so it belongs in the payload.

Appears a day or so after each week's games, and grows a week at a time.
"""
import os

import pandas as pd

SEASON = 2026
PATH = "stats_week_2026.csv"
TAKE = 5

# (column, label, unit) per category. The unit is the headline number; the extras
# ride along so a line reads like a box score rather than a bare figure.
CATEGORIES = [
    ("Passing", "passing_yards", "Pass yds",
     [("passing_tds", "TD"), ("passing_interceptions", "INT")]),
    ("Rushing", "rushing_yards", "Rush yds",
     [("carries", "car"), ("rushing_tds", "TD")]),
    ("Receiving", "receiving_yards", "Rec yds",
     [("receptions", "rec"), ("receiving_tds", "TD")]),
    ("Sacks", "def_sacks", "Sacks",
     [("def_tackles_solo", "tkl"), ("def_tackles_for_loss", "TFL")]),
    ("Tackles", "def_tackles_solo", "Solo tkl",
     [("def_sacks", "sacks"), ("def_pass_defended", "PD")]),
]


def build(player_ids):
    if not os.path.exists(PATH) or os.path.getsize(PATH) < 2_000:
        return {}, {"live": False, "season": SEASON}

    d = pd.read_csv(PATH, low_memory=False)
    if "season_type" in d.columns:
        d = d[d.season_type == "REG"]
    if d.empty:
        return {}, {"live": False, "season": SEASON}

    out = {}
    for week, wk in d.groupby("week"):
        cats = []
        for name, col, label, extras in CATEGORIES:
            if col not in wk.columns:
                continue
            pool = wk[wk[col].notna() & (wk[col] > 0)]
            if pool.empty:
                continue
            top = pool.nlargest(TAKE, col)
            rows = []
            for _, r in top.iterrows():
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
                    "v": int(v) if v.is_integer() else round(v, 1),
                    "x": "  ".join(bits),
                })
            if rows:
                cats.append({"name": name, "label": label, "rows": rows})
        if cats:
            out[str(int(week))] = cats

    weeks = sorted(int(w) for w in out)
    return out, {"live": bool(out), "season": SEASON,
                 "weeks": weeks, "latest": weeks[-1] if weeks else None}

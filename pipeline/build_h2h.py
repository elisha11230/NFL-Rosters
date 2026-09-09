"""
Head-to-head records, 1999 to last season.

Uses the full schedule rather than the ten-year history window, because a
non-division opponent is only met three or four times a decade and a 2-1 record
says nothing. Since 1999 a division rival is worth about fifty games and even a
rare opponent gets a usable sample.

Relocated franchises are folded into their current abbreviation, or the Chargers
would have three separate head-to-head records against everyone. Houston enters
in 2002 and simply has fewer games, which needs no special handling.
"""
import pandas as pd

FIRST = 1999

RELOCATED = {"SD": "LAC", "OAK": "LV", "STL": "LA"}


def build(teams):
    s = pd.read_csv("sched.csv", low_memory=False)
    s = s[(s.season >= FIRST) & s.home_score.notna()]

    rec = {}
    for _, g in s.iterrows():
        h = RELOCATED.get(g.home_team, g.home_team)
        a = RELOCATED.get(g.away_team, g.away_team)
        if h not in teams or a not in teams:
            continue
        post = g.game_type != "REG"
        for me, opp, ms, os_ in ((h, a, g.home_score, g.away_score),
                                 (a, h, g.away_score, g.home_score)):
            d = rec.setdefault(me, {}).setdefault(opp, {
                "w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "post": 0, "last": None})
            d["w" if ms > os_ else "l" if ms < os_ else "t"] += 1
            d["pf"] += int(ms)
            d["pa"] += int(os_)
            if post:
                d["post"] += 1
            yr = int(g.season)
            if d["last"] is None or yr > d["last"][0]:
                d["last"] = (yr, "W" if ms > os_ else "L" if ms < os_ else "T")

    out = {}
    for team, opps in rec.items():
        o = {}
        for opp, d in opps.items():
            n = d["w"] + d["l"] + d["t"]
            o[opp] = {
                "w": d["w"], "l": d["l"], "t": d["t"],
                "rec": f"{d['w']}-{d['l']}" + (f"-{d['t']}" if d["t"] else ""),
                "n": n,
                "pct": round(d["w"] / max(1, n) * 100),
                "post": d["post"],
                "last": f"{d['last'][0]} {d['last'][1]}" if d["last"] else None,
            }
        out[team] = o
    return out


def summarise(h2h, teams):
    """Best and worst matchup per team, for a one-line summary."""
    out = {}
    for team, opps in h2h.items():
        # Only matchups with a real sample say anything.
        real = {k: v for k, v in opps.items() if v["n"] >= 8}
        if not real:
            continue
        best = max(real.items(), key=lambda x: (x[1]["pct"], x[1]["n"]))
        worst = min(real.items(), key=lambda x: (x[1]["pct"], -x[1]["n"]))
        out[team] = {
            "best": {"opp": best[0], "rec": best[1]["rec"]},
            "worst": {"opp": worst[0], "rec": worst[1]["rec"]},
            "from": FIRST,
        }
    return out

"""
Ten seasons of team history.

Everything here comes out of the schedule file, which carries every game back to
1999 with scores, game type and the coach on each side. Records, playoff finishes,
division standing and coaching tenure all fall out of the same source, so nothing
can disagree with anything else.

Division alignment is taken from the current teams file and applied backwards.
That is safe for this window: the divisions have not changed since the 2002
realignment. Extending this before 2002 would need per-season alignment.

The 2026 head coach column is unreliable (see coaches_2026.py), but historical
seasons are fine -- that staleness only affects the upcoming season.
"""
import pandas as pd

FIRST = 2016
LAST = 2025

ROUND_ORDER = {"WC": 1, "DIV": 2, "CON": 3, "SB": 4}
LOST = {"WC": "Lost Wild Card", "DIV": "Lost Divisional",
        "CON": "Lost Conf. Championship", "SB": "Lost Super Bowl"}
SHORT = {"Missed playoffs": "\u2013", "Lost Wild Card": "WC",
         "Lost Divisional": "DIV", "Lost Conf. Championship": "CONF",
         "Lost Super Bowl": "SB loss", "Won Super Bowl": "CHAMPION"}

# Two franchises relocated inside this window and the schedule files them under
# their old city for those seasons. Without folding them in, the Chargers lose
# 2016 and the Raiders lose 2016-19, and the league appears to have 34 teams.
RELOCATED = {"SD": "LAC", "OAK": "LV", "STL": "LA"}
# City the franchise played in during those years, so the table can say so
# rather than silently attributing a San Diego season to Los Angeles.
FORMER_CITY = {"SD": "San Diego", "OAK": "Oakland", "STL": "St. Louis"}


def build(teams, divisions):
    """teams: set of abbreviations. divisions: team -> division name."""
    s = pd.read_csv("sched.csv", low_memory=False)
    s = s[(s.season >= FIRST) & (s.season <= LAST) & s.home_score.notna()]

    rows = []
    for _, g in s.iterrows():
        for raw, opp, ms, os_, coach in (
            (g.home_team, g.away_team, g.home_score, g.away_score, g.home_coach),
            (g.away_team, g.home_team, g.away_score, g.home_score, g.away_coach),
        ):
            me = RELOCATED.get(raw, raw)
            if me not in teams:
                continue
            rows.append({
                "season": int(g.season), "type": g.game_type, "team": me,
                "raw": raw,
                "opp": opp, "pf": ms, "pa": os_, "coach": coach,
                # Not "div": DataFrame.div is pandas' division method, so
                # attribute access would silently return the operator instead.
                "divgame": bool(g.get("div_game", 0)),
            })
    df = pd.DataFrame(rows)

    out = {}
    for (team, season), g in df.groupby(["team", "season"]):
        reg = g[g.type == "REG"]
        post = g[g.type != "REG"]
        w = int((reg.pf > reg.pa).sum())
        l = int((reg.pf < reg.pa).sum())
        t = int((reg.pf == reg.pa).sum())

        dv = reg[reg.divgame]
        dw = int((dv.pf > dv.pa).sum())
        dl = int((dv.pf < dv.pa).sum())

        finish, best = "Missed playoffs", 0
        for _, p in post.iterrows():
            r = p.type
            if r not in ROUND_ORDER or ROUND_ORDER[r] < best:
                continue
            best = ROUND_ORDER[r]
            won = p.pf > p.pa
            finish = ("Won Super Bowl" if (r == "SB" and won)
                      else LOST[r] if not won else finish)

        coach = reg.coach.mode()
        # If the franchise played that season under an old name, say so.
        played_as = {r for r in reg.raw if r in FORMER_CITY}
        out.setdefault(team, {})[season] = {
            "y": season, "w": w, "l": l, "t": t,
            "rec": f"{w}-{l}" + (f"-{t}" if t else ""),
            "pf": int(reg.pf.sum()), "pa": int(reg.pa.sum()),
            "div": f"{dw}-{dl}",
            "fin": SHORT.get(finish, finish),
            "champ": finish == "Won Super Bowl",
            "playoff": finish != "Missed playoffs",
            "coach": coach.iloc[0] if len(coach) else None,
            "as": FORMER_CITY[played_as.pop()] if played_as else None,
        }

    # Division standing, computed within each season from the records above.
    for season in range(FIRST, LAST + 1):
        by_div = {}
        for team, seasons in out.items():
            if season in seasons:
                by_div.setdefault(divisions.get(team), []).append(team)
        for _dname, members in by_div.items():
            members.sort(key=lambda t: (-out[t][season]["w"], out[t][season]["l"],
                                        -(out[t][season]["pf"] - out[t][season]["pa"])))
            for i, t in enumerate(members, 1):
                out[t][season]["dr"] = i
                out[t][season]["dn"] = len(members)

    result = {}
    for team, seasons in out.items():
        hist = [seasons[y] for y in sorted(seasons)]
        wins = sum(h["w"] for h in hist)
        losses = sum(h["l"] for h in hist)
        ties = sum(h["t"] for h in hist)
        result[team] = {
            "seasons": hist,
            "w": wins, "l": losses, "t": ties,
            "record": f"{wins}-{losses}" + (f"-{ties}" if ties else ""),
            "pct": round(wins / max(1, wins + losses + ties) * 100, 1),
            "playoffs": sum(1 for h in hist if h["playoff"]),
            "titles": sum(1 for h in hist if h["champ"]),
            "div_titles": sum(1 for h in hist if h.get("dr") == 1),
            "best": max(hist, key=lambda h: (h["w"], -h["l"]))["y"],
            "worst": min(hist, key=lambda h: (h["w"], -h["l"]))["y"],
            "from": FIRST, "to": LAST,
        }

    # League rank over the whole span, so the summary line means something.
    pct = pd.Series({t: v["pct"] for t, v in result.items()})
    rk = pct.rank(ascending=False, method="min").astype(int)
    for t, r in rk.items():
        result[t]["rank"] = int(r)
        result[t]["n"] = len(pct)
    return result

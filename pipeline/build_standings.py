"""
Standings for the current season.

Built from the schedule file, which gains scores as games are played, so this
produces nothing in preseason and fills in on its own from week 1 onward. No
extra download: the same sched.csv already used for records, coaches and
head-to-head.

Ordering is by win percentage, then division record, then points difference. That
is a reasonable approximation and not the league's full tiebreaker, which runs to
a dozen steps involving common opponents and strength of victory. The app says so
rather than implying an authority it does not have.
"""
import pandas as pd

SEASON = 2026


def build(teams, divisions):
    s = pd.read_csv("sched.csv", low_memory=False)
    s = s[(s.season == SEASON) & (s.game_type == "REG") & s.home_score.notna()]
    if s.empty:
        return {}, {"live": False, "season": SEASON, "played": 0}

    rec = {t: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0,
               "dw": 0, "dl": 0, "cw": 0, "cl": 0, "form": []} for t in teams}

    conf = {t: divisions.get(t, " ").split()[0] for t in teams}

    for _, g in s.sort_values(["week"]).iterrows():
        h, a = g.home_team, g.away_team
        if h not in rec or a not in rec:
            continue
        hs, as_ = g.home_score, g.away_score
        same_div = divisions.get(h) == divisions.get(a)
        same_conf = conf.get(h) == conf.get(a)
        for me, opp, ms, os_ in ((h, a, hs, as_), (a, h, as_, hs)):
            d = rec[me]
            d["pf"] += int(ms)
            d["pa"] += int(os_)
            res = "W" if ms > os_ else "L" if ms < os_ else "T"
            d["w" if res == "W" else "l" if res == "L" else "t"] += 1
            if same_div:
                d["dw" if res == "W" else "dl"] += 1 if res != "T" else 0
            if same_conf:
                d["cw" if res == "W" else "cl"] += 1 if res != "T" else 0
            d["form"].append(res)

    out = {}
    for t, d in rec.items():
        n = d["w"] + d["l"] + d["t"]
        if not n:
            continue
        out[t] = {
            "w": d["w"], "l": d["l"], "t": d["t"],
            "rec": f"{d['w']}-{d['l']}" + (f"-{d['t']}" if d["t"] else ""),
            "pct": round((d["w"] + 0.5 * d["t"]) / n, 4),
            "pf": d["pf"], "pa": d["pa"], "diff": d["pf"] - d["pa"],
            "div": f"{d['dw']}-{d['dl']}",
            "conf": f"{d['cw']}-{d['cl']}",
            "form": d["form"][-5:],
            "played": n,
        }

    # Order inside each division, and across each conference.
    def key(t):
        v = out[t]
        dw, dl = (int(x) for x in v["div"].split("-"))
        return (-v["pct"], -(dw - dl), -v["diff"])

    by_div, by_conf = {}, {}
    for t in out:
        by_div.setdefault(divisions.get(t), []).append(t)
        by_conf.setdefault(conf.get(t), []).append(t)
    for d, members in by_div.items():
        members.sort(key=key)
        for i, t in enumerate(members, 1):
            out[t]["dpos"] = i
            out[t]["division"] = d
    # Seeds only mean something once most of the league has played. In the first
    # days of a season two teams have a result and both would show as the top
    # seed in their conference, which is true and useless.
    enough = len(out) >= len(teams) * 0.75
    for c, members in by_conf.items():
        members.sort(key=key)
        for i, t in enumerate(members, 1):
            out[t]["cpos"] = i
            out[t]["conf_name"] = c
            # Seven make the postseason: four division winners and three others.
            out[t]["seed"] = (i if i <= 7 else None) if enough else None

    tables = {
        "divisions": {d: members for d, members in sorted(by_div.items())},
        "conferences": {c: members for c, members in sorted(by_conf.items())},
    }
    return {"teams": out, "tables": tables}, {
        "live": True, "season": SEASON,
        "played": int(len(s)), "week": int(s.week.max()),
        "partial": not enough,
    }

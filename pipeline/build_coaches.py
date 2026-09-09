"""
Coaching staffs and head coach tenure.

Names come from coaches_2026.py, which is hand maintained because nflverse's
schedule coach column is only partly updated for 2026 (see that file for the
detail). The schedule is still the source for tenure and record, since counting
seasons a named coach worked for a named team is exactly what it is good at.
"""
import pandas as pd
from coaches_2026 import STAFFS_2026, SCHEDULE_ALIASES, ROLES

CURRENT = 2026


def _long(sched):
    """One row per team per game, with that team's coach."""
    home = sched.dropna(subset=["home_coach"]).rename(
        columns={"home_team": "team", "home_coach": "coach",
                 "home_score": "pf", "away_score": "pa"})
    away = sched.dropna(subset=["away_coach"]).rename(
        columns={"away_team": "team", "away_coach": "coach",
                 "away_score": "pf", "home_score": "pa"})
    cols = ["season", "week", "game_type", "team", "coach", "pf", "pa"]
    return pd.concat([home[cols], away[cols]], ignore_index=True)


def build(teams):
    sched = pd.read_csv("sched.csv", low_memory=False)
    lg = _long(sched)
    lg = lg[lg.team.isin(teams)]

    out = {}
    for team in sorted(teams):
        staff = STAFFS_2026.get(team)
        if not staff:
            continue
        hc = staff["hc"]
        lookup = SCHEDULE_ALIASES.get(hc, hc)

        mine = lg[(lg.team == team) & (lg.coach == lookup)]
        seasons = set(mine.season.astype(int))

        # Walk back only through consecutive seasons, so a coach who left and
        # returned is credited with the current stint rather than both.
        start = CURRENT
        for yr in range(CURRENT - 1, min(seasons or {CURRENT}) - 1, -1):
            if yr in seasons:
                start = yr
            else:
                break

        stint = mine[(mine.season >= start) & mine.pf.notna()]
        reg = stint[stint.game_type == "REG"]
        post = stint[stint.game_type != "REG"]
        w = int((reg.pf > reg.pa).sum())
        l = int((reg.pf < reg.pa).sum())
        t = int((reg.pf == reg.pa).sum())
        sb = post[(post.game_type == "SB") & (post.pf > post.pa)]

        out[team] = {
            "name": hc,
            "since": int(start),
            "years": CURRENT - int(start) + 1,
            "rookie": start == CURRENT,
            "record": f"{w}-{l}" + (f"-{t}" if t else ""),
            "playoffs": len({int(y) for y in post.season.unique()}),
            "titles": int(len(sb)),
            "staff": [
                {"role": label, "name": staff[key][0],
                 "since": staff[key][1],
                 "years": CURRENT - staff[key][1] + 1}
                for key, label in ROLES
            ],
        }
    return out


if __name__ == "__main__":
    import json
    d = json.load(open("nfl_data.json"))
    res = build(set(d["teams"]))
    print(f"{len(res)} teams, {sum(1 for c in res.values() if c['rookie'])} new head coaches\n")
    for k in sorted(res, key=lambda x: res[x]["since"]):
        c = res[k]
        tag = "1st yr" if c["rookie"] else f"{c['years']}th yr {c['record']}"
        coords = "  ".join(f"{s['name']} ({s['since']})" for s in c["staff"])
        print(f"  {k:<4} {c['name']:<21}{tag:<14} {coords}")

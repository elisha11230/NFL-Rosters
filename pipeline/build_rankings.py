"""
Team power ratings, computed several ways.

Editorial power rankings -- a writer's weekly top 32 -- are published as articles
and have no feed. Scraping them would be fragile and is a terms question, so this
does not try.

What it does instead is compute ratings by four independent methods from data
already in the pipeline. Each is a recognised approach with a different blind
spot, which is the point: where they agree you can be confident, and where they
disagree that disagreement is itself informative.

  SRS          margin of victory adjusted for who you played. Solved by
               iteration, the standard method.
  Pythagorean  expected win rate from points for and against. Ignores how the
               points were arranged, so it sees through lucky close wins.
  EPA          expected points added per play, offence minus defence. Play level
               rather than score level, so it is the least affected by garbage
               time and by a fluke return.
  Differential plain net points per game. The blunt one, kept because it is
               transparent and everyone understands it.

The consensus is the average of the four ranks. A team's spread across the four
is reported too, because a side ranked 4th by one measure and 20th by another is
telling you something a single number would hide.
"""
import os

import pandas as pd

SEASON = 2026
SRS_ROUNDS = 12          # iterations; converges well before this


def _played(teams, through_week=None):
    s = pd.read_csv("sched.csv", low_memory=False)
    s = s[(s.season == SEASON) & (s.game_type == "REG") & s.home_score.notna()]
    if through_week is not None:
        s = s[s.week <= through_week]
    rows = []
    for _, g in s.iterrows():
        if g.home_team not in teams or g.away_team not in teams:
            continue
        rows.append({"team": g.home_team, "opp": g.away_team, "week": int(g.week),
                     "pf": g.home_score, "pa": g.away_score})
        rows.append({"team": g.away_team, "opp": g.home_team, "week": int(g.week),
                     "pf": g.away_score, "pa": g.home_score})
    return pd.DataFrame(rows)


def _srs(df, teams):
    """Margin adjusted for schedule. Each round replaces a team's rating with its
    average margin plus the average rating of its opponents."""
    margin = {t: 0.0 for t in teams}
    games = {t: 0 for t in teams}
    for t, grp in df.groupby("team"):
        margin[t] = float((grp.pf - grp.pa).mean())
        games[t] = len(grp)
    rating = dict(margin)
    for _ in range(SRS_ROUNDS):
        nxt = {}
        for t in teams:
            mine = df[df.team == t]
            if mine.empty:
                nxt[t] = 0.0
                continue
            sos = sum(rating.get(o, 0.0) for o in mine.opp) / len(mine)
            nxt[t] = margin[t] + sos
        # Centre on zero so the numbers stay comparable between weeks.
        mean = sum(nxt.values()) / len(nxt)
        rating = {t: v - mean for t, v in nxt.items()}
    return rating, games


def _pythagorean(df, teams):
    """Expected win rate from points scored and allowed. The 2.37 exponent is the
    one commonly fitted for professional football."""
    out = {}
    for t in teams:
        mine = df[df.team == t]
        if mine.empty:
            out[t] = 0.5
            continue
        pf, pa = float(mine.pf.sum()), float(mine.pa.sum())
        if pf + pa == 0:
            out[t] = 0.5
        else:
            out[t] = pf ** 2.37 / (pf ** 2.37 + pa ** 2.37)
    return out


_PBP_CACHE = {}


def _epa(teams, through_week=None, path="pbp2026.parquet"):
    """Offence EPA per play minus defence EPA per play allowed. Absent until the
    current season's play-by-play is published.

    The file is read once and cached: this is called once per week of the season
    to build the history, and re-reading a parquet each time is wasteful."""
    if not os.path.exists(path) or os.path.getsize(path) < 10_000:
        return None
    if "df" not in _PBP_CACHE:
        try:
            _PBP_CACHE["df"] = pd.read_parquet(
                path, columns=["posteam", "defteam", "epa", "play_type", "week"])
        except Exception:
            _PBP_CACHE["df"] = None
    p = _PBP_CACHE["df"]
    if p is None:
        return None
    if through_week is not None:
        p = p[p.week <= through_week]
    p = p[p.play_type.isin(["pass", "run"]) & p.epa.notna()]
    if p.empty:
        return None
    off = p.groupby("posteam").epa.mean()
    dfn = p.groupby("defteam").epa.mean()
    return {t: float(off.get(t, 0)) - float(dfn.get(t, 0)) for t in teams}


def _rate(all_teams, through_week=None):
    """Ratings using only games up to and including a week. Called once per
    completed week so that movement between weeks can be shown."""
    df = _played(all_teams, through_week)
    if df.empty:
        return None, None, None
    teams = sorted({t for t in all_teams if len(df[df.team == t])})
    if not teams:
        return None, None, None

    srs, games = _srs(df, teams)
    pyth = _pythagorean(df, teams)
    epa = _epa(teams, through_week)
    diff = {}
    for t in teams:
        mine = df[df.team == t]
        diff[t] = float((mine.pf - mine.pa).mean()) if len(mine) else 0.0

    methods = [("SRS", srs, "Margin, adjusted for schedule"),
               ("Pythagorean", pyth, "Expected win rate from points"),
               ("Differential", diff, "Net points per game")]
    if epa:
        methods.insert(2, ("EPA", epa, "Expected points added per play"))

    ranks = {}
    for name, vals, _desc in methods:
        order = sorted(teams, key=lambda t: -vals.get(t, 0))
        for i, t in enumerate(order, 1):
            ranks.setdefault(t, {})[name] = i

    table = {}
    for t in teams:
        mine = ranks.get(t, {})
        nums = list(mine.values())
        table[t] = {
            "methods": [{"name": n, "rank": mine[n],
                         "value": round(float(v.get(t, 0)), 3)}
                        for n, v, _d in methods],
            "avg": round(sum(nums) / len(nums), 2),
            "spread": max(nums) - min(nums),
            "games": games.get(t, 0),
        }
    order = sorted(table, key=lambda t: table[t]["avg"])
    for i, t in enumerate(order, 1):
        table[t]["rank"] = i
    return table, methods, int(len(df) / 2)


def build(teams):
    df = _played(teams)
    if df.empty:
        return {}, {"live": False, "season": SEASON, "games": 0}

    weeks = sorted(int(w) for w in df.week.unique())
    latest = weeks[-1]

    # A rating for every completed week, so movement is a real comparison of two
    # rankings rather than a number carried over from the last build.
    history = {}
    for w in weeks:
        table, _m, _g = _rate(teams, w)
        if table:
            history[w] = {t: v["rank"] for t, v in table.items()}

    out, methods, games = _rate(teams, latest)
    if not out:
        return {}, {"live": False, "season": SEASON, "games": 0}

    prev = history.get(latest - 1) if latest > 1 else None
    for t, v in out.items():
        was = prev.get(t) if prev else None
        if was:
            # Rank numbers fall as a team climbs, so invert the sign.
            v["move"] = was - v["rank"]
            v["was"] = was
        elif prev:
            v["new"] = True           # played this week, not the week before
        v["history"] = [history[w].get(t) for w in weeks if w in history]

    out_meta = {
        "live": True, "season": SEASON,
        "games": games,
        "week": latest,
        "weeks": weeks,
        "ranked": len(out),
        "unranked": sorted(t for t in teams if t not in out),
        "hasMovement": bool(prev),
        "methods": [{"name": n, "desc": d} for n, _v, d in methods],
    }
    return out, out_meta

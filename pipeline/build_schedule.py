"""
Each team's 2026 schedule.

The schedule file was already being downloaded for coach tenure and last season's
records; the 272 games of the upcoming season sat unused in it. Opponent
difficulty is last season's record, which is the only honest measure available
before anyone has played a snap.
"""
import pandas as pd

SEASON = 2026


def build(teams, last_season_records):
    """last_season_records: team -> {'w':, 'l':, 'record': } from build_teams."""
    s = pd.read_csv("sched.csv", low_memory=False)
    s = s[(s.season == SEASON) & (s.game_type == "REG")]

    out = {}
    for team in teams:
        mine = s[(s.home_team == team) | (s.away_team == team)]
        games = []
        weeks_played = set()
        for _, g in mine.sort_values("week").iterrows():
            home = g.home_team == team
            opp = g.away_team if home else g.home_team
            rec = last_season_records.get(opp, {})
            games.append({
                "wk": int(g.week),
                "opp": opp,
                "home": bool(home),
                "rec": rec.get("record"),
                "w": rec.get("w"),
            })
            weeks_played.add(int(g.week))

        # The bye is the week inside the season that has no game on the slate.
        allw = set(range(1, int(mine.week.max()) + 1)) if len(mine) else set()
        bye = sorted(allw - weeks_played)

        # Strength of schedule: opponents' win total last season.
        wins = [g["w"] for g in games if g["w"] is not None]
        out[team] = {
            "games": games,
            "bye": bye[0] if bye else None,
            "opp_wins": sum(wins) if wins else None,
            "opp_games": len(wins),
        }

    # A league-wide slate, keyed by week. The per-team view above answers "who do
    # we play"; this answers "what is on this weekend", which is what a scores
    # page needs. Built here rather than in the browser so the kickoff times and
    # dates come from the same source as everything else.
    byweek = {}
    for _, g in s.sort_values(["week", "gameday", "gametime"]).iterrows():
        if g.home_team not in teams or g.away_team not in teams:
            continue
        byweek.setdefault(int(g.week), []).append({
            "a": g.away_team, "h": g.home_team,
            "d": g.gameday if isinstance(g.gameday, str) else None,
            "wd": g.weekday if isinstance(g.weekday, str) else None,
            "t": g.gametime if isinstance(g.gametime, str) else None,
        })

    # Rank the slates against each other, 1 = toughest.
    tot = {t: v["opp_wins"] for t, v in out.items() if v["opp_wins"] is not None}
    if tot:
        rk = pd.Series(tot).rank(ascending=False, method="min").astype(int)
        for t, r in rk.items():
            out[t]["sos_rank"] = int(r)
            out[t]["sos_n"] = len(tot)
    return out, byweek

"""
nfelo: an Elo-style NFL model by Robby Greer (nfeloapp.com), published as a
game file in its GitHub repository (greerreNFL/nfelo, output_data/
nfelo_games.csv) and updated through the season. Credited in the app wherever
it is shown.

For every game, including the coming week's, the file carries both teams'
ratings going in (adjusted for quarterback, rest and travel), the model's
win probability and projected spread, and the betting market's opening and
closing lines. Two things come out of it here:

  games    this season's games keyed by week and "AWAY@HOME": the home side's
           win probability, nfelo's spread and the market's spread, both from
           the home side's point of view (negative means home favoured).
  ratings  each team's rating going into its latest game in the file, which is
           its current rating; also used as a fifth power-ranking method.

nfelo uses two older team codes; they are mapped to the app's.
"""
import os

import pandas as pd

SEASON = 2026
PATH = "nfelo_games.csv"
CODES = {"OAK": "LV", "LAR": "LA", "SD": "LAC", "STL": "LA"}


def _load():
    if not (os.path.exists(PATH) and os.path.getsize(PATH) > 50_000):
        return None
    d = pd.read_csv(PATH, low_memory=False)
    parts = d.game_id.astype(str).str.split("_", expand=True)
    if parts.shape[1] < 4:
        return None
    d = d.assign(season=pd.to_numeric(parts[0], errors="coerce"),
                 week=pd.to_numeric(parts[1], errors="coerce"),
                 away=parts[2].map(lambda c: CODES.get(c, c)),
                 home=parts[3].map(lambda c: CODES.get(c, c)))
    return d[d.season == SEASON]


def _num(v, nd):
    return None if pd.isna(v) else round(float(v), nd)


def ratings(teams, through_week=None):
    """Each team's rating going into its latest game up to the week after
    through_week, which is its rating after that week. None when absent."""
    d = _load()
    if d is None or d.empty:
        return None
    if through_week is not None:
        d = d[d.week <= through_week + 1]
    out = {}
    for r in d.sort_values("week").itertuples():
        if r.home in teams:
            out[r.home] = float(r.starting_nfelo_home)
        if r.away in teams:
            out[r.away] = float(r.starting_nfelo_away)
    return out or None


def build(teams):
    d = _load()
    if d is None or d.empty:
        return {}, {"live": False}
    games = {}
    for r in d.itertuples():
        p = r.nfelo_home_probability_close if not pd.isna(r.nfelo_home_probability_close) \
            else r.nfelo_home_probability_open
        s = r.nfelo_home_line_close if not pd.isna(r.nfelo_home_line_close) else r.nfelo_home_line_open
        v = r.home_line_close if not pd.isna(r.home_line_close) else r.home_line_open
        if pd.isna(p):
            continue
        games.setdefault(str(int(r.week)), {})[f"{r.away}@{r.home}"] = [_num(p, 3), _num(s, 1), _num(v, 1)]
    cur = ratings(teams) or {}
    order = sorted(cur, key=lambda t: -cur[t])
    meta = {"live": True, "season": SEASON, "weeks": sorted(int(w) for w in games),
            "games": sum(len(v) for v in games.values()),
            "ratings": {t: [round(cur[t]), i + 1] for i, t in enumerate(order)},
            "credit": "nfelo (nfeloapp.com) by Robby Greer"}
    return games, meta

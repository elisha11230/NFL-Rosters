"""
Builds the team section: record, playoff finish, and offense / defense /
special teams rankings for the 2025 season.

Called by build_data.py. Sources:
  sched.csv            -> record, points for/against, playoff results
  team_2025.csv        -> season offensive + defensive production, kicking
  team_week_2025.csv   -> joined against itself on opponent to get yards allowed
"""
import pandas as pd

SEASON = 2025

# How far each playoff round gets you. Losing in round N is worse than losing
# in round N+1, and winning the Super Bowl tops the list.
ROUND_ORDER = {"WC": 1, "DIV": 2, "CON": 3, "SB": 4}
ROUND_LOST = {
    "WC": "Lost Wild Card",
    "DIV": "Lost Divisional",
    "CON": "Lost Conf. Championship",
    "SB": "Lost Super Bowl",
}


def _rank(series, ascending=False):
    """1 = best. ascending=True when a lower number is better."""
    return series.rank(ascending=ascending, method="min").astype(int)


def build(teams):
    sched = pd.read_csv("sched.csv", low_memory=False)
    sched = sched[(sched.season == SEASON) & sched.home_score.notna()]
    tm = pd.read_csv("team_2025.csv", low_memory=False)
    wk = pd.read_csv("team_week_2025.csv", low_memory=False)
    wk = wk[wk.season_type == "REG"]

    reg = sched[sched.game_type == "REG"]
    post = sched[sched.game_type != "REG"]

    # ---------------------------------------------------------- record
    rec = {t: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0} for t in teams}
    for _, g in reg.iterrows():
        h, a, hs, as_ = g.home_team, g.away_team, g.home_score, g.away_score
        for me, opp, ms, os_ in ((h, a, hs, as_), (a, h, as_, hs)):
            if me not in rec:
                continue
            rec[me]["pf"] += ms
            rec[me]["pa"] += os_
            rec[me]["w" if ms > os_ else "l" if ms < os_ else "t"] += 1

    # ---------------------------------------------------------- playoffs
    finish = {t: "Missed playoffs" for t in teams}
    best = {t: 0 for t in teams}
    for _, g in post.iterrows():
        rnd = g.game_type
        if rnd not in ROUND_ORDER:
            continue
        won = g.home_team if g.home_score > g.away_score else g.away_team
        for t in (g.home_team, g.away_team):
            if t not in finish or ROUND_ORDER[rnd] < best[t]:
                continue
            best[t] = ROUND_ORDER[rnd]
            finish[t] = ("Won Super Bowl" if (rnd == "SB" and t == won)
                         else ROUND_LOST[rnd] if t != won
                         else f"Reached {'Super Bowl' if rnd == 'CON' else 'next round'}")
    # A team that won its CON game reached the Super Bowl, which the SB row
    # then overwrites with the real outcome. Nothing left saying "next round".

    # ---------------------------------------------------------- yards allowed
    # Every weekly row is one team's production in one game. Re-key it by the
    # opponent and it becomes what that opponent's defense gave up.
    off = wk.groupby("team").agg(
        yds_pass=("passing_yards", "sum"),
        yds_rush=("rushing_yards", "sum"),
        turn_lost=("passing_interceptions", "sum"),
    ).reset_index()
    allowed = wk.groupby("opponent_team").agg(
        yds_pass_a=("passing_yards", "sum"),
        yds_rush_a=("rushing_yards", "sum"),
    ).reset_index().rename(columns={"opponent_team": "team"})

    df = tm[tm.season_type == "REG"].merge(off, on="team").merge(allowed, on="team")
    df = df[df.team.isin(teams)].copy()
    df["g"] = df.team.map(lambda t: rec[t]["w"] + rec[t]["l"] + rec[t]["t"])
    df["pf_g"] = df.team.map(lambda t: rec[t]["pf"]) / df.g
    df["pa_g"] = df.team.map(lambda t: rec[t]["pa"]) / df.g
    df["yds_g"] = (df.yds_pass + df.yds_rush) / df.g
    df["yds_a_g"] = (df.yds_pass_a + df.yds_rush_a) / df.g
    df["pass_g"] = df.yds_pass / df.g
    df["rush_g"] = df.yds_rush / df.g
    df["pass_a_g"] = df.yds_pass_a / df.g
    df["rush_a_g"] = df.yds_rush_a / df.g
    df["takeaways"] = df.def_interceptions + df.fumble_recovery_opp
    df["ret_yds"] = df.punt_return_yards + df.kickoff_return_yards
    df["fg_pct"] = df.fg_pct * 100          # nflverse stores this as a fraction

    # ---------------------------------------------------------- unit ranks
    # Offense and defense lead on points, the number people actually argue about.
    # Special teams has no single headline stat, so average four component ranks
    # and rank the averages.
    st_parts = pd.concat([
        _rank(df.fg_pct.fillna(0)),
        _rank(df.special_teams_tds.fillna(0)),
        _rank(df.ret_yds.fillna(0)),
        _rank(df.fg_blocked.fillna(0) + df.pat_blocked.fillna(0), ascending=True),
    ], axis=1)
    df["st_score"] = st_parts.mean(axis=1)

    df["r_off"] = _rank(df.pf_g)
    df["r_def"] = _rank(df.pa_g, ascending=True)
    df["r_st"] = _rank(df.st_score, ascending=True)

    R = {  # label -> (column, lower_is_better)
        "yds_g": ("yds_g", False), "pass_g": ("pass_g", False),
        "rush_g": ("rush_g", False), "pf_g": ("pf_g", False),
        "pa_g": ("pa_g", True), "yds_a_g": ("yds_a_g", True),
        "pass_a_g": ("pass_a_g", True), "rush_a_g": ("rush_a_g", True),
        "def_sacks": ("def_sacks", False), "takeaways": ("takeaways", False),
        "fg_pct": ("fg_pct", False), "ret_yds": ("ret_yds", False),
        "special_teams_tds": ("special_teams_tds", False),
    }
    for key, (col, asc) in R.items():
        df["rk_" + key] = _rank(df[col].fillna(0), ascending=asc)

    # ---------------------------------------------------------- emit
    def line(row, key, label, decimals=1):
        col, _ = R[key]
        v = row[col]
        v = round(float(v), decimals) if decimals else int(v)
        return {"l": label, "v": v, "r": int(row["rk_" + key])}

    out = {}
    for _, r in df.iterrows():
        t = r.team
        w, l, ti = rec[t]["w"], rec[t]["l"], rec[t]["t"]
        out[t] = {
            "record": f"{w}-{l}" + (f"-{ti}" if ti else ""),
            "w": w, "l": l, "t": ti,
            "pf": int(rec[t]["pf"]), "pa": int(rec[t]["pa"]),
            "finish": finish[t],
            "champ": finish[t] == "Won Super Bowl",
            "units": [
                {"name": "Offense", "rank": int(r.r_off), "stats": [
                    line(r, "pf_g", "Points / game"),
                    line(r, "yds_g", "Total yds / game"),
                    line(r, "pass_g", "Pass yds / game"),
                    line(r, "rush_g", "Rush yds / game"),
                ]},
                {"name": "Defense", "rank": int(r.r_def), "stats": [
                    line(r, "pa_g", "Points allowed / game"),
                    line(r, "yds_a_g", "Total yds allowed / game"),
                    line(r, "pass_a_g", "Pass yds allowed / game"),
                    line(r, "rush_a_g", "Rush yds allowed / game"),
                    line(r, "def_sacks", "Sacks", 0),
                    line(r, "takeaways", "Takeaways", 0),
                ]},
                {"name": "Special teams", "rank": int(r.r_st), "stats": [
                    line(r, "fg_pct", "Field goal %"),
                    line(r, "ret_yds", "Return yards", 0),
                    line(r, "special_teams_tds", "Return TDs", 0),
                ]},
            ],
        }
    return out


if __name__ == "__main__":
    import json
    t = pd.read_csv("teams.csv")
    res = build(set(t.team_abbr))
    for k in ["SEA", "NE", "PHI"]:
        print(k, res[k]["record"], "|", res[k]["finish"],
              "| off", res[k]["units"][0]["rank"],
              "def", res[k]["units"][1]["rank"],
              "st", res[k]["units"][2]["rank"])

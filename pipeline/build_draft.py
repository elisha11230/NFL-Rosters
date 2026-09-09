"""
Draft position per player, and how each roster was built.

Three sources are layered because none covers everyone:

  players_master.csv  round, pick, year and drafting team for 1,518 players
  draft_picks.csv     the same for anyone master missed
  roster_2026.csv     `draft_number` for this year's class, whose gsis ids do
                      not exist yet -- draft_picks lists them under placeholder
                      PFR ids like MEN516487, so they are matched on pick number
                      instead, which is unique within a draft

Note draft_picks.csv uses Pro Football Reference team codes (GNB, KAN, LVR),
not nflverse ones. Joining on team without translating silently drops eight
franchises.

The team-level view answers a question the depth chart cannot: how much of this
roster did the club draft itself, and how much did it buy.
"""
import pandas as pd

CURRENT_DRAFT = 2026

# Pro Football Reference codes -> nflverse
PFR_TEAM = {
    "GNB": "GB", "KAN": "KC", "LVR": "LV", "LAR": "LA", "NWE": "NE",
    "NOR": "NO", "SFO": "SF", "TAM": "TB", "OAK": "LV", "SDG": "LAC",
    "STL": "LA", "RAI": "LV", "RAM": "LA", "JAC": "JAX", "ARZ": "ARI",
    "BLT": "BAL", "CLV": "CLE", "HST": "HOU", "SL": "LA", "SD": "LAC",
}


def _norm_team(t):
    if not isinstance(t, str):
        return None
    return PFR_TEAM.get(t, t)


def build(players, depth_rows, master, roster):
    dp = pd.read_csv("draft_picks.csv", low_memory=False)

    # Pick number -> round, for translating this year's class.
    cur = dp[dp.season == CURRENT_DRAFT]
    pick_round = dict(zip(cur.pick, cur["round"]))
    pick_team = {p: _norm_team(t) for p, t in zip(cur.pick, cur.team)}

    by_gsis = dp[dp.gsis_id.notna()].drop_duplicates("gsis_id").set_index("gsis_id")
    rk = roster.set_index("gsis_id") if "gsis_id" in roster.columns else None

    out = {}
    for pid, p in players.items():
        yr = rnd = pick = team = None

        v = master.draft_round.get(pid)
        if pd.notna(v):
            rnd = int(v)
            yr = int(master.draft_year.get(pid)) if pd.notna(master.draft_year.get(pid)) else None
            pk = master.draft_pick.get(pid)
            pick = int(pk) if pd.notna(pk) else None
            team = _norm_team(master.draft_team.get(pid))
        elif pid in by_gsis.index:
            r = by_gsis.loc[pid]
            rnd = int(r["round"]) if pd.notna(r["round"]) else None
            yr = int(r.season) if pd.notna(r.season) else None
            pick = int(r.pick) if pd.notna(r.pick) else None
            team = _norm_team(r.team)
        elif rk is not None and pid in rk.index:
            pk = rk.draft_number.get(pid)
            if pd.notna(pk):
                pick = int(pk)
                rnd = pick_round.get(pick)
                rnd = int(rnd) if rnd is not None and pd.notna(rnd) else None
                team = pick_team.get(pick)
                yr = CURRENT_DRAFT

        if rnd:
            out[pid] = {"rd": rnd, "pk": pick, "yr": yr, "tm": team}
        else:
            out[pid] = {"rd": None}          # undrafted
    return out


def team_summary(draft, players, depth_rows):
    """Per team: how the roster breaks down by round, and how much of it the
    club drafted itself."""
    team_of = {}
    for team, rows in depth_rows.items():
        for r in rows:
            team_of.setdefault(r["pid"], team)

    agg = {}
    for pid, d in draft.items():
        team = team_of.get(pid)
        if not team:
            continue
        a = agg.setdefault(team, {"rounds": {}, "udfa": 0, "own": 0,
                                  "acquired": 0, "total": 0, "capital": 0})
        a["total"] += 1
        if not d["rd"]:
            a["udfa"] += 1
            a["acquired"] += 1          # an undrafted player was signed, not drafted
            continue
        a["rounds"][d["rd"]] = a["rounds"].get(d["rd"], 0) + 1
        if d["tm"] == team:
            a["own"] += 1
        else:
            a["acquired"] += 1
        # Rough draft capital: an early pick is worth more than a late one.
        a["capital"] += max(0, 8 - d["rd"])

    out = {}
    for team, a in agg.items():
        rounds = [{"r": r, "n": a["rounds"][r]} for r in sorted(a["rounds"])]
        out[team] = {
            "rounds": rounds,
            "udfa": a["udfa"],
            "own": a["own"],
            "acquired": a["acquired"],
            "total": a["total"],
            "own_pct": round(a["own"] / max(1, a["total"]) * 100, 1),
            "first": a["rounds"].get(1, 0),
        }

    pct = pd.Series({t: v["own_pct"] for t, v in out.items()})
    rk = pct.rank(ascending=False, method="min").astype(int)
    for t, r in rk.items():
        out[t]["own_rank"] = int(r)
        out[t]["n"] = len(pct)
    return out

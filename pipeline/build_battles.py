"""
Position battles.

The movement tracker answers "who is climbing". This answers the different and
more useful question: "where is the job actually contested".

A battle is scored from the snapshot history at each (team, position):

  flip      the starter changed hands at all -- the strongest signal
  churn     how many distinct players have held the top spot
  recency   how recently the order last moved
  swaps     total reordering among the top three, which catches a spot that is
            unsettled even when the same man keeps ending up first

Scoring on flips alone would miss a job where three players keep trading second
and third while the starter never changes, which is exactly the kind of spot that
resolves in preseason.
"""
import datetime as dt

import pandas as pd

WINDOW_DAYS = 75          # roughly since minicamp
TOP_N = 3                 # how deep to watch for reordering
MAX_PER_TEAM = 5


def _parse(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def build(dc_all, players, teams):
    dc = dc_all[dc_all.gsis_id.notna()].copy()
    snaps = sorted(dc.dt.unique())
    if len(snaps) < 3:
        return {}
    last = _parse(snaps[-1])
    window = [s for s in snaps if (last - _parse(s)).days <= WINDOW_DAYS]
    if len(window) < 3:
        window = snaps[-12:]

    # Thin the history: consecutive snapshots hours apart say nothing new, and
    # comparing every pair would count one change many times over.
    picked, seen_days = [], set()
    for s in window:
        day = s[:10]
        if day not in seen_days:
            seen_days.add(day)
            picked.append(s)
    if picked[-1] != window[-1]:
        picked.append(window[-1])

    sub = dc[dc.dt.isin(picked)]
    # (dt, team, pos) -> ordered list of player ids
    order = {}
    for (d, team, pos), g in sub.groupby(["dt", "team", "pos_abb"], sort=False):
        best = g.groupby("gsis_id").pos_rank.min().sort_values()
        order[(d, team, pos)] = list(best.index[:TOP_N])

    keys = {(t, p) for (_d, t, p) in order}
    out = {}
    for team, pos in keys:
        seq = [(d, order[(d, team, pos)]) for d in picked if (d, team, pos) in order]
        if len(seq) < 3:
            continue
        starters = [s[1][0] for s in seq if s[1]]
        if not starters:
            continue

        holders = []
        for s in starters:
            if not holders or holders[-1] != s:
                holders.append(s)
        flips = len(holders) - 1

        swaps, last_change = 0, None
        for i in range(1, len(seq)):
            if seq[i][1] != seq[i - 1][1]:
                swaps += 1
                last_change = seq[i][0]

        if flips == 0 and swaps < 2:
            continue

        days_since = (last - _parse(last_change)).days if last_change else 999
        score = (flips * 100
                 + len(set(starters)) * 25
                 + swaps * 6
                 + max(0, 40 - days_since))

        current = seq[-1][1]
        contenders = []
        for pid in current:
            p = players.get(pid)
            if not p:
                continue
            contenders.append({
                "pid": pid, "name": p["name"], "num": p["num"],
                "held": starters.count(pid),
            })
        if len(contenders) < 2:
            continue

        out.setdefault(team, []).append({
            "pos": pos,
            "score": score,
            "flips": flips,
            "swaps": swaps,
            "days": days_since,
            "snaps": len(seq),
            "men": contenders,
        })

    for team in out:
        out[team].sort(key=lambda x: -x["score"])
        out[team] = out[team][:MAX_PER_TEAM]
        for b in out[team]:
            b.pop("score", None)
    return out

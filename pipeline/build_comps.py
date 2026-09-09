"""
Player comparables.

For each player, the five most similar others in the league. Similarity is
Euclidean distance over z-scored features, computed inside a position group so a
safety is never compared to a guard.

Features are a mix of physical, usage and production. Each is z-scored within the
bucket before distance, otherwise receiving yards (hundreds) would drown out age
(tens) and height (inches) entirely.

This is deliberately not a projection. It says who a player resembles, which is an
honest thing to compute, rather than what he will do, which is not.
"""
import math

import pandas as pd

TOP_N = 5
MIN_POOL = 12

# feature -> weight. Usage and production carry more than build, because two
# players of the same size in the same position are not alike if one plays every
# snap and the other plays none.
FEATURES = {
    "age": 1.0,
    "height": 0.6,
    "weight": 0.6,
    "snap_pct": 1.4,
    "prod": 1.6,
    "prod2": 1.2,
    "apy": 0.8,
}

# The one or two numbers that define production for each group.
PROD = {
    "QB": ("passing_yards", "passing_tds"),
    "RB": ("rushing_yards", "receptions"),
    "WR": ("receiving_yards", "receptions"),
    "TE": ("receiving_yards", "receptions"),
    "DL": ("def_sacks", "def_tackles_solo"),
    "LB": ("def_tackles_solo", "def_sacks"),
    "DB": ("def_tackles_solo", "def_pass_defended"),
}


def build(players, buckets, master, stats, snaps_by_pid):
    births = master.birth_date.to_dict()
    season = stats.set_index("player_id")

    rows = {}
    for pid, p in players.items():
        b = buckets.get(pid)
        if b not in PROD:
            continue
        f = {}

        bd = births.get(pid)
        if isinstance(bd, str) and len(bd) >= 10:
            try:
                f["age"] = (pd.Timestamp("2026-09-01")
                            - pd.Timestamp(bd[:10])).days / 365.25
            except ValueError:
                pass
        if p.get("ht"):
            f["height"] = float(p["ht"])
        if p.get("wt"):
            f["weight"] = float(p["wt"])
        f["snap_pct"] = float(snaps_by_pid.get(pid, 0))
        if p.get("ct"):
            f["apy"] = float(p["ct"]["apy"])

        c1, c2 = PROD[b]
        if pid in season.index:
            r = season.loc[pid]
            if not isinstance(r, pd.Series):
                r = r.iloc[0]
            f["prod"] = float(r.get(c1) or 0)
            f["prod2"] = float(r.get(c2) or 0)

        # A player with nothing but a height is not comparable to anyone.
        if len([k for k in f if k in ("prod", "prod2", "snap_pct")]) < 2:
            continue
        rows.setdefault(b, {})[pid] = f

    out = {}
    for bucket, pool in rows.items():
        if len(pool) < MIN_POOL:
            continue
        ids = list(pool)
        # z-score each feature across the pool
        stat = {}
        for feat in FEATURES:
            vals = [pool[i][feat] for i in ids if feat in pool[i]]
            if len(vals) < MIN_POOL:
                continue
            mu = sum(vals) / len(vals)
            sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals)) or 1.0
            stat[feat] = (mu, sd)

        vec = {}
        for i in ids:
            vec[i] = {f: (pool[i][f] - stat[f][0]) / stat[f][1]
                      for f in stat if f in pool[i]}

        for i in ids:
            vi = vec[i]
            best = []
            for j in ids:
                if j == i:
                    continue
                vj = vec[j]
                shared = [f for f in vi if f in vj]
                if len(shared) < 3:
                    continue
                d = math.sqrt(sum(FEATURES[f] * (vi[f] - vj[f]) ** 2
                                  for f in shared) / len(shared))
                best.append((d, j))
            if not best:
                continue
            best.sort()
            out[i] = [{"pid": j, "d": round(d, 2)} for d, j in best[:TOP_N]]
    return out

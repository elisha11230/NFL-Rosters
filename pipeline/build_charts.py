"""
Where a player actually works: target charts for receivers, gap charts for backs.

A stat line says a receiver had 1,100 yards. It does not say he lives fifteen
yards downfield on the sideline while the man opposite him works underneath in
the middle. That is a player's role, and it is visible in the play-by-play
because every pass carries a depth and a third of the field, and every run
carries a direction and a gap.

Targets are stored as individual points because the shape of the scatter is the
information. Runs are aggregated into the nine location/gap buckets, since there
are only nine and a cloud of dots would say less than a grid.

Compact by design: a target is [air_yards, direction, flags], three small numbers,
because a busy receiver has well over a hundred of them.
"""
import pandas as pd

SEASON = 2025
MIN_TARGETS = 12
MIN_CARRIES = 20

DIRECTION = {"left": 0, "middle": 1, "right": 2}
GAPS = ["end", "tackle", "guard"]          # outside to inside

COLUMNS = ["play_type", "pass_location", "air_yards", "complete_pass",
           "touchdown", "yards_gained", "receiver_player_id",
           "rusher_player_id", "run_location", "run_gap", "interception"]


def build(player_ids, pbp=None, path="pbp2025.parquet"):
    p = pbp if pbp is not None else pd.read_parquet(path, columns=COLUMNS)

    # ---------------------------------------------------------- targets
    rec = p[p.receiver_player_id.notna()
            & p.receiver_player_id.isin(player_ids)
            & p.air_yards.notna()
            & p.pass_location.notna()]

    targets = {}
    for pid, g in rec.groupby("receiver_player_id", sort=False):
        if len(g) < MIN_TARGETS:
            continue
        pts = []
        for _, r in g.iterrows():
            # flags: 1 caught, 2 touchdown, 4 intercepted
            f = 0
            if r.complete_pass == 1:
                f |= 1
            if r.touchdown == 1:
                f |= 2
            if r.interception == 1:
                f |= 4
            pts.append([int(r.air_yards), DIRECTION.get(r.pass_location, 1), f])
        caught = sum(1 for x in pts if x[2] & 1)
        depths = [x[0] for x in pts]
        targets[pid] = {
            "pts": pts,
            "n": len(pts),
            "c": caught,
            # Average depth of target is the single number that summarises a
            # scatter, so it rides along rather than being recomputed in the app.
            "adot": round(sum(depths) / len(depths), 1),
            "deep": sum(1 for d in depths if d >= 20),
        }

    # ---------------------------------------------------------- runs
    run = p[p.rusher_player_id.notna()
            & p.rusher_player_id.isin(player_ids)
            & p.run_location.notna()]

    runs = {}
    for pid, g in run.groupby("rusher_player_id", sort=False):
        if len(g) < MIN_CARRIES:
            continue
        cells = {}
        for _, r in g.iterrows():
            gap = r.run_gap if isinstance(r.run_gap, str) else "middle"
            key = f"{r.run_location}|{gap}"
            c = cells.setdefault(key, {"n": 0, "y": 0, "td": 0})
            c["n"] += 1
            c["y"] += int(r.yards_gained or 0)
            if r.touchdown == 1:
                c["td"] += 1
        out = []
        for key, c in cells.items():
            loc, gap = key.split("|")
            out.append({
                "loc": DIRECTION.get(loc, 1), "gap": gap,
                "n": c["n"], "avg": round(c["y"] / c["n"], 1), "td": c["td"],
            })
        out.sort(key=lambda x: -x["n"])
        runs[pid] = {"cells": out, "n": int(len(g)),
                     "avg": round(float(g.yards_gained.sum()) / len(g), 1)}

    return targets, runs

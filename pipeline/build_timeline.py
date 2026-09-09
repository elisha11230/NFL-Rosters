"""
The depth chart as it looked each week of the offseason.

The release holds 140 snapshots going back to March and the app has only ever
rendered the newest one. This keeps a weekly sample so the field can be scrubbed
through time.

Stored as a baseline plus per-week diffs. Storing every week in full costs about
1MB; only a fraction of slots change from one week to the next, so recording just
those brings it to roughly 0.16MB for the same information.

Weekly rather than daily on purpose: consecutive daily snapshots are mostly
identical, and a slider with 140 stops that mostly do nothing is worse than one
with 23 that each mean something.
"""
import datetime as dt

import pandas as pd

DEPTH = 4          # how many names to keep per slot


def _parse(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def build(dc_all, player_ids):
    dc = dc_all[dc_all.gsis_id.notna()]
    snaps = sorted(dc.dt.unique())
    if len(snaps) < 3:
        return None

    # One sample per ISO week, plus the newest snapshot whatever week it is in.
    picked, seen = [], set()
    for s in snaps:
        wk = _parse(s).isocalendar()[:2]
        if wk not in seen:
            seen.add(wk)
            picked.append(s)
    if picked[-1] != snaps[-1]:
        picked.append(snaps[-1])

    sub = dc[dc.dt.isin(picked)]
    frames = {}
    for (d, team, grp, slot), g in sub.groupby(
            ["dt", "team", "pos_grp", "pos_slot"], sort=False):
        ids = [p for p in g.sort_values("pos_rank").gsis_id[:DEPTH]
               if p in player_ids]
        if ids:
            frames.setdefault(d, {}).setdefault(team, {}) \
                  .setdefault(grp, {})[str(int(slot))] = ids

    dates = [d for d in picked if d in frames]
    if len(dates) < 2:
        return None

    baseline = frames[dates[0]]
    diffs, prev = [], baseline
    for d in dates[1:]:
        cur = frames[d]
        change = {}
        for team, grps in cur.items():
            for grp, slots in grps.items():
                for slot, ids in slots.items():
                    if prev.get(team, {}).get(grp, {}).get(slot) != ids:
                        change.setdefault(team, {}).setdefault(grp, {})[slot] = ids
        diffs.append(change)
        prev = cur

    return {
        "dates": [d[:10] for d in dates],
        "base": baseline,
        "diffs": diffs,
    }

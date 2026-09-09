"""
Depth chart movement.

The depth chart release is not a current snapshot -- it is 132 snapshots going
back to March, and the app was reading only the newest one. This module diffs the
newest against earlier ones to answer the question that actually matters in July:
who is climbing.

Movement is measured per (team, position) rather than per formation slot, because
receivers are ranked across the whole group and their slot assignment shuffles as
the order changes. Comparing rank within a position is stable; comparing within a
slot is not.
"""
import datetime as dt
import pandas as pd

WINDOWS = [("2w", 14), ("season", None)]   # None = first snapshot of the year


def _parse(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def _nearest(snaps, target):
    return min(snaps, key=lambda s: abs((_parse(s) - target).total_seconds()))


def build(dc_all, player_ids):
    """dc_all: the full depth chart frame, every snapshot."""
    snaps = sorted(dc_all.dt.unique())
    latest = snaps[-1]
    last_t = _parse(latest)

    def rank_map(snapshot):
        f = dc_all[dc_all.dt == snapshot]
        f = f[f.gsis_id.notna()]
        # A player can hold several posts (RB and KR). Keep his best rank at each
        # position; that is the one that describes his standing there.
        g = f.groupby(["gsis_id", "team", "pos_abb"]).pos_rank.min()
        return g.to_dict()

    now = rank_map(latest)
    refs = {}
    for label, days in WINDOWS:
        snap = snaps[0] if days is None else _nearest(snaps, last_t - dt.timedelta(days=days))
        refs[label] = (rank_map(snap), snap)

    out = {}
    for (pid, team, pos), rank_now in now.items():
        if pid not in player_ids:
            continue
        entry = {}
        for label, (past, _snap) in refs.items():
            was = past.get((pid, team, pos))
            if was is None:
                entry[label] = {"new": True}
            elif was != rank_now:
                # Lower rank number is better, so a drop in number is a rise.
                entry[label] = {"d": int(was - rank_now), "from": int(was)}
        if not entry:
            continue
        prev = out.get(pid)
        # Keep whichever position shows the larger recent move, so a chip shows
        # the change a person would actually care about.
        score = abs(entry.get("2w", {}).get("d", 0))
        if prev is None or score > prev["_score"]:
            out[pid] = {"pos": pos, "_score": score, **entry}

    for v in out.values():
        v.pop("_score", None)

    meta = {label: {"snapshot": snap, "days": days}
            for (label, days), (_, snap) in
            zip(WINDOWS, (refs[l] for l, _ in WINDOWS))}
    return out, meta


def summarise(movement, depth_rows, players):
    """Per team: the biggest risers, so the team panel can lead with them."""
    team_of = {}
    for team, rows in depth_rows.items():
        for r in rows:
            team_of.setdefault(r["pid"], team)

    by_team = {}
    for pid, m in movement.items():
        team = team_of.get(pid)
        if not team:
            continue
        two = m.get("2w") or {}
        season = m.get("season") or {}
        d = two.get("d") or season.get("d") or 0
        if d <= 0 and not (two.get("new") or season.get("new")):
            continue
        by_team.setdefault(team, []).append({
            "pid": pid,
            "name": players[pid]["name"],
            "pos": m["pos"],
            "d": d,
            "new": bool(two.get("new") or season.get("new")),
            "recent": "2w" in m,
        })

    for team, lst in by_team.items():
        lst.sort(key=lambda x: (-int(x["recent"]), -x["d"]))
        by_team[team] = lst[:6]
    return by_team

"""
This season week by week: form, player of the game, and the rookie class.

From nflverse's weekly player stats (stats_week_2026.csv, one row per player
per game), last season's (stats_week_2025.csv) for a baseline, and snap counts
(snaps_2026.csv). Three things come out of it:

  form      each player's games this season with a one-line summary and a
            points figure, and whether he is running hot or cold: his last
            three games against the ten before them (reaching back into last
            season early on), so a role player's normal week does not read
            as a slump.
  pog       the player of the game for every finished game: the best single
            game by points, either side of the ball.
  rookies   every rookie's snap share, games and points this season, and
            where that production ranks among rookies at his position next
            to where he was drafted among them.

Points: PPR fantasy points for the offence, because they weigh yards,
touchdowns and catches in a way most fans already read; for defenders a
simple defensive score in the same spirit (a sack 4, an interception 6, a
solo tackle 1). Kickers, punters and linemen have no points; linemen are
measured by snaps.
"""
import os

import pandas as pd

SEASON = 2026
CUR, PREV, SNAPS = "stats_week_2026.csv", "stats_week_2025.csv", "snaps_2026.csv"
SNAPS_PREV = "snaps.csv"   # last season's snap counts, already downloaded for other pages
MIN_SHARE = 0.25           # a game he played less of than this (left hurt, rested) is not form

RECENT = 3            # games that make up "lately"
BASE = 10             # games before those to compare against
MIN_BASE_GAMES = 4
MIN_BASE_PTS = 6.0    # below this a player's role is too small to run hot or cold
HOT, COLD = 1.35, 0.65
MIN_SWING = 4.0       # and the difference must be at least this many points

DEF_POS = {"DL", "LB", "DB", "DE", "DT", "CB", "S", "OLB", "ILB", "MLB", "NT", "FS", "SS", "EDGE"}
NO_POINTS = {"OL", "T", "G", "C", "K", "P", "LS"}
GROUP = {"QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "OL": "OL", "T": "OL", "G": "OL", "C": "OL",
         "DL": "DL", "DE": "DL", "DT": "DL", "NT": "DL", "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB",
         "DB": "DB", "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "K": "K", "P": "P", "LS": "LS"}


def _n(v):
    try:
        return 0.0 if pd.isna(v) else float(v)
    except (TypeError, ValueError):
        return 0.0


def def_points(r):
    return (_n(r.def_tackles_solo) + 0.5 * _n(r.def_tackle_assists) + _n(r.def_tackles_for_loss)
            + 4 * _n(r.def_sacks) + 6 * _n(r.def_interceptions) + 1.5 * _n(r.def_pass_defended)
            + 3 * _n(r.def_fumbles_forced) + 3 * _n(r.fumble_recovery_opp) + 6 * _n(r.def_tds)
            + 2 * _n(r.def_safeties))


def points(r):
    """A game's points for whichever side of the ball he played."""
    return max(_n(r.fantasy_points_ppr), def_points(r))


def _i(v):
    return int(round(_n(v)))


def line(r):
    """One game in a few words, built from what he actually did."""
    bits = []
    if _n(r.attempts) >= 5:
        b = f"{_i(r.completions)}/{_i(r.attempts)}, {_i(r.passing_yards)} yds"
        if _n(r.passing_tds): b += f", {_i(r.passing_tds)} TD"
        if _n(r.passing_interceptions): b += f", {_i(r.passing_interceptions)} INT"
        bits.append(b)
        if _n(r.rushing_yards) >= 20 or _n(r.rushing_tds):
            bits.append(f"{_i(r.rushing_yards)} rush" + (f", {_i(r.rushing_tds)} TD" if _n(r.rushing_tds) else ""))
        return " · ".join(bits)
    if _n(r.carries) >= 3:
        b = f"{_i(r.carries)} car, {_i(r.rushing_yards)} yds"
        if _n(r.rushing_tds): b += f", {_i(r.rushing_tds)} TD"
        bits.append(b)
    if _n(r.receptions) or _n(r.targets) >= 2:
        b = f"{_i(r.receptions)} rec, {_i(r.receiving_yards)} yds"
        if _n(r.receiving_tds): b += f", {_i(r.receiving_tds)} TD"
        bits.append(b)
    if bits:
        return " · ".join(bits)
    tk = _n(r.def_tackles_solo) + _n(r.def_tackle_assists)
    d = []
    if tk: d.append(f"{_i(tk)} tkl")
    if _n(r.def_sacks): d.append(f"{_n(r.def_sacks):g} sack" + ("s" if _n(r.def_sacks) != 1 else ""))
    if _n(r.def_interceptions): d.append(f"{_i(r.def_interceptions)} INT")
    if _n(r.def_pass_defended): d.append(f"{_i(r.def_pass_defended)} PD")
    if _n(r.def_fumbles_forced): d.append(f"{_i(r.def_fumbles_forced)} FF")
    if _n(r.def_tds): d.append(f"{_i(r.def_tds)} TD")
    if d:
        return ", ".join(d)
    if _n(r.fg_att):
        return f"{_i(r.fg_made)}/{_i(r.fg_att)} FG"
    return ""


def _reg(path):
    if not (os.path.exists(path) and os.path.getsize(path) > 2_000):
        return None
    d = pd.read_csv(path, low_memory=False)
    return d[d.season_type == "REG"] if "season_type" in d else d


def _snap_games(path, pfr2gsis, season):
    """Share of the snaps he played in each game, keyed (gsis id, season, week)."""
    if not (os.path.exists(path) and os.path.getsize(path) > 2_000):
        return None, {}
    sn = pd.read_csv(path, low_memory=False)
    sn = sn[sn.game_type == "REG"] if "game_type" in sn else sn
    sn = sn.assign(gid=sn.pfr_player_id.map(pfr2gsis),
                   share=sn[["offense_pct", "defense_pct"]].fillna(0).max(axis=1))
    sn = sn[sn.gid.notna()]
    return sn, {(r.gid, season, int(r.week)): float(r.share) for r in sn.itertuples()}


def build(players, master):
    cur = _reg(CUR)
    if cur is None or cur.empty:
        return {}, {}, {}, {"live": False}
    prev = _reg(PREV)
    cur = cur[cur.player_id.isin(players)].copy()
    cur["pts"] = cur.apply(points, axis=1)
    cur["line"] = cur.apply(line, axis=1)
    weeks = int(cur.week.max())

    # ---- player of the game: the best single game, either side of the ball
    pog = {}
    for gid, g in cur.groupby("game_id"):
        top = g.sort_values("pts", ascending=False).iloc[0]
        if top.pts < 8:
            continue
        parts = str(gid).split("_")           # 2026_01_ARI_LAC: away, then home
        if len(parts) < 4:
            continue
        pog.setdefault(str(int(top.week)), {})[f"{parts[2]}@{parts[3]}"] = {
            "pid": top.player_id, "t": top.team, "pts": round(float(top.pts), 1), "x": top.line}

    pfr2gsis = {v: k for k, v in master.pfr_id.dropna().items()} if "pfr_id" in master else {}
    sn_cur, share = _snap_games(SNAPS, pfr2gsis, SEASON)
    _, share_prev = _snap_games(SNAPS_PREV, pfr2gsis, SEASON - 1)
    share.update(share_prev)

    # ---- form
    hist = cur[["player_id", "season", "week", "pts"]]
    if prev is not None:
        p2 = prev[prev.player_id.isin(players)].copy()
        p2["pts"] = p2.apply(points, axis=1)
        hist = pd.concat([p2[["player_id", "season", "week", "pts"]], hist])
    hist = hist.sort_values(["season", "week"])
    # Games he barely played (left hurt, rested) say nothing about form. Without
    # snap counts for a game it is kept.
    hist = hist[[share.get((r.player_id, int(r.season), int(r.week)), 1.0) >= MIN_SHARE
                 for r in hist.itertuples()]]
    form = {}
    for pid, g in cur.sort_values("week").groupby("player_id"):
        pos = str(players[pid].get("pos") or "")
        if pos in NO_POINTS:
            continue
        rec = {"w": [[int(r.week), r.opponent_team, round(float(r.pts), 1), r.line] for r in g.itertuples()]}
        hp = hist[hist.player_id == pid]
        h = hp.pts.tolist()
        recent_cur = int((hp.season == SEASON).sum())
        if recent_cur >= RECENT and len(h) >= RECENT + MIN_BASE_GAMES:
            recent, base = h[-RECENT:], h[-RECENT - BASE:-RECENT]
            ra, ba = sum(recent) / len(recent), sum(base) / len(base)
            rec.update(r=round(ra, 1), b=round(ba, 1), bn=len(base))
            if ba >= MIN_BASE_PTS:
                if ra >= ba * HOT and ra - ba >= MIN_SWING:
                    rec["s"] = "hot"
                elif ra <= ba * COLD and ba - ra >= MIN_SWING:
                    rec["s"] = "cold"
        form[pid] = rec

    # ---- rookies
    snap = {}
    if sn_cur is not None:
        for gid, g in sn_cur.groupby("gid"):
            if gid in players:
                snap[gid] = {"g": int(len(g)), "sn": round(float(g.share.mean()) * 100),
                             "st": round(float(g.st_pct.fillna(0).mean()) * 100)}
    tot = cur.groupby("player_id").pts.sum()
    rook = {pid: p for pid, p in players.items() if p.get("rook")}
    rows = {}
    for pid, p in rook.items():
        s = snap.get(pid, {})
        rows[pid] = {"grp": GROUP.get(str(p.get("pos") or ""), "Other"),
                     "pts": round(float(tot.get(pid, 0.0)), 1),
                     "g": s.get("g", int((cur.player_id == pid).sum())),
                     "sn": s.get("sn"), "st": s.get("st")}
    # Rank by production within the position group (linemen by snap share),
    # next to where each was drafted among the rookies at that position.
    by = {}
    for pid, r in rows.items():
        by.setdefault(r["grp"], []).append(pid)
    for grp, ids in by.items():
        key = (lambda i: (rows[i]["sn"] or 0)) if grp == "OL" else (lambda i: rows[i]["pts"])
        played = [i for i in ids if rows[i]["g"]]
        for rank, i in enumerate(sorted(played, key=key, reverse=True), 1):
            rows[i]["pr"] = rank
        picks = sorted(ids, key=lambda i: players[i].get("pick") or 999)
        for rank, i in enumerate(picks, 1):
            rows[i]["dk"] = rank
        for i in ids:
            rows[i]["n"] = len(ids)
    meta = {"live": True, "season": SEASON, "weeks": weeks, "form": len(form),
            "hot": sum(1 for v in form.values() if v.get("s") == "hot"),
            "cold": sum(1 for v in form.values() if v.get("s") == "cold"),
            "games": sum(len(v) for v in pog.values()), "rookies": len(rows),
            "recent": RECENT, "base": BASE}
    return form, pog, rows, meta

"""
FTN charting: what a person watching every play records that the box score
cannot. Drops, contested and catchable balls, interception-worthy throws, play
action, blitzes, throws from outside the pocket.

From nflverse's copy of FTN Data's charting (CC-BY-SA 4.0: the app credits
"FTN Data via nflverse" wherever it is shown). Each charted play is joined to
the nflverse play-by-play on game and play id, which says who threw, who was
targeted, and what the play was worth in expected points.

Per player, season to date. As with Next Gen Stats, a league rank needs enough
volume, scaled to the weeks played. Team rates (play action, motion, blitzing)
feed the Charting leaderboards.
"""
import os

import pandas as pd

SEASON = 2026
FTN = "ftn_2026.parquet"
PBP = "pbp2026.parquet"
QB_PER_WEEK = 12        # dropbacks
REC_PER_WEEK = 3.5      # targets
CONTESTED_MIN = 5       # contested targets before a contested-catch rate means much


def _b(s):
    return s.fillna(False).astype(bool)


def _rank(values, v, higher_better):
    vals = [x for x in values if x is not None]
    if v is None or len(vals) < 8:
        return None, None
    r = sum(1 for x in vals if (x > v if higher_better else x < v)) + 1
    return r, len(vals)


def build(players, team_abbrs):
    if not (os.path.exists(FTN) and os.path.exists(PBP)):
        return {}, {}, {"live": False}
    f = pd.read_parquet(FTN)
    p = pd.read_parquet(PBP, columns=["game_id", "play_id", "week", "posteam", "defteam",
                                      "passer_player_id", "receiver_player_id", "qb_dropback",
                                      "pass_attempt", "complete_pass", "epa", "play_type"])
    if f.empty:
        return {}, {}, {"live": False}
    f = f.copy()
    f["play_id"] = pd.to_numeric(f.nflverse_play_id, errors="coerce")
    p["play_id"] = pd.to_numeric(p.play_id, errors="coerce")
    m = f.merge(p, left_on=["nflverse_game_id", "play_id"], right_on=["game_id", "play_id"], how="inner")
    weeks = int(m.week_x.max()) if "week_x" in m else int(m.week.max())

    # ---- quarterbacks, per dropback
    db = m[(m.qb_dropback == 1) & m.passer_player_id.isin(players)].copy()
    db["blitz"] = db.n_blitzers.fillna(0) > 0
    qb = {}
    for pid, g in db.groupby("passer_player_id"):
        att = g[g.pass_attempt == 1]
        bl = g[g.blitz]
        qb[pid] = {
            "db": int(len(g)),
            "pa": round(_b(g.is_play_action).mean() * 100, 1),
            "blz": round(g.blitz.mean() * 100, 1),
            "epab": round(bl.epa.mean(), 2) if len(bl) >= 8 else None,
            "iw": int(_b(att.is_interception_worthy).sum()),
            "iwr": round(_b(att.is_interception_worthy).mean() * 100, 1) if len(att) else None,
            "oop": round(_b(g.is_qb_out_of_pocket).mean() * 100, 1),
            "ta": int(_b(g.is_throw_away).sum()),
            "qfs": int(_b(g.is_qb_fault_sack).sum()),
        }
    need_qb = QB_PER_WEEK * weeks
    qual = {k: v for k, v in qb.items() if v["db"] >= need_qb}
    # key: higher is better (None = rank by most)
    QB_RANK = {"pa": None, "blz": None, "epab": True, "iwr": False, "oop": None}

    # ---- receivers, per target
    tg = m[(m.pass_attempt == 1) & m.receiver_player_id.isin(players)].copy()
    rec = {}
    for pid, g in tg.groupby("receiver_player_id"):
        catchable = _b(g.is_catchable_ball)
        contested = _b(g.is_contested_ball)
        drops = int(_b(g.is_drop).sum())
        ct = int(contested.sum())
        rec[pid] = {
            "tg": int(len(g)),
            "drop": drops,
            "dropr": round(drops / catchable.sum() * 100, 1) if catchable.sum() else None,
            "ctg": ct,
            "ccr": round(((g.complete_pass == 1) & contested).sum() / ct * 100, 1) if ct >= CONTESTED_MIN else None,
            "cre": int(_b(g.is_created_reception).sum()),
            "cat": round(catchable.mean() * 100, 1),
        }
    need_rec = REC_PER_WEEK * weeks
    qual_rec = {k: v for k, v in rec.items() if v["tg"] >= need_rec}
    REC_RANK = {"dropr": False, "ccr": True, "cre": True, "cat": True}

    out = {}
    for pid, v in qb.items():
        mm = {}
        for k in ("pa", "blz", "epab", "iwr", "oop", "iw", "ta", "qfs"):
            r = n = None
            if k in QB_RANK and pid in qual:
                hb = QB_RANK[k]
                r, n = _rank([q[k] for q in qual.values()], v[k], True if hb is None else hb)
            mm[k] = [v[k], r, n]
        out.setdefault(pid, {"s": SEASON})["qb"] = {"vol": v["db"], "m": mm}
    for pid, v in rec.items():
        mm = {}
        for k in ("drop", "dropr", "ctg", "ccr", "cre", "cat"):
            r = n = None
            if k in REC_RANK and pid in qual_rec and v[k] is not None:
                pool = [q[k] for q in qual_rec.values() if q[k] is not None]
                r, n = _rank(pool, v[k], REC_RANK[k])
            mm[k] = [v[k], r, n]
        out.setdefault(pid, {"s": SEASON})["rec"] = {"vol": v["tg"], "m": mm}

    # ---- teams
    teams = {}
    off = m[m.qb_dropback == 1]
    plays = m[m.play_type.isin(["pass", "run"])]
    for t in team_abbrs:
        o = off[off.posteam == t]
        allp = plays[plays.posteam == t]
        d = off[off.defteam == t]
        if not len(allp):
            continue
        teams[t] = {
            "pa": round(_b(o.is_play_action).mean() * 100, 1) if len(o) else None,
            "mot": round(_b(allp.is_motion).mean() * 100, 1),
            "nh": round(_b(allp.is_no_huddle).mean() * 100, 1),
            "blz": round((d.n_blitzers.fillna(0) > 0).mean() * 100, 1) if len(d) else None,
            "rush": round(d.n_pass_rushers.dropna().mean(), 2) if len(d) else None,
        }
    meta = {"live": True, "season": SEASON, "weeks": weeks,
            "need": {"qb": need_qb, "rec": round(need_rec)}, "players": len(out),
            "credit": "FTN Data via nflverse (CC-BY-SA 4.0)"}
    return out, teams, meta

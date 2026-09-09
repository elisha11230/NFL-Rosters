"""
Builds nfl_data.json for the depth chart app.

Sources (all free, all from nflverse):
  depth_charts_2026.csv  -> formation slots + depth order
  roster_2026.csv        -> jersey numbers, headshots, bio
  stats_player_reg_2025  -> last season's stats
  teams_colors_logos.csv -> team colors

Run this again any time to refresh. Nothing here needs an API key.
"""
import gc
import json
import re
import pandas as pd
from top100 import (TOP100, TOP100_PREV, TOP100_2026_META, ALIASES,
                    NOT_ON_ROSTER, CURRENT_YEAR as T100_YEAR,
                    PREV_YEAR as T100_PREV_YEAR)

OUT = "nfl_data.json"

# ---------------------------------------------------------------- load

# Read once and keep both views: the full history feeds movement and battles,
# the newest snapshot feeds everything else. Re-reading this 38MB file per
# consumer is what pushed the build past the container's memory limit.
DC_ALL = pd.read_csv("depth_charts_2026.csv", low_memory=False)
dc = DC_ALL[DC_ALL.dt == DC_ALL.dt.max()].copy()   # newest snapshot only
snapshot = dc.dt.max()

roster = pd.read_csv("roster_2026.csv", low_memory=False)
roster = roster.sort_values("week").groupby("gsis_id", as_index=False).last()

# The season roster is a snapshot and lags signings, so ~110 players who appear
# on a current depth chart are missing from it. The master players table covers
# every player nflverse knows about; use it to fill those gaps.
master = pd.read_csv("players_master.csv", low_memory=False)
master = master[master.gsis_id.notna()].set_index("gsis_id")
MASTER = {
    "pos": master.position.to_dict(),
    # ESPN's athlete id, so a live box score can be matched to a player on the
    # chart. Every player currently resolves, which is why live stats can land
    # on the field rather than in a separate table.
    "espn": master.espn_id.to_dict(),
    "num": master.jersey_number.to_dict(),
    "img": master.headshot.to_dict(),
    "ht": master.height.to_dict(),
    "wt": master.weight.to_dict(),
    "col": master.college_name.to_dict(),
    "exp": master.years_of_experience.to_dict(),
    "name": master.display_name.to_dict(),
}

stats = pd.read_csv("stats_2025.csv", low_memory=False)
teams = pd.read_csv("teams.csv")
teams = teams[teams.team_abbr.isin(dc.team.unique())]

# Where each player was last season, so we can flag anyone who moved. Take the
# last week they appear, which is their end-of-season team after any trade.
prev = pd.read_csv("roster_2025.csv", low_memory=False)
prev = prev.sort_values("week").groupby("gsis_id", as_index=False).last()
PREV_TEAM = dict(zip(prev.gsis_id, prev.team))

# Draft position for the 2026 class lives in this season's roster; the master
# players table has not been backfilled with 2026 rounds yet.
DRAFT_PICK = {r.gsis_id: r.draft_number for _, r in roster.iterrows()
              if not pd.isna(r.get("draft_number"))}
ROOKIE_YEAR = master.rookie_season.to_dict()

# ---------------------------------------------------------------- top 100

def norm(n):
    n = re.sub(r"[^a-z ]", "", str(n).lower())
    return re.sub(r"\s+", " ", n).strip()

top100, top100_prev = {}, {}
for rank, name in TOP100.items():
    top100.setdefault(norm(name), []).append(rank)
for rank, name in TOP100_PREV.items():
    top100_prev[norm(name)] = rank
for alias, real in ALIASES.items():
    if norm(real) in top100:
        top100[norm(alias)] = top100[norm(real)]
    if norm(real) in top100_prev:
        top100_prev[norm(alias)] = top100_prev[norm(real)]

# Position families, for judging whether a player could be the man on the list.
# EDGE spans ends and stand-up rushers, which sources file as DE, OLB or LB.
_T100_FAMILY = {
    "QB": {"QB"}, "RB": {"RB", "FB"}, "WR": {"WR"}, "TE": {"TE"},
    "OT": {"T", "OT", "OL"}, "OG": {"G", "OG", "OL"}, "C": {"C", "OL"},
    "EDGE": {"DE", "OLB", "LB", "EDGE", "DL"}, "DL": {"DT", "NT", "DL", "DE"},
    "LB": {"LB", "ILB", "MLB", "OLB"}, "CB": {"CB", "DB"},
    "S": {"S", "SS", "FS", "DB"}, "DB": {"DB", "CB", "S", "SS", "FS"},
}


def _t100_score(rk, pos, team):
    want_pos, want_team = TOP100_2026_META.get(rk, (None, None))
    score = 0
    if want_team and team and want_team == team:
        score += 2
    if want_pos and pos and pos in _T100_FAMILY.get(want_pos, {want_pos}):
        score += 1
    return score


def assign_top100(players, team_of):
    """Give each of the 100 entries to exactly one player.

    Names are not unique in this league. Cleveland have a rookie linebacker
    called Justin Jefferson, and there is a Byron Young on the Rams and another
    in Philadelphia. Scoring each player independently badges both, because both
    look plausible on their own -- so the candidates for a rank are compared
    against each other and only the best takes it.
    """
    candidates = {}
    for pid, p in players.items():
        ranks = top100.get(norm(p["name"]))
        if not ranks:
            continue
        if isinstance(ranks, int):
            ranks = [ranks]
        for rk in ranks:
            candidates.setdefault(rk, []).append(
                (_t100_score(rk, p["pos"], team_of.get(pid)), pid))

    for rk, cands in candidates.items():
        cands.sort(key=lambda c: c[0], reverse=True)
        best_score, best_pid = cands[0]
        if best_score <= 0:
            continue                 # nobody plausible; leave the entry unmatched
        players[best_pid]["t100"] = rk
        prev = top100_prev.get(norm(players[best_pid]["name"]))
        players[best_pid]["t100p"] = prev if isinstance(prev, int) else None

# ---------------------------------------------------------------- stat lines
# Which stats to surface, per position group, and whether high = good.

STAT_SETS = {
    "QB": [("passing_yards", "Pass yds"), ("passing_tds", "Pass TD"),
           ("passing_interceptions", "INT"), ("rushing_yards", "Rush yds"),
           ("rushing_tds", "Rush TD")],
    "RB": [("rushing_yards", "Rush yds"), ("rushing_tds", "Rush TD"),
           ("carries", "Carries"), ("receptions", "Rec"),
           ("receiving_yards", "Rec yds")],
    "WR": [("receptions", "Rec"), ("receiving_yards", "Rec yds"),
           ("receiving_tds", "Rec TD"), ("targets", "Targets")],
    "TE": [("receptions", "Rec"), ("receiving_yards", "Rec yds"),
           ("receiving_tds", "Rec TD"), ("targets", "Targets")],
    "DL": [("def_sacks", "Sacks"), ("def_tackles_solo", "Solo tkl"),
           ("def_qb_hits", "QB hits"), ("def_tackles_for_loss", "TFL")],
    "LB": [("def_tackles_solo", "Solo tkl"), ("def_sacks", "Sacks"),
           ("def_tackles_for_loss", "TFL"), ("def_pass_defended", "PD")],
    "DB": [("def_tackles_solo", "Solo tkl"), ("def_pass_defended", "PD"),
           ("def_interceptions", "INT"), ("def_tackles_for_loss", "TFL")],
    "K":  [("fg_made", "FG made"), ("fg_att", "FG att"),
           ("fg_pct", "FG%"), ("fg_long", "Long")],
    "P":  [("punt_returns", "Ret"), ("punt_return_yards", "Ret yds")],
}
LOWER_IS_BETTER = {"passing_interceptions"}

# Group nflverse positions into our stat buckets. None = no meaningful box score
# (offensive linemen, long snappers).
POS_BUCKET = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
    "T": None, "G": None, "C": None, "OL": None, "OT": None, "OG": None,
    "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
    "CB": "DB", "S": "DB", "SS": "DB", "FS": "DB", "DB": "DB",
    "K": "K", "PK": "K", "P": "P", "LS": None,
    # Depth-chart abbreviations. Without these, any player we can only identify
    # from the depth chart falls through to no bucket and silently loses their
    # whole stat line -- which is exactly what happened to Cameron Jordan.
    "LDE": "DL", "RDE": "DL", "LDT": "DL", "RDT": "DL",
    "WLB": "LB", "SLB": "LB", "LILB": "LB", "RILB": "LB",
    "LCB": "DB", "RCB": "DB", "NB": "DB",
    "LT": None, "LG": None, "RG": None, "RT": None,
    "H": None, "PR": None, "KR": None,
}

# Positions that describe a role rather than a player's actual spot. Never let
# one of these win over a real position, or a returner ends up bucketed as "KR".
ROLE_ONLY = {"H", "PR", "KR", "LS"}

stats["bucket"] = stats.position.map(POS_BUCKET)

# League ranks: computed within bucket, only among players with real volume,
# so a backup QB with 3 attempts doesn't get "1st in INT".
VOLUME_GATE = {
    "QB": ("attempts", 150), "RB": ("carries", 50), "WR": ("targets", 30),
    "TE": ("targets", 20), "DL": ("games", 8), "LB": ("games", 8),
    "DB": ("games", 8), "K": ("fg_att", 10), "P": ("games", 8),
}

ranks = {}   # (gsis_id, stat) -> (rank, pool_size)
for bucket, statset in STAT_SETS.items():
    pool = stats[stats.bucket == bucket].copy()
    gate_col, gate_min = VOLUME_GATE.get(bucket, ("games", 1))
    if gate_col in pool.columns:
        pool = pool[pool[gate_col].fillna(0) >= gate_min]
    n = len(pool)
    if n == 0:
        continue
    for col, _label in statset:
        if col not in pool.columns:
            continue
        asc = col in LOWER_IS_BETTER
        r = pool[col].fillna(0).rank(ascending=asc, method="min").astype(int)
        for pid, rk in zip(pool.player_id, r):
            ranks[(pid, col)] = (int(rk), n)

def stat_line(pid, bucket):
    row = stats[stats.player_id == pid]
    if row.empty or bucket not in STAT_SETS:
        return None
    row = row.iloc[0]
    out = {"games": int(row.get("games", 0) or 0), "items": []}
    for col, label in STAT_SETS[bucket]:
        if col not in row or pd.isna(row[col]):
            continue
        val = row[col]
        val = round(float(val), 1) if col == "fg_pct" else int(val)
        entry = {"l": label, "v": val}
        if (pid, col) in ranks:
            rk, pool = ranks[(pid, col)]
            entry["r"] = rk
            entry["n"] = pool
        out["items"].append(entry)
    return out if out["items"] else None

# ---------------------------------------------------------------- assemble

rmap = roster.set_index("gsis_id").to_dict("index")
STATS_POS = stats.set_index("player_id").position.to_dict()


def pick(pid, key, roster_key, info):
    """Roster first, then the master players table. Blank/NaN counts as missing."""
    v = info.get(roster_key)
    if v is not None and not (isinstance(v, float) and pd.isna(v)) and v != "":
        return v
    v = MASTER[key].get(pid)
    return None if v is None or (isinstance(v, float) and pd.isna(v)) else v


def resolve_pos(pid, info, dc_abb):
    """A player's real position. The depth-chart code is the last resort because
    it encodes alignment (LDE, RILB) and sometimes just a role (KR)."""
    for cand in (info.get("position"), MASTER["pos"].get(pid), STATS_POS.get(pid)):
        if isinstance(cand, str) and cand and cand not in ROLE_ONLY:
            return cand
    return dc_abb


players, seen = {}, set()
CURRENT_TEAM = {}
for _, r in dc.iterrows():
    if not pd.isna(r.gsis_id):
        CURRENT_TEAM.setdefault(r.gsis_id, r.team)

for _, r in dc.iterrows():
    pid = r.gsis_id
    if pd.isna(pid):
        continue
    if pid not in seen:
        seen.add(pid)
        info = rmap.get(pid, {})
        pos = resolve_pos(pid, info, r.pos_abb)
        bucket = POS_BUCKET.get(pos)
        nm = (info.get("full_name") or MASTER["name"].get(pid) or r.player_name)
        num = pick(pid, "num", "jersey_number", info)
        exp = pick(pid, "exp", "years_exp", info)
        img = pick(pid, "img", "headshot_url", info)

        # Roster movement. A player can hold rookie status into a second year if
        # he spent the first on a practice squad without playing, so he may show
        # up on last season's roster too. Rookie is the more useful fact and the
        # pair reads as a contradiction, so it wins.
        is_rookie = ROOKIE_YEAR.get(pid) == 2026
        was = PREV_TEAM.get(pid)
        moved = None if is_rookie else (was if (was and was != CURRENT_TEAM.get(pid)) else None)
        pick_no = DRAFT_PICK.get(pid)
        players[pid] = {
            "id": pid,
            "name": nm,
            "num": None if num is None else int(num),
            "pos": pos,
            "im": None,
            "img": img if isinstance(img, str) else None,
            "ht": pick(pid, "ht", "height", info),
            "wt": pick(pid, "wt", "weight", info),
            "exp": None if exp is None else int(exp),
            "col": pick(pid, "col", "college", info),
            "t100": None,        # assigned once every club is known
            "t100p": None,
            "eid": (lambda e: None if e is None or (isinstance(e, float) and pd.isna(e))
                    else str(int(e)))(MASTER["espn"].get(pid)),
            "rook": 1 if is_rookie else 0,
            "pick": None if pick_no is None or pd.isna(pick_no) else int(pick_no),
            "prev": moved,
            "dnp": 1 if (not is_rookie and not was) else 0,
            "st": stat_line(pid, bucket),
        }

team_rows = {}
for _, r in dc.iterrows():
    if pd.isna(r.gsis_id):
        continue
    team_rows.setdefault(r.team, []).append({
        "grp": r.pos_grp, "slot": int(r.pos_slot), "abb": r.pos_abb,
        "name": r.pos_name, "rank": int(r.pos_rank), "pid": r.gsis_id,
    })

team_meta = {}
for _, t in teams.iterrows():
    team_meta[t.team_abbr] = {
        "name": t.team_name, "nick": t.team_nick, "conf": t.team_conf,
        "div": t.team_division, "c1": t.team_color, "c2": t.team_color2,
        "logo": t.team_logo_espn,
    }

# Headshots all live on the same NFL.com Cloudinary CDN. Store only the unique
# trailing segment and rebuild the URL in the browser -- saves ~250KB.
IMG_BASE = "https://static.www.nfl.com/image/upload/f_auto,q_auto/league/"
IMG_ALT = "https://static.www.nfl.com/image/private/f_auto,q_auto/league/"
for p in players.values():
    u = p.pop("img", None)
    if not u:
        p["im"] = None
    elif u.startswith(IMG_BASE):
        p["im"] = u[len(IMG_BASE):]
    elif u.startswith(IMG_ALT):
        p["im"] = "!" + u[len(IMG_ALT):]
    else:
        p["im"] = "@" + u

import build_advanced
BUCKETS = {pid: POS_BUCKET.get(p["pos"]) for pid, p in players.items()}
adv = build_advanced.build(set(players), master, BUCKETS)
for pid, a in adv.items():
    players[pid]["adv"] = a
print(f"advanced   {len(adv)} players have an advanced block")

import build_contracts
contracts = build_contracts.build(set(players), BUCKETS)
for pid, ct in contracts.items():
    players[pid]["ct"] = ct
print(f"contracts  {len(contracts)} players with an active deal")

# ---------------------------------------------------------------- movement
import build_movement
movement, move_meta = build_movement.build(DC_ALL, set(players))
for pid, m in movement.items():
    players[pid]["mv"] = {k: v for k, v in m.items() if k != "pos"}
risers = build_movement.summarise(movement, team_rows, players)
print(f"movement   {len(movement)} players changed depth rank since March")

# ---------------------------------------------------------------- highlights
import build_highlights
import build_situational
# One read, only the columns the two modules actually use.
_pbp_cols = sorted(set(build_highlights.COLUMNS) | set(build_situational.COLUMNS))
PBP = pd.read_parquet("pbp2025.parquet", columns=_pbp_cols)
highlights = build_highlights.build(set(players), pbp=PBP)
for pid, hl in highlights.items():
    players[pid]["hl"] = hl
print(f"highlights {sum(len(v) for v in highlights.values())} plays for {len(highlights)} players")

# ---------------------------------------------------------------- career
import build_career
career = build_career.build(set(players), BUCKETS)
career_trunc = build_career.truncated(career, master, set(players))
for pid, rows in career.items():
    players[pid]["car"] = rows
    if pid in career_trunc:
        players[pid]["carFrom"] = career_trunc[pid]
print(f"career     {sum(len(v) for v in career.values())} seasons for {len(career)} players"
      f" ({len(career_trunc)} careers predate {build_career.FIRST})")

# ---------------------------------------------------------------- game logs
import build_gamelog
gamelog = build_gamelog.build(set(players), BUCKETS)
for pid, rows in gamelog.items():
    players[pid]["log"] = rows
print(f"gamelog    {sum(len(v) for v in gamelog.values())} games for {len(gamelog)} players")

# ---------------------------------------------------------------- battles
import build_battles
battles = build_battles.build(DC_ALL, players, set(team_meta))
print(f"battles    {sum(len(v) for v in battles.values())} contested spots "
      f"across {len(battles)} teams")

# ---------------------------------------------------------------- situational
situational = build_situational.build(set(players), BUCKETS, pbp=PBP)
del PBP
gc.collect()
for pid, rows in situational.items():
    players[pid]["sit"] = rows
print(f"situational {len(situational)} players with down-and-distance splits")

# ---------------------------------------------------------------- injuries
import build_injuries
injuries, inj_meta = build_injuries.build(set(players))
for pid, inj in injuries.items():
    players[pid]["inj"] = inj
# Grouped by club as well, so a game preview can show both sides without
# scanning every player.
inj_by_team = {}
_inj_team_of = {}
for _t, _rows in team_rows.items():
    for _r in _rows:
        _inj_team_of.setdefault(_r["pid"], _t)
for _pid, _inj in injuries.items():
    _tm = _inj_team_of.get(_pid)
    if not _tm:
        continue
    inj_by_team.setdefault(_tm, []).append({
        "pid": _pid, "name": players[_pid]["name"], "pos": players[_pid]["pos"],
        **_inj,
    })
for _tm in inj_by_team:
    inj_by_team[_tm].sort(key=lambda x: (-x["sev"], x["name"]))

print("injuries   " + (f"{len(injuries)} designations across {len(inj_by_team)} teams"
                       if inj_meta["available"]
                       else f"no {inj_meta['season']} report yet (expected until games start)"))

import build_coaches
coaches = build_coaches.build(set(team_meta))
print(f"coaches    {len(coaches)} head coaches "
      f"({sum(1 for c in coaches.values() if c['rookie'])} in their first year)")

import build_teams
team_season = build_teams.build(set(team_meta))

# ---------------------------------------------------------------- timeline
import build_timeline
timeline = build_timeline.build(DC_ALL, set(players))
print(f"timeline   {len(timeline['dates'])} weekly snapshots "
      f"{timeline['dates'][0]} to {timeline['dates'][-1]}" if timeline
      else "timeline   not enough snapshots")

# ---------------------------------------------------------------- comparables
import build_comps
_snap_pct = {}
try:
    _sn = pd.read_csv("snaps.csv", low_memory=False)
    _pfr2gsis = {v: k for k, v in master.pfr_id.dropna().items()}
    for pf, g in _sn.groupby("pfr_player_id"):
        gid = _pfr2gsis.get(pf)
        if gid:
            _snap_pct[gid] = float(
                pd.concat([g.offense_pct, g.defense_pct]).fillna(0).max() * 100)
except Exception:
    pass
comps = build_comps.build(players, BUCKETS, master, stats, _snap_pct)
for pid, c in comps.items():
    players[pid]["cmp"] = c
print(f"comps      {len(comps)} players have comparables")

# ---------------------------------------------------------------- draft
import build_draft
draft = build_draft.build(players, team_rows, master, roster)
draft_teams = build_draft.team_summary(draft, players, team_rows)
for pid, dv in draft.items():
    if dv["rd"]:
        players[pid]["dr"] = dv
print(f"draft      {sum(1 for v in draft.values() if v['rd'])} drafted, "
      f"{sum(1 for v in draft.values() if not v['rd'])} undrafted")

# ---------------------------------------------------------------- head to head
import build_h2h
h2h = build_h2h.build(set(team_meta))
h2h_sum = build_h2h.summarise(h2h, set(team_meta))
print(f"h2h        matchups since {build_h2h.FIRST} for {len(h2h)} teams")

# ---------------------------------------------------------------- past leaders
import build_leaders_history
leaders_past = build_leaders_history.build()
print(f"leaders    {len(leaders_past)} categories, "
      f"{build_leaders_history.SHOW_FROM}-{build_leaders_history.LAST}")

# ---------------------------------------------------------------- this season
# Both of these are no-ops until real games are played, then switch themselves
# on. Neither is an error when it produces nothing.
import build_current
current, cur_meta = build_current.build(set(players), BUCKETS)
for pid, c in current.items():
    players[pid]["cur"] = c
print("current    " + (
    f"{cur_meta['players']} players, {cur_meta['weeks']} weeks in"
    + ("" if cur_meta["ranked"] else " (too early to rank)")
    if cur_meta["live"] else
    f"no {cur_meta['season']} stats published yet"))

import build_standings
standings, stand_meta = build_standings.build(
    set(team_meta), dict(zip(teams.team_abbr, teams.team_division)))
print("standings  " + (f"through week {stand_meta['week']}, {stand_meta['played']} games"
                       if stand_meta["live"] else "no games played yet"))

# ---------------------------------------------------------------- history
import build_history
history = build_history.build(set(team_meta),
                              dict(zip(teams.team_abbr, teams.team_division)))
print(f"history    {build_history.FIRST}-{build_history.LAST} for {len(history)} teams")

# ---------------------------------------------------------------- roster views
import build_roster, build_schedule
roster_views = build_roster.build(players, team_rows, master)
schedule, slate = build_schedule.build(set(team_meta), team_season)
print(f"roster     cap + age for {len(roster_views)} teams")
print(f"schedule   {sum(len(v['games']) for v in schedule.values())} team-games, "
      f"{sum(len(v) for v in slate.values())} fixtures across {len(slate)} weeks")

# Top 100, resolved now that each player's club is known. During the first pass
# there is no team available to break a shared name with.
_team_of = {}
for _t, _rows in team_rows.items():
    for _r in _rows:
        _team_of.setdefault(_r["pid"], _t)
assign_top100(players, _team_of)

# First NFL season, for the "what changed since I last watched" view. Career
# stats only reach back to 2016, so fall back to experience, then to the rookie
# flag. Anything we cannot date is left null rather than guessed.
for pid, p in players.items():
    first = None
    if p.get("carFrom"):
        first = p["carFrom"]
    elif p.get("car"):
        first = p["car"][0]["y"]
    elif p.get("exp") is not None:
        first = 2026 - int(p["exp"])
    elif p.get("rook"):
        first = 2026
    p["first"] = first
_dated = sum(1 for p in players.values() if p["first"])
print(f"debut      {_dated} of {len(players)} players have a first season")

payload = {
    "snapshot": snapshot,
    "statsSeason": 2025,
    "t100Year": T100_YEAR,
    "t100PrevYear": T100_PREV_YEAR,
    "imgBase": IMG_BASE,
    "imgAlt": IMG_ALT,
    "teams": team_meta,
    "season": team_season,
    "coaches": coaches,
    "careerSchema": build_career.SCHEMA,
    "posBucket": {k: v for k, v in POS_BUCKET.items() if v},
    "careerFirst": build_career.FIRST,
    "risers": risers,
    "battles": battles,
    "roster": roster_views,
    "schedule": schedule,
    "slate": slate,
    "history": history,
    "current": cur_meta,
    "standings": standings,
    "standMeta": stand_meta,
    "leadersPast": leaders_past,
    "draft": draft_teams,
    "h2h": h2h,
    "h2hSum": h2h_sum,
    "timeline": timeline,
    "moveMeta": move_meta,
    "injMeta": inj_meta,
    "injuries": inj_by_team,
    "depth": team_rows,
    "players": {k: v for k, v in players.items()},
}

with open(OUT, "w") as f:
    json.dump(payload, f, separators=(",", ":"))

matched = sum(1 for p in players.values() if p["t100"])
print(f"snapshot   {snapshot}")
print(f"teams      {len(team_meta)}")
print(f"players    {len(players)}")
_moved = sum(1 for p in players.values() if p["t100"] and p["t100p"])
print(f"top100     {matched}/100 matched ({_moved} also on the {T100_PREV_YEAR} list)")
print(f"with stats {sum(1 for p in players.values() if p['st'])}")
import os
print(f"size       {os.path.getsize(OUT)/1e6:.2f} MB")

assigned = {p["t100"] for p in players.values() if p["t100"]}
missing = [n for rk, n in sorted(TOP100.items())
           if rk not in assigned and n not in NOT_ON_ROSTER]

# Anyone with a real stat line we failed to attach is a bug, not a data gap.
statted = set(stats.player_id)
dropped = [p["name"] + f" ({p['pos']})" for pid, p in players.items()
           if pid in statted and not p["st"] and POS_BUCKET.get(p["pos"]) is not None]
print(f"no headshot {sum(1 for p in players.values() if not p['im'])}")
if dropped:
    print(f"\nSTATS DROPPED for {len(dropped)}: {', '.join(dropped[:12])}")
else:
    print("every player with a 2025 stat line has it attached")
print(f"off roster {len(NOT_ON_ROSTER)} (expected: {', '.join(sorted(NOT_ON_ROSTER))})")
if missing:
    print(f"\nUNMATCHED - needs an alias ({len(missing)}): {', '.join(missing)}")
else:
    print("\nall remaining top 100 players matched cleanly")

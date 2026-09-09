"""
Advanced stats, on top of the box score in build_data.py.

Sources (all nflverse, all free):
  advstats_week_pass.csv  -> pressure, blitz, bad throws  (PFR charting)
  advstats_week_rush.csv  -> yards before/after contact, broken tackles
  advstats_week_rec.csv   -> drops, broken tackles, passer rating when targeted
  advstats_week_def.csv   -> coverage: targets, yards allowed, rating allowed,
                             plus pass rush: pressures, hurries, QB hits
  snaps.csv               -> snap counts and share

These are weekly, so everything gets summed to a season and rate stats are
recomputed from the totals rather than averaged (averaging a per-game rate
overweights low-volume games).

Joined on pfr_player_id, which reaches ~2,600 of the ~2,900 players on a depth
chart. Anyone unmatched simply gets no advanced block, and the UI hides it.
"""
import pandas as pd

SEASON = 2025


def _season(path, id_col="pfr_player_id"):
    d = pd.read_csv(path, low_memory=False)
    d = d[d.game_type == "REG"] if "game_type" in d.columns else d
    return d[d[id_col].notna()]


def _rank(s, ascending=False):
    return s.rank(ascending=ascending, method="min").astype(int)


def build(player_ids, master, buckets):
    """player_ids: gsis ids in the app. master: players.csv indexed by gsis_id.
    buckets: gsis_id -> stat bucket (QB/RB/WR/TE/DL/LB/DB/K)."""
    link = master.pfr_id.dropna()
    pfr2gsis = {v: k for k, v in link.items() if k in player_ids}

    pas = _season("advstats_week_pass.csv")
    rus = _season("advstats_week_rush.csv")
    rec = _season("advstats_week_rec.csv")
    dfn = _season("advstats_week_def.csv")
    snp = _season("snaps.csv")

    # ---------------------------------------------------------- season sums
    P = pas.groupby("pfr_player_id").agg(
        sacked=("times_sacked", "sum"), blitzed=("times_blitzed", "sum"),
        hurried=("times_hurried", "sum"), hit=("times_hit", "sum"),
        pressured=("times_pressured", "sum"),
        bad=("passing_bad_throws", "sum"), drops=("passing_drops", "sum"),
    )
    R = rus.groupby("pfr_player_id").agg(
        car=("carries", "sum"),
        ybc=("rushing_yards_before_contact", "sum"),
        yac=("rushing_yards_after_contact", "sum"),
        broke=("rushing_broken_tackles", "sum"),
    )
    C = rec.groupby("pfr_player_id").agg(
        drop=("receiving_drop", "sum"), drop_pct=("receiving_drop_pct", "mean"),
        broke=("receiving_broken_tackles", "sum"),
        rating=("receiving_rat", "mean"),
    )
    D = dfn.groupby("pfr_player_id").agg(
        tgt=("def_targets", "sum"), cmp=("def_completions_allowed", "sum"),
        yds=("def_yards_allowed", "sum"), td=("def_receiving_td_allowed", "sum"),
        rating=("def_passer_rating_allowed", "mean"), adot=("def_adot", "mean"),
        press=("def_pressures", "sum"), hurr=("def_times_hurried", "sum"),
        hits=("def_times_hitqb", "sum"), blitz=("def_times_blitzed", "sum"),
    )
    S = snp.groupby("pfr_player_id").agg(
        off=("offense_snaps", "sum"), off_p=("offense_pct", "mean"),
        dfs=("defense_snaps", "sum"), dfs_p=("defense_pct", "mean"),
        st=("st_snaps", "sum"), st_p=("st_pct", "mean"),
    )

    # ---------------------------------------------------------- rate stats
    # Pressure rate has to be measured against dropbacks. Blitzes are not a
    # denominator -- a quarterback can be pressured without being blitzed and
    # blitzed without being pressured.
    box = pd.read_csv("stats_2025.csv", low_memory=False)
    box = box[box.player_id.isin(player_ids)]
    gsis2pfr = {v: k for k, v in pfr2gsis.items()}
    vol = {"drop_backs": {}, "carries": {}, "targets": {}}
    for _, b in box.iterrows():
        pf = gsis2pfr.get(b.player_id)
        if not pf:
            continue
        vol["drop_backs"][pf] = (b.attempts or 0) + (b.sacks_suffered or 0)
        vol["carries"][pf] = b.carries or 0
        vol["targets"][pf] = b.targets or 0

    P["dropbacks"] = pd.Series(vol["drop_backs"])
    P["press_pct"] = P.pressured / P.dropbacks.replace(0, pd.NA) * 100
    R["ybc_att"] = R.ybc / R.car.replace(0, pd.NA)
    R["yac_att"] = R.yac / R.car.replace(0, pd.NA)
    D["cmp_pct"] = D.cmp / D.tgt.replace(0, pd.NA) * 100
    D["yds_tgt"] = D.yds / D.tgt.replace(0, pd.NA)

    frames = {"P": P, "R": R, "C": C, "D": D, "S": S}

    # Volume series a metric should be gated on before it earns a rank. Coverage
    # stats gate on how often a player was thrown at; pass-rush stats gate on
    # snaps played, because a pure rusher is rarely targeted and would otherwise
    # be excluded from his own best category.
    def_snaps = S.dfs.fillna(0)
    off_snaps = S.off.fillna(0)
    GATES = {
        "dropbacks": (pd.Series(vol["drop_backs"]), 200),
        "carries":   (pd.Series(vol["carries"]), 60),
        "targets":   (pd.Series(vol["targets"]), 35),
        "coverage":  (D.tgt.fillna(0), 30),
        "rushsnaps": (def_snaps, 250),
        "offsnaps":  (off_snaps, 250),
    }

    # ---------------------------------------------------------- what to show
    # (frame, column, label, decimals, lower_is_better, gate)
    SETS = {
        "QB": [("P", "press_pct", "Pressure rate %", 1, True, "dropbacks"),
               ("P", "pressured", "Times pressured", 0, False, "dropbacks"),
               ("P", "sacked", "Times sacked", 0, True, "dropbacks"),
               ("P", "blitzed", "Times blitzed", 0, False, "dropbacks"),
               ("P", "bad", "Bad throws", 0, True, "dropbacks"),
               ("P", "drops", "Dropped by receivers", 0, True, "dropbacks")],
        "RB": [("R", "ybc_att", "Yds before contact / att", 2, False, "carries"),
               ("R", "yac_att", "Yds after contact / att", 2, False, "carries"),
               ("R", "broke", "Broken tackles", 0, False, "carries"),
               ("C", "drop", "Drops", 0, True, "targets")],
        "WR": [("C", "rating", "Passer rating when targeted", 1, False, "targets"),
               ("C", "broke", "Broken tackles", 0, False, "targets"),
               ("C", "drop", "Drops", 0, True, "targets"),
               ("C", "drop_pct", "Drop rate %", 1, True, "targets")],
        "DL": [("D", "press", "Pressures", 0, False, "rushsnaps"),
               ("D", "hurr", "Hurries", 0, False, "rushsnaps"),
               ("D", "hits", "QB hits", 0, False, "rushsnaps"),
               ("D", "blitz", "Times blitzed", 0, False, "rushsnaps")],
        "DB": [("D", "rating", "Passer rating allowed", 1, True, "coverage"),
               ("D", "cmp_pct", "Completion % allowed", 1, True, "coverage"),
               ("D", "yds_tgt", "Yds allowed / target", 2, True, "coverage"),
               ("D", "tgt", "Targeted", 0, False, "coverage"),
               ("D", "td", "TDs allowed", 0, True, "coverage"),
               ("D", "adot", "Avg depth of target", 1, False, "coverage")],
    }
    SETS["TE"] = SETS["WR"]
    SETS["LB"] = SETS["DL"] + [
        ("D", "rating", "Passer rating allowed", 1, True, "coverage"),
        ("D", "cmp_pct", "Completion % allowed", 1, True, "coverage")]

    # ---------------------------------------------------------- ranks
    ranks = {}
    for bucket, spec in SETS.items():
        pool_ids = {p for p, b in buckets.items() if b == bucket}
        pool_pfr = [k for k, v in pfr2gsis.items() if v in pool_ids]
        for fr, col, _lab, _dec, asc, gate in spec:
            f = frames[fr]
            sub = f[f.index.isin(pool_pfr) & f[col].notna()]
            gser, gmin = GATES[gate]
            qualified = gser[gser >= gmin].index
            sub = sub[sub.index.isin(qualified)]
            if len(sub) < 8:
                continue
            rk = _rank(sub[col], ascending=asc)
            for pid, v in rk.items():
                ranks[(pid, fr, col)] = (int(v), len(sub))

    # ---------------------------------------------------------- emit
    out = {}
    for pfr, gsis in pfr2gsis.items():
        b = buckets.get(gsis)
        items = []
        for fr, col, lab, dec, _asc, _g in SETS.get(b, []):
            f = frames[fr]
            if pfr not in f.index or pd.isna(f.at[pfr, col]):
                continue
            v = f.at[pfr, col]
            v = int(round(v)) if dec == 0 else round(float(v), dec)
            e = {"l": lab, "v": v}
            if (pfr, fr, col) in ranks:
                r, n = ranks[(pfr, fr, col)]
                e["r"], e["n"] = r, n
            items.append(e)

        snaps = None
        if pfr in S.index:
            s = S.loc[pfr]
            parts = []
            if s.off and s.off > 0:
                parts.append({"l": "Offensive snaps", "v": int(s.off),
                              "pct": round(float(s.off_p) * 100, 1)})
            if s.dfs and s.dfs > 0:
                parts.append({"l": "Defensive snaps", "v": int(s.dfs),
                              "pct": round(float(s.dfs_p) * 100, 1)})
            if s.st and s.st > 0:
                parts.append({"l": "Special teams snaps", "v": int(s.st),
                              "pct": round(float(s.st_p) * 100, 1)})
            snaps = parts or None

        if items or snaps:
            out[gsis] = {"items": items, "snaps": snaps}
    return out

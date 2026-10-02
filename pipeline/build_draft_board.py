"""
Ten drafts, pick by pick, with how each career has gone.

From nflverse's draft_picks.csv, which the pipeline already downloads for the
team pages. Each pick carries the player's All-Pro and Pro Bowl selections,
seasons as a starter, Pro Football Reference's weighted career value (w_av),
and his last season in the league.

Steal and bust tags are given only to classes old enough to judge (2023 and
earlier: three seasons is too soon to call anyone either), and only at the
extremes:
  steal  a career in the top 32 of his class by w_av, from the third round or
         later -- a first-round career at a mid-round price
  bust   a first-round pick outside the top half of his class by w_av who has
         started two seasons or fewer
Everything in between is left untagged, because most picks are neither.
"""
import pandas as pd

from build_draft import _norm_team

FIRST, LAST = 2017, 2026
JUDGE_THROUGH = LAST - 3


def _i(v):
    try:
        return int(v) if pd.notna(v) else 0
    except (TypeError, ValueError):
        return 0


def build(players):
    dp = pd.read_csv("draft_picks.csv", low_memory=False)
    dp = dp[dp.season.between(FIRST, LAST)].copy()
    out = {}
    for yr, grp in dp.groupby("season"):
        yr = int(yr)
        grp = grp.sort_values("pick")
        judge = yr <= JUDGE_THROUGH
        av_rank = grp.w_av.fillna(0).rank(ascending=False, method="min") if judge else None
        half = len(grp) / 2
        rows = []
        for idx, r in grp.iterrows():
            gsis = r.gsis_id if isinstance(r.gsis_id, str) else None
            row = {
                "p": _i(r.pick), "r": _i(r["round"]),
                "t": _norm_team(r.team),
                "n": r.pfr_player_name if isinstance(r.pfr_player_name, str) else "",
                "pos": r.position if isinstance(r.position, str) else "",
                "c": r.college if isinstance(r.college, str) else "",
            }
            if gsis and gsis in players:
                row["id"] = gsis
            # Only what is non-zero, to keep the payload small.
            for key, col in (("ap", "allpro"), ("pb", "probowls"), ("st", "seasons_started"),
                             ("g", "games")):
                v = _i(r.get(col))
                if v:
                    row[key] = v
            if pd.notna(r.get("w_av")) and r.w_av:
                row["av"] = int(r.w_av)
            if pd.notna(r.get("to")):
                row["to"] = _i(r.to)
            if _i(r.get("hof")):
                row["hof"] = 1
            if judge:
                ar = int(av_rank[idx])
                if ar <= 32 and row["r"] >= 3:
                    row["tag"] = "steal"
                elif row["r"] == 1 and ar > half and _i(r.get("seasons_started")) <= 2:
                    row["tag"] = "bust"
            rows.append(row)
        out[str(yr)] = rows
    meta = {"first": FIRST, "last": LAST, "judged_through": JUDGE_THROUGH,
            "picks": sum(len(v) for v in out.values())}
    return out, meta

"""
Situational splits: how a player performs when the down and distance matter.

Attribution is limited to the ball carrier, passer and target, because those are
the only roles play-by-play identifies cleanly on every snap. Defensive situational
work is not attempted here -- tackle credit in the raw feed is inconsistent, and
the coverage and pass-rush numbers in build_advanced.py already cover that ground
with data that was charted rather than inferred.

Rates are computed from season totals, never averaged across games.
"""
import pandas as pd

SEASON = 2025
MIN_PLAYS = 12          # below this a rate is noise, so no rate is shown

ROLES = {"passer_player_id": "pass",
         "rusher_player_id": "run",
         "receiver_player_id": "catch"}


def build(player_ids, buckets, path="pbp2025.parquet", pbp=None):
    p = pbp if pbp is not None else pd.read_parquet(path)
    p = p[p.play_type.isin(["pass", "run"]) & p.epa.notna()]

    frames = []
    for col, role in ROLES.items():
        sub = p[p[col].notna() & p[col].isin(player_ids)].copy()
        if sub.empty:
            continue
        sub["pid"] = sub[col]
        frames.append(sub)
    if not frames:
        return {}
    a = pd.concat(frames, ignore_index=True)

    # A pass counts once for the thrower and once for the target, which is what
    # we want -- each is being judged on the same snap from his own side.
    a["third"] = a.down == 3
    a["rz"] = a.yardline_100 <= 20
    a["short"] = (a.down.isin([3, 4])) & (a.ydstogo <= 2)
    a["early"] = a.down.isin([1, 2])

    out = {}
    for pid, g in a.groupby("pid", sort=False):
        if buckets.get(pid) not in ("QB", "RB", "WR", "TE"):
            continue
        rows = []

        def add(label, mask, num_col=None, kind="success"):
            sel = g[mask]
            n = len(sel)
            if n < MIN_PLAYS:
                return
            if kind == "success":
                # 'success' is nflverse's flag for a play that gained enough to
                # keep the drive on schedule.
                rate = sel.success.mean() * 100
                rows.append({"l": label, "n": n, "v": round(rate, 1), "u": "%",
                             "sub": "success rate"})
            elif kind == "convert":
                # Third and fourth down each have their own flag. Using only the
                # third-down one scores every fourth-down conversion as a failure.
                conv = (sel.third_down_converted.fillna(0)
                        + sel.fourth_down_converted.fillna(0)).clip(upper=1)
                rate = conv.mean() * 100
                rows.append({"l": label, "n": n, "v": round(rate, 1), "u": "%",
                             "sub": "converted"})
            elif kind == "td":
                rate = sel.touchdown.fillna(0).mean() * 100
                rows.append({"l": label, "n": n, "v": round(rate, 1), "u": "%",
                             "sub": "ended in a TD"})
            elif kind == "epa":
                rows.append({"l": label, "n": n, "v": round(sel.epa.mean(), 2),
                             "u": "", "sub": "EPA per play"})

        add("Third down", g.third, kind="convert")
        add("Red zone", g.rz, kind="td")
        add("Third or fourth and short", g.short, kind="convert")
        add("Early downs", g.early, kind="epa")
        add("All plays", g.index == g.index, kind="success")

        if rows:
            out[pid] = rows

    # League rank within position for each split, so a percentage means something.
    label_index = {}
    for pid, rows in out.items():
        for r in rows:
            label_index.setdefault((buckets[pid], r["l"]), []).append((pid, r["v"]))
    for (bucket, label), vals in label_index.items():
        if len(vals) < 8:
            continue
        s = pd.Series({p: v for p, v in vals})
        rk = s.rank(ascending=False, method="min").astype(int)
        for pid, r in rk.items():
            for row in out[pid]:
                if row["l"] == label:
                    row["r"] = int(r)
                    row["rn"] = len(s)
    return out


COLUMNS = ["play_type", "epa", "down", "ydstogo", "yardline_100", "success",
           "third_down_converted", "fourth_down_converted", "touchdown",
           "passer_player_id", "rusher_player_id", "receiver_player_id"]

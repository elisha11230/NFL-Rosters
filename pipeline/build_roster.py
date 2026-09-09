"""
Roster construction: where a team's money goes, and how old the roster is.

Both are team-level views built from data already in the payload, so neither adds
a download.

Coverage caveat on money: contracts exist for about 2,200 of the ~2,900 players on
a depth chart. Rookies on unsigned deals and camp bodies are missing. The totals
are therefore a shape, not a cap sheet, and the UI says so.
"""
import datetime as dt
import pandas as pd

SEASON_START = dt.date(2026, 9, 1)

# Coarser than the stat buckets. Nobody asks how much a team spends on
# "special teams K versus P"; they ask about the offensive line.
CAP_GROUP = {
    "QB": "Quarterback",
    "RB": "Running back", "FB": "Running back",
    "WR": "Receiver", "TE": "Receiver",
    "T": "O-line", "G": "O-line", "C": "O-line", "OL": "O-line",
    "OT": "O-line", "OG": "O-line",
    "DE": "D-line", "DT": "D-line", "NT": "D-line", "DL": "D-line",
    "LB": "Linebacker", "ILB": "Linebacker", "OLB": "Linebacker", "MLB": "Linebacker",
    "CB": "Secondary", "S": "Secondary", "SS": "Secondary", "FS": "Secondary",
    "DB": "Secondary",
    "K": "Specialist", "PK": "Specialist", "P": "Specialist", "LS": "Specialist",
}
ORDER = ["Quarterback", "Running back", "Receiver", "O-line",
         "D-line", "Linebacker", "Secondary", "Specialist"]


def build(players, depth_rows, master):
    births = master.birth_date.to_dict()

    team_of = {}
    for team, rows in depth_rows.items():
        for r in rows:
            team_of.setdefault(r["pid"], team)

    money, ages, counts = {}, {}, {}
    for pid, p in players.items():
        team = team_of.get(pid)
        if not team:
            continue
        grp = CAP_GROUP.get(p["pos"])

        ct = p.get("ct")
        if ct and grp:
            money.setdefault(team, {}).setdefault(grp, [0.0, 0])
            money[team][grp][0] += ct["apy"]
            money[team][grp][1] += 1

        b = births.get(pid)
        if isinstance(b, str) and len(b) >= 10:
            try:
                bd = dt.date.fromisoformat(b[:10])
            except ValueError:
                continue
            age = (SEASON_START - bd).days / 365.25
            ages.setdefault(team, []).append((age, grp, p["name"], pid))
        counts[team] = counts.get(team, 0) + 1

    out = {}
    for team in depth_rows:
        m = money.get(team, {})
        total = sum(v[0] for v in m.values())
        groups = []
        for g in ORDER:
            if g not in m:
                continue
            amt, n = m[g]
            groups.append({
                "g": g, "m": round(amt, 1), "n": n,
                "pct": round(amt / total * 100, 1) if total else 0,
            })
        groups.sort(key=lambda x: -x["m"])

        alist = ages.get(team, [])
        by_unit = {}
        for age, grp, _nm, _p in alist:
            if grp:
                by_unit.setdefault(grp, []).append(age)
        # Sort on age alone. Sorting the whole tuple falls through to comparing
        # the position group when two players share an age, and that can be None.
        oldest = sorted(alist, key=lambda x: x[0], reverse=True)[:1]
        youngest = sorted(alist, key=lambda x: x[0])[:1]

        out[team] = {
            "cap": {
                "total": round(total, 1),
                "covered": sum(v[1] for v in m.values()),
                "roster": counts.get(team, 0),
                "groups": groups,
            },
            "age": {
                "avg": round(sum(a for a, *_ in alist) / len(alist), 1) if alist else None,
                "n": len(alist),
                "units": [{"g": g, "a": round(sum(v) / len(v), 1)}
                          for g, v in sorted(by_unit.items(), key=lambda x: ORDER.index(x[0]))],
                "oldest": {"name": oldest[0][2], "age": round(oldest[0][0], 1)} if oldest else None,
                "youngest": {"name": youngest[0][2], "age": round(youngest[0][0], 1)} if youngest else None,
            },
        }

    # League ranks so a number means something on its own.
    avg_ages = {t: v["age"]["avg"] for t, v in out.items() if v["age"]["avg"]}
    if avg_ages:
        s = pd.Series(avg_ages)
        rk = s.rank(ascending=True, method="min").astype(int)   # 1 = youngest
        for t, r in rk.items():
            out[t]["age"]["rank"] = int(r)
            out[t]["age"]["n_teams"] = len(s)
    return out

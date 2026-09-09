"""
Injury designations.

nflverse publishes weekly injury reports per season. The 2026 file does not exist
yet -- it appears once games are played. This module looks for the current season,
falls back to reporting nothing, and never silently shows last season's injuries
as if they were current. That failure mode is exactly what the stale contracts CSV
did, and it is not worth repeating.

Wire it up now; it starts producing in September on its own.
"""
import os
import urllib.request

import pandas as pd

SEASON = 2026
URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
       "injuries/injuries_{year}.csv")
LOCAL = "injuries_{year}.csv"

# Two different columns carry two different things, and early in a week only the
# second exists. The game designation (Out, Doubtful, Questionable) is not
# published until Friday; before that all there is is who practised and how much.
# Reading only report_status therefore finds nothing on a Wednesday, which is
# exactly when someone checks a preview.
REPORT_SEVERITY = {
    "Out": 4, "Doubtful": 3, "Questionable": 2,
    "Injured Reserve": 5, "IR": 5, "PUP": 5,
    "Physically Unable to Perform": 5, "Non-Football Injury": 5,
}
PRACTICE_SEVERITY = {
    "Did Not Participate In Practice": 3,
    "Limited Participation in Practice": 2,
    "Full Participation in Practice": 1,
}
LABEL = {
    5: "Out for now", 4: "Out", 3: "Doubtful", 2: "Questionable", 1: "On the report",
}
PRACTICE_LABEL = {
    "Did Not Participate In Practice": "Did not practise",
    "Limited Participation in Practice": "Limited in practice",
    "Full Participation in Practice": "Practised fully",
}


def fetch(year=SEASON):
    """Download the season's injuries if available. Returns a path or None."""
    path = LOCAL.format(year=year)
    if os.path.exists(path):
        return path
    try:
        req = urllib.request.Request(URL.format(year=year),
                                     headers={"User-Agent": "depth-chart-app"})
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 200:
                return None
            data = r.read()
        if data[:9] == b"Not Found" or len(data) < 200:
            return None
        with open(path, "wb") as f:
            f.write(data)
        return path
    except Exception:
        return None


def build(player_ids, year=SEASON):
    path = fetch(year)
    if not path:
        return {}, {"available": False, "season": year}

    d = pd.read_csv(path, low_memory=False)
    d = d[d.gsis_id.notna() & d.gsis_id.isin(player_ids)]
    if d.empty:
        return {}, {"available": False, "season": year}

    # Newest report per player.
    d = d.sort_values("week").groupby("gsis_id", as_index=False).last()

    out = {}
    for _, r in d.iterrows():
        report = r.get("report_status")
        practice = r.get("practice_status")
        report = report if isinstance(report, str) else None
        practice = practice if isinstance(practice, str) else None

        sev = REPORT_SEVERITY.get(report)
        label = LABEL.get(sev) if sev else None
        if not sev and practice:
            sev = PRACTICE_SEVERITY.get(practice)
            label = PRACTICE_LABEL.get(practice)
        if not sev:
            continue

        detail = (r.get("practice_primary_injury")
                  or r.get("report_primary_injury"))
        out[r.gsis_id] = {
            "sev": int(sev),
            "label": label,
            "detail": detail if isinstance(detail, str) else None,
            "week": None if pd.isna(r.get("week")) else int(r["week"]),
            # Practice notes are softer than a game designation, and the UI
            # should not dress one as the other.
            "kind": "report" if report else "practice",
        }
    return out, {"available": True, "season": year,
                 "week": int(d.week.max()) if "week" in d else None}

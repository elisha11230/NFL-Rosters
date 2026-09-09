#!/usr/bin/env python3
"""
Verify every data source before a build.

This exists because two sources have failed silently already, in two different
ways, and both produced a build that looked correct:

  1. contracts.csv.gz downloaded fine, parsed fine, and was three years stale --
     it reported a veteran's expired rookie deal as his current salary.
  2. ngs_passing.csv 404'd. The server returned nine bytes reading "Not Found",
     curl exited 0, and the file sat on disk looking like a CSV.

Size, parseability and recency are three separate questions and a source can pass
two while failing the third. Run this before build_data.py. Non-zero exit means
do not ship.
"""
import os
import sys

import pandas as pd

# name -> (path, min_bytes, kind, recency check or None)
#
# The recency check takes the loaded frame and returns (ok, message). It is the
# most important column: a file that parses cleanly can still be years old.
def _max_year(col, min_year):
    def check(df):
        if col not in df.columns:
            return False, f"no {col} column"
        yr = int(pd.to_numeric(df[col], errors="coerce").max())
        return yr >= min_year, f"newest {col} is {yr}, wanted >= {min_year}"
    check.column = col
    return check


def _has_snapshot_after(col, iso):
    def check(df):
        if col not in df.columns:
            return False, f"no {col} column"
        newest = str(df[col].max())
        return newest >= iso, f"newest {col} is {newest[:10]}, wanted >= {iso[:10]}"
    check.column = col
    return check


SOURCES = [
    ("depth charts",   "depth_charts_2026.csv", 5_000_000, "csv",
     _has_snapshot_after("dt", "2026-06-01")),
    ("roster 2026",    "roster_2026.csv",         200_000, "csv",
     _max_year("season", 2026)),
    ("roster 2025",    "roster_2025.csv",         200_000, "csv",
     _max_year("season", 2025)),
    ("players master", "players_master.csv",    1_000_000, "csv", None),
    ("player stats",   "stats_2025.csv",          500_000, "csv",
     _max_year("season", 2025)),
    ("team stats",     "team_2025.csv",            20_000, "csv",
     _max_year("season", 2025)),
    ("team weekly",    "team_week_2025.csv",       50_000, "csv",
     _max_year("season", 2025)),
    ("schedules",      "sched.csv",               500_000, "csv",
     _max_year("season", 2026)),
    ("teams",          "teams.csv",                 3_000, "csv", None),
    ("snap counts",    "snaps.csv",             1_000_000, "csv",
     _max_year("season", 2025)),
    ("adv pass",       "advstats_week_pass.csv",   50_000, "csv", None),
    ("adv rush",       "advstats_week_rush.csv",   50_000, "csv", None),
    ("adv rec",        "advstats_week_rec.csv",   100_000, "csv", None),
    ("adv def",        "advstats_week_def.csv",   200_000, "csv", None),
    # Read the parquet, never the csv.gz -- the gzipped CSV in this release is
    # stale. This check is what catches it if that ever changes again.
    ("contracts",      "contracts.parquet",     1_000_000, "parquet",
     _max_year("year_signed", 2025)),
    ("play by play",   "pbp2025.parquet",      10_000_000, "parquet",
     _max_year("season", 2025)),
    ("career 2016",    "career/2016.csv",         500_000, "csv",
     _max_year("season", 2016)),
    ("career 2025",    "career/2025.csv",         500_000, "csv",
     _max_year("season", 2025)),
    ("weekly stats",   "stats_week_2025.csv",     500_000, "csv",
     _max_year("season", 2025)),
    ("draft picks",    "draft_picks.csv",       1_000_000, "csv",
     _max_year("season", 2026)),
]


def check_one(name, path, min_bytes, kind, recency):
    if not os.path.exists(path):
        return False, "missing"

    size = os.path.getsize(path)
    if size < min_bytes:
        # The signature failure: an HTML or plain-text error page saved as data.
        with open(path, "rb") as f:
            head = f.read(200)
        if b"Not Found" in head or head.lstrip()[:1] == b"<":
            return False, f"server error saved as data ({size} bytes: {head[:40]!r})"
        return False, f"only {size:,} bytes, expected at least {min_bytes:,}"

    try:
        # Parquet files here carry list-of-struct columns that explode in
        # memory -- contracts.parquet is 6MB on disk and gigabytes materialised.
        # Read only the column the recency check needs plus a couple of flat
        # ones: enough to prove the file parses and is current.
        if kind == "parquet":
            import pyarrow.parquet as pq
            flat = [f.name for f in pq.ParquetFile(path).schema_arrow
                    if str(f.type)[:4] not in ("list", "stru")]
            want = [getattr(recency, "column", None)] if recency else []
            want = [c for c in want if c in flat] or flat[:3]
            df = pd.read_parquet(path, columns=want)
        else:
            df = pd.read_csv(path, low_memory=False, nrows=200_000)
    except Exception as e:
        return False, f"will not parse: {type(e).__name__}: {e}"

    if df.empty:
        return False, "parsed but empty"

    if recency:
        ok, msg = recency(df)
        if not ok:
            return False, "STALE: " + msg
        return True, f"{size/1e6:.1f} MB, {msg}"

    return True, f"{size/1e6:.1f} MB, {len(df.columns)} cols"


# Sources that do not exist until the season produces them. Absent is normal
# here; present but broken is not.
OPTIONAL = [
    ("stats 2026", "stats_2026.csv", 50_000, "csv", _max_year("season", 2026)),
    ("injuries 2026", "injuries_2026.csv", 200, "csv", _max_year("season", 2026)),
]


def check_optional():
    lines = []
    for name, path, min_bytes, kind, recency in OPTIONAL:
        if not os.path.exists(path):
            lines.append((name, True, "not published yet"))
            continue
        ok, detail = check_one(name, path, min_bytes, kind, recency)
        lines.append((name, ok, detail))
    return lines


def check_top100():
    """The Top 100 is hand maintained, so it gets checked like a source."""
    try:
        import top100 as t
    except Exception as e:
        return False, f"will not import: {e}"
    for year, lst in ((t.CURRENT_YEAR, t.TOP100), (t.PREV_YEAR, t.TOP100_PREV)):
        if len(lst) != 100:
            return False, f"{year} list has {len(lst)} entries, not 100"
        if sorted(lst) != list(range(1, 101)):
            return False, f"{year} list is not ranked 1-100"
        if len(set(lst.values())) != 100:
            return False, f"{year} list repeats a name"
    if len(t.TOP100_2026_META) != len(t.TOP100):
        return False, "meta and list are different lengths"
    return True, f"{t.CURRENT_YEAR} and {t.PREV_YEAR}, 100 each, ranked 1-100"


def main():
    print(f"{'source':<16}{'status':<8}detail")
    print("-" * 72)
    bad = []
    for name, path, min_bytes, kind, recency in SOURCES:
        ok, detail = check_one(name, path, min_bytes, kind, recency)
        print(f"{name:<16}{'ok' if ok else 'FAIL':<8}{detail}")
        if not ok:
            bad.append((name, detail))

    for name, ok, detail in check_optional():
        print(f"{name:<16}{'ok' if ok else 'FAIL':<8}{detail}")
        if not ok:
            bad.append((name, detail))

    ok, detail = check_top100()
    print(f"{'top 100':<16}{'ok' if ok else 'FAIL':<8}{detail}")
    if not ok:
        bad.append(("top 100", detail))

    print()
    if bad:
        print(f"{len(bad)} source(s) failed. Do not build:")
        for n, d in bad:
            print(f"  {n}: {d}")
        return 1
    print(f"all {len(SOURCES)} sources present, parseable and current")
    return 0


if __name__ == "__main__":
    sys.exit(main())

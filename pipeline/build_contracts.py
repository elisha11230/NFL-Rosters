"""
Player contracts, sourced from OverTheCap via nflverse.

IMPORTANT: read the parquet, not the csv.gz. The gzipped CSV in that release is
stale -- it stops at contracts signed in 2022 and still flags expired deals as
active, so it would report a player's rookie contract as his current salary. The
parquet is the maintained asset and runs through the current league year.

Money in this dataset is already in millions: value 41.2 means $41.2M.
"""
import pandas as pd

CURRENT_YEAR = 2026

COLUMNS = ["player", "position", "team", "is_active", "year_signed", "years",
           "value", "apy", "guaranteed", "apy_cap_pct", "gsis_id"]


def build(player_ids, buckets):
    # Only the flat columns. This file also carries season_history and
    # contract_history as list-of-struct columns; materialising those turns a
    # 6MB file into gigabytes and gets the build OOM-killed.
    c = pd.read_parquet("contracts.parquet", columns=COLUMNS)

    # Guard against silently shipping stale figures if the upstream asset ever
    # regresses the way the CSV did.
    newest = int(c.year_signed.max())
    if newest < CURRENT_YEAR - 1:
        raise SystemExit(
            f"contracts data looks stale: newest contract signed {newest}. "
            "Check the parquet asset before shipping salary figures."
        )

    c = c[c.is_active == True]                                   # noqa: E712
    c = c[c.gsis_id.notna() & c.gsis_id.isin(player_ids)]
    # One row per player: the most recently signed active deal.
    c = c.sort_values("year_signed").groupby("gsis_id", as_index=False).last()

    # Average per year is the number that actually compares across contracts of
    # different lengths, so rank on that within each position group.
    ranks = {}
    for bucket in set(buckets.values()):
        if bucket is None:
            continue
        pool = c[c.gsis_id.map(buckets.get) == bucket]
        pool = pool[pool.apy.notna()]
        if len(pool) < 8:
            continue
        rk = pool.apy.rank(ascending=False, method="min").astype(int)
        for gid, v in zip(pool.gsis_id, rk):
            ranks[gid] = (int(v), len(pool))

    out = {}
    for _, r in c.iterrows():
        if pd.isna(r.apy):
            continue
        e = {
            "apy": round(float(r.apy), 2),
            "yrs": None if pd.isna(r.years) else int(r.years),
            "val": None if pd.isna(r.value) else round(float(r.value), 2),
            "gtd": None if pd.isna(r.guaranteed) else round(float(r.guaranteed), 2),
            "signed": None if pd.isna(r.year_signed) else int(r.year_signed),
            "cap": None if pd.isna(r.apy_cap_pct) else round(float(r.apy_cap_pct) * 100, 1),
        }
        if r.gsis_id in ranks:
            e["r"], e["n"] = ranks[r.gsis_id]
        out[r.gsis_id] = e
    return out


if __name__ == "__main__":
    import json
    d = json.load(open("nfl_data.json"))
    buckets = {k: v.get("pos") for k, v in d["players"].items()}
    res = build(set(d["players"]), buckets)
    print(f"{len(res)} players with an active contract")

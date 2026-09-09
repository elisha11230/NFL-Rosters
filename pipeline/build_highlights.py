"""
Player highlights, as text.

Actual video is not available -- see the note at the bottom of this file. What is
available is every one of the 48,771 plays from last season with a description
and an EPA value, which is enough to answer "what were his biggest plays" in
words.

Plays are ranked by EPA rather than raw yardage, because EPA already knows that a
12-yard gain on 3rd-and-11 matters more than a 20-yard gain on 1st-and-10.

A player is credited on a play if he was one of the principals: threw it, ran it,
caught it, sacked the passer, or took it away.
"""
import re
import pandas as pd

SEASON = 2025
TOP_N = 4
# A floor so a deep backup's best moment is a real play rather than a routine
# six-yard gain that happened to be his largest.
MIN_EPA = 1.0

# column -> how to describe that player's involvement.
#
# Fumble recovery is deliberately absent. The credited recoverer can be on either
# side, so flipping the sign the way we do for genuine defensive plays turns a
# quarterback recovering his own disaster into a 6-EPA "highlight". Sacks and
# interceptions already cover the defensive moments worth showing.
ROLES = {
    "passer_player_id": "pass",
    "rusher_player_id": "run",
    "receiver_player_id": "catch",
    "sack_player_id": "sack",
    "interception_player_id": "int",
}
DEFENSIVE = {"sack", "int"}


def _clean(desc):
    """Strip the clock, formation notes, jersey numbers and personnel
    announcements out of a PBP string.

    '(7:11) (Shotgun) 4-D.Prescott pass deep middle to 9-K.Turpin for 86 yards,
    TOUCHDOWN.'  ->  'D.Prescott pass deep middle to K.Turpin for 86 yards,
    TOUCHDOWN.'
    """
    d = str(desc)
    d = re.sub(r"^\(\d*:\d+\)\s*", "", d)                     # game clock, incl. (:32)
    d = re.sub(r"\((Shotgun|No Huddle|Punt formation|Field Goal formation)[^)]*\)\s*",
               "", d)
    d = re.sub(r"\b[\w.'-]+ reported in as eligible\.\s*", "", d)   # personnel notes
    d = re.sub(r"\b\d{1,2}-([A-Z]\.)", r"\1", d)              # jersey numbers
    d = re.sub(r"\s+", " ", d).strip()
    d = re.split(r"\s*Penalty on ", d)[0].strip()             # penalty tails
    return d[:150]


def build(player_ids, path="pbp2025.parquet", pbp=None):
    p = pbp if pbp is not None else pd.read_parquet(path)
    p = p[p.epa.notna() & p.desc.notna()]
    p = p[p.play_type.isin(["pass", "run"])]

    frames = []
    for col, role in ROLES.items():
        if col not in p.columns:
            continue
        sub = p[p[col].notna() & p[col].isin(player_ids)].copy()
        if sub.empty:
            continue

        # A player's own turnover is never his highlight, however the net EPA
        # shook out after a return or a recovery.
        if role not in DEFENSIVE:
            if "interception" in sub.columns:
                sub = sub[sub.interception != 1]
            if "fumble_lost" in sub.columns:
                sub = sub[sub.fumble_lost != 1]

        sub["pid"] = sub[col]
        sub["role"] = role
        # A defender's good play is a bad play for the offence, and EPA is always
        # from the offence's point of view, so flip the sign for those.
        sub["value"] = -sub.epa if role in DEFENSIVE else sub.epa
        frames.append(sub[["pid", "role", "value", "epa", "week", "desc",
                           "yards_gained", "touchdown", "posteam", "defteam"]])

    if not frames:
        return {}
    allp = pd.concat(frames, ignore_index=True)
    allp = allp[allp.value >= MIN_EPA]
    allp = allp.sort_values("value", ascending=False)

    out = {}
    for pid, grp in allp.groupby("pid", sort=False):
        # One play can credit a player twice (rusher and receiver on a lateral);
        # de-duplicate on the description.
        seen, plays = set(), []
        for _, r in grp.iterrows():
            key = (int(r.week), str(r.desc)[:60])
            if key in seen:
                continue
            seen.add(key)
            plays.append({
                "wk": int(r.week),
                "vs": r.defteam if r.posteam else None,
                "epa": round(float(r.value), 1),
                "yds": None if pd.isna(r.yards_gained) else int(r.yards_gained),
                "td": bool(r.touchdown),
                "d": _clean(r.desc),
            })
            if len(plays) >= TOP_N:
                break
        if plays:
            out[pid] = plays
    return out


# ---------------------------------------------------------------------------
# On actual video:
#
# There is no free, structured source of NFL game footage. The league licenses it
# exclusively and there is no public clip API. The only legitimate route to real
# video is YouTube's embed player against their Data API, which needs an API key,
# carries a daily quota, and would mean this app can no longer run offline from a
# single file.
#
# What costs nothing is a constructed search link -- one tap from a player's
# profile to that player's highlights on YouTube. No key, no quota, no scraping,
# and it lands on official league uploads for anyone well known enough to have
# them. That is what the app does.
# ---------------------------------------------------------------------------
def youtube_query(name, season=SEASON):
    return f"{name} {season} highlights"


# Columns this module touches. build_data loads the union of these and
# build_situational's once -- the full play-by-play frame is 174MB in memory
# against 14MB for the slice actually used, which is the difference between
# the build fitting in the container and being killed.
COLUMNS = ["play_type", "epa", "desc", "week", "posteam", "defteam",
           "yards_gained", "touchdown", "interception", "fumble_lost",
           "passer_player_id", "rusher_player_id", "receiver_player_id",
           "sack_player_id", "interception_player_id"]

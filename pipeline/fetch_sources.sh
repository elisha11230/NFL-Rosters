#!/usr/bin/env bash
# Download every source the build needs.
#
# Kept as a script rather than instructions in a README so that the GitHub Action
# and a person at a terminal run exactly the same thing. If these two ever drift,
# the automated build and the local one stop agreeing and that is a miserable bug
# to chase.
set -euo pipefail

B=https://github.com/nflverse/nflverse-data/releases/download
NFLDATA=https://raw.githubusercontent.com/nflverse/nfldata/master/data

# Every successful download is also copied into .srccache, which the GitHub
# workflow carries from one run to the next. So when a source fails to download
# -- in September 2026 the depth chart file answered with server errors for a
# few minutes, presumably while nflverse was replacing it -- the build can fall
# back to the last good copy instead of failing outright.
CACHE=.srccache
mkdir -p "$CACHE/career"
LAST_CODE=""
# Adjustable only so the failure paths can be tested without waiting minutes.
RETRIES=${FETCH_RETRIES:-6}
DELAY=${FETCH_DELAY:-20}

# fetch <destination> <url>
# Returns 0 on success, 4 when the file does not exist (404), 1 on anything
# else. Retries transient trouble (timeouts, 408/429/5xx, refused connections)
# for up to about five minutes, but not a 404: a file that is not there yet will
# still not be there in twenty seconds. Downloads to a temporary name first, so
# a failed attempt can never leave a half-written file in place.
fetch() {
  local tmp="$1.part" code
  code=$(curl -sL --connect-timeout 20 --max-time 900 \
              --retry "$RETRIES" --retry-delay "$DELAY" --retry-max-time 300 --retry-connrefused \
              -o "$tmp" -w '%{http_code}' "$2" 2>/dev/null) || true
  if [ "$code" = "200" ] && [ -s "$tmp" ]; then
    mv "$tmp" "$1"
    cp "$1" "$CACHE/$1"
    return 0
  fi
  rm -f "$tmp"
  LAST_CODE="${code:-no response}"
  [ "$code" = "404" ] && return 4
  return 1
}

size() { du -h "$1" | cut -f1; }

# A source the build cannot do without.
get() {  # get <destination> <url>
  if fetch "$1" "$2"; then
    printf '  %-28s %s\n' "$1" "$(size "$1")"
    return 0
  fi
  if [ -s "$CACHE/$1" ]; then
    cp "$CACHE/$1" "$1"
    printf '  %-28s download failed (%s), using the copy from the last good build\n' "$1" "$LAST_CODE"
    echo "::warning::$1 could not be downloaded (HTTP $LAST_CODE); this build used the last good copy"
    return 0
  fi
  printf '  %-28s download failed (%s) and there is no earlier copy\n' "$1" "$LAST_CODE"
  echo "::error::$1 could not be downloaded (HTTP $LAST_CODE) from $2"
  exit 1
}

echo "current season data"
get depth_charts_2026.csv "$B/depth_charts/depth_charts_2026.csv"
get roster_2026.csv       "$B/rosters/roster_2026.csv"
get roster_2025.csv       "$B/rosters/roster_2025.csv"
get players_master.csv    "$B/players/players.csv"
get teams.csv             "$B/teams/teams_colors_logos.csv"
get sched.csv             "$B/schedules/games.csv"
get draft_picks.csv       "$B/draft_picks/draft_picks.csv"
get airports.csv          "$NFLDATA/airports.csv"

echo "last season stats"
get stats_2025.csv        "$B/stats_player/stats_player_reg_2025.csv"
get stats_week_2025.csv   "$B/stats_player/stats_player_week_2025.csv"
get team_2025.csv         "$B/stats_team/stats_team_reg_2025.csv"
get team_week_2025.csv    "$B/stats_team/stats_team_week_2025.csv"
get snaps.csv             "$B/snap_counts/snap_counts_2025.csv"

echo "charting"
for k in pass rush rec def; do
  get "advstats_week_$k.csv" "$B/pfr_advstats/advstats_week_${k}_2025.csv"
done

echo "contracts and play-by-play"
# Parquet, never the csv.gz: that gzipped CSV is stale and still reports expired
# deals as active. See build_contracts.py.
get contracts.parquet     "$B/contracts/historical_contracts.parquet"
get pbp2025.parquet       "$B/pbp/play_by_play_2025.parquet"

# Current season. These 404 until the first Tuesday of the season, which is a
# normal state, not a failure -- so this block must not abort the script.
echo "current season (optional until week 1 is played)"
# A source that may legitimately not exist yet. Only a 404 means "not published":
# this used to treat every failure that way, so a server hiccup would quietly
# drop the current season's stats from the site instead of being noticed.
optional() {  # optional <destination> <url>
  if fetch "$1" "$2"; then
    printf '  %-28s %s\n' "$1" "$(size "$1")"
  elif [ "$LAST_CODE" = "404" ]; then
    rm -f "$1"
    printf '  %-28s not published yet\n' "$1"
  elif [ -s "$CACHE/$1" ]; then
    cp "$CACHE/$1" "$1"
    printf '  %-28s download failed (%s), using the copy from the last good build\n' "$1" "$LAST_CODE"
    echo "::warning::$1 could not be downloaded (HTTP $LAST_CODE); this build used the last good copy"
  else
    rm -f "$1"
    printf '  %-28s download failed (%s), carrying on without it\n' "$1" "$LAST_CODE"
    echo "::warning::$1 could not be downloaded (HTTP $LAST_CODE); the build carried on without it"
  fi
}
optional stats_2026.csv       "$B/stats_player/stats_player_reg_2026.csv"
optional stats_week_2026.csv  "$B/stats_player/stats_player_week_2026.csv"
optional snaps_2026.csv       "$B/snap_counts/snap_counts_2026.csv"
optional injuries_2026.csv    "$B/injuries/injuries_2026.csv"
optional pbp2026.parquet      "$B/pbp/play_by_play_2026.parquet"
for k in pass rush rec def; do
  optional "advstats26_$k.csv" "$B/pfr_advstats/advstats_week_${k}_2026.csv"
done
optional qbr_week.csv         "$B/espn_data/qbr_week_level.csv"
optional team_2026.csv        "$B/stats_team/stats_team_reg_2026.csv"

# Madden ratings come from a committed CSV in a public repository, not from EA:
# there is no EA ratings API, and scraping their site is fragile and a terms
# question. build_madden.py fetches it directly, so nothing is needed here.

echo "career history"
mkdir -p career
for y in $(seq 2016 2025); do
  get "career/$y.csv" "$B/stats_player/stats_player_reg_$y.csv"
done

echo
echo "all sources downloaded"

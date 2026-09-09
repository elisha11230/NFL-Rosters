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

get() {  # get <destination> <url>
  curl -sSL --retry 3 --retry-delay 2 --fail -o "$1" "$2"
  printf '  %-28s %s\n' "$1" "$(du -h "$1" | cut -f1)"
}

echo "current season data"
get depth_charts_2026.csv "$B/depth_charts/depth_charts_2026.csv"
get roster_2026.csv       "$B/rosters/roster_2026.csv"
get roster_2025.csv       "$B/rosters/roster_2025.csv"
get players_master.csv    "$B/players/players.csv"
get teams.csv             "$B/teams/teams_colors_logos.csv"
get sched.csv             "$B/schedules/games.csv"
get draft_picks.csv       "$B/draft_picks/draft_picks.csv"

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
optional() {
  if curl -sSL --fail -o "$1" "$2" 2>/dev/null; then
    printf '  %-28s %s\n' "$1" "$(du -h "$1" | cut -f1)"
  else
    rm -f "$1"
    printf '  %-28s not published yet\n' "$1"
  fi
}
optional stats_2026.csv       "$B/stats_player/stats_player_reg_2026.csv"
optional stats_week_2026.csv  "$B/stats_player/stats_player_week_2026.csv"
optional snaps_2026.csv       "$B/snap_counts/snap_counts_2026.csv"
optional injuries_2026.csv    "$B/injuries/injuries_2026.csv"

echo "career history"
mkdir -p career
for y in $(seq 2016 2025); do
  get "career/$y.csv" "$B/stats_player/stats_player_reg_$y.csv"
done

echo
echo "all sources downloaded"

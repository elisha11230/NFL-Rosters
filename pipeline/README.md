# NFL depth chart viewer — data pipeline

Rebuilds `nfl-depth-chart.html` from scratch. No API key, no account, nothing paid.

## Refresh the data

```bash
pip install pandas

# 1. pull the sources (nflverse publishes these as GitHub release assets)
B=https://github.com/nflverse/nflverse-data/releases/download
curl -sL -o depth_charts_2026.csv "$B/depth_charts/depth_charts_2026.csv"   # all snapshots, not just the newest
curl -sL -o roster_2026.csv       "$B/rosters/roster_2026.csv"
curl -sL -o roster_2025.csv       "$B/rosters/roster_2025.csv"   # for movement tags
curl -sL -o stats_2025.csv        "$B/stats_player/stats_player_reg_2025.csv"
curl -sL -o teams.csv             "$B/teams/teams_colors_logos.csv"
curl -sL -o team_2025.csv         "$B/stats_team/stats_team_reg_2025.csv"
curl -sL -o team_week_2025.csv    "$B/stats_team/stats_team_week_2025.csv"
curl -sL -o sched.csv             "$B/schedules/games.csv"
curl -sL -o players_master.csv    "$B/players/players.csv"

# advanced: PFR charting + snap counts
for k in pass rush rec def; do
  curl -sL -o "advstats_week_$k.csv" "$B/pfr_advstats/advstats_week_${k}_2025.csv"
done
curl -sL -o snaps.csv "$B/snap_counts/snap_counts_2025.csv"

# contracts -- parquet, NOT the csv.gz (see note below)
curl -sL -o contracts.parquet "$B/contracts/historical_contracts.parquet"

# highlights (20MB)
curl -sL -o pbp2025.parquet "$B/pbp/play_by_play_2025.parquet"

# career history (build_career.py downloads these itself on first run)
mkdir -p career
for y in $(seq 2016 2025); do
  curl -sL -o "career/$y.csv" "$B/stats_player/stats_player_reg_$y.csv"
done

# 2. verify every source before trusting any of it
python3 verify_sources.py     # non-zero exit means do not build

# 3. build nfl_data.json
python3 build_data.py

# 4. assemble the single distributable file (icons + data)
python3 build_app.py
```

Run it on a cron or a GitHub Action during the season. Depth charts move weekly.

## Files

| File | What it does |
|---|---|
| `build_data.py` | Joins the sources, computes league ranks, emits `nfl_data.json` |
| `build_teams.py` | Records, playoff finishes, offense/defense/ST unit ranks |
| `build_advanced.py` | PFR charting stats and snap counts, joined on `pfr_id` |
| `build_contracts.py` | Active contracts from OverTheCap, with APY rank by position |
| `build_coaches.py` | Coaching staffs, plus head coach tenure and record |
| `build_movement.py` | Depth chart movement, diffed across the snapshot history |
| `build_roster.py` | Cap allocation by position group, and roster age |
| `build_schedule.py` | 2026 slate, bye week, strength of schedule |
| `build_injuries.py` | Injury designations. Dormant until the season starts |
| `build_highlights.py` | Biggest plays per player, pulled from play-by-play |
| `build_situational.py` | Third down, red zone and short-yardage splits |
| `build_career.py` | Season-by-season career stats back to 2016 |
| `build_gamelog.py` | Week-by-week logs for last season |
| `build_battles.py` | Contested depth chart spots, from the snapshot history |
| `build_history.py` | Ten seasons of records, division finishes and playoff results |
| `build_draft.py` | Draft position per player, and roster construction per team |
| `build_h2h.py` | Head-to-head records between franchises since 1999 |
| `build_timeline.py` | Weekly depth chart history, as a baseline plus diffs |
| `build_comps.py` | Nearest-neighbour player comparables |
| `build_leaders_history.py` | League leaders 2021-2025 with year-on-year movement |
| `verify_sources.py` | Checks every source for size, parseability and recency |
| `coaches_2026.py` | Hand-maintained staff list. Update each offseason |
| `check_layout.py` | Field collision check. Run after editing `FORMS` |
| `make_icon.py` | Draws the app icon, exports PNG + SVG at every size |
| `embed_icons.py` | Turns those into data URIs and a web app manifest |
| `build_app.py` | Final assembly. Injects icons + data, writes the HTML |

The template is never modified by the build — `<!--ICONS-->` and `/*__DATA__*/`
are the two injection slots, so it stays readable and editable.

## League leaders

The **Leaders** button opens a leaderboard across every ranked number in the
payload — 94 player categories plus contracts and seven team ones. It needs no
extra data: every stat already carries its rank and pool size, so this just
inverts what is there.

Categories with a box-score history also carry a year strip: 2021 through 2025,
each name showing how far it moved from the season before.

Categories are grouped by position rather than flat, because that is how the
ranks were computed. A single "sacks" leaderboard mixing edge rushers with
cornerbacks would be noise; "Defensive line / Sacks" is a real ranking of 183
comparable players. Anything with fewer than ten ranked players is dropped rather
than shown as a thin list.

## Learn mode

The rest of the app assumes you already know who these players are. Three parts
assume you do not:

- **Learn** (button above the field) opens a quiz. Three formats — name the face,
  name the starter at a position, name the team — over either the 97 best players
  or all 883 starters. Anything missed is pushed back into the same session rather
  than marked wrong and forgotten, because recall with a second attempt is what
  actually fixes a name.
- **If you stopped watching** in the team panel takes a year and shows how much of
  that first string arrived after it. Stop at 2021 and 53% of the league's
  starters are people who had not played a down. The "still here from before" list
  matters as much as the new one — it is the part you already know.
- **Simple** hides movement badges, Top 100 markers, depth counts and the time
  slider, leaving names and faces.

Debut year comes from career stats where available, then years of experience,
then the rookie flag. Every player on a chart resolves to a year.

## Deep links

The app keeps its state in the URL hash, so views are bookmarkable and shareable:

| Hash | Opens |
|---|---|
| `#/PHI` | Philadelphia, offense |
| `#/PHI/def` | Philadelphia, defensive alignment |
| `#/p/00-0036389` | That player, on the field, profile open |

Browser back and forward work as expected. Press `/` anywhere to focus search.

## A note on file size

The single file is now 2.33 MB. That is fine opened locally, and acceptable
served over https, but it is the practical limit for this approach. The next
substantial feature should come with a change: move `nfl_data.json` out of the
HTML and fetch it at load, so the page renders immediately and the data streams
in. That also lets you cache the payload separately from the app, and it needs
hosting — which is the same step described below.

## Turning over to the new season

The app was built during an offseason, so everything in it described 2025. Two
modules handle the switch and both are no-ops until real games exist:

- `build_current.py` pulls the current season's player stats. Ranks are withheld
  until at least two weeks have been played, because one week ranks nobody
  meaningfully; before that it shows totals and says so. Profiles then lead with
  this season and label the old block "Last season".
- `build_standings.py` computes standings from the schedule file, which gains
  scores as games are played. Ordering is win rate, then division record, then
  points difference — close to the league's tiebreakers but not the full dozen
  steps, and the page says so.

Both appear on their own a few days after week 1. The **Standings** tab on the
scores page stays hidden until there is something to show.

`fetch_sources.sh` treats these as optional: a 404 before the season is a normal
state, not a failure, so it must not abort the run. `verify_sources.py` checks
them only if they are present.

## Scores and schedule

The **Scores** button opens a full season view at `#/scores`, or `#/scores/7` for
a particular week. Two sources, each used for what it is good at:

- **The slate** — all 272 fixtures with dates and kickoff times, already in the
  payload. Future weeks therefore work with no network at all, and the page draws
  instantly rather than sitting blank behind a request.
- **ESPN** — asked per date for whichever week you are looking at, and only for
  scores. Results fill in over the fixtures once they arrive.

Kickoff times are stored as US Eastern and rendered in the reader's own zone.
Finished games mark the winner; live ones are outlined in red. Tapping a played
game opens the box score.

Tapping a fixture that has not kicked off opens a **preview** instead of an empty
box score: the betting line and total, both sides' records and unit ranks, the
head-to-head record since 1999, individual matchups, and every Top 100 player in
the game with their movement.

The **injury report** shows both sides with a severity dot, the designation and
the body part, and any player in a matchup who may not play is flagged there too
— a matchup means something different if one of them is doubtful.

Matchups pair a player against the unit he will actually face — quarterback
against the corner he sees most, lead back against the middle linebacker, edge
rusher against the left tackle — using the depth charts and last season's ranks
already loaded. Nothing is predicted; every figure is something that happened.

The betting line rides along on the scoreboard response, so it costs no extra
request. It is labelled as the market's view rather than a recommendation.

It is a route inside the app rather than a separate file, so a name in a box
score still opens that player's profile.

## Hold a chip to switch players

Holding a player on the field opens the depth at that spot right under your
thumb: everyone listed there, with number, Top 100 rank and injury status, and a
tap puts any of them on the field. Right-click does the same on a desktop.
91% of slots have somebody to switch to.

This replaced a four-step route — tap the chip, scroll the panel, find the depth
list, tap a name — for answering "who else plays here".

Built on pointer events rather than touch events, so one implementation covers a
finger, a mouse and a stylus. The press is cancelled if the finger moves more
than ten pixels, otherwise every scroll that began on a chip would open it, and
the click that follows a completed hold is swallowed so the profile does not open
underneath.

## How it works — the concepts library

Seventeen animated diagrams behind the **How it works** button: eight routes,
four coverage ideas, three from the run game, two on pressure.

This replaced a live play animation that was cut. That version reconstructed the
last real play on a field, and it did not earn its place: the play text sitting
directly above it was faster to read and more precise, the route shapes were
invented anyway, and there was no defence in it, so there was nothing to watch.
Motion without information is decoration.

Invented motion is dishonest when it claims to show what happened in a real play,
and entirely legitimate when it is teaching — a whiteboard diagram is meant to be
idealised. So the same engine now answers the questions the rest of the app
cannot: what a slant looks like, why a nickel back is on the depth chart, where
the A gap is, why the left tackle is paid like a quarterback.

Offence is drawn light and defence dark, which is the convention every coaching
diagram uses. Zone coverages draw the patch of grass each defender is responsible
for, because that is the whole point of a zone and invisible otherwise.

## Lineup game

The **Lineup** button opens the depth chart in reverse: the formation drawn empty
with only position labels, and eleven real players in a tray with their positions
hidden. Put each man where he belongs, then check.

Placing is **tap-select then tap-place**, not HTML5 drag-and-drop. Drag events do
not fire on touch screens at all, and this is most useful on a phone, so tapping
is the real mechanism and dragging is layered on top for a mouse.

**Mirrored and depth-ordered slots are graded as interchangeable.** Nobody can
reasonably know which of three receivers is "WR2", so any of the three counts, and
the same goes for the two guards, the safeties, the corners and the interior
line. Left tackle against right tackle is a real distinction and stays graded.
Without this the game would punish guesses that were not guessable.

Best score per team and unit is saved alongside the quiz progress.

## Visual views

- **Faces** (button above the field) is every player on the roster as a
  photograph, grouped by position, starters first. The field diagram explains
  structure; structure is not the hard part when you are learning a league.
- **Target charts** plot every pass thrown at a receiver by how far it travelled
  in the air and which third of the field it went to. Filled means caught, gold
  means a touchdown. The scatter shows a role no stat line does: Puka Nacua's
  average depth is 10.1 yards, Saquon Barkley's is 0.6.
- **Run gap charts** put a back's carries in the nine location/gap buckets, shaded
  by volume. Nine cells say more than a cloud of dots would.
- **Career arcs** draw the season table as a line with the best year marked, so a
  rise, a peak or an injury year reads instantly.
- **Season strips** show ten years as blocks sized by points difference.
- **Cap treemaps** use area rather than a stacked bar, because money is a
  proportion question and area reads proportion better.
- **Play arrows** draw the most recent live play between the actual player chips.
  The participants are read out of the play text — passer, target, ball carrier,
  tackler — resolved to players, and their positions read from the DOM so the line
  always agrees with what is on screen. Everyone involved is ringed: green for the
  offence, amber for the defender.

  An earlier version guessed instead: a fixed start point, a direction from the
  word "left", a length from the yardage. It ignored the one thing this app has,
  which is knowing where every player is standing.

  Nothing is drawn unless it can be drawn honestly. Wrong team on screen, wrong
  unit, a backup who is not on the chart, a field goal or a penalty — all produce
  no line rather than a plausible-looking invention. A completion connects two
  chips, an incompletion dashes to the intended target, a run carries upfield by
  the distance actually gained, and a sack pushes backwards.

`build_charts.py` stores a target as `[air_yards, direction, flags]` — three small
numbers, because a busy receiver has over two hundred of them.

## Watch mode

A **Watch** button appears on the live strip while a game is actually in progress.
It opens a full-screen view meant to sit beside a television: large score, clock,
down and distance, field position, win probability, and a reverse-chronological
play feed that refreshes every twenty seconds.

**Every name in the play feed is tappable.** Play text arrives as
`J.Hurts pass short right to D.Smith for 8 yards`, and knowing who those people
are is the entire point of this app, so names are matched against the two rosters
in the game and turned into links to the player's profile.

Matching is first-initial plus surname, scoped to the two teams playing rather
than the whole league, which keeps collisions rare. Where a club genuinely has
two players sharing a key, the one higher on the depth chart wins — announcers
mean the starter far more often than his backup. Suffixes (Jr, III) are stripped
before matching, and the `NE-K.Byard` form the feed uses for recoveries and
returns still resolves.

**The defence is pulled out of the parentheses.** Play text follows firm
conventions — a trailing `(C.Gonzalez)` is a tackle, `(C.Gonzalez, Z.Baun)` an
assist, names after `sacked` a sack, `INTERCEPTED by` a takeaway, `FUMBLES (…)`
the forcer and `RECOVERED by` the recoverer. Those are parsed into labelled tags
under each play, with the names linked like any other. Left inline they are easy
to miss, which hides half the game from somebody still learning who these people
are.

**Watch mode also ranks the defence live**, weighting sacks and takeaways above
raw tackle counts — two sacks is a bigger afternoon than eleven tackles, and a
straight tackle count would say otherwise.

Play text is built as DOM nodes rather than markup, so nothing arriving from the
feed is ever interpreted as HTML.

## Other live sources

Four more, all free and three needing no key at all:

- **Weather** from Open-Meteo, for the preview. Requested only for outdoor games
  at a club's usual ground: indoor fixtures and the nine international games carry
  no coordinates, so no request is made. Wind over about 15 mph, steady rain or
  real cold get called out, because those measurably suppress scoring.
  Coordinates come from nflverse's airports file — an airport sits ten or twenty
  miles from its stadium, which does not matter when forecasts are gridded at
  roughly that scale.
- **Inactives** from ESPN, which land about ninety minutes before kickoff and
  settle what a Wednesday "questionable" only hinted at.
- **Trending players** from Sleeper's public feed: how many fantasy managers added
  a player in the last day, across millions of leagues. A crowd noticing something
  is a signal this app cannot produce from its own data, and a good breakout
  detector.
- **Line movement** without a paid odds key. Multi-book history costs money, but
  the useful part is the drift, so the first line ever seen for a fixture is
  remembered locally and the change shown against it. It fills in over a week
  rather than appearing at once, and the note says so.

`fetch_sources.sh` also now pulls the current season's play-by-play and team stats
when they exist, so situational splits, target charts and highlights start
covering games that just happened.

## Live game day

The app polls ESPN's undocumented scoreboard endpoint. No key, no account. When
a game is on it shows a score strip above the field, and any player with a stat
line that day gets it printed under his chip and on his profile — the depth chart
annotated with what is actually happening.

Matching works because every player carries `eid`, ESPN's athlete id, taken from
the master players table. All 2,956 resolve.

What it shows, all of it optional and all of it hidden when the feed is not
carrying that field:

- **Score strip** above the field, with down and distance and win probability
- **Today's game** panel in the team panel: score, down and distance, a field
  position bar, last play, a win probability sparkline, and how many projected
  starters have actually recorded a stat
- **Full box score** — click any score. Team totals side by side, then a tab per
  side with every category the feed is carrying: passing, rushing, receiving,
  defence, kicking, returns. Categories are read from the response rather than
  hardcoded, because they differ between a game in progress and a finished one,
  and between preseason and regular season. Players on a depth chart in the app
  are clickable and open their profile; camp bodies who are not still appear, as
  plain rows
- **Drives**, most recent first, with result, plays, yards and time
- **Green ring** on the chip of any player confirmed on the field today, as
  opposed to merely projected there
- **"Against his usual day"** on a player profile: today's figures set beside his
  own per-game average for last season, so a number means something

The field position bar is deliberately its own strip and not drawn on the
formation. The formation shows who lines up where; it is not a scale map of the
field, and spotting a real yard line on it would misrepresent both.

The strip has three treatments and only one of them is loud. A game in progress
gets the red background and a pulsing dot; a scheduled game gets neutral styling,
the opponent and the kickoff time, and **no score** — inventing a 0-0 before
kickoff reads as a live tie. A finished game shows the final quietly.

Polling gap is re-evaluated after every refresh rather than fixed at startup, so
a game that is merely scheduled when the page loads causes the app to tighten from
five minutes to thirty seconds once it actually kicks off.

**This endpoint is not ours.** It is undocumented and ESPN can change or remove it
without notice, so every call is wrapped: if the request is blocked, rate limited,
or the response shape changes, the live strip does not appear and nothing else
notices. Polling is 30 seconds while a game is live and 5 minutes otherwise —
polling harder would be rude and risks being cut off.

If direct browser access turns out to be blocked by CORS, set `PROXY` at the top
of the live section to a Cloudflare Worker URL. The worker is about twenty lines:
fetch the upstream URL, return it with `Access-Control-Allow-Origin: *`.

## Saved learning progress

Now that the app is served over https, browser storage works, so the quiz
remembers what you know. Each player is a card in a Leitner box: a right answer
promotes it, a wrong one sends it back to the start, and higher boxes come back
after longer gaps (1, 3, 7, then 21 days). Questions are drawn due-first, then
never-seen, then the rest.

A name counts as learned after three correct answers in a row. The setup screen
shows how many you know, how many are due, and your daily streak. If storage is
unavailable the quiz still runs, it just starts fresh each time.

## Putting it on an Android home screen

The icons are embedded in the HTML, so the browser tab favicon works straight
away from a local file. A **home screen icon is different**: Chrome will not load
a web app manifest from a `file://` page, so opening the downloaded file and
tapping "Add to Home screen" gives you a generic shortcut.

To get the real icon and a full-screen app, serve it over https. The fastest
free option:

1. Make a GitHub repo, upload `nfl-depth-chart.html`, rename it `index.html`
2. Settings → Pages → deploy from `main` branch, root
3. Open the resulting `https://…github.io/…` URL in Chrome on Android
4. Menu → Add to Home screen

You get the icon, no browser chrome, and the app is reachable from any device.
The `icons/` folder holds the same art as standalone files if you would rather
link them from a hosted page than rely on the embedded data URIs.
| `top100.py` | The Top 100 list plus name aliases for roster matching |
| `app_template.html` | The app. `/*__DATA__*/` is the injection point |

## Season rollover

- Bump the year in the download URLs and in `stat_line`'s season.
- Add the new Top 100 to `top100_2025.py` when NFL Network finishes revealing it.
  The 2026 list concludes September 4, 2026.
- Check the `UNMATCHED` line the build prints. Anything listed there needs either
  an entry in `ALIASES` (roster spells the name differently) or in
  `NOT_ON_2026_ROSTER` (player left the league).

## Notes on the data

- **Formation slots are free.** nflverse's depth chart already assigns each player
  a `pos_grp` (`3WR 1TE`, `Base 4-3 D`, `Base 3-4 D`, `Special Teams`), a
  `pos_slot`, and a `pos_rank`. `FORMS` in the template only maps those slots to
  x/y coordinates. You never have to guess who lines up where.
- **Receivers rank across the group, not per slot.** Slot 1 holds WR1/4/7/10,
  slot 2 holds WR2/5/8/11, slot 8 holds WR3/6/9/12. Sort by `rank` within a slot
  and take the first — do not filter on `rank == 1`.
- **League ranks** are computed per position bucket among players who cleared a
  volume gate (see `VOLUME_GATE`), so a backup QB with four attempts is not
  ranked first in interceptions.
- **Yards allowed** is not published directly. `build_teams.py` takes the weekly
  team stats, re-keys each row by `opponent_team`, and sums — one team's offensive
  output in a game is by definition what the other defense gave up.
- **Unit ranks.** Offense and defense rank on points per game, which is the number
  people actually argue about. Special teams has no single headline stat, so it
  averages four component ranks (field goal rate, return yardage, return
  touchdowns, blocks allowed) and ranks the averages. Ties are real and share a
  rank: Buffalo and Detroit both scored 481 points, so both sit 4th on offense.
- **Playoff finish** is derived from the schedule, not hardcoded. A team's result
  is the round of its last postseason game plus whether it won that game.
- **The season roster is not complete.** It is a snapshot and lags signings, so
  roughly 110 players on a current depth chart are missing from it entirely.
  `players_master.csv` covers every player nflverse knows about and is used as a
  fallback for position, jersey number, headshot and bio. Without it those
  players silently lose their stat lines.
- **Never bucket a player by their depth-chart position code.** Those encode
  alignment (`LDE`, `RILB`) or just a role (`KR`, `H`), not the player's actual
  position. Resolution order is roster, then master table, then the stats file,
  and only then the depth-chart code. The build prints `STATS DROPPED` if any
  player with a real stat line failed to get one attached — that line should
  always read "every player ... has it attached".
- **Advanced stats join on `pfr_id`, not `gsis_id`**, which reaches about 2,600
  of the 2,900 players on a depth chart. Anyone unmatched gets no advanced block
  and the disclosure is hidden rather than shown empty.
- **Rate stats are recomputed from season totals**, never averaged across weeks —
  averaging a per-game rate overweights low-volume games.
- **Rank gates use the volume that fits the metric.** Coverage stats gate on how
  often a player was thrown at; pass-rush stats gate on snaps, because a pure
  rusher is rarely targeted and would otherwise be excluded from his own best
  category. Below the gate the value still shows, just without a rank.
- **Rookie and movement tags.** Last season's roster is compared against the
  current depth chart to flag anyone who changed teams. Draft position comes from
  `roster_2026.csv`, not the master table, which has not been backfilled with
  2026 rounds. Note `draft_number` is a player's career draft slot, not a
  2026-only field, so it is only surfaced on the rookie tag.
- **A player can be a rookie and still appear on last season's roster** if he
  spent that year on a practice squad without playing. Showing both tags reads as
  a contradiction, so the rookie tag wins and the movement tag is suppressed.
- **Contracts: read the parquet, never the `csv.gz`.** That release ships both,
  and the gzipped CSV is stale — it stops at deals signed in 2022 and still flags
  expired contracts as active, so it reports a veteran's rookie deal as his
  current salary. The parquet is the maintained asset and runs to the current
  league year. `build_contracts.py` refuses to run if the newest contract it sees
  is more than a year old, so this cannot regress silently.
- **Contract money is already in millions** in that file: `value` of 41.2 means
  $41.2M. Do not multiply.
- **Salary rank is by average per year**, which is the only figure that compares
  sensibly across contracts of different lengths. Total value rewards long deals
  and guaranteed money rewards recent ones.
- **Do not trust the schedule's coach column for current staff.** It looks
  authoritative and is partly right, which makes it dangerous. For 2026 it
  reflects seven of the ten head coaching changes and misses three, still listing
  Jonathan Gannon in Arizona, Raheem Morris in Atlanta and Sean McDermott in
  Buffalo. Names come from `coaches_2026.py` instead; that file asserts its head
  coaches against the reported hire list on import, so a careless edit cannot
  quietly reintroduce a departed coach.
- **The schedule is still used for tenure and record**, which is what it is
  actually reliable at: counting seasons and games a named coach worked for a
  named team. Feed it the correct name and the arithmetic is sound.
- **Coordinators are not in nflverse in any form.** Names and start years are
  hand maintained in `coaches_2026.py`, taken from Wikipedia's three coordinator
  pages, whose rows cite dated club announcements, and cross checked against a
  published 2026 staff table. Re-check before each season and after any
  in-season firing.
- **Head coach start years are derived, coordinator start years are stored.**
  The schedule can confirm which seasons a named head coach worked for a team,
  so deriving is safer than transcribing. It knows nothing about coordinators,
  so those years live in the file and the import asserts each one is present and
  plausible.
- **Tampa Bay has no separate defensive coordinator** in most published tables.
  Todd Bowles has called that defense since 2019 and kept the duty after being
  promoted to head coach in 2022, so he is listed in both roles rather than
  leaving a hole.
- **Tenure walks back only through consecutive seasons.** A coach who left a team
  and later returned is credited with his current stint, not the union of both.
- **The depth chart file is a history, not a snapshot.** It holds 132 captures
  going back to March, and reading only the newest one throws away the most
  interesting thing in it. `build_movement.py` diffs the current chart against a
  fortnight ago and against the first capture of the year.
- **Movement is measured per position, not per formation slot.** Receivers are
  ranked across the whole group and their slot assignment shuffles as the order
  changes, so slot-to-slot comparison invents moves that did not happen.
- **Cap allocation is a shape, not a cap sheet.** Contracts exist for roughly
  2,200 of the 2,900 players on a depth chart; unsigned rookies and camp bodies
  are missing. The UI states the coverage rather than implying completeness.
- **The injury report has two columns, and early in a week only one is filled.**
  The game designation (out, doubtful, questionable) is not published until late
  in the week; before that all there is is who practised and how much. Reading
  only `report_status` finds nothing on a Wednesday, which is exactly when
  somebody opens a preview. `build_injuries.py` reads the game designation when
  it exists and falls back to practice participation, labelling the two
  differently so a full participant is not dressed as a doubt.
- **Injuries never fall back to last season.** The module looks for the current
  year and reports nothing when it is absent; showing 2025 designations as
  current would be the same failure as the stale contracts CSV.
- **Highlights are text, not video.** There is no free structured source of NFL
  game footage; the league licenses it exclusively and there is no public clip
  API. What exists is every play of the season with a description and an EPA
  value, which answers "what were his biggest plays" in words. Profiles also
  carry a constructed YouTube search link, which needs no API key and lands on
  official uploads for anyone well known enough to have them.
- **Plays rank on EPA, not yardage**, because EPA already knows twelve yards on
  3rd-and-11 beats twenty on 1st-and-10.
- **Fumble recovery is deliberately not a credited role.** The recoverer can be
  on either side, so flipping the EPA sign the way we do for genuine defensive
  plays turned a quarterback recovering his own interception into a 6-EPA
  "highlight". A player's own turnovers are filtered out explicitly too.
- **Run `verify_sources.py` before every build.** Two sources have already failed
  silently in two different ways, and both produced a build that looked correct:
  the contracts `csv.gz` downloaded and parsed fine while being three years stale,
  and `ngs_passing.csv` 404'd, leaving nine bytes reading "Not Found" on disk with
  curl exiting 0. Size, parseability and recency are three separate questions and
  a file can pass two while failing the third.
- **Situational splits cover skill positions only.** Passer, rusher and target are
  the only roles play-by-play identifies cleanly on every snap. Tackle credit in
  the raw feed is inconsistent, so defensive situational work is not attempted;
  the charted coverage and pass-rush numbers already cover that ground.
- **Third and fourth down have separate conversion flags.** Using only
  `third_down_converted` scores every fourth-down conversion as a failure, which
  understated short-yardage rates by roughly half before it was caught.
- **Career history starts in 2016 by choice.** nflverse goes back to 1999, but
  coverage of players still on a 2026 chart collapses before 2016 — twelve rows
  in 2010 against 1,763 in 2025. Going further back roughly doubles the download
  for a rounding error of extra seasons. Veterans whose careers predate the
  window are flagged in the UI rather than shown as if 2016 were their rookie
  year.
- **Never use `rookie_season` from the master table to bound a career.** It
  carries name collisions: eight players on current charts inherit an older
  player's record, one of them claiming a 1976 rookie season. Career stats join
  on `player_id`, so those cannot leak in.
- **Position battles score reshuffling, not just lead changes.** A job can be
  genuinely contested while the same man keeps ending up first — Miami's right
  tackle had zero lead changes and three reorderings behind it. Scoring on flips
  alone would have missed exactly the spots that resolve in preseason.
- **Battle detection thins the snapshot history to one per day.** Consecutive
  captures hours apart say nothing new, and comparing every pair counts a single
  change many times over.
- **Game logs come from the weekly stats file, not play-by-play.** Smaller,
  cleaner, and already aggregated. Weeks with no game are absent rather than
  zeroed, so a bye and a healthy scratch do not look alike.
- **Never load `contracts.parquet` or `play_by_play` whole.** Both carry columns
  that explode in memory: contracts has `season_history` and `contract_history` as
  list-of-struct, turning a 6MB file into enough to get the build OOM-killed in a
  4GB container, and play-by-play's 372 columns take 174MB against 14MB for the
  15 actually used. Both modules declare a `COLUMNS` list; pass it to
  `read_parquet`.
- **Read the depth chart file once.** It is 38MB and four modules want it. The
  build now keeps `DC_ALL` (full history, for movement and battles) alongside the
  newest snapshot, rather than each module re-reading it.
- **Team history folds relocations.** The schedule files the Chargers' 2016 under
  `SD` and the Raiders' 2016-19 under `OAK`. Without folding those in the league
  appears to have 34 teams and two franchises lose seasons. Those years are
  marked with an asterisk and the old city named, rather than silently
  attributing a San Diego season to Los Angeles.
- **Do not name a DataFrame column `div`.** `DataFrame.div` is pandas' division
  method, so attribute access returns the operator instead of the column and
  fails with a type error far from the cause.
- **`draft_picks.csv` uses Pro Football Reference team codes**, not nflverse
  ones: GNB, KAN, LVR, LAR, NWE, NOR, SFO, TAM. Joining on team without
  translating silently drops eight franchises.
- **This year's draft class has no gsis ids yet.** `draft_picks.csv` lists them
  under placeholder PFR ids like `MEN516487`, so they are matched on pick number
  instead, which is unique within a draft. Draft data is layered: master table
  first, then draft_picks, then the roster's `draft_number`.
- **Head-to-head uses 1999 onward, not the ten-year window.** A non-division
  opponent is met three or four times a decade and a 2-1 record says nothing.
  Since 1999 a division rival is worth about fifty games.
- **The timeline is stored as a baseline plus weekly diffs.** Every week in full
  costs about 1MB; only a fraction of slots change week to week, so recording just
  those brings the same information to roughly 0.16MB. Replaying all diffs must
  reproduce today's chart exactly — that is the test worth keeping.
- **Weekly, not daily.** Consecutive daily snapshots are mostly identical, and a
  slider with 140 stops that mostly do nothing is worse than one with 23 that each
  mean something.
- **Comparables z-score every feature within the position group** before measuring
  distance. Without it, receiving yards (hundreds) drowns out age (tens) and
  height (inches) entirely and every comp becomes "a player with similar yardage".
- **Historical leaderboards are computed from the season files, not the current
  payload.** A 2021 board must include whoever actually led that year; 20% of the
  names across the five years are no longer on any depth chart, and filtering to
  the current 2,956 players would quietly rewrite history. Those rows render
  greyed and unclickable.
- **Six seasons are ranked to display five**, so every name on the 2021 board has
  a 2020 rank to move against.
- **"Unranked last year" is not the same as "first time".** Aidan Hutchinson led
  nothing in 2024 because he broke his leg, not because he was new. The build
  checks whether a player appeared in the previous season at all before calling
  a debut, and labels the two cases differently.
- **Movement is a change in rank, not in the number.** A player can gain yards and
  still fall.
- **Names are not unique, so the Top 100 cannot be matched on name alone.**
  Cleveland have a rookie linebacker called Justin Jefferson, and there is a
  Byron Young on the Rams and another in Philadelphia. Scoring each player
  independently badges both, because each looks plausible by itself. `top100.py`
  carries a position and club for every entry, and `assign_top100` compares the
  candidates for a rank against each other so exactly one takes it.
- **Badges are resolved after the roster is built**, not while players are being
  created, because a shared name can only be broken with a club and that is not
  known during the first pass.
- **Always ask the CDN for the size you are going to draw.** Headshots sit on
  NFL.com's Cloudinary, which serves whatever the URL requests. The stored base
  asks for `f_auto,q_auto` and no dimensions, so it returned a full-resolution
  portrait for a circle drawn at 44px. `imgUrl(player, width)` inserts
  `c_fill,g_face,w_N` into the transform, which is by far the biggest speed win
  available here.
- **Sizes snap to four buckets** (96, 128, 192, 320) rather than the exact pixel
  size of each element. Every distinct URL is its own CDN cache entry, so a few
  shared sizes beat a bespoke one per component.
- **`faceImg()` is the only place an `<img>` is built**, so lazy loading and async
  decoding are applied once rather than at sixteen call sites. Anything in a long
  scrolling list is lazy; the field and profile are not, because they are visible
  immediately.
- **Headshots** come from NFL.com's CDN. Fine for a private project. If this ever
  goes public you need licensed images — see SportsDataIO.

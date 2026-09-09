"""
2026 NFL coaching staffs, with the year each coach took the job.

WHY THIS FILE EXISTS
--------------------
nflverse carries a head coach on every game in the schedule, and that column is
tempting because tenure and record fall out of it for free. But for 2026 it is
only partly updated: of the ten head coaching changes this offseason it reflects
seven and misses three. It still lists Jonathan Gannon in Arizona, Raheem Morris
in Atlanta and Sean McDermott in Buffalo, all of whom were replaced. A source
that is wrong for three teams while looking right for twenty-nine is worse than
one that is uniformly stale, so head coach names come from here instead.

Coordinators are not in nflverse at all, in any form.

The schedule is still used, but only for what it is reliable at: counting the
seasons and games a named head coach actually worked for a named team. Head
coach `since` years are therefore derived, not stored here.

VERIFICATION
------------
Head coaches cross checked against NFL.com's coaching tracker, ESPN, Yahoo and
Fox Sports, which independently agree on the same ten changes:
  Saleh (TEN), Harbaugh (NYG), Stefanski (ATL), Monken (CLE), LaFleur (ARI),
  Kubiak (LV), Minter (BAL), Hafley (MIA), McCarthy (PIT), Brady (BUF)
Coordinator names and start years come from Wikipedia's three coordinator pages,
whose entries cite dated club announcements, cross checked against a published
2026 staff table.

Compiled 30 July 2026. Staffs change; re-check before each season and after any
in-season firing.
"""

# team: {role: (name, year they took this job with this team)}
# Head coach start years are derived from the schedule, so only the name is here.
STAFFS_2026 = {
    # ---- AFC East
    "BUF": {"hc": "Joe Brady",
            "oc": ("Pete Carmichael Jr.", 2026), "dc": ("Jim Leonhard", 2026),
            "st": ("Jeff Rodgers", 2026)},
    "MIA": {"hc": "Jeff Hafley",
            "oc": ("Bobby Slowik", 2026), "dc": ("Sean Duggan", 2026),
            "st": ("Chris Tabor", 2026)},
    "NE":  {"hc": "Mike Vrabel",
            "oc": ("Josh McDaniels", 2025), "dc": ("Zak Kuhr", 2026),
            "st": ("Jeremy Springer", 2024)},
    "NYJ": {"hc": "Aaron Glenn",
            "oc": ("Frank Reich", 2026), "dc": ("Brian Duker", 2026),
            "st": ("Chris Banjo", 2025)},
    # ---- AFC North
    "BAL": {"hc": "Jesse Minter",
            "oc": ("Declan Doyle", 2026), "dc": ("Anthony Weaver", 2026),
            "st": ("Anthony Levine Sr.", 2026)},
    "CIN": {"hc": "Zac Taylor",
            "oc": ("Dan Pitcher", 2024), "dc": ("Al Golden", 2025),
            "st": ("Darrin Simmons", 2003)},
    "CLE": {"hc": "Todd Monken",
            "oc": ("Travis Switzer", 2026), "dc": ("Mike Rutenberg", 2026),
            "st": ("Byron Storer", 2026)},
    "PIT": {"hc": "Mike McCarthy",
            "oc": ("Brian Angelichio", 2026), "dc": ("Patrick Graham", 2026),
            "st": ("Danny Crossman", 2026)},
    # ---- AFC South
    "HOU": {"hc": "DeMeco Ryans",
            "oc": ("Nick Caley", 2025), "dc": ("Matt Burke", 2023),
            "st": ("Frank Ross", 2021)},
    "IND": {"hc": "Shane Steichen",
            "oc": ("Jim Bob Cooter", 2026), "dc": ("Lou Anarumo", 2025),
            "st": ("Brian Mason", 2023)},
    "JAX": {"hc": "Liam Coen",
            "oc": ("Grant Udinski", 2025), "dc": ("Anthony Campanile", 2025),
            "st": ("Heath Farwell", 2022)},
    "TEN": {"hc": "Robert Saleh",
            "oc": ("Brian Daboll", 2026), "dc": ("Gus Bradley", 2026),
            "st": ("John Fassel", 2025)},
    # ---- AFC West
    "DEN": {"hc": "Sean Payton",
            "oc": ("Davis Webb", 2026), "dc": ("Vance Joseph", 2023),
            "st": ("Darren Rizzi", 2025)},
    "KC":  {"hc": "Andy Reid",
            "oc": ("Eric Bieniemy", 2026), "dc": ("Steve Spagnuolo", 2019),
            "st": ("Dave Toub", 2013)},
    "LAC": {"hc": "Jim Harbaugh",
            "oc": ("Mike McDaniel", 2026), "dc": ("Chris O'Leary", 2026),
            "st": ("Ryan Ficken", 2022)},
    "LV":  {"hc": "Klint Kubiak",
            "oc": ("Andrew Janocko", 2026), "dc": ("Rob Leonard", 2026),
            "st": ("Joe DeCamillis", 2026)},
    # ---- NFC East
    "DAL": {"hc": "Brian Schottenheimer",
            "oc": ("Klayton Adams", 2025), "dc": ("Christian Parker", 2026),
            "st": ("Nick Sorensen", 2025)},
    "NYG": {"hc": "John Harbaugh",
            "oc": ("Matt Nagy", 2026), "dc": ("Dennard Wilson", 2026),
            "st": ("Chris Horton", 2026)},
    "PHI": {"hc": "Nick Sirianni",
            "oc": ("Sean Mannion", 2026), "dc": ("Vic Fangio", 2024),
            "st": ("Michael Clay", 2021)},
    "WAS": {"hc": "Dan Quinn",
            "oc": ("David Blough", 2026), "dc": ("Daronte Jones", 2026),
            "st": ("Larry Izzo", 2024)},
    # ---- NFC North
    "CHI": {"hc": "Ben Johnson",
            "oc": ("Press Taylor", 2026), "dc": ("Dennis Allen", 2025),
            "st": ("Richard Hightower", 2022)},
    "DET": {"hc": "Dan Campbell",
            "oc": ("Drew Petzing", 2026), "dc": ("Kelvin Sheppard", 2025),
            "st": ("Dave Fipp", 2021)},
    "GB":  {"hc": "Matt LaFleur",
            "oc": ("Adam Stenavich", 2022), "dc": ("Jonathan Gannon", 2026),
            "st": ("Cameron Achord", 2026)},
    "MIN": {"hc": "Kevin O'Connell",
            "oc": ("Wes Phillips", 2022), "dc": ("Brian Flores", 2023),
            "st": ("Matt Daniels", 2022)},
    # ---- NFC South
    "ATL": {"hc": "Kevin Stefanski",
            "oc": ("Tommy Rees", 2026), "dc": ("Jeff Ulbrich", 2025),
            "st": ("Craig Aukerman", 2026)},
    "CAR": {"hc": "Dave Canales",
            "oc": ("Brad Idzik", 2024), "dc": ("Ejiro Evero", 2023),
            "st": ("Tracy Smith", 2024)},
    "NO":  {"hc": "Kellen Moore",
            "oc": ("Doug Nussmeier", 2025), "dc": ("Brandon Staley", 2025),
            "st": ("Phil Galiano", 2025)},
    # Bowles has called Tampa Bay's defense since 2019 and kept the duty after
    # being promoted to head coach in 2022, which is why some staff tables show
    # the Buccaneers with no separate defensive coordinator.
    "TB":  {"hc": "Todd Bowles",
            "oc": ("Zac Robinson", 2026), "dc": ("Todd Bowles", 2019),
            "st": ("Danny Smith", 2026)},
    # ---- NFC West
    "ARI": {"hc": "Mike LaFleur",
            "oc": ("Nathaniel Hackett", 2026), "dc": ("Nick Rallis", 2023),
            "st": ("Michael Ghobrial", 2026)},
    "LA":  {"hc": "Sean McVay",
            "oc": ("Nate Scheelhaase", 2026), "dc": ("Chris Shula", 2024),
            "st": ("Bubba Ventrone", 2026)},
    "SEA": {"hc": "Mike Macdonald",
            "oc": ("Brian Fleury", 2026), "dc": ("Aden Durde", 2024),
            "st": ("Jay Harbaugh", 2024)},
    "SF":  {"hc": "Kyle Shanahan",
            "oc": ("Klay Kubiak", 2025), "dc": ("Raheem Morris", 2026),
            "st": ("Brant Boyer", 2025)},
}

# Head coaches hired for 2026. Asserted on import so a careless edit cannot
# quietly reintroduce a departed coach.
NEW_HC_2026 = {
    "TEN": "Robert Saleh", "NYG": "John Harbaugh", "ATL": "Kevin Stefanski",
    "CLE": "Todd Monken", "ARI": "Mike LaFleur", "LV": "Klint Kubiak",
    "BAL": "Jesse Minter", "MIA": "Jeff Hafley", "PIT": "Mike McCarthy",
    "BUF": "Joe Brady",
}

# Spellings that differ between the schedule and reporting. Left side is the
# correct spelling, right side is how the schedule writes it, so tenure lookups
# still match.
SCHEDULE_ALIASES = {"Klint Kubiak": "Klint Kubliak"}

ROLES = [("oc", "Offensive coordinator"),
         ("dc", "Defensive coordinator"),
         ("st", "Special teams")]

for _t, _n in NEW_HC_2026.items():
    assert STAFFS_2026[_t]["hc"] == _n, f"{_t} head coach disagrees with the hire list"
assert len(STAFFS_2026) == 32, "expected 32 teams"
for _t, _s in STAFFS_2026.items():
    for _k, _ in ROLES:
        assert _s.get(_k) and _s[_k][0], f"{_t} is missing a {_k}"
        assert 1990 <= _s[_k][1] <= 2026, f"{_t} {_k} has an implausible start year"

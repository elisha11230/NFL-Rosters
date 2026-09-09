"""
NFL Top 100, as voted by the players.

Two lists are kept, not one. The current year is what the app badges; the year
before is what makes the badge mean something, because a rank on its own does not
say whether a player is arriving or fading. Lamar Jackson is 69th this year and
was 2nd last year, and that is the interesting fact about him.

2026 premiered 22 June and concluded 3 September 2026. Myles Garrett was voted
first for the first time in his career, having been traded from Cleveland to the
Rams that offseason. Washington was the only club with nobody on the list.

Sources: NFL.com's reveal articles and Sharp Football's compiled tables, which
agree with each other and with the 2025 list already in this file.
Compiled 8 September 2026.
"""

TOP100_2026 = {
    1: "Myles Garrett", 2: "Josh Allen", 3: "Bijan Robinson",
    4: "Matthew Stafford", 5: "Jaxon Smith-Njigba", 6: "Christian McCaffrey",
    7: "Puka Nacua", 8: "Micah Parsons", 9: "Jahmyr Gibbs",
    10: "Patrick Surtain II",
    11: "Drake Maye", 12: "Will Anderson Jr.", 13: "Trey McBride",
    14: "Brian Burns", 15: "Derrick Henry", 16: "Ja'Marr Chase",
    17: "Jonathan Taylor", 18: "Patrick Mahomes", 19: "Justin Jefferson",
    20: "James Cook",
    21: "Sam Darnold", 22: "Amon-Ra St. Brown", 23: "Danielle Hunter",
    24: "Maxx Crosby", 25: "Derek Stingley Jr.", 26: "De'Von Achane",
    27: "Devin Lloyd", 28: "Christian Gonzalez", 29: "Jalen Carter",
    30: "Aidan Hutchinson",
    31: "Dak Prescott", 32: "Nik Bonitto", 33: "Jared Goff",
    34: "Saquon Barkley", 35: "Jared Verse", 36: "George Pickens",
    37: "Penei Sewell", 38: "Cooper DeJean", 39: "Justin Herbert",
    40: "Trent Williams",
    41: "T.J. Watt", 42: "Garett Bolles", 43: "Chris Jones", 44: "Joe Burrow",
    45: "Zack Baun", 46: "George Kittle", 47: "Quinyon Mitchell",
    48: "Josh Hines-Allen", 49: "Joe Thuney", 50: "Derwin James",
    51: "Caleb Williams", 52: "Tristan Wirfs", 53: "Davante Adams",
    54: "Fred Warner", 55: "CeeDee Lamb", 56: "Jalen Hurts",
    57: "Dion Dawkins", 58: "Nico Collins", 59: "Bo Nix", 60: "Brock Bowers",
    61: "Kevin Byard", 62: "Trevor Lawrence", 63: "Kyle Hamilton",
    64: "Chris Olave", 65: "Roquan Smith", 66: "Drake London",
    67: "Jordyn Brooks", 68: "Courtland Sutton", 69: "Lamar Jackson",
    70: "Xavier McKinney",
    71: "Zay Flowers", 72: "Jordan Love", 73: "Zach Allen", 74: "Josh Jacobs",
    75: "Budda Baker", 76: "Jaycee Horn", 77: "Baker Mayfield",
    78: "Josh Sweat", 79: "Travis Kelce", 80: "A.J. Brown",
    81: "Bobby Wagner", 82: "Jalen Ramsey", 83: "Jeffery Simmons",
    84: "Byron Young", 85: "Brock Purdy", 86: "Tuli Tuipulotu",
    87: "Tetairoa McMillan", 88: "Jack Campbell", 89: "Kyren Williams",
    90: "Derrick Brown",
    91: "Montez Sweat", 92: "Azeez Al-Shaair", 93: "Carson Schwesinger",
    94: "Creed Humphrey", 95: "Demario Davis", 96: "Travis Etienne",
    97: "Ernest Jones", 98: "Bryce Young", 99: "Quenton Nelson",
    100: "Cameron Jordan",
}

TOP100_2025 = {
    1: "Saquon Barkley", 2: "Lamar Jackson", 3: "Josh Allen", 4: "Ja'Marr Chase",
    5: "Patrick Mahomes", 6: "Joe Burrow", 7: "Derrick Henry", 8: "Myles Garrett",
    9: "Justin Jefferson", 10: "Patrick Surtain II",
    11: "T.J. Watt", 12: "Chris Jones", 13: "Penei Sewell", 14: "Trey Hendrickson",
    15: "Jared Goff", 16: "Fred Warner", 17: "Dexter Lawrence",
    18: "Derek Stingley Jr.", 19: "Jalen Hurts", 20: "Amon-Ra St. Brown",
    21: "Jayden Daniels", 22: "Maxx Crosby", 23: "Lane Johnson",
    24: "Brock Bowers", 25: "Danielle Hunter", 26: "Zack Baun",
    27: "Jahmyr Gibbs", 28: "Tristan Wirfs", 29: "A.J. Brown",
    30: "Xavier McKinney",
    31: "George Kittle", 32: "Nico Collins", 33: "Josh Jacobs", 34: "Budda Baker",
    35: "CeeDee Lamb", 36: "Micah Parsons", 37: "Travis Kelce", 38: "Nik Bonitto",
    39: "C.J. Stroud", 40: "Roquan Smith",
    41: "Puka Nacua", 42: "Dion Dawkins", 43: "Jalen Carter", 44: "Mike Evans",
    45: "Trent Williams", 46: "Will Anderson Jr.", 47: "Tyreek Hill",
    48: "Jonathan Greenard", 49: "Quinyon Mitchell", 50: "Baker Mayfield",
    51: "Kyle Hamilton", 52: "Terry McLaurin", 53: "Jared Verse",
    54: "Derwin James", 55: "Aidan Hutchinson", 56: "Justin Herbert",
    57: "Nick Bosa", 58: "Joe Mixon", 59: "Matthew Stafford",
    60: "Cooper DeJean",
    61: "Brian Thomas Jr.", 62: "Bijan Robinson", 63: "Josh Hines-Allen",
    64: "Bo Nix", 65: "Trey McBride", 66: "Jalen Ramsey", 67: "Malik Nabers",
    68: "Jordan Love", 69: "Jordan Mailata", 70: "Frankie Luvu",
    71: "Kerby Joseph", 72: "Sam Darnold", 73: "Christian McCaffrey",
    74: "Bobby Wagner", 75: "Patrick Queen", 76: "Vita Vea", 77: "Tee Higgins",
    78: "Khalil Mack", 79: "Dak Prescott", 80: "Rashan Gary",
    81: "Trent McDuffie", 82: "Jerry Jeudy", 83: "Cameron Heyward",
    84: "Christian Gonzalez", 85: "Kyren Williams", 86: "Laremy Tunsil",
    87: "Quinnen Williams", 88: "Andrew Van Ginkel", 89: "James Cook",
    90: "Zach Allen",
    91: "Tua Tagovailoa", 92: "Jessie Bates III", 93: "Creed Humphrey",
    94: "Sam LaPorta", 95: "Josh Sweat", 96: "Lavonte David", 97: "Drake London",
    98: "Aaron Jones", 99: "Leonard Williams", 100: "Ladd McConkey",
}

# Position and club for each 2026 entry, used only to break ties. Names are not
# unique in this league: Cleveland have a rookie linebacker called Justin
# Jefferson, and there is a Byron Young on the Rams and another in Philadelphia.
# Matching on name alone badged the wrong man in both cases.
TOP100_2026_META = {
    1: ("EDGE","LA"), 2: ("QB","BUF"), 3: ("RB","ATL"), 4: ("QB","LA"),
    5: ("WR","SEA"), 6: ("RB","SF"), 7: ("WR","LA"), 8: ("EDGE","GB"),
    9: ("RB","DET"), 10: ("CB","DEN"), 11: ("QB","NE"), 12: ("EDGE","HOU"),
    13: ("TE","ARI"), 14: ("EDGE","NYG"), 15: ("RB","BAL"), 16: ("WR","CIN"),
    17: ("RB","IND"), 18: ("QB","KC"), 19: ("WR","MIN"), 20: ("RB","BUF"),
    21: ("QB","SEA"), 22: ("WR","DET"), 23: ("EDGE","HOU"), 24: ("EDGE","LV"),
    25: ("CB","HOU"), 26: ("RB","MIA"), 27: ("LB","CAR"), 28: ("CB","NE"),
    29: ("DL","PHI"), 30: ("EDGE","DET"), 31: ("QB","DAL"), 32: ("EDGE","DEN"),
    33: ("QB","DET"), 34: ("RB","PHI"), 35: ("EDGE","CLE"), 36: ("WR","DAL"),
    37: ("OT","DET"), 38: ("CB","PHI"), 39: ("QB","LAC"), 40: ("OT","SF"),
    41: ("EDGE","PIT"), 42: ("OT","DEN"), 43: ("DL","KC"), 44: ("QB","CIN"),
    45: ("LB","PHI"), 46: ("TE","SF"), 47: ("CB","PHI"), 48: ("EDGE","JAX"),
    49: ("OG","CHI"), 50: ("S","LAC"), 51: ("QB","CHI"), 52: ("OT","TB"),
    53: ("WR","LA"), 54: ("LB","SF"), 55: ("WR","DAL"), 56: ("QB","PHI"),
    57: ("OT","BUF"), 58: ("WR","HOU"), 59: ("QB","DEN"), 60: ("TE","LV"),
    61: ("S","NE"), 62: ("QB","JAX"), 63: ("S","BAL"), 64: ("WR","NO"),
    65: ("LB","BAL"), 66: ("WR","ATL"), 67: ("LB","MIA"), 68: ("WR","DEN"),
    69: ("QB","BAL"), 70: ("S","GB"), 71: ("WR","BAL"), 72: ("QB","GB"),
    73: ("DL","DEN"), 74: ("RB","GB"), 75: ("S","ARI"), 76: ("CB","CAR"),
    77: ("QB","TB"), 78: ("EDGE","ARI"), 79: ("TE","KC"), 80: ("WR","NE"),
    81: ("LB",None), 82: ("DB","PIT"), 83: ("DL","TEN"), 84: ("EDGE","LA"),
    85: ("QB","SF"), 86: ("EDGE","LAC"), 87: ("WR","CAR"), 88: ("LB","DET"),
    89: ("RB","LA"), 90: ("DL","CAR"), 91: ("EDGE","CHI"), 92: ("LB","HOU"),
    93: ("LB","CLE"), 94: ("C","KC"), 95: ("LB","NYJ"), 96: ("RB","NO"),
    97: ("LB","SEA"), 98: ("QB","CAR"), 99: ("OG","IND"), 100: ("EDGE","NO"),
}

# The list the app badges, and the one it measures movement against.
TOP100 = TOP100_2026
TOP100_PREV = TOP100_2025
CURRENT_YEAR = 2026
PREV_YEAR = 2025

# How the roster files spell a name, mapped to how the list spells it.
ALIASES = {
    "Jessie Bates": "Jessie Bates III",
    "Will Anderson": "Will Anderson Jr.",
    "Aaron Jones Sr.": "Aaron Jones",
    "Pat Surtain II": "Patrick Surtain II",
    "Derek Stingley": "Derek Stingley Jr.",
    "Brian Thomas": "Brian Thomas Jr.",
    "Tetairoa McMillan": "Tetairoa McMillan",
    "Travis Etienne Jr.": "Travis Etienne",
}

# On the list but not on any depth chart, so the build should not flag them.
# Bobby Wagner was voted 81st while unsigned.
NOT_ON_ROSTER = {"Bobby Wagner"}

assert len(TOP100_2026) == 100, "2026 list is not 100 long"
assert len(TOP100_2025) == 100, "2025 list is not 100 long"
assert len(set(TOP100_2026.values())) == 100, "duplicate name in the 2026 list"
assert len(set(TOP100_2025.values())) == 100, "duplicate name in the 2025 list"

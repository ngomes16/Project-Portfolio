from __future__ import annotations

from typing import Optional

from .util import normalize_team_name


# Minimal-but-complete NBA team name <-> abbreviation mapping.
# Note: team names in your raw files may vary ("LA Clippers" vs "Los Angeles Clippers").
_ALIASES_TO_ABBREV: dict[str, str] = {
    # Atlantic
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "New York Knicks": "NYK",
    "Philadelphia 76ers": "PHI",
    "Toronto Raptors": "TOR",
    # Central
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Detroit Pistons": "DET",
    "Indiana Pacers": "IND",
    "Milwaukee Bucks": "MIL",
    # Southeast
    "Atlanta Hawks": "ATL",
    "Charlotte Hornets": "CHA",
    "Miami Heat": "MIA",
    "Orlando Magic": "ORL",
    "Washington Wizards": "WAS",
    # Northwest
    "Denver Nuggets": "DEN",
    "Minnesota Timberwolves": "MIN",
    "Oklahoma City Thunder": "OKC",
    "Portland Trail Blazers": "POR",
    "Utah Jazz": "UTA",
    # Pacific
    "Golden State Warriors": "GSW",
    "Los Angeles Clippers": "LAC",
    "LA Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "LA Lakers": "LAL",
    "Phoenix Suns": "PHX",
    "Sacramento Kings": "SAC",
    # Southwest
    "Dallas Mavericks": "DAL",
    "Houston Rockets": "HOU",
    "Memphis Grizzlies": "MEM",
    "New Orleans Pelicans": "NOP",
    "San Antonio Spurs": "SAS",
}

_ABBREV_TO_CANONICAL: dict[str, str] = {}
for name, abbr in _ALIASES_TO_ABBREV.items():
    _ABBREV_TO_CANONICAL.setdefault(abbr, name)


def normalize_team_abbrev(abbrev: str) -> str:
    return abbrev.strip().upper()


def abbrev_from_team_name(team_name: str) -> Optional[str]:
    key = normalize_team_name(team_name)
    return _ALIASES_TO_ABBREV.get(key)


def team_name_from_abbrev(abbrev: str) -> Optional[str]:
    return _ABBREV_TO_CANONICAL.get(normalize_team_abbrev(abbrev))


def build_abbrev_to_team_map(team_names: list[str]) -> dict[str, str]:
    """
    Given the two team names for a game, return a mapping like {"MIA": "Miami Heat"}.
    """
    out: dict[str, str] = {}
    for nm in team_names:
        abbr = abbrev_from_team_name(nm)
        if abbr:
            out[abbr] = nm
    return out



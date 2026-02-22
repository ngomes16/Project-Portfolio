"""Parser for NBA matchup/schedule data with betting lines.

Parses copy-pasted schedule data from ESPN or similar sites:
    Saturday, January 3, 2026
    ...
    Minnesota
      @  
    
    Miami
    3:00 PM	
    NBA TV
    Tickets as low as $28	
    Line: MIN -2.5
    O/U: 238.5

Handles various formats including:
- Upcoming games with times and betting lines
- LIVE games (currently in progress)
- Completed games (skipped during parsing)
- Games without betting lines
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..team_aliases import abbrev_from_team_name


# Lines that should be skipped during parsing (noise/headers)
_SKIP_LINES: set[str] = {
    "matchup", "time", "tv", "tickets", "odds by", "draft kings",
    "result", "winner high", "loser high", "nbc", "peacock", "espn",
    "tnt", "nba tv", "abc",
}

# Patterns that indicate noise lines to skip
_SKIP_PATTERNS: list[str] = [
    r"tickets as low as",
    r"\d+ pts",  # Player points like "32 Pts"
    r"^\d+$",  # Just numbers
    r"^[A-Z]{2,4} \d+,? [A-Z]{2,4} \d+",  # Game results like "UTAH 123, CLE 112"
]

# Team city/name mapping for partial matches
_CITY_TO_TEAM: dict[str, str] = {
    "atlanta": "Atlanta Hawks",
    "boston": "Boston Celtics",
    "brooklyn": "Brooklyn Nets",
    "charlotte": "Charlotte Hornets",
    "chicago": "Chicago Bulls",
    "cleveland": "Cleveland Cavaliers",
    "dallas": "Dallas Mavericks",
    "denver": "Denver Nuggets",
    "detroit": "Detroit Pistons",
    "golden state": "Golden State Warriors",
    "houston": "Houston Rockets",
    "indiana": "Indiana Pacers",
    "la clippers": "Los Angeles Clippers",
    "la lakers": "Los Angeles Lakers",
    "los angeles clippers": "Los Angeles Clippers",
    "los angeles lakers": "Los Angeles Lakers",
    "memphis": "Memphis Grizzlies",
    "miami": "Miami Heat",
    "milwaukee": "Milwaukee Bucks",
    "minnesota": "Minnesota Timberwolves",
    "new orleans": "New Orleans Pelicans",
    "new york": "New York Knicks",
    "oklahoma city": "Oklahoma City Thunder",
    "orlando": "Orlando Magic",
    "philadelphia": "Philadelphia 76ers",
    "phoenix": "Phoenix Suns",
    "portland": "Portland Trail Blazers",
    "sacramento": "Sacramento Kings",
    "san antonio": "San Antonio Spurs",
    "toronto": "Toronto Raptors",
    "utah": "Utah Jazz",
    "washington": "Washington Wizards",
    # Short forms - LA requires context to disambiguate
    "la": None,  # Requires context (line info) to determine Lakers vs Clippers
    "los angeles": None,  # Requires context to determine Lakers vs Clippers
}

# Abbreviation mapping for lines
_ABBREV_MAP: dict[str, str] = {
    "ATL": "Atlanta Hawks",
    "BOS": "Boston Celtics",
    "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors",
    "GS": "Golden State Warriors",
    "HOU": "Houston Rockets",
    "IND": "Indiana Pacers",
    "LAC": "Los Angeles Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans",
    "NO": "New Orleans Pelicans",
    "NYK": "New York Knicks",
    "NY": "New York Knicks",
    "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",
    "SA": "San Antonio Spurs",
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}


@dataclass
class ParsedMatchup:
    """Parsed matchup data from schedule paste."""
    game_date: str  # YYYY-MM-DD format
    away_team: str  # Full team name
    home_team: str  # Full team name
    away_abbrev: str
    home_abbrev: str
    game_time: Optional[str] = None  # e.g., "3:00 PM"
    spread: Optional[float] = None  # Positive = home favored, negative = away favored
    favorite_abbrev: Optional[str] = None  # Which team is favored
    over_under: Optional[float] = None
    tv_channel: Optional[str] = None
    status: str = "scheduled"  # scheduled, live, completed


def _is_skip_line(text: str) -> bool:
    """Check if a line should be skipped (noise/headers)."""
    text_lower = text.strip().lower()
    
    # Empty lines
    if not text_lower:
        return True
    
    # Known skip phrases
    if text_lower in _SKIP_LINES:
        return True
    
    # Skip patterns (regex)
    for pattern in _SKIP_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    
    return False


def _is_completed_game_result(text: str) -> bool:
    """Check if a line indicates a completed game result like 'UTAH 123, CLE 112'."""
    # Pattern: TEAM SCORE, TEAM SCORE (e.g., "UTAH 123, CLE 112" or "IND 98, BOS 96")
    pattern = r"^[A-Z]{2,4}\s+\d+,?\s+[A-Z]{2,4}\s+\d+$"
    return bool(re.match(pattern, text.strip(), re.IGNORECASE))


def _resolve_team_name(text: str, line_abbrev: Optional[str] = None) -> Optional[str]:
    """Resolve a city/team name or abbreviation to full team name.
    
    Args:
        text: The city, team name, or abbreviation
        line_abbrev: Optional abbreviation from the Line (e.g., LAL, LAC) to help disambiguate
    """
    text_clean = text.strip()
    text_lower = text_clean.lower()
    text_upper = text_clean.upper()

    # Guard against matching team names inside non-team lines like:
    # "Line: LAL -4.5" or "Tickets as low as $65"
    if (":" in text_lower or any(ch.isdigit() for ch in text_lower)) and text_lower not in _CITY_TO_TEAM:
        return None
    
    # Empty or too short strings can't be team names
    if len(text_lower) < 2:
        return None
    
    # Skip noise lines that might look like teams
    if _is_skip_line(text):
        return None
    
    # Check abbreviation map first (for 2-3 letter codes like DEN, NOP, GSW)
    if len(text_clean) <= 4 and text_upper in _ABBREV_MAP:
        return _ABBREV_MAP[text_upper]
    
    # Handle LA disambiguation
    if text_lower in ("la", "los angeles"):
        # If we have line context, use it
        if line_abbrev in ("LAL", "LAC"):
            return "Los Angeles Lakers" if line_abbrev == "LAL" else "Los Angeles Clippers"
        # "LA" (short) typically refers to Clippers, "Los Angeles" (full) typically refers to Lakers
        if text_lower == "la":
            return "Los Angeles Clippers"
        else:
            return "Los Angeles Lakers"
    
    # Check exact matches first
    if text_lower in _CITY_TO_TEAM:
        result = _CITY_TO_TEAM[text_lower]
        if result is not None:
            return result
    
    # Check partial matches (avoid very short keys like "la" to prevent false positives, e.g. "LAL")
    if len(text_lower) >= 3:
        for city, team in _CITY_TO_TEAM.items():
            if len(city) < 3 or team is None:
                continue
            if city in text_lower or text_lower in city:
                return team
    
    # Check if it's a full team name
    for team in _CITY_TO_TEAM.values():
        if team is not None and text_lower in team.lower():
            return team
    
    return None


def _resolve_abbrev_to_team(abbrev: str) -> Optional[str]:
    """Resolve an abbreviation to full team name."""
    return _ABBREV_MAP.get(abbrev.upper())


def _parse_date(text: str) -> Optional[str]:
    """Parse a date string to YYYY-MM-DD format."""
    # Try common formats
    formats = [
        "%A, %B %d, %Y",  # "Saturday, January 3, 2026"
        "%B %d, %Y",      # "January 3, 2026"
        "%m/%d/%Y",       # "01/03/2026"
        "%m-%d-%Y",       # "01-03-2026"
        "%Y-%m-%d",       # "2026-01-03"
    ]
    
    text = text.strip()
    
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def _parse_spread_line(line: str) -> tuple[Optional[str], Optional[float]]:
    """
    Parse a spread line like 'Line: MIN -2.5' or 'Line: NY -3.5'.
    Returns (team_abbrev, spread_value) where positive = team is favored.
    """
    # Pattern: Line: ABBREV -X.X or Line: ABBREV +X.X
    m = re.search(r"Line:\s*([A-Z]{2,3})\s*([+-]?\d+(?:\.\d+)?)", line, re.IGNORECASE)
    if m:
        abbrev = m.group(1).upper()
        spread_val = float(m.group(2))
        return abbrev, spread_val
    return None, None


def _parse_over_under(line: str) -> Optional[float]:
    """Parse over/under from line like 'O/U: 238.5'."""
    m = re.search(r"O/U:\s*(\d+(?:\.\d+)?)", line, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _parse_time(line: str) -> Optional[str]:
    """Parse game time from line like '3:00 PM'."""
    m = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))", line, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def parse_matchups_text(text: str) -> list[ParsedMatchup]:
    """
    Parse pasted matchup schedule text into structured matchup data.
    
    Handles multiple formats from ESPN/NBA.com including:
    - Upcoming games with times and betting lines
    - LIVE games (in progress) 
    - Completed games (skipped)
    - Games without betting lines
    
    The expected format is messy copy-paste like:
    
        Saturday, January 3, 2026
        MATCHUP
        TIME
        TV
        tickets
        Odds by
        draft kings
        
        Minnesota
          @  
        
        Miami
        3:00 PM	
        NBA TV
        Tickets as low as $28	
        Line: MIN -2.5
        O/U: 238.5
    
    Returns:
        List of ParsedMatchup objects
    """
    matchups: list[ParsedMatchup] = []
    lines = text.splitlines()
    
    # First, try to find the date
    game_date: Optional[str] = None
    for line in lines[:10]:  # Check first 10 lines for date
        parsed = _parse_date(line.strip())
        if parsed:
            game_date = parsed
            break
    
    # If no date found, use today
    if not game_date:
        game_date = datetime.now().strftime("%Y-%m-%d")
    
    # Track if we're in a completed games section
    in_completed_section = False
    
    # Find matchup blocks
    # Pattern: Team1 (away) -> "@" -> Team2 (home) -> time/LIVE -> channel -> line -> O/U
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if we've entered the completed games section
        # Indicated by headers like "result" "winner high" "loser high"
        if line.lower() in ("result", "winner high", "loser high"):
            in_completed_section = True
            i += 1
            continue
        
        # Check for new upcoming games section (reset completed flag)
        if re.match(r"^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", line.lower()):
            in_completed_section = False
            # Try to parse this as a new date
            new_date = _parse_date(line)
            if new_date:
                game_date = new_date
            i += 1
            continue
        
        # Skip header/noise lines
        if _is_skip_line(line):
            i += 1
            continue
        
        # Skip completed game results (e.g., "UTAH 123, CLE 112")
        if _is_completed_game_result(line):
            in_completed_section = True
            i += 1
            continue
        
        # First, scan ahead to find the line info for LA disambiguation
        # Look for "Line: XXX" in the upcoming lines to get context
        future_favorite_abbrev = None
        for k in range(i, min(i + 15, len(lines))):
            future_line = lines[k].strip()
            if "line:" in future_line.lower():
                abbrev, _ = _parse_spread_line(future_line)
                if abbrev:
                    future_favorite_abbrev = abbrev
                break
        
        # Check for single-line format like "DEN @ NOP" or "Denver @ New Orleans"
        single_line_match = re.match(
            r'^([A-Za-z\s]+)\s+@\s+([A-Za-z\s]+)\s*(?:(\d{1,2}:\d{2}\s*(?:PM|AM)?(?:\s*\(ET\))?))?',
            line, re.IGNORECASE
        )
        if single_line_match:
            away_part = single_line_match.group(1).strip()
            home_part = single_line_match.group(2).strip()
            time_part = single_line_match.group(3)
            
            away_team = _resolve_team_name(away_part, future_favorite_abbrev)
            home_team = _resolve_team_name(home_part, future_favorite_abbrev)
            
            if away_team and home_team:
                # Found a single-line matchup
                game_time = time_part
                spread = None
                over_under = None
                favorite_abbrev = None
                tv_channel = None
                
                # Look at next few lines for Line/O/U info
                for k in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[k].strip()
                    if "line:" in next_line.lower():
                        abbrev, val = _parse_spread_line(next_line)
                        if abbrev and val is not None:
                            favorite_abbrev = abbrev
                            spread = val
                    elif "o/u:" in next_line.lower():
                        over_under = _parse_over_under(next_line)
                
                # Determine spread sign
                if spread is not None and favorite_abbrev:
                    away_abbrev = abbrev_from_team_name(away_team)
                    if favorite_abbrev.upper() == away_abbrev.upper() if away_abbrev else False:
                        spread = -abs(spread)
                    else:
                        spread = abs(spread)
                
                matchup = ParsedMatchup(
                    away_team=away_team,
                    home_team=home_team,
                    away_abbrev=abbrev_from_team_name(away_team) or "",
                    home_abbrev=abbrev_from_team_name(home_team) or "",
                    game_date=game_date,
                    game_time=game_time,
                    tv_channel=tv_channel,
                    spread=spread,
                    over_under=over_under,
                    favorite_abbrev=favorite_abbrev,
                    status="scheduled",
                )
                matchups.append(matchup)
                i += 1
                continue
        
        # Check if this line looks like a team city/name
        away_team = _resolve_team_name(line, future_favorite_abbrev)
        if not away_team:
            i += 1
            continue
        
        # Look for "@" indicator and home team in next lines
        home_team = None
        game_time = None
        tv_channel = None
        spread = None
        favorite_abbrev = None
        over_under = None
        is_live = False
        is_completed = in_completed_section
        
        # Scan ahead for the rest of the matchup info
        j = i + 1
        found_at = False
        while j < len(lines) and j < i + 20:  # Look ahead up to 20 lines
            next_line = lines[j].strip()
            next_line_lower = next_line.lower()
            
            # Check for completed game result - skip this matchup entirely
            if _is_completed_game_result(next_line):
                is_completed = True
                j += 1
                continue
            
            # Found the @ separator
            if "@" in next_line and len(next_line) < 5:
                found_at = True
                j += 1
                continue
            
            # After @, look for home team
            if found_at and not home_team:
                potential_home = _resolve_team_name(next_line, future_favorite_abbrev)
                if potential_home:
                    home_team = potential_home
                    j += 1
                    continue
            
            # Check for LIVE indicator
            if next_line_lower == "live":
                is_live = True
                j += 1
                continue
            
            # Look for game time
            if not game_time and not is_live:
                time_match = _parse_time(next_line)
                if time_match:
                    game_time = time_match
            
            # Look for TV channel (more comprehensive matching)
            if any(ch in next_line.upper() for ch in ["NBA TV", "ESPN", "TNT", "ABC", "NBC", "PEACOCK"]):
                if tv_channel:
                    tv_channel += " / " + next_line.strip()
                else:
                    tv_channel = next_line.strip()
            
            # Look for spread line
            if "line:" in next_line_lower:
                abbrev, val = _parse_spread_line(next_line)
                if abbrev and val is not None:
                    favorite_abbrev = abbrev
                    spread = val
            
            # Look for O/U
            if "o/u:" in next_line_lower:
                over_under = _parse_over_under(next_line)
            
            # Stop if we hit another likely team line (start of next matchup)
            # But not if we haven't found a home team yet
            if home_team:
                potential_next_team = _resolve_team_name(next_line, None)
                if potential_next_team and _parse_time(next_line) is None and ":" not in next_line:
                    break
            
            j += 1
        
        # Skip completed games - don't add them to results
        if is_completed and not is_live:
            i = j
            continue
        
        # If we found a valid matchup, add it
        if away_team and home_team:
            away_abbrev = abbrev_from_team_name(away_team) or ""
            home_abbrev = abbrev_from_team_name(home_team) or ""

            # Disambiguate "Los Angeles" when the pasted matchup doesn't specify Lakers vs Clippers.
            # If the spread favorite indicates LAL/LAC but our resolved team abbrevs don't match,
            # prefer the favorite abbrev for the LA team.
            if favorite_abbrev in ("LAL", "LAC") and favorite_abbrev not in (away_abbrev, home_abbrev):
                if away_team.startswith("Los Angeles"):
                    away_team = "Los Angeles Lakers" if favorite_abbrev == "LAL" else "Los Angeles Clippers"
                    away_abbrev = favorite_abbrev
                elif home_team.startswith("Los Angeles"):
                    home_team = "Los Angeles Lakers" if favorite_abbrev == "LAL" else "Los Angeles Clippers"
                    home_abbrev = favorite_abbrev
            
            # Convert spread to home team perspective
            # If favorite is away team, spread is negative for home
            if spread is not None and favorite_abbrev:
                if favorite_abbrev == away_abbrev:
                    # Away team favored, home team spread is positive (underdog)
                    spread = abs(spread)
                elif favorite_abbrev == home_abbrev:
                    # Home team favored, spread is negative
                    spread = -abs(spread)
            
            # Determine status
            status = "live" if is_live else "scheduled"
            
            matchups.append(ParsedMatchup(
                game_date=game_date,
                away_team=away_team,
                home_team=home_team,
                away_abbrev=away_abbrev,
                home_abbrev=home_abbrev,
                game_time=game_time,
                spread=spread,
                favorite_abbrev=favorite_abbrev,
                over_under=over_under,
                tv_channel=tv_channel,
                status=status,
            ))
            
            # Move past this matchup
            i = j
        else:
            i += 1
    
    return matchups


def parse_simple_matchup(away: str, home: str, date: str, spread: Optional[float] = None, over_under: Optional[float] = None) -> Optional[ParsedMatchup]:
    """Create a matchup from simple inputs (for manual entry)."""
    away_team = _resolve_team_name(away) or _resolve_abbrev_to_team(away)
    home_team = _resolve_team_name(home) or _resolve_abbrev_to_team(home)
    
    if not away_team or not home_team:
        return None
    
    away_abbrev = abbrev_from_team_name(away_team) or ""
    home_abbrev = abbrev_from_team_name(home_team) or ""
    
    return ParsedMatchup(
        game_date=date,
        away_team=away_team,
        home_team=home_team,
        away_abbrev=away_abbrev,
        home_abbrev=home_abbrev,
        spread=spread,
        over_under=over_under,
    )


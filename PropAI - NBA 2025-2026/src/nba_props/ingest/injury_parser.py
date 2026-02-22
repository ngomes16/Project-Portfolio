"""Parser for NBA injury report data.

Parses copy-pasted injury reports from the official NBA injury report format like:
    Injury Report: 01/03/26 02:45 PM
    Page 1 of 6
    Game Date Game Time Matchup Team Player Name Current Status Reason
    01/03/2026 05:00 (ET) MIN@MIA Minnesota Timberwolves Beringer, Joan Out G League - On Assignment
    ...

Key parsing challenges handled:
1. Reports span multiple pages with "Page X of Y" headers that break mid-team
2. New matchups can appear on a line (e.g., "TOR@IND Toronto Raptors Barrett, RJ Out ...")
3. Team names must be tracked carefully to avoid mis-attribution
4. Player names may lack accents or have suffixes (Jr., III, etc.)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple

from ..team_aliases import abbrev_from_team_name, team_name_from_abbrev, normalize_team_abbrev


@dataclass
class InjuryEntry:
    """A single injury report entry."""
    game_date: str  # YYYY-MM-DD format
    team_name: str
    team_abbrev: str
    player_name: str
    status: str  # OUT, QUESTIONABLE, PROBABLE, DOUBTFUL, AVAILABLE
    reason: str
    game_time: Optional[str] = None
    matchup: Optional[str] = None  # e.g., "MIN@MIA"
    is_g_league: bool = False  # G League assignment or Two-Way
    

@dataclass
class ParsedInjuryReport:
    """Complete parsed injury report."""
    report_date: str  # Date/time the report was generated
    entries: list[InjuryEntry] = field(default_factory=list)
    teams_not_submitted: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # Parsing warnings


# Status mappings
_STATUS_MAP = {
    "OUT": "OUT",
    "O": "OUT",
    "QUESTIONABLE": "QUESTIONABLE",
    "Q": "QUESTIONABLE",
    "PROBABLE": "PROBABLE",
    "P": "PROBABLE",
    "DOUBTFUL": "DOUBTFUL",
    "D": "DOUBTFUL",
    "AVAILABLE": "AVAILABLE",
    "GTD": "QUESTIONABLE",  # Game Time Decision
}

# Team name mappings (full names)
_TEAM_NAMES = {
    "atlanta hawks": "Atlanta Hawks",
    "boston celtics": "Boston Celtics",
    "brooklyn nets": "Brooklyn Nets",
    "charlotte hornets": "Charlotte Hornets",
    "chicago bulls": "Chicago Bulls",
    "cleveland cavaliers": "Cleveland Cavaliers",
    "dallas mavericks": "Dallas Mavericks",
    "denver nuggets": "Denver Nuggets",
    "detroit pistons": "Detroit Pistons",
    "golden state warriors": "Golden State Warriors",
    "houston rockets": "Houston Rockets",
    "indiana pacers": "Indiana Pacers",
    "la clippers": "Los Angeles Clippers",
    "los angeles clippers": "Los Angeles Clippers",
    "la lakers": "Los Angeles Lakers",
    "los angeles lakers": "Los Angeles Lakers",
    "memphis grizzlies": "Memphis Grizzlies",
    "miami heat": "Miami Heat",
    "milwaukee bucks": "Milwaukee Bucks",
    "minnesota timberwolves": "Minnesota Timberwolves",
    "new orleans pelicans": "New Orleans Pelicans",
    "new york knicks": "New York Knicks",
    "oklahoma city thunder": "Oklahoma City Thunder",
    "orlando magic": "Orlando Magic",
    "philadelphia 76ers": "Philadelphia 76ers",
    "phoenix suns": "Phoenix Suns",
    "portland trail blazers": "Portland Trail Blazers",
    "sacramento kings": "Sacramento Kings",
    "san antonio spurs": "San Antonio Spurs",
    "toronto raptors": "Toronto Raptors",
    "utah jazz": "Utah Jazz",
    "washington wizards": "Washington Wizards",
}

# Matchup abbreviations to team names - needed when we detect a new matchup
_MATCHUP_ABBREV_TO_TEAM = {
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
    "GS": "Golden State Warriors",  # Alternate abbreviation
    "HOU": "Houston Rockets",
    "IND": "Indiana Pacers",
    "LAC": "Los Angeles Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans",
    "NO": "New Orleans Pelicans",  # Alternate abbreviation
    "NYK": "New York Knicks",
    "NY": "New York Knicks",  # Alternate abbreviation
    "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "PHX": "Phoenix Suns",
    "PHO": "Phoenix Suns",  # Alternate abbreviation
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",
    "SA": "San Antonio Spurs",  # Alternate abbreviation
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}


def _normalize_team_name(name: str) -> Optional[str]:
    """Normalize a team name to its standard form."""
    name_lower = name.strip().lower()
    return _TEAM_NAMES.get(name_lower)


def _team_name_from_matchup_abbrev(abbrev: str) -> Optional[str]:
    """Get full team name from matchup abbreviation."""
    return _MATCHUP_ABBREV_TO_TEAM.get(abbrev.upper())


# Map team names to abbreviations
_TEAM_ABBREVS = {
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}


def _get_team_abbrev(team_name: str) -> str:
    """Get team abbreviation from full team name."""
    return _TEAM_ABBREVS.get(team_name, team_name[:3].upper())


def _parse_player_name(name: str) -> str:
    """Convert 'LastName, FirstName' to 'FirstName LastName' and normalize."""
    name = name.strip()
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        if len(parts) == 2:
            name = f"{parts[1]} {parts[0]}"
    
    # Handle suffixes - ensure proper formatting
    # e.g., "Oubre Jr., Kelly" -> "Kelly Oubre Jr."
    # Already handled by the comma split above
    
    # Normalize unicode (remove accents for matching, but preserve structure)
    # This helps match "Dončić" to "Doncic" in database lookups
    
    return name.strip()


def normalize_player_name_for_db_match(name: str) -> str:
    """
    Normalize a player name for database matching.
    - Removes accents (é -> e, ć -> c, etc.)
    - Lowercases
    - Handles suffixes (Jr., III, II, Sr.)
    """
    # Normalize unicode - decompose and remove combining characters (accents)
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    
    # Lowercase for comparison
    return ascii_name.lower().strip()


def _normalize_status(status: str) -> str:
    """Normalize injury status to standard form."""
    status = status.strip().upper()
    return _STATUS_MAP.get(status, status)


def _is_g_league_reason(reason: str) -> bool:
    """Check if the reason indicates G League assignment."""
    reason_lower = reason.lower()
    return any(term in reason_lower for term in [
        "g league",
        "two-way",
        "on assignment",
        "g-league",
    ])


def _parse_date(date_str: str) -> Optional[str]:
    """Parse date string to YYYY-MM-DD format."""
    formats = [
        "%m/%d/%Y",  # 01/03/2026
        "%m/%d/%y",  # 01/03/26
        "%Y-%m-%d",  # 2026-01-03
    ]
    
    date_str = date_str.strip()
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


def _parse_report_header(text: str) -> Optional[str]:
    """Extract the report date/time from header."""
    # Pattern: "Injury Report: 01/03/26 02:45 PM"
    m = re.search(r"Injury Report:\s*(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2}\s*[AP]M)", text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return None


def _extract_matchup_info(line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract matchup info from a line.
    
    Returns: (matchup_str, away_team, home_team) where matchup_str is like "TOR@IND"
    """
    # Pattern for matchup: ABC@DEF where ABC and DEF are 2-3 letter team abbreviations
    matchup_pattern = re.compile(r'\b([A-Z]{2,3})@([A-Z]{2,3})\b')
    m = matchup_pattern.search(line)
    if m:
        away_abbrev = m.group(1)
        home_abbrev = m.group(2)
        matchup_str = f"{away_abbrev}@{home_abbrev}"
        away_team = _team_name_from_matchup_abbrev(away_abbrev)
        home_team = _team_name_from_matchup_abbrev(home_abbrev)
        return matchup_str, away_team, home_team
    return None, None, None


def _find_team_in_line(line: str) -> Tuple[Optional[str], int]:
    """
    Find a team name in the line and return it with its position.
    
    Returns: (team_name, end_position) where end_position is where team name ends
    """
    # Build pattern for team names, sorted by length (longest first to avoid partial matches)
    team_names_sorted = sorted(_TEAM_NAMES.values(), key=len, reverse=True)
    
    for team_name in team_names_sorted:
        # Use word boundary for shorter names, but exact match for longer
        pattern = re.compile(re.escape(team_name), re.IGNORECASE)
        m = pattern.search(line)
        if m:
            return team_name, m.end()
    
    return None, -1


def _is_page_break_line(line: str) -> bool:
    """Check if this line is a page break/header that should be skipped."""
    line_stripped = line.strip()
    
    # Page number line
    if re.match(r'^Page\s+\d+\s+of\s+\d+', line_stripped, re.IGNORECASE):
        return True
    
    # Report header line
    if line_stripped.startswith("Injury Report:"):
        return True
    
    # Column header line
    if "Game Date" in line_stripped and "Player Name" in line_stripped:
        return True
    if "Current Status" in line_stripped:
        return True
    
    return False


def parse_injury_report_text(text: str) -> ParsedInjuryReport:
    """
    Parse the raw injury report text into structured data.
    
    The injury report format is typically:
    - Header with date/time: "Injury Report: 01/14/26 11:45 AM"
    - Page headers: "Page 1 of 6"
    - Column headers: "Game Date Game Time Matchup Team Player Name Current Status Reason"
    - Data rows with various formats
    
    Key parsing rules:
    1. A new game block starts when we see a date (e.g., "01/14/2026")
    2. A new matchup within a date starts when we see "@" pattern (e.g., "TOR@IND")
    3. Within a matchup, teams are listed in order: away team first, then home team
    4. Team names like "Toronto Raptors" indicate team context for following players
    5. Page breaks should NOT reset team context - they just interrupt the flow
    
    Returns:
        ParsedInjuryReport with all parsed entries
    """
    result = ParsedInjuryReport(
        report_date=_parse_report_header(text) or datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    
    lines = text.splitlines()
    
    # Current parsing state
    current_game_date: Optional[str] = None
    current_game_time: Optional[str] = None
    current_matchup: Optional[str] = None
    current_team: Optional[str] = None
    # Track teams in current matchup for validation
    matchup_away_team: Optional[str] = None
    matchup_home_team: Optional[str] = None
    
    # Patterns
    date_pattern = re.compile(r'^(\d{1,2}/\d{1,2}/\d{2,4})\s+')
    time_pattern = re.compile(r'(\d{1,2}:\d{2})\s*\(ET\)')
    matchup_pattern = re.compile(r'\b([A-Z]{2,3})@([A-Z]{2,3})\b')
    status_words = ["Out", "Questionable", "Probable", "Doubtful", "Available", "GTD"]
    status_pattern = re.compile(r'\b(' + '|'.join(status_words) + r')\b', re.IGNORECASE)
    
    # Build team name pattern
    team_names_sorted = sorted(_TEAM_NAMES.values(), key=len, reverse=True)
    team_pattern = re.compile(
        r'(' + '|'.join(re.escape(name) for name in team_names_sorted) + r')',
        re.IGNORECASE
    )
    
    def parse_player_entry_from_text(text: str, team_name: str) -> Optional[InjuryEntry]:
        """Parse a player entry from text, given the team context."""
        # Find status word
        status_match = status_pattern.search(text)
        if not status_match:
            return None
        
        # Everything before status is potentially player name (with noise)
        player_part = text[:status_match.start()].strip()
        # Everything after status is reason
        reason_part = text[status_match.end():].strip()
        
        # Clean player_part by removing known noise
        # Remove date patterns
        player_part = date_pattern.sub('', player_part)
        # Remove time patterns
        player_part = re.sub(r'\d{1,2}:\d{2}\s*\(ET\)', '', player_part)
        # Remove matchup patterns
        player_part = matchup_pattern.sub('', player_part)
        # Remove team names (all of them)
        for team in team_names_sorted:
            player_part = re.sub(re.escape(team), '', player_part, flags=re.IGNORECASE)
        # Remove page headers
        player_part = re.sub(r'Page\s+\d+\s+of\s+\d+', '', player_part, flags=re.IGNORECASE)
        player_part = re.sub(r'Injury Report:.*', '', player_part, flags=re.IGNORECASE)
        # Clean up whitespace
        player_part = ' '.join(player_part.split())
        
        if not player_part or len(player_part) < 2:
            return None
        
        # Parse player name (convert "LastName, FirstName" format)
        player_name = _parse_player_name(player_part)
        
        if not player_name or len(player_name) < 2:
            return None
        
        # Validate: player name should look reasonable
        # Should not be all digits, should not be too short
        if player_name.isdigit():
            return None
        
        status = _normalize_status(status_match.group(1))
        team_abbrev = _get_team_abbrev(team_name)
        is_g_league = _is_g_league_reason(reason_part)
        
        return InjuryEntry(
            game_date=current_game_date or "",
            team_name=team_name,
            team_abbrev=team_abbrev,
            player_name=player_name,
            status=status,
            reason=reason_part,
            game_time=current_game_time,
            matchup=current_matchup,
            is_g_league=is_g_league,
        )
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Skip page breaks and headers - but DON'T reset team context
        if _is_page_break_line(line):
            i += 1
            continue
        
        # =====================================================
        # IMPORTANT: Check for NEW MATCHUP first (before anything else)
        # This handles lines like "TOR@IND Toronto Raptors Barrett, RJ Out ..."
        # AND lines like "09:30 (ET) DEN@DAL Denver Nuggets NOT YET SUBMITTED"
        # We need to update matchup context even if NOT YET SUBMITTED
        # =====================================================
        matchup_str, away_team, home_team = _extract_matchup_info(line)
        
        if matchup_str:
            # This is a new matchup - update context
            current_matchup = matchup_str
            matchup_away_team = away_team
            matchup_home_team = home_team
            
            # Check for date at start of line
            date_match = date_pattern.match(line)
            if date_match:
                parsed_date = _parse_date(date_match.group(1))
                if parsed_date:
                    current_game_date = parsed_date
            
            # Check for time
            time_match = time_pattern.search(line)
            if time_match:
                current_game_time = time_match.group(1)
            
            # Look for team name after the matchup
            # Find where matchup ends
            matchup_match = matchup_pattern.search(line)
            if matchup_match:
                remainder = line[matchup_match.end():].strip()
                
                # Check if this team has NOT YET SUBMITTED
                if "NOT YET SUBMITTED" in remainder.upper():
                    team_match = team_pattern.search(remainder)
                    if team_match:
                        team_name = _normalize_team_name(team_match.group(1))
                        if team_name:
                            result.teams_not_submitted.append(team_name)
                    i += 1
                    continue
                
                # Look for team name in remainder
                team_match = team_pattern.search(remainder)
                if team_match:
                    team_name = _normalize_team_name(team_match.group(1))
                    if team_name:
                        current_team = team_name
                        
                        # Parse player info from after team name
                        player_text = remainder[team_match.end():]
                        if player_text.strip():
                            entry = parse_player_entry_from_text(player_text, current_team)
                            if entry:
                                result.entries.append(entry)
            
            i += 1
            continue
        
        # =====================================================
        # Check for NOT YET SUBMITTED (without matchup on same line)
        # This handles lines like "Chicago Bulls NOT YET SUBMITTED"
        # =====================================================
        if "NOT YET SUBMITTED" in line.upper():
            # Try to extract team name from this line
            team_match = team_pattern.search(line)
            if team_match:
                team_name = _normalize_team_name(team_match.group(1))
                if team_name:
                    result.teams_not_submitted.append(team_name)
            i += 1
            continue
        
        # =====================================================
        # Check for date line (new date block without matchup on same line)
        # =====================================================
        date_match = date_pattern.match(line)
        if date_match:
            parsed_date = _parse_date(date_match.group(1))
            if parsed_date:
                current_game_date = parsed_date
            
            # Check for time
            time_match = time_pattern.search(line)
            if time_match:
                current_game_time = time_match.group(1)
            
            i += 1
            continue
        
        # =====================================================
        # Check for time line (new game time without date)
        # =====================================================
        if time_pattern.search(line) and not date_pattern.match(line):
            time_match = time_pattern.search(line)
            if time_match:
                current_game_time = time_match.group(1)
            
            # Continue to check for matchup and team on this line
            # (This handles lines like "08:00 (ET) BKN@NOP Brooklyn Nets ...")
            # But if we get here, we already checked for matchup above, so just move on
            i += 1
            continue
        
        # =====================================================
        # Check if line starts with a team name (team switch within matchup)
        # =====================================================
        team_match = team_pattern.match(line)
        if team_match:
            team_name = _normalize_team_name(team_match.group(1))
            if team_name:
                # Validate team is part of current matchup (if we have one)
                if current_matchup and matchup_away_team and matchup_home_team:
                    if team_name not in [matchup_away_team, matchup_home_team]:
                        # This is actually a NEW matchup, not a team switch
                        # This shouldn't happen often, but handle gracefully
                        result.warnings.append(
                            f"Team '{team_name}' doesn't match current matchup '{current_matchup}'. "
                            f"Line: {line[:50]}..."
                        )
                
                current_team = team_name
                
                # Parse player from remainder of line
                remainder = line[team_match.end():].strip()
                if remainder:
                    entry = parse_player_entry_from_text(remainder, current_team)
                    if entry:
                        result.entries.append(entry)
            
            i += 1
            continue
        
        # =====================================================
        # Otherwise, try to parse as player entry with current team context
        # =====================================================
        if current_team and current_game_date:
            entry = parse_player_entry_from_text(line, current_team)
            if entry:
                result.entries.append(entry)
        
        i += 1
    
    return result


def _parse_player_from_remaining(
    remaining: str,
    team_name: str,
    game_date: str,
    game_time: Optional[str],
    matchup: Optional[str],
) -> Optional[InjuryEntry]:
    """Parse player info from the remaining part of a line after team name.
    
    This function handles messy input where player names might contain:
    - Extra matchup info (e.g., "DEN@NOP")
    - Time info (e.g., "08:00 (ET)")
    - Team names (e.g., "Denver Nuggets")
    """
    
    status_words = ["Out", "Questionable", "Probable", "Doubtful", "Available", "GTD"]
    status_pattern = re.compile(r"\b(" + "|".join(status_words) + r")\b", re.IGNORECASE)
    
    status_match = status_pattern.search(remaining)
    if not status_match:
        return None
    
    status = _normalize_status(status_match.group(1))
    
    # Everything before status is player name (potentially with noise)
    player_part = remaining[:status_match.start()].strip()
    # Everything after status is reason
    reason = remaining[status_match.end():].strip()
    
    # Clean up player_part - remove common noise patterns
    # 1. Remove time patterns like "08:00 (ET)"
    player_part = re.sub(r'\d{1,2}:\d{2}\s*\(ET\)', '', player_part)
    # 2. Remove matchup patterns like "DEN@NOP" or "MIN@MIL"
    player_part = re.sub(r'\b[A-Z]{2,3}@[A-Z]{2,3}\b', '', player_part)
    # 3. Remove team names
    for team in _TEAM_NAMES.values():
        player_part = re.sub(re.escape(team), '', player_part, flags=re.IGNORECASE)
    # 4. Remove extra whitespace
    player_part = ' '.join(player_part.split())
    
    # Parse player name (might be "LastName, FirstName" format)
    player_name = _parse_player_name(player_part)
    
    if not player_name or len(player_name) < 3:
        return None
    
    # Additional validation: player name should look like a real name
    # At minimum: should have at least 2 parts or be longer than 5 characters
    if ' ' not in player_name and len(player_name) < 5:
        return None
    
    team_abbrev = _get_team_abbrev(team_name)
    is_g_league = _is_g_league_reason(reason)
    
    return InjuryEntry(
        game_date=game_date,
        team_name=team_name,
        team_abbrev=team_abbrev,
        player_name=player_name,
        status=status,
        reason=reason,
        game_time=game_time,
        matchup=matchup,
        is_g_league=is_g_league,
    )


def filter_meaningful_injuries(report: ParsedInjuryReport) -> list[InjuryEntry]:
    """
    Filter injury report to only include meaningful entries for betting analysis.
    Excludes G-League assignments and two-way players.
    """
    return [
        entry for entry in report.entries
        if not entry.is_g_league and entry.status in ("OUT", "QUESTIONABLE", "PROBABLE", "DOUBTFUL")
    ]


def get_injuries_by_team(report: ParsedInjuryReport, team: str) -> list[InjuryEntry]:
    """Get all injuries for a specific team."""
    team_upper = team.upper()
    return [
        entry for entry in report.entries
        if entry.team_abbrev.upper() == team_upper or entry.team_name.lower() == team.lower()
    ]


def get_injuries_for_date(report: ParsedInjuryReport, date: str) -> list[InjuryEntry]:
    """Get all injuries for a specific date."""
    return [entry for entry in report.entries if entry.game_date == date]


def summarize_injury_report(report: ParsedInjuryReport) -> dict:
    """Generate a summary of the injury report."""
    meaningful = filter_meaningful_injuries(report)
    
    by_status = {}
    by_team = {}
    
    for entry in meaningful:
        # Count by status
        by_status[entry.status] = by_status.get(entry.status, 0) + 1
        
        # Group by team
        if entry.team_abbrev not in by_team:
            by_team[entry.team_abbrev] = []
        by_team[entry.team_abbrev].append({
            "player": entry.player_name,
            "status": entry.status,
            "reason": entry.reason,
        })
    
    return {
        "report_date": report.report_date,
        "total_entries": len(report.entries),
        "meaningful_entries": len(meaningful),
        "by_status": by_status,
        "by_team": by_team,
        "teams_not_submitted": report.teams_not_submitted,
        "warnings": report.warnings,  # Include any parsing warnings
    }

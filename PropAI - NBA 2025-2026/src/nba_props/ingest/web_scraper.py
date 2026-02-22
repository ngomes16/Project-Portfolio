"""
Web scraper for NBA data from ESPN and NBA.com.

This module provides functions to scrape:
1. Injury reports from ESPN (https://www.espn.com/nba/injuries)
2. Matchups/Schedule from ESPN (https://www.espn.com/nba/schedule/_/date/YYYYMMDD)
3. Box scores from NBA.com JSON API (https://cdn.nba.com/static/json/liveData/boxscore/)

Requires: beautifulsoup4, requests
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_SCRAPING_DEPS = True
except ImportError:
    HAS_SCRAPING_DEPS = False


# ============================================================================
# Data Classes for scraped data
# ============================================================================

@dataclass
class ScrapedInjury:
    """A single injury entry scraped from ESPN."""
    team_name: str
    player_name: str
    position: str
    status: str  # Out, Day-To-Day, etc.
    est_return_date: str
    comment: str


@dataclass
class ScrapedInjuryReport:
    """Complete scraped injury report."""
    scrape_time: str
    injuries: list[ScrapedInjury] = field(default_factory=list)


@dataclass
class ScrapedMatchup:
    """A single matchup scraped from ESPN schedule."""
    game_date: str  # YYYY-MM-DD
    away_team: str
    home_team: str
    game_time: Optional[str] = None
    tv_channel: Optional[str] = None
    spread: Optional[float] = None
    favorite: Optional[str] = None  # Team abbreviation
    over_under: Optional[float] = None
    status: str = "scheduled"  # scheduled, completed, live


@dataclass
class ScrapedPlayerStats:
    """Player stats from a box score."""
    player_name: str
    team: str
    minutes: Optional[str] = None
    fg: Optional[str] = None  # e.g., "3-11"
    fg_pct: Optional[str] = None
    tp: Optional[str] = None  # 3-pointers
    tp_pct: Optional[str] = None
    ft: Optional[str] = None  # free throws
    ft_pct: Optional[str] = None
    oreb: Optional[int] = None
    dreb: Optional[int] = None
    reb: Optional[int] = None
    ast: Optional[int] = None
    stl: Optional[int] = None
    blk: Optional[int] = None
    tov: Optional[int] = None
    pf: Optional[int] = None
    pts: Optional[int] = None
    plus_minus: Optional[int] = None


@dataclass
class ScrapedBoxScore:
    """Box score data for a single game."""
    game_date: str
    away_team: str
    home_team: str
    away_score: Optional[int] = None
    home_score: Optional[int] = None
    player_stats: list[ScrapedPlayerStats] = field(default_factory=list)
    box_score_url: str = ""


# ============================================================================
# Team name mappings
# ============================================================================

TEAM_NAME_MAP = {
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

CITY_TO_TEAM = {
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
    "la": "Los Angeles Clippers",  # Default LA to Clippers
    "los angeles": "Los Angeles Lakers",  # Default Los Angeles to Lakers
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
}

TEAM_ABBREV_MAP = {
    "ATL": "Atlanta Hawks",
    "BOS": "Boston Celtics",
    "BKN": "Brooklyn Nets",
    "BRK": "Brooklyn Nets",
    "CHA": "Charlotte Hornets",
    "CHO": "Charlotte Hornets",
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
    "PHO": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",
    "SA": "San Antonio Spurs",
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}


def normalize_team_name(name: str) -> str:
    """Normalize a team name to its full standard form."""
    name_lower = name.strip().lower()
    
    # Check full name mapping
    if name_lower in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[name_lower]
    
    # Check city mapping
    if name_lower in CITY_TO_TEAM:
        return CITY_TO_TEAM[name_lower]
    
    # Check abbreviation mapping
    name_upper = name.strip().upper()
    if name_upper in TEAM_ABBREV_MAP:
        return TEAM_ABBREV_MAP[name_upper]
    
    return name.strip()


def get_team_abbrev(team_name: str) -> str:
    """Get abbreviation from full team name."""
    abbrev_reverse = {v: k for k, v in TEAM_ABBREV_MAP.items() if len(k) == 3}
    return abbrev_reverse.get(team_name, team_name[:3].upper())


# ============================================================================
# Request helpers
# ============================================================================

def _get_page(url: str, headers: dict = None, max_retries: int = 3, retry_delay: float = 5.0) -> Optional[str]:
    """Fetch a page with proper headers and retry logic for rate limiting."""
    if not HAS_SCRAPING_DEPS:
        raise ImportError("requests and beautifulsoup4 are required for web scraping. "
                         "Install them with: pip install requests beautifulsoup4")
    
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    if headers:
        default_headers.update(headers)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=default_headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Too Many Requests
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
            print(f"Error fetching {url}: {e}")
            return None
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
    
    return None


# ============================================================================
# ESPN Injury Scraper
# ============================================================================

def scrape_espn_injuries() -> ScrapedInjuryReport:
    """
    Scrape injury report from ESPN.
    
    URL: https://www.espn.com/nba/injuries
    
    Returns:
        ScrapedInjuryReport with all injuries grouped by team
    """
    url = "https://www.espn.com/nba/injuries"
    html = _get_page(url)
    
    if not html:
        return ScrapedInjuryReport(scrape_time=datetime.now().isoformat())
    
    soup = BeautifulSoup(html, "html.parser")
    report = ScrapedInjuryReport(scrape_time=datetime.now().isoformat())
    
    # ESPN uses sections where each team has:
    # - A header element (div or heading) with just the team name
    # - A table with injury data
    
    # Method 1: Find all team sections by looking for team name patterns
    # ESPN's structure has team headers that match known team names
    all_team_names = list(TEAM_NAME_MAP.values())  # All full team names
    
    # Find all text nodes that are known team names
    # These serve as section headers
    current_team = None
    processed_tables = set()
    
    # Find team sections - look for parent containers with team headers
    # ESPN uses <section> or similar container elements
    for section in soup.find_all(["section", "div"]):
        # Look for a team name in the section's immediate children
        for child in section.children:
            if hasattr(child, 'get_text'):
                text = child.get_text(strip=True)
                # Check if this is a team name (but not a long concatenated string)
                if len(text) < 50:  # Team names are short
                    normalized = normalize_team_name(text)
                    if normalized in all_team_names:
                        current_team = normalized
                        break
        
        if not current_team:
            continue
        
        # Find table in this section
        table = section.find("table")
        if table and id(table) not in processed_tables:
            processed_tables.add(id(table))
            _parse_espn_injury_table(table, current_team, report)
    
    # Method 2: Fallback - iterate through all tables and find preceding team headers
    if len(report.injuries) == 0:
        tables = soup.find_all("table")
        for table in tables:
            if id(table) in processed_tables:
                continue
            
            # Look for team name in previous siblings, going up the tree
            team_name = _find_team_header_for_table(table, all_team_names)
            if team_name:
                _parse_espn_injury_table(table, team_name, report)
    
    return report


def _find_team_header_for_table(table, all_team_names: list) -> Optional[str]:
    """Find the team name header for a given table element."""
    # Walk up the tree and look at previous siblings
    current = table
    for _ in range(10):  # Limit depth
        # Check previous siblings
        for sibling in current.previous_siblings:
            if hasattr(sibling, 'get_text'):
                text = sibling.get_text(strip=True)
                if len(text) < 50:  # Team names are short
                    normalized = normalize_team_name(text)
                    if normalized in all_team_names:
                        return normalized
        # Move up to parent
        if current.parent:
            current = current.parent
        else:
            break
    return None


def _parse_espn_injury_table(table, team_name: str, report: ScrapedInjuryReport):
    """Parse an ESPN injury table and add injuries to the report."""
    rows = table.find_all("tr")
    
    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 4:
            continue
        
        # Skip header rows
        first_cell_text = cells[0].get_text(strip=True).upper()
        if first_cell_text in ["NAME", "PLAYER", ""]:
            continue
        if cells[0].get("class") and "Table__TH" in " ".join(cells[0].get("class", [])):
            continue
        
        # Extract player name - may be in a link
        player_cell = cells[0]
        player_link = player_cell.find("a")
        if player_link:
            player_name = player_link.get_text(strip=True)
        else:
            player_name = player_cell.get_text(strip=True)
        
        # Skip if player name is too long (likely a parsing error with concatenated cells)
        if len(player_name) > 100:
            continue
        
        # Skip empty or header rows
        if not player_name or player_name.upper() in ["NAME", "PLAYER"]:
            continue
        
        # Extract other fields
        position = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        est_return = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        status = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        comment = cells[4].get_text(strip=True) if len(cells) > 4 else ""
        
        # Skip if position is too long (parsing error)
        if len(position) > 10:
            continue
        
        injury = ScrapedInjury(
            team_name=team_name,
            player_name=player_name,
            position=position,
            status=status,
            est_return_date=est_return,
            comment=comment,
        )
        report.injuries.append(injury)


# ============================================================================
# ESPN Schedule/Matchups Scraper
# ============================================================================

def scrape_espn_schedule(date_str: str) -> list[ScrapedMatchup]:
    """
    Scrape NBA schedule/matchups from ESPN for a specific date.
    
    Args:
        date_str: Date in format "YYYYMMDD" or "YYYY-MM-DD"
    
    URL: https://www.espn.com/nba/schedule/_/date/YYYYMMDD
    
    Returns:
        List of ScrapedMatchup objects for games on that date ONLY
    """
    # Normalize date format to YYYYMMDD
    date_str = date_str.replace("-", "")
    url = f"https://www.espn.com/nba/schedule/_/date/{date_str}"
    
    html = _get_page(url)
    if not html:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    matchups = []
    
    # Parse date to YYYY-MM-DD format for output
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        game_date = dt.strftime("%Y-%m-%d")
        # Create target date patterns (e.g., "January 27, 2026")
        # Note: Use non-padded day for matching
        target_date_str = f"{dt.strftime('%B')} {dt.day}, {dt.year}"  # "January 27, 2026"
    except ValueError:
        game_date = date_str
        target_date_str = None
    
    # ESPN shows multiple dates on the page with date headers like:
    # "Tuesday, January 27, 2026" followed by a table of games
    # We need to find ONLY the table for our target date
    
    # Strategy: Find all date headers, identify which one matches our target,
    # then only process the table that follows it
    
    # Find the target date section by looking for the date text in the page
    target_table = None
    
    if target_date_str:
        # Find all elements that contain our target date string
        page_text = html
        
        # Find tables and check which one is under our target date
        tables = soup.find_all("table")
        
        for i, table in enumerate(tables):
            # Get all preceding text from the table up to the previous table (or start)
            preceding_text = ""
            
            # Walk backwards to find the nearest date header
            current = table
            for _ in range(50):  # Limit iterations
                prev = current.previous_element
                if prev is None:
                    break
                current = prev
                
                if hasattr(prev, 'get_text'):
                    text = prev.get_text(strip=True) if hasattr(prev, 'get_text') else str(prev)
                    # Check if this is a date header for our target
                    if target_date_str in text:
                        target_table = table
                        break
                    # Check if we hit a different date (means we passed our section)
                    elif any(f", {dt.year}" in text for month in 
                            ["January", "February", "March", "April", "May", "June",
                             "July", "August", "September", "October", "November", "December"]
                            if month in text and target_date_str not in text):
                        break
                elif isinstance(prev, str):
                    if target_date_str in prev:
                        target_table = table
                        break
            
            if target_table:
                break
    
    # If we couldn't find the target table, fall back to first table
    # but this shouldn't happen normally
    if target_table is None:
        tables = soup.find_all("table")
        if tables:
            target_table = tables[0]
    
    if target_table is None:
        return []
    
    # Now parse only the target table
    rows = target_table.find_all("tr")
    
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        
        # Try to extract matchup info from the row
        # ESPN format: Team @ Team | Time | TV | Tickets | Odds
        row_text = row.get_text(separator=" | ", strip=True)
        
        # Look for @ symbol indicating away @ home
        if "@" not in row_text:
            continue
        
        # Find team links - ESPN uses links with /nba/team/_/name/ pattern
        # Note: ESPN has 2 links per team (image + text), filter to non-empty text only
        all_team_links = row.find_all("a", href=re.compile(r"/nba/team/_/name/"))
        team_links = [link for link in all_team_links if link.get_text(strip=True)]
        
        away_team = None
        home_team = None
        
        if len(team_links) >= 2:
            # First non-empty team link is away, second is home
            away_team = normalize_team_name(team_links[0].get_text(strip=True))
            home_team = normalize_team_name(team_links[1].get_text(strip=True))
        elif len(all_team_links) >= 2:
            # Try extracting from href if text is empty
            teams_from_href = []
            for link in all_team_links:
                href = link.get("href", "")
                match = re.search(r"/nba/team/_/name/([^/]+)", href)
                if match:
                    abbrev = match.group(1).upper()
                    team_name = TEAM_ABBREV_MAP.get(abbrev)
                    if team_name and team_name not in teams_from_href:
                        teams_from_href.append(team_name)
            if len(teams_from_href) >= 2:
                away_team = teams_from_href[0]
                home_team = teams_from_href[1]
        
        # Fallback: try text parsing
        if not away_team or not home_team:
            parts = row_text.split("@")
            if len(parts) >= 2:
                away_part = parts[0].strip().split("|")[-1].strip()
                home_part = parts[1].strip().split("|")[0].strip()
                away_team = normalize_team_name(away_part)
                home_team = normalize_team_name(home_part)
        
        # Skip if we couldn't find both teams
        if not away_team or not home_team:
            continue
        
        # Skip if either team name is too short (likely parsing error)
        if len(away_team) < 5 or len(home_team) < 5:
            continue
        
        # Extract game time
        time_match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)", row_text, re.IGNORECASE)
        game_time = time_match.group(1) if time_match else None
        
        # Extract spread
        spread = None
        favorite = None
        spread_match = re.search(r"Line:\s*([A-Z]{2,3})\s*([+-]?\d+\.?\d*)", row_text)
        if spread_match:
            favorite = spread_match.group(1)
            spread = float(spread_match.group(2))
        
        # Extract over/under
        over_under = None
        ou_match = re.search(r"O/U:\s*(\d+\.?\d*)", row_text)
        if ou_match:
            over_under = float(ou_match.group(1))
        
        # Determine status
        status = "scheduled"
        if "LIVE" in row_text.upper():
            status = "live"
        elif re.search(r"[A-Z]{2,3}\s+\d+,?\s+[A-Z]{2,3}\s+\d+", row_text):
            status = "completed"
        
        # Check for TV channel
        tv_channel = None
        for channel in ["ESPN", "TNT", "ABC", "NBC", "NBA TV", "Peacock"]:
            if channel.upper() in row_text.upper():
                tv_channel = channel
                break
        
        matchup = ScrapedMatchup(
            game_date=game_date,
            away_team=away_team,
            home_team=home_team,
            game_time=game_time,
            tv_channel=tv_channel,
            spread=spread,
            favorite=favorite,
            over_under=over_under,
            status=status,
        )
        matchups.append(matchup)
    
    # Deduplicate matchups (same teams shouldn't appear twice for same date)
    seen = set()
    unique_matchups = []
    for m in matchups:
        key = (m.away_team, m.home_team)
        if key not in seen:
            seen.add(key)
            unique_matchups.append(m)
    
    return unique_matchups


# ============================================================================
# NBA.com Box Score Scraper (JSON API)
# ============================================================================

# NBA.com team ID to team name mapping
NBA_TEAM_ID_MAP = {
    1610612737: "Atlanta Hawks",
    1610612738: "Boston Celtics",
    1610612751: "Brooklyn Nets",
    1610612766: "Charlotte Hornets",
    1610612741: "Chicago Bulls",
    1610612739: "Cleveland Cavaliers",
    1610612742: "Dallas Mavericks",
    1610612743: "Denver Nuggets",
    1610612765: "Detroit Pistons",
    1610612744: "Golden State Warriors",
    1610612745: "Houston Rockets",
    1610612754: "Indiana Pacers",
    1610612746: "Los Angeles Clippers",
    1610612747: "Los Angeles Lakers",
    1610612763: "Memphis Grizzlies",
    1610612748: "Miami Heat",
    1610612749: "Milwaukee Bucks",
    1610612750: "Minnesota Timberwolves",
    1610612740: "New Orleans Pelicans",
    1610612752: "New York Knicks",
    1610612760: "Oklahoma City Thunder",
    1610612753: "Orlando Magic",
    1610612755: "Philadelphia 76ers",
    1610612756: "Phoenix Suns",
    1610612757: "Portland Trail Blazers",
    1610612758: "Sacramento Kings",
    1610612759: "San Antonio Spurs",
    1610612761: "Toronto Raptors",
    1610612762: "Utah Jazz",
    1610612764: "Washington Wizards",
}

# Reverse mapping: team name to ID
TEAM_NAME_TO_NBA_ID = {v: k for k, v in NBA_TEAM_ID_MAP.items()}


def _get_json(url: str, headers: dict = None, max_retries: int = 3, retry_delay: float = 2.0) -> Optional[dict]:
    """Fetch JSON from a URL with retry logic."""
    if not HAS_SCRAPING_DEPS:
        raise ImportError("requests is required for web scraping. "
                         "Install it with: pip install requests")
    
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com",
    }
    
    if headers:
        default_headers.update(headers)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=default_headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Too Many Requests
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
            print(f"Error fetching {url}: {e}")
            return None
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
        except ValueError as e:
            print(f"Error parsing JSON from {url}: {e}")
            return None
    
    return None


def get_nba_schedule_for_date(date_str: str) -> list[dict]:
    """
    Get NBA games scheduled for a specific date from NBA.com schedule API.
    
    Args:
        date_str: Date in format "YYYY-MM-DD" or "YYYYMMDD"
    
    Returns:
        List of game dicts with gameId, homeTeam, awayTeam, gameStatus
    """
    # Normalize date format
    date_str = date_str.replace("-", "")
    if len(date_str) != 8:
        raise ValueError(f"Invalid date format: {date_str}")
    
    # Format to YYYY-MM-DD for matching
    dt = datetime.strptime(date_str, "%Y%m%d")
    target_date = dt.strftime("%Y-%m-%d")
    
    # Use the NBA.com CDN scoreboard API for the specific date
    # Format: https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json
    # For historical dates, we use the schedule API
    schedule_url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
    
    data = _get_json(schedule_url)
    if not data:
        return []
    
    games = []
    
    # Navigate to the games list
    try:
        league_schedule = data.get("leagueSchedule", {})
        game_dates = league_schedule.get("gameDates", [])
        
        for game_date_entry in game_dates:
            game_date = game_date_entry.get("gameDate", "")
            # gameDate format: "01/26/2026 12:00:00 AM" - extract just the date
            if game_date:
                date_part = game_date.split(" ")[0]  # "01/26/2026"
                # Convert to YYYY-MM-DD
                try:
                    dt_entry = datetime.strptime(date_part, "%m/%d/%Y")
                    entry_date_str = dt_entry.strftime("%Y-%m-%d")
                except ValueError:
                    continue
                
                if entry_date_str == target_date:
                    for game in game_date_entry.get("games", []):
                        game_id = game.get("gameId", "")
                        home_team = game.get("homeTeam", {})
                        away_team = game.get("awayTeam", {})
                        game_status = game.get("gameStatus", 1)  # 1=scheduled, 2=live, 3=final
                        
                        games.append({
                            "gameId": game_id,
                            "homeTeam": {
                                "teamId": home_team.get("teamId"),
                                "teamName": home_team.get("teamName", ""),
                                "teamCity": home_team.get("teamCity", ""),
                                "teamTricode": home_team.get("teamTricode", ""),
                            },
                            "awayTeam": {
                                "teamId": away_team.get("teamId"),
                                "teamName": away_team.get("teamName", ""),
                                "teamCity": away_team.get("teamCity", ""),
                                "teamTricode": away_team.get("teamTricode", ""),
                            },
                            "gameStatus": game_status,
                            "gameStatusText": game.get("gameStatusText", ""),
                        })
                    break  # Found the date, no need to continue
    except Exception as e:
        print(f"Error parsing NBA schedule: {e}")
        return []
    
    return games


def scrape_nba_box_score(game_id: str, game_date: str, away_team: str, home_team: str) -> ScrapedBoxScore:
    """
    Scrape a box score from NBA.com JSON API.
    
    Args:
        game_id: NBA.com game ID (e.g., "0022500656")
        game_date: Date in YYYY-MM-DD format
        away_team: Away team full name
        home_team: Home team full name
    
    Returns:
        ScrapedBoxScore with player stats
    """
    url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
    
    box_score = ScrapedBoxScore(
        game_date=game_date,
        away_team=away_team,
        home_team=home_team,
        box_score_url=f"https://www.nba.com/game/{game_id}/box-score",
    )
    
    data = _get_json(url)
    if not data:
        return box_score
    
    try:
        game = data.get("game", {})
        
        # Get scores
        home_team_data = game.get("homeTeam", {})
        away_team_data = game.get("awayTeam", {})
        
        box_score.home_score = home_team_data.get("score")
        box_score.away_score = away_team_data.get("score")
        
        # Parse player stats for away team
        for player in away_team_data.get("players", []):
            stats = player.get("statistics", {})
            
            # Skip players with no minutes (DNP)
            minutes_str = stats.get("minutes", "PT00M00.00S")
            if minutes_str == "PT00M00.00S" or not stats:
                continue
            
            # Parse minutes from ISO format (e.g., "PT32M45.00S" -> "32:45")
            minutes = _parse_nba_minutes(minutes_str)
            
            player_stats = ScrapedPlayerStats(
                player_name=player.get("name", ""),
                team=away_team,
                minutes=minutes,
                fg=f"{stats.get('fieldGoalsMade', 0)}-{stats.get('fieldGoalsAttempted', 0)}",
                fg_pct=f"{stats.get('fieldGoalsPercentage', 0):.1f}",
                tp=f"{stats.get('threePointersMade', 0)}-{stats.get('threePointersAttempted', 0)}",
                tp_pct=f"{stats.get('threePointersPercentage', 0):.1f}",
                ft=f"{stats.get('freeThrowsMade', 0)}-{stats.get('freeThrowsAttempted', 0)}",
                ft_pct=f"{stats.get('freeThrowsPercentage', 0):.1f}",
                oreb=stats.get("reboundsOffensive"),
                dreb=stats.get("reboundsDefensive"),
                reb=stats.get("reboundsTotal"),
                ast=stats.get("assists"),
                stl=stats.get("steals"),
                blk=stats.get("blocks"),
                tov=stats.get("turnovers"),
                pf=stats.get("foulsPersonal"),
                pts=stats.get("points"),
                plus_minus=stats.get("plusMinusPoints"),
            )
            box_score.player_stats.append(player_stats)
        
        # Parse player stats for home team
        for player in home_team_data.get("players", []):
            stats = player.get("statistics", {})
            
            # Skip players with no minutes (DNP)
            minutes_str = stats.get("minutes", "PT00M00.00S")
            if minutes_str == "PT00M00.00S" or not stats:
                continue
            
            # Parse minutes
            minutes = _parse_nba_minutes(minutes_str)
            
            player_stats = ScrapedPlayerStats(
                player_name=player.get("name", ""),
                team=home_team,
                minutes=minutes,
                fg=f"{stats.get('fieldGoalsMade', 0)}-{stats.get('fieldGoalsAttempted', 0)}",
                fg_pct=f"{stats.get('fieldGoalsPercentage', 0):.1f}",
                tp=f"{stats.get('threePointersMade', 0)}-{stats.get('threePointersAttempted', 0)}",
                tp_pct=f"{stats.get('threePointersPercentage', 0):.1f}",
                ft=f"{stats.get('freeThrowsMade', 0)}-{stats.get('freeThrowsAttempted', 0)}",
                ft_pct=f"{stats.get('freeThrowsPercentage', 0):.1f}",
                oreb=stats.get("reboundsOffensive"),
                dreb=stats.get("reboundsDefensive"),
                reb=stats.get("reboundsTotal"),
                ast=stats.get("assists"),
                stl=stats.get("steals"),
                blk=stats.get("blocks"),
                tov=stats.get("turnovers"),
                pf=stats.get("foulsPersonal"),
                pts=stats.get("points"),
                plus_minus=stats.get("plusMinusPoints"),
            )
            box_score.player_stats.append(player_stats)
    
    except Exception as e:
        print(f"Error parsing box score for game {game_id}: {e}")
    
    return box_score


def _parse_nba_minutes(minutes_str: str) -> str:
    """
    Parse NBA.com minutes format (ISO 8601 duration) to readable format.
    
    Args:
        minutes_str: e.g., "PT32M45.00S" or "PT5M30.00S"
    
    Returns:
        Formatted string like "32:45" or "5:30"
    """
    if not minutes_str or minutes_str == "PT00M00.00S":
        return "0:00"
    
    # Parse PT{minutes}M{seconds}S format
    match = re.match(r"PT(\d+)M([\d.]+)S", minutes_str)
    if match:
        mins = int(match.group(1))
        secs = int(float(match.group(2)))
        return f"{mins}:{secs:02d}"
    
    return minutes_str


def scrape_box_scores_for_date(date_str: str) -> list[ScrapedBoxScore]:
    """
    Scrape all box scores for a specific date from NBA.com.
    
    Args:
        date_str: Date in format "YYYY-MM-DD", "YYYYMMDD", or "MM/DD/YYYY"
    
    Returns:
        List of ScrapedBoxScore objects
    """
    # Normalize date
    date_str = date_str.replace("/", "-")
    if len(date_str) == 8 and "-" not in date_str:
        dt = datetime.strptime(date_str, "%Y%m%d")
        date_str = dt.strftime("%Y-%m-%d")
    
    # Get games for this date from NBA schedule
    games = get_nba_schedule_for_date(date_str)
    
    if not games:
        print(f"No games found for {date_str}")
        return []
    
    box_scores = []
    for game in games:
        # Only scrape completed games (gameStatus == 3)
        if game.get("gameStatus") != 3:
            status_text = game.get("gameStatusText", "not completed")
            print(f"Skipping game {game['gameId']} - {status_text}")
            continue
        
        game_id = game["gameId"]
        away_team_data = game["awayTeam"]
        home_team_data = game["homeTeam"]
        
        # Build full team names
        away_team = f"{away_team_data['teamCity']} {away_team_data['teamName']}"
        home_team = f"{home_team_data['teamCity']} {home_team_data['teamName']}"
        
        # Normalize team names
        away_team = normalize_team_name(away_team)
        home_team = normalize_team_name(home_team)
        
        print(f"Scraping box score: {away_team} @ {home_team} (game {game_id})...")
        box_score = scrape_nba_box_score(game_id, date_str, away_team, home_team)
        box_scores.append(box_score)
        
        # Be polite to the server
        time.sleep(0.5)
    
    return box_scores


# ============================================================================
# Export functions for formatted output
# ============================================================================

def injuries_to_text(report: ScrapedInjuryReport) -> str:
    """Convert injury report to readable text format."""
    lines = [
        f"NBA Injury Report",
        f"Scraped: {report.scrape_time}",
        f"Total injuries: {len(report.injuries)}",
        "=" * 60,
        "",
    ]
    
    # Group by team
    by_team = {}
    for injury in report.injuries:
        team = injury.team_name
        if team not in by_team:
            by_team[team] = []
        by_team[team].append(injury)
    
    for team in sorted(by_team.keys()):
        lines.append(f"\n{team}")
        lines.append("-" * 40)
        for injury in by_team[team]:
            lines.append(f"  {injury.player_name} ({injury.position})")
            lines.append(f"    Status: {injury.status}")
            lines.append(f"    Est. Return: {injury.est_return_date}")
            lines.append(f"    Details: {injury.comment[:100]}..." if len(injury.comment) > 100 else f"    Details: {injury.comment}")
    
    return "\n".join(lines)


def matchups_to_text(matchups: list[ScrapedMatchup]) -> str:
    """Convert matchups to readable text format."""
    if not matchups:
        return "No matchups found."
    
    lines = [
        f"NBA Matchups for {matchups[0].game_date}",
        f"Total games: {len(matchups)}",
        "=" * 60,
        "",
    ]
    
    for m in matchups:
        lines.append(f"{m.away_team} @ {m.home_team}")
        if m.game_time:
            lines.append(f"  Time: {m.game_time}")
        if m.tv_channel:
            lines.append(f"  TV: {m.tv_channel}")
        if m.spread is not None:
            lines.append(f"  Spread: {m.favorite} {m.spread:+.1f}")
        if m.over_under is not None:
            lines.append(f"  O/U: {m.over_under}")
        lines.append(f"  Status: {m.status}")
        lines.append("")
    
    return "\n".join(lines)


def box_scores_to_text(box_scores: list[ScrapedBoxScore]) -> str:
    """Convert box scores to readable text format."""
    if not box_scores:
        return "No box scores found."
    
    lines = [
        f"NBA Box Scores for {box_scores[0].game_date}",
        f"Total games: {len(box_scores)}",
        "=" * 60,
    ]
    
    for bs in box_scores:
        lines.append("")
        lines.append(f"{bs.away_team} ({bs.away_score or '?'}) @ {bs.home_team} ({bs.home_score or '?'})")
        lines.append(f"URL: {bs.box_score_url}")
        lines.append("-" * 50)
        
        # Group stats by team
        by_team = {}
        for ps in bs.player_stats:
            if ps.team not in by_team:
                by_team[ps.team] = []
            by_team[ps.team].append(ps)
        
        for team, players in by_team.items():
            lines.append(f"\n{team}:")
            lines.append(f"{'Player':<25} {'MIN':<8} {'PTS':<5} {'REB':<5} {'AST':<5} {'STL':<5} {'BLK':<5}")
            lines.append("-" * 60)
            for p in players:
                mins = p.minutes or "-"
                pts = str(p.pts) if p.pts is not None else "-"
                reb = str(p.reb) if p.reb is not None else "-"
                ast = str(p.ast) if p.ast is not None else "-"
                stl = str(p.stl) if p.stl is not None else "-"
                blk = str(p.blk) if p.blk is not None else "-"
                lines.append(f"{p.player_name:<25} {mins:<8} {pts:<5} {reb:<5} {ast:<5} {stl:<5} {blk:<5}")
    
    return "\n".join(lines)


# ============================================================================
# Main entry points for CLI/Web integration
# ============================================================================

def fetch_injuries() -> ScrapedInjuryReport:
    """Fetch current injury report from ESPN."""
    return scrape_espn_injuries()


def fetch_matchups(date_str: str) -> list[ScrapedMatchup]:
    """Fetch matchups for a specific date from ESPN."""
    return scrape_espn_schedule(date_str)


def fetch_box_scores(date_str: str) -> list[ScrapedBoxScore]:
    """Fetch box scores for a specific date from NBA.com JSON API."""
    return scrape_box_scores_for_date(date_str)

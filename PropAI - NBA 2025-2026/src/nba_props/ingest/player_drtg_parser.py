"""
Player Defensive Rating (DRTG) Parser
=====================================

Parses raw data from StatMuse or similar sources that provide individual
player defensive ratings (DRTG).

DRTG (Defensive Rating) is the number of points a player allows per 100 possessions.
Lower DRTG = better defender.

Data format example (from StatMuse):
    NAME	DRTG	SEASON	TM	GP	MPG	PPG	RPG	APG	SPG	BPG	...
1	Mark Williams	109.5	2025-26	PHX	31	23.7	12.4	8.2	1.1	1.2	0.8	...

The parser extracts:
- Player name
- DRTG value
- Season
- Team abbreviation
- Games played, minutes per game
- Basic stats (PPG, RPG, APG, SPG, BPG)

Usage:
    from nba_props.ingest.player_drtg_parser import parse_player_drtg_text, save_player_drtg_to_db
    
    result = parse_player_drtg_text(raw_text)
    with db.connect() as conn:
        save_player_drtg_to_db(conn, result)
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..team_aliases import normalize_team_abbrev, team_name_from_abbrev


@dataclass
class PlayerDRTG:
    """A single player's defensive rating data."""
    rank: int  # Rank on the team for DRTG
    name: str
    drtg: float  # Defensive rating (lower = better)
    season: str  # e.g., "2025-26"
    team_abbrev: str  # e.g., "PHX"
    games_played: int
    minutes_per_game: float
    
    # Optional additional stats
    ppg: Optional[float] = None
    rpg: Optional[float] = None
    apg: Optional[float] = None
    spg: Optional[float] = None
    bpg: Optional[float] = None
    plus_minus: Optional[int] = None


@dataclass
class PlayerDRTGParseResult:
    """Result of parsing player DRTG data."""
    team_abbrev: str
    season: str
    rows: list[PlayerDRTG]
    parse_date: str  # When we parsed this data
    source_url: Optional[str] = None
    errors: list[str] = field(default_factory=list)


def _clean_player_name(name: str) -> str:
    """Clean player name by removing duplicate names and extra whitespace."""
    # Handle cases like "Mark Williams\nMark Williams" 
    parts = name.strip().split('\n')
    if len(parts) > 1:
        # Take the first non-empty part
        name = parts[0].strip()
    
    # Remove any extra whitespace
    name = ' '.join(name.split())
    return name


def _normalize_team_from_raw(raw_team: str) -> str:
    """Normalize team abbreviation from raw input like 'PHXPHX' or 'PHX'."""
    raw = raw_team.strip().upper()
    
    # Handle doubled abbreviations like "PHXPHX"
    if len(raw) >= 6 and raw[:3] == raw[3:6]:
        raw = raw[:3]
    elif len(raw) >= 4 and raw[:2] == raw[2:4]:
        raw = raw[:2]
    
    # Common abbreviation normalizations
    abbrev_map = {
        "NO": "NOP", "PHO": "PHX", "GS": "GSW", "SA": "SAS", 
        "NY": "NYK", "BKN": "BKN", "WSH": "WAS", "CHA": "CHO"
    }
    
    normalized = normalize_team_abbrev(raw)
    if normalized:
        return normalized
    
    return abbrev_map.get(raw, raw)


def _parse_float_safe(value: str) -> Optional[float]:
    """Safely parse a float value."""
    try:
        # Remove commas from numbers like "1,062"
        cleaned = value.strip().replace(',', '')
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def _parse_int_safe(value: str) -> Optional[int]:
    """Safely parse an integer value."""
    try:
        cleaned = value.strip().replace(',', '')
        return int(float(cleaned))  # Handle "31.0" -> 31
    except (ValueError, AttributeError):
        return None


def _parse_plus_minus(value: str) -> Optional[int]:
    """Parse plus/minus value like '+37' or '-20'."""
    try:
        cleaned = value.strip().replace('+', '')
        return int(cleaned)
    except (ValueError, AttributeError):
        return None


# Team name patterns for auto-detection
_TEAM_NAME_PATTERNS = {
    "pistons": "DET",
    "detroit": "DET",
    "celtics": "BOS",
    "boston": "BOS",
    "nets": "BKN",
    "brooklyn": "BKN",
    "hornets": "CHA",
    "charlotte": "CHA",
    "bulls": "CHI",
    "chicago": "CHI",
    "cavaliers": "CLE",
    "cleveland": "CLE",
    "cavs": "CLE",
    "mavericks": "DAL",
    "dallas": "DAL",
    "mavs": "DAL",
    "nuggets": "DEN",
    "denver": "DEN",
    "warriors": "GSW",
    "golden state": "GSW",
    "rockets": "HOU",
    "houston": "HOU",
    "pacers": "IND",
    "indiana": "IND",
    "clippers": "LAC",
    "lakers": "LAL",
    "grizzlies": "MEM",
    "memphis": "MEM",
    "heat": "MIA",
    "miami": "MIA",
    "bucks": "MIL",
    "milwaukee": "MIL",
    "timberwolves": "MIN",
    "minnesota": "MIN",
    "wolves": "MIN",
    "pelicans": "NOP",
    "new orleans": "NOP",
    "knicks": "NYK",
    "new york": "NYK",
    "thunder": "OKC",
    "oklahoma city": "OKC",
    "okc": "OKC",
    "magic": "ORL",
    "orlando": "ORL",
    "76ers": "PHI",
    "sixers": "PHI",
    "philadelphia": "PHI",
    "suns": "PHX",
    "phoenix": "PHX",
    "trail blazers": "POR",
    "blazers": "POR",
    "portland": "POR",
    "kings": "SAC",
    "sacramento": "SAC",
    "spurs": "SAS",
    "san antonio": "SAS",
    "raptors": "TOR",
    "toronto": "TOR",
    "jazz": "UTA",
    "utah": "UTA",
    "wizards": "WAS",
    "washington": "WAS",
    "hawks": "ATL",
    "atlanta": "ATL",
}


def _detect_team_from_text(text: str) -> Optional[str]:
    """
    Try to detect the team from the text content.
    
    Looks for patterns like:
    - "which pistons player"
    - "Phoenix Suns players"
    - "for the Pistons this season"
    - "Interpreted as: Which pistons player"
    - "Lakers defensive rating"
    """
    text_lower = text.lower()
    
    # Look for patterns like "which <team> player" or "<team> players"
    # Check first 2000 characters for team mentions
    sample = text_lower[:2000]
    
    # Sort by length (longer names first) to match "new orleans" before "new"
    for team_name, abbrev in sorted(_TEAM_NAME_PATTERNS.items(), key=lambda x: -len(x[0])):
        # Check for patterns like:
        # - "which <team> player"
        # - "for the <team>"
        # - "<Team> players"
        # - "<team> this season"
        # - "<team> defensive"
        # - "<team>'s" (possessive)
        patterns = [
            f"which {team_name}",
            f"for the {team_name}",
            f"{team_name} player",
            f"{team_name} this season",
            f"{team_name}'s",
            f"{team_name} defensive",
            f"{team_name} defense",
            f"{team_name} has the",
            f"the {team_name}",
        ]
        for pattern in patterns:
            if pattern in sample:
                return abbrev
    
    return None


def parse_player_drtg_text(
    text: str,
    expected_team: Optional[str] = None,
    expected_season: str = "2025-26",
) -> PlayerDRTGParseResult:
    """
    Parse player DRTG data from raw text (typically from StatMuse).
    
    The parser is designed to handle noisy input with ads, navigation elements,
    and other extraneous content mixed in with the data.
    
    Args:
        text: Raw text containing DRTG data
        expected_team: If provided, filter to this team only. If None, will try to auto-detect.
        expected_season: Season to use (default: 2025-26)
    
    Returns:
        PlayerDRTGParseResult with parsed rows and metadata
    """
    rows: list[PlayerDRTG] = []
    errors: list[str] = []
    
    # Try to auto-detect team if not provided
    detected_team = expected_team
    if not detected_team:
        detected_team = _detect_team_from_text(text)
    
    lines = text.split('\n')
    
    # First pass: find the data rows
    # Look for patterns like "1\tMark Williams\n109.5\n2025-26\nPHXPHX\n31\n..."
    # Or tab-separated: "1\tMark Williams\t109.5\t2025-26\tPHX\t31\t..."
    
    # Collect all content into segments for analysis
    all_values: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Split on tabs and add each part
        parts = line.split('\t')
        for part in parts:
            part = part.strip()
            if part:
                all_values.append(part)
    
    # Now look for data patterns
    # A valid row starts with a rank number (1, 2, 3...)
    # followed by player name, DRTG, season, team, GP, MPG, PPG, RPG, APG, SPG, BPG, ...
    
    i = 0
    while i < len(all_values):
        # Check if this looks like a rank number (1-30)
        try:
            rank = int(all_values[i])
            if not (1 <= rank <= 50):
                i += 1
                continue
        except ValueError:
            i += 1
            continue
        
        # Found a potential rank, try to parse the row
        # Expected order: rank, name, drtg, season, team, gp, mpg, ppg, rpg, apg, spg, bpg, ...
        
        if i + 10 >= len(all_values):
            i += 1
            continue
        
        # Collect potential values - the name might be split across multiple entries
        name_parts = []
        j = i + 1
        
        # Collect name parts until we hit the DRTG value (a float around 100-130)
        while j < len(all_values):
            val = all_values[j]
            # Check if this looks like a DRTG value (90-140 range typically)
            try:
                maybe_drtg = float(val)
                if 90 <= maybe_drtg <= 140:
                    break
            except ValueError:
                pass
            name_parts.append(val)
            j += 1
            if len(name_parts) > 5:  # Too many parts, probably not a valid row
                break
        
        if not name_parts or j >= len(all_values):
            i += 1
            continue
        
        # Parse the name
        name = _clean_player_name(' '.join(name_parts))
        
        # Validate it looks like a player name (at least 2 parts)
        if len(name.split()) < 2 or len(name) < 5:
            i += 1
            continue
        
        # Now j points to the DRTG value
        drtg = _parse_float_safe(all_values[j])
        if drtg is None or not (90 <= drtg <= 140):
            i += 1
            continue
        
        # Continue parsing remaining fields
        j += 1
        
        # Season (should look like "2025-26")
        season = expected_season
        if j < len(all_values) and re.match(r'\d{4}-\d{2}', all_values[j]):
            season = all_values[j]
            j += 1
        
        # Team abbreviation
        if j >= len(all_values):
            i += 1
            continue
        team_raw = all_values[j]
        team_abbrev = _normalize_team_from_raw(team_raw)
        j += 1
        
        # If expected_team is provided, filter
        if expected_team and team_abbrev != expected_team.upper():
            i += 1
            continue
        
        if not detected_team:
            detected_team = team_abbrev
        
        # Games Played
        gp = _parse_int_safe(all_values[j]) if j < len(all_values) else None
        if gp is None or not (1 <= gp <= 100):
            i += 1
            continue
        j += 1
        
        # Minutes per game
        mpg = _parse_float_safe(all_values[j]) if j < len(all_values) else None
        if mpg is None:
            i += 1
            continue
        j += 1
        
        # PPG, RPG, APG, SPG, BPG
        ppg = _parse_float_safe(all_values[j]) if j < len(all_values) else None
        j += 1
        rpg = _parse_float_safe(all_values[j]) if j < len(all_values) else None
        j += 1
        apg = _parse_float_safe(all_values[j]) if j < len(all_values) else None
        j += 1
        spg = _parse_float_safe(all_values[j]) if j < len(all_values) else None
        j += 1
        bpg = _parse_float_safe(all_values[j]) if j < len(all_values) else None
        j += 1
        
        # Check if the next value is a plus/minus (starts with + or -)
        # or a simple integer that could be a plus/minus
        plus_minus = None
        if j < len(all_values):
            val = all_values[j]
            # Check if it's an explicit plus/minus value
            if val.startswith('+') or val.startswith('-'):
                plus_minus = _parse_plus_minus(val)
                j += 1
            else:
                # Could be an implicit plus/minus (just a number)
                # Check if it's in a reasonable range and not a potential next rank
                try:
                    maybe_pm = int(val)
                    # Plus/minus values are typically -200 to +200
                    # But small values 1-30 might be next ranks
                    if abs(maybe_pm) <= 250 and maybe_pm > 30:
                        # Likely a plus/minus value
                        plus_minus = maybe_pm
                        j += 1
                    elif maybe_pm < 0:
                        # Negative numbers are likely plus/minus
                        plus_minus = maybe_pm
                        j += 1
                    # If it's 1-30, leave it for the next rank detection
                except ValueError:
                    pass
        
        # Create the player record
        player = PlayerDRTG(
            rank=rank,
            name=name,
            drtg=drtg,
            season=season,
            team_abbrev=team_abbrev,
            games_played=gp,
            minutes_per_game=mpg,
            ppg=ppg,
            rpg=rpg,
            apg=apg,
            spg=spg,
            bpg=bpg,
            plus_minus=plus_minus,
        )
        rows.append(player)
        
        # Move to next potential row
        i = j
    
    # Validate results
    if not rows:
        errors.append("No valid DRTG data rows parsed from input")
    elif len(rows) < 3:
        errors.append(f"Only {len(rows)} rows parsed - data may be incomplete")
    
    return PlayerDRTGParseResult(
        team_abbrev=detected_team or "UNKNOWN",
        season=expected_season,
        rows=rows,
        parse_date=datetime.now().strftime("%Y-%m-%d"),
        errors=errors,
    )


def save_player_drtg_to_db(
    conn: sqlite3.Connection,
    result: PlayerDRTGParseResult,
) -> dict:
    """
    Save parsed player DRTG data to the database.
    
    Creates the player_drtg table if it doesn't exist.
    Updates existing records or inserts new ones.
    
    Returns dict with status and counts.
    """
    if not result.rows:
        return {"status": "error", "message": "No data to save", "count": 0}
    
    # Create table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_drtg (
            id INTEGER PRIMARY KEY,
            player_id INTEGER,
            player_name TEXT NOT NULL,
            team_abbrev TEXT NOT NULL,
            season TEXT NOT NULL DEFAULT '2025-26',
            drtg REAL NOT NULL,
            drtg_rank INTEGER,
            games_played INTEGER,
            minutes_per_game REAL,
            ppg REAL,
            rpg REAL,
            apg REAL,
            spg REAL,
            bpg REAL,
            plus_minus INTEGER,
            as_of_date TEXT NOT NULL,
            source TEXT DEFAULT 'statmuse',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(player_name, team_abbrev, season)
        )
    """)
    
    # Create indexes for fast lookups
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_drtg_team 
        ON player_drtg(team_abbrev)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_drtg_player 
        ON player_drtg(player_name)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_drtg_drtg 
        ON player_drtg(drtg)
    """)
    
    inserted = 0
    updated = 0
    
    for row in result.rows:
        # Try to find player_id from players table
        player_row = conn.execute(
            "SELECT id FROM players WHERE name = ?",
            (row.name,)
        ).fetchone()
        player_id = player_row["id"] if player_row else None
        
        # Check if record exists
        existing = conn.execute(
            """
            SELECT id FROM player_drtg 
            WHERE player_name = ? AND team_abbrev = ? AND season = ?
            """,
            (row.name, row.team_abbrev, row.season),
        ).fetchone()
        
        if existing:
            # Update existing record
            conn.execute(
                """
                UPDATE player_drtg
                SET player_id = COALESCE(?, player_id),
                    drtg = ?,
                    drtg_rank = ?,
                    games_played = ?,
                    minutes_per_game = ?,
                    ppg = ?,
                    rpg = ?,
                    apg = ?,
                    spg = ?,
                    bpg = ?,
                    plus_minus = ?,
                    as_of_date = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    player_id,
                    row.drtg,
                    row.rank,
                    row.games_played,
                    row.minutes_per_game,
                    row.ppg,
                    row.rpg,
                    row.apg,
                    row.spg,
                    row.bpg,
                    row.plus_minus,
                    result.parse_date,
                    existing["id"],
                ),
            )
            updated += 1
        else:
            # Insert new record
            conn.execute(
                """
                INSERT INTO player_drtg
                (player_id, player_name, team_abbrev, season, drtg, drtg_rank,
                 games_played, minutes_per_game, ppg, rpg, apg, spg, bpg, plus_minus,
                 as_of_date, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'statmuse')
                """,
                (
                    player_id,
                    row.name,
                    row.team_abbrev,
                    row.season,
                    row.drtg,
                    row.rank,
                    row.games_played,
                    row.minutes_per_game,
                    row.ppg,
                    row.rpg,
                    row.apg,
                    row.spg,
                    row.bpg,
                    row.plus_minus,
                    result.parse_date,
                ),
            )
            inserted += 1
    
    conn.commit()
    
    # Update data freshness tracking
    _update_data_freshness(conn, result)
    
    return {
        "status": "success",
        "team": result.team_abbrev,
        "inserted": inserted,
        "updated": updated,
        "total": len(result.rows),
    }


def _update_data_freshness(conn: sqlite3.Connection, result: PlayerDRTGParseResult) -> None:
    """Update the data_freshness table with DRTG info."""
    data_type = f"player_drtg_{result.team_abbrev}"
    
    conn.execute(
        """
        INSERT INTO data_freshness (data_type, last_updated, records_count, notes)
        VALUES (?, datetime('now'), ?, ?)
        ON CONFLICT(data_type) DO UPDATE SET
            last_updated = datetime('now'),
            records_count = excluded.records_count,
            notes = excluded.notes
        """,
        (data_type, len(result.rows), f"DRTG data for {result.team_abbrev}"),
    )
    conn.commit()


def get_player_drtg(
    conn: sqlite3.Connection,
    player_name: str,
    season: str = "2025-26",
) -> Optional[PlayerDRTG]:
    """Get DRTG data for a specific player."""
    row = conn.execute(
        """
        SELECT * FROM player_drtg
        WHERE player_name = ? AND season = ?
        """,
        (player_name, season),
    ).fetchone()
    
    if not row:
        return None
    
    return PlayerDRTG(
        rank=row["drtg_rank"] or 0,
        name=row["player_name"],
        drtg=row["drtg"],
        season=row["season"],
        team_abbrev=row["team_abbrev"],
        games_played=row["games_played"] or 0,
        minutes_per_game=row["minutes_per_game"] or 0.0,
        ppg=row["ppg"],
        rpg=row["rpg"],
        apg=row["apg"],
        spg=row["spg"],
        bpg=row["bpg"],
        plus_minus=row["plus_minus"],
    )


def get_team_drtg_rankings(
    conn: sqlite3.Connection,
    team_abbrev: str,
    season: str = "2025-26",
) -> list[PlayerDRTG]:
    """Get all players with DRTG data for a team, sorted by DRTG (best first)."""
    rows = conn.execute(
        """
        SELECT * FROM player_drtg
        WHERE team_abbrev = ? AND season = ?
        ORDER BY drtg ASC
        """,
        (team_abbrev.upper(), season),
    ).fetchall()
    
    return [
        PlayerDRTG(
            rank=row["drtg_rank"] or i + 1,
            name=row["player_name"],
            drtg=row["drtg"],
            season=row["season"],
            team_abbrev=row["team_abbrev"],
            games_played=row["games_played"] or 0,
            minutes_per_game=row["minutes_per_game"] or 0.0,
            ppg=row["ppg"],
            rpg=row["rpg"],
            apg=row["apg"],
            spg=row["spg"],
            bpg=row["bpg"],
            plus_minus=row["plus_minus"],
        )
        for i, row in enumerate(rows)
    ]


def get_league_drtg_rankings(
    conn: sqlite3.Connection,
    season: str = "2025-26",
    limit: int = 50,
    min_minutes: float = 15.0,
) -> list[PlayerDRTG]:
    """Get league-wide DRTG rankings (best defenders first)."""
    rows = conn.execute(
        """
        SELECT * FROM player_drtg
        WHERE season = ? AND minutes_per_game >= ?
        ORDER BY drtg ASC
        LIMIT ?
        """,
        (season, min_minutes, limit),
    ).fetchall()
    
    return [
        PlayerDRTG(
            rank=i + 1,
            name=row["player_name"],
            drtg=row["drtg"],
            season=row["season"],
            team_abbrev=row["team_abbrev"],
            games_played=row["games_played"] or 0,
            minutes_per_game=row["minutes_per_game"] or 0.0,
            ppg=row["ppg"],
            rpg=row["rpg"],
            apg=row["apg"],
            spg=row["spg"],
            bpg=row["bpg"],
            plus_minus=row["plus_minus"],
        )
        for i, row in enumerate(rows)
    ]


def get_drtg_data_freshness(
    conn: sqlite3.Connection,
    team_abbrev: Optional[str] = None,
) -> dict:
    """
    Get freshness info for DRTG data.
    
    Returns dict with teams that have DRTG data and when it was last updated.
    """
    if team_abbrev:
        row = conn.execute(
            """
            SELECT data_type, last_updated, records_count, notes
            FROM data_freshness
            WHERE data_type = ?
            """,
            (f"player_drtg_{team_abbrev.upper()}",),
        ).fetchone()
        
        if row:
            return {
                "team": team_abbrev.upper(),
                "last_updated": row["last_updated"],
                "records_count": row["records_count"],
                "notes": row["notes"],
            }
        return {"team": team_abbrev.upper(), "last_updated": None, "records_count": 0}
    
    # Get all teams with DRTG data
    rows = conn.execute(
        """
        SELECT data_type, last_updated, records_count, notes
        FROM data_freshness
        WHERE data_type LIKE 'player_drtg_%'
        ORDER BY last_updated DESC
        """,
    ).fetchall()
    
    result = {}
    for row in rows:
        team = row["data_type"].replace("player_drtg_", "")
        result[team] = {
            "last_updated": row["last_updated"],
            "records_count": row["records_count"],
            "notes": row["notes"],
        }
    
    return result


def get_teams_needing_drtg_update(
    conn: sqlite3.Connection,
    max_age_days: int = 14,
) -> list[dict]:
    """
    Get list of teams that need DRTG data updates.
    
    Returns teams with stale or missing DRTG data, prioritized by:
    1. Teams with no DRTG data at all
    2. Teams with oldest data
    3. Teams with upcoming games
    """
    from datetime import datetime, timedelta
    
    # Get all 30 NBA teams
    all_teams = [
        "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN",
        "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA",
        "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX",
        "POR", "SAC", "SAS", "TOR", "UTA", "WAS"
    ]
    
    # Get current DRTG data status
    drtg_status = get_drtg_data_freshness(conn)
    
    cutoff_date = (datetime.now() - timedelta(days=max_age_days)).strftime("%Y-%m-%d %H:%M:%S")
    
    needs_update = []
    
    for team in all_teams:
        status = drtg_status.get(team)
        
        if not status or not status.get("last_updated"):
            # No data at all - highest priority
            needs_update.append({
                "team": team,
                "priority": "HIGH",
                "reason": "No DRTG data available",
                "last_updated": None,
                "records_count": 0,
            })
        elif status["last_updated"] < cutoff_date:
            # Stale data
            needs_update.append({
                "team": team,
                "priority": "MEDIUM",
                "reason": f"Data is over {max_age_days} days old",
                "last_updated": status["last_updated"],
                "records_count": status["records_count"],
            })
    
    # Sort by priority (HIGH first), then by last_updated (oldest first)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    needs_update.sort(key=lambda x: (
        priority_order.get(x["priority"], 3),
        x["last_updated"] or "0000-00-00"
    ))
    
    return needs_update

"""
Defense vs Position Parser
==========================

Parses raw data from Hashtag Basketball's NBA Defense vs Position page.
Each position (PG, SG, SF, PF, C) has its own data set showing how each team
defends against that position.

Data format (per line):
Position  Team  OverallRank  PTS  PTS_Rank  FG%  FG%_Rank  FT%  FT%_Rank  3PM  3PM_Rank  REB  REB_Rank  AST  AST_Rank  STL  STL_Rank  BLK  BLK_Rank  TO  TO_Rank

Example:
PG	OKC   2	21.7   35	40.6   1	72.4   23	3.3   130	6.2   24	7.1   121	1.7   77	0.4   6	4.1   38

Interpretation:
- Lower overall rank = BETTER defense at that position
- Stats shown are what teams ALLOW to that position
- For betting: Target players against teams with WORSE defense (higher rank)
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..team_aliases import normalize_team_abbrev


# Mapping from standard NBA abbreviations to Hashtag Basketball abbreviations
# (used when the defense data was imported from Hashtag Basketball)
_STANDARD_TO_HASHTAG_ABBREV: dict[str, str] = {
    "GSW": "GS",    # Golden State Warriors
    "NYK": "NY",    # New York Knicks  
    "PHX": "PHO",   # Phoenix Suns
    "SAS": "SA",    # San Antonio Spurs
    "NOP": "NO",    # New Orleans Pelicans
    "CHO": "CHA",   # Charlotte Hornets (some systems use CHO)
}

def _normalize_abbrev_for_defense_lookup(abbrev: str) -> str:
    """
    Normalize team abbreviation for defense vs position lookup.
    Converts standard NBA abbreviations to Hashtag Basketball format.
    """
    abbrev = normalize_team_abbrev(abbrev).upper()
    return _STANDARD_TO_HASHTAG_ABBREV.get(abbrev, abbrev)


@dataclass
class DefenseVsPositionRow:
    """A single row of defense vs position data."""
    position: str  # PG, SG, SF, PF, C
    team_abbrev: str
    overall_rank: int  # 1-150 (cross-position rank)
    
    # Stats allowed to this position (per 48 min)
    pts_allowed: float
    pts_rank: int
    
    fg_pct_allowed: float
    fg_pct_rank: int
    
    ft_pct_allowed: float
    ft_pct_rank: int
    
    tpm_allowed: float  # 3-pointers made
    tpm_rank: int
    
    reb_allowed: float
    reb_rank: int
    
    ast_allowed: float
    ast_rank: int
    
    stl_allowed: float
    stl_rank: int
    
    blk_allowed: float
    blk_rank: int
    
    to_allowed: float  # Turnovers forced
    to_rank: int


@dataclass
class DefenseVsPositionParseResult:
    """Result of parsing defense vs position data."""
    position: str
    rows: list[DefenseVsPositionRow]
    last_updated: Optional[str]  # Date from "Last updated:" line
    source: str = "hashtag_basketball"
    errors: list[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def _parse_float(value: str) -> float:
    """Parse a float value, stripping percentage signs."""
    return float(value.rstrip('%'))


def _parse_row(line: str) -> Optional[DefenseVsPositionRow]:
    """
    Parse a single line of defense vs position data.
    
    Format: Position  Team  Rank  PTS  PTS_Rank  FG%  FG%_Rank  FT%  FT%_Rank  3PM  3PM_Rank  REB  REB_Rank  AST  AST_Rank  STL  STL_Rank  BLK  BLK_Rank  TO  TO_Rank
    
    Example: PG	OKC   2	21.7   35	40.6   1	72.4   23	3.3   130	6.2   24	7.1   121	1.7   77	0.4   6	4.1   38
    """
    # Skip non-data lines
    if not line.strip():
        return None
    
    # Valid positions
    valid_positions = {"PG", "SG", "SF", "PF", "C"}
    
    # Split on whitespace
    parts = line.split()
    
    # Must start with a position
    if not parts or parts[0] not in valid_positions:
        return None
    
    # Need at least: Position + Team + Rank + 9 stat pairs (value + rank) = 3 + 18 = 21 values
    # But team name and first rank are often merged like "OKC   2" which splits to "OKC" "2"
    if len(parts) < 20:
        return None
    
    try:
        position = parts[0]
        team_raw = parts[1]
        
        # Normalize team abbreviation
        team_abbrev = normalize_team_abbrev(team_raw)
        if not team_abbrev:
            # Try common mappings
            team_map = {
                "NO": "NOP", "PHO": "PHX", "GS": "GSW", "SA": "SAS", 
                "NY": "NYK", "BKN": "BKN", "WSH": "WAS"
            }
            team_abbrev = team_map.get(team_raw, team_raw)
        
        # Index 2 should be overall rank
        overall_rank = int(parts[2])
        
        # Parse stats (each stat has value followed by rank)
        # Index 3: PTS, Index 4: PTS_rank
        # Index 5: FG%, Index 6: FG%_rank
        # etc.
        idx = 3
        
        pts_allowed = _parse_float(parts[idx])
        pts_rank = int(parts[idx + 1])
        
        fg_pct_allowed = _parse_float(parts[idx + 2])
        fg_pct_rank = int(parts[idx + 3])
        
        ft_pct_allowed = _parse_float(parts[idx + 4])
        ft_pct_rank = int(parts[idx + 5])
        
        tpm_allowed = _parse_float(parts[idx + 6])
        tpm_rank = int(parts[idx + 7])
        
        reb_allowed = _parse_float(parts[idx + 8])
        reb_rank = int(parts[idx + 9])
        
        ast_allowed = _parse_float(parts[idx + 10])
        ast_rank = int(parts[idx + 11])
        
        stl_allowed = _parse_float(parts[idx + 12])
        stl_rank = int(parts[idx + 13])
        
        blk_allowed = _parse_float(parts[idx + 14])
        blk_rank = int(parts[idx + 15])
        
        to_allowed = _parse_float(parts[idx + 16])
        to_rank = int(parts[idx + 17])
        
        return DefenseVsPositionRow(
            position=position,
            team_abbrev=team_abbrev,
            overall_rank=overall_rank,
            pts_allowed=pts_allowed,
            pts_rank=pts_rank,
            fg_pct_allowed=fg_pct_allowed,
            fg_pct_rank=fg_pct_rank,
            ft_pct_allowed=ft_pct_allowed,
            ft_pct_rank=ft_pct_rank,
            tpm_allowed=tpm_allowed,
            tpm_rank=tpm_rank,
            reb_allowed=reb_allowed,
            reb_rank=reb_rank,
            ast_allowed=ast_allowed,
            ast_rank=ast_rank,
            stl_allowed=stl_allowed,
            stl_rank=stl_rank,
            blk_allowed=blk_allowed,
            blk_rank=blk_rank,
            to_allowed=to_allowed,
            to_rank=to_rank,
        )
    except (ValueError, IndexError) as e:
        return None


def parse_defense_vs_position_text(
    text: str,
    expected_position: Optional[str] = None,
) -> DefenseVsPositionParseResult:
    """
    Parse defense vs position data from raw text.
    
    Args:
        text: Raw text from Hashtag Basketball defense vs position page
        expected_position: If provided, only parse rows for this position (PG, SG, SF, PF, C)
    
    Returns:
        DefenseVsPositionParseResult with parsed rows and metadata
    """
    rows = []
    errors = []
    last_updated = None
    detected_position = None
    
    lines = text.split("\n")
    
    for line in lines:
        line = line.strip()
        
        # Try to extract the "Last updated" date
        if "Last updated:" in line or "Last updated" in line.lower():
            # Extract date like "06 January 2026"
            date_match = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", line)
            if date_match:
                try:
                    date_str = date_match.group(1)
                    # Parse "06 January 2026" format
                    dt = datetime.strptime(date_str, "%d %B %Y")
                    last_updated = dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
        
        # Try to parse as data row
        row = _parse_row(line)
        if row:
            # Filter by expected position if specified
            if expected_position:
                if row.position == expected_position:
                    rows.append(row)
                    detected_position = expected_position
            else:
                rows.append(row)
                if not detected_position:
                    detected_position = row.position
    
    # Determine the primary position from the data
    if rows and not expected_position:
        # Count positions to find the most common one
        pos_counts = {}
        for row in rows:
            pos_counts[row.position] = pos_counts.get(row.position, 0) + 1
        
        if pos_counts:
            detected_position = max(pos_counts, key=pos_counts.get)
    
    result = DefenseVsPositionParseResult(
        position=detected_position or expected_position or "UNKNOWN",
        rows=rows,
        last_updated=last_updated,
        source="hashtag_basketball",
        errors=errors,
    )
    
    # Add warnings
    if not rows:
        errors.append("No valid data rows parsed from input")
    elif len(rows) < 30:
        errors.append(f"Only {len(rows)} rows parsed, expected ~30 (one per team)")
    
    return result


def save_defense_vs_position_to_db(
    conn: sqlite3.Connection,
    result: DefenseVsPositionParseResult,
) -> dict:
    """
    Save parsed defense vs position data to the database.
    
    Returns dict with status and counts.
    """
    if not result.rows:
        return {"status": "error", "message": "No data to save", "count": 0}
    
    position = result.position
    as_of_date = result.last_updated or datetime.now().strftime("%Y-%m-%d")
    
    inserted = 0
    updated = 0
    
    for row in result.rows:
        # Check if row exists
        existing = conn.execute(
            """
            SELECT id FROM team_defense_vs_position 
            WHERE team_abbrev = ? AND position = ? AND season = '2025-26'
            """,
            (row.team_abbrev, row.position),
        ).fetchone()
        
        if existing:
            # Update existing row
            conn.execute(
                """
                UPDATE team_defense_vs_position
                SET overall_rank = ?, as_of_date = ?,
                    pts_allowed = ?, pts_rank = ?,
                    fg_pct_allowed = ?, fg_pct_rank = ?,
                    ft_pct_allowed = ?, ft_pct_rank = ?,
                    tpm_allowed = ?, tpm_rank = ?,
                    reb_allowed = ?, reb_rank = ?,
                    ast_allowed = ?, ast_rank = ?,
                    stl_allowed = ?, stl_rank = ?,
                    blk_allowed = ?, blk_rank = ?,
                    to_allowed = ?, to_rank = ?,
                    source = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    row.overall_rank, as_of_date,
                    row.pts_allowed, row.pts_rank,
                    row.fg_pct_allowed, row.fg_pct_rank,
                    row.ft_pct_allowed, row.ft_pct_rank,
                    row.tpm_allowed, row.tpm_rank,
                    row.reb_allowed, row.reb_rank,
                    row.ast_allowed, row.ast_rank,
                    row.stl_allowed, row.stl_rank,
                    row.blk_allowed, row.blk_rank,
                    row.to_allowed, row.to_rank,
                    result.source,
                    existing["id"],
                ),
            )
            updated += 1
        else:
            # Insert new row
            conn.execute(
                """
                INSERT INTO team_defense_vs_position (
                    team_abbrev, position, season, overall_rank, as_of_date,
                    pts_allowed, pts_rank, fg_pct_allowed, fg_pct_rank,
                    ft_pct_allowed, ft_pct_rank, tpm_allowed, tpm_rank,
                    reb_allowed, reb_rank, ast_allowed, ast_rank,
                    stl_allowed, stl_rank, blk_allowed, blk_rank,
                    to_allowed, to_rank, source
                ) VALUES (?, ?, '2025-26', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.team_abbrev, row.position, row.overall_rank, as_of_date,
                    row.pts_allowed, row.pts_rank,
                    row.fg_pct_allowed, row.fg_pct_rank,
                    row.ft_pct_allowed, row.ft_pct_rank,
                    row.tpm_allowed, row.tpm_rank,
                    row.reb_allowed, row.reb_rank,
                    row.ast_allowed, row.ast_rank,
                    row.stl_allowed, row.stl_rank,
                    row.blk_allowed, row.blk_rank,
                    row.to_allowed, row.to_rank,
                    result.source,
                ),
            )
            inserted += 1
    
    conn.commit()
    
    # Update data freshness
    conn.execute(
        """
        INSERT OR REPLACE INTO data_freshness (data_type, last_updated, records_count, notes)
        VALUES (?, datetime('now'), ?, ?)
        """,
        (
            f"defense_vs_position_{position}",
            len(result.rows),
            f"Position: {position}, Source: {result.source}",
        ),
    )
    conn.commit()
    
    return {
        "status": "success",
        "position": position,
        "as_of_date": as_of_date,
        "inserted": inserted,
        "updated": updated,
        "total": len(result.rows),
    }


def get_defense_vs_position(
    conn: sqlite3.Connection,
    team_abbrev: str,
    position: str,
) -> Optional[DefenseVsPositionRow]:
    """
    Get defense vs position data for a specific team and position.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation (e.g., "LAL", "BOS") - any standard format
        position: Position (PG, SG, SF, PF, C)
    
    Returns:
        DefenseVsPositionRow if found, None otherwise
    """
    # Normalize the abbreviation for Hashtag Basketball format
    normalized_abbrev = _normalize_abbrev_for_defense_lookup(team_abbrev)
    
    row = conn.execute(
        """
        SELECT * FROM team_defense_vs_position
        WHERE team_abbrev = ? AND position = ? AND season = '2025-26'
        """,
        (normalized_abbrev, position),
    ).fetchone()
    
    if not row:
        return None
    
    return DefenseVsPositionRow(
        position=row["position"],
        team_abbrev=row["team_abbrev"],
        overall_rank=row["overall_rank"],
        pts_allowed=row["pts_allowed"],
        pts_rank=row["pts_rank"],
        fg_pct_allowed=row["fg_pct_allowed"],
        fg_pct_rank=row["fg_pct_rank"],
        ft_pct_allowed=row["ft_pct_allowed"],
        ft_pct_rank=row["ft_pct_rank"],
        tpm_allowed=row["tpm_allowed"],
        tpm_rank=row["tpm_rank"],
        reb_allowed=row["reb_allowed"],
        reb_rank=row["reb_rank"],
        ast_allowed=row["ast_allowed"],
        ast_rank=row["ast_rank"],
        stl_allowed=row["stl_allowed"],
        stl_rank=row["stl_rank"],
        blk_allowed=row["blk_allowed"],
        blk_rank=row["blk_rank"],
        to_allowed=row["to_allowed"],
        to_rank=row["to_rank"],
    )


def get_all_defense_vs_position_for_team(
    conn: sqlite3.Connection,
    team_abbrev: str,
) -> list[DefenseVsPositionRow]:
    """
    Get all defense vs position data for a team (all 5 positions).
    
    Returns:
        List of DefenseVsPositionRow, one for each position if available
    """
    rows = conn.execute(
        """
        SELECT * FROM team_defense_vs_position
        WHERE team_abbrev = ? AND season = '2025-26'
        ORDER BY position
        """,
        (team_abbrev,),
    ).fetchall()
    
    result = []
    for row in rows:
        result.append(DefenseVsPositionRow(
            position=row["position"],
            team_abbrev=row["team_abbrev"],
            overall_rank=row["overall_rank"],
            pts_allowed=row["pts_allowed"],
            pts_rank=row["pts_rank"],
            fg_pct_allowed=row["fg_pct_allowed"],
            fg_pct_rank=row["fg_pct_rank"],
            ft_pct_allowed=row["ft_pct_allowed"],
            ft_pct_rank=row["ft_pct_rank"],
            tpm_allowed=row["tpm_allowed"],
            tpm_rank=row["tpm_rank"],
            reb_allowed=row["reb_allowed"],
            reb_rank=row["reb_rank"],
            ast_allowed=row["ast_allowed"],
            ast_rank=row["ast_rank"],
            stl_allowed=row["stl_allowed"],
            stl_rank=row["stl_rank"],
            blk_allowed=row["blk_allowed"],
            blk_rank=row["blk_rank"],
            to_allowed=row["to_allowed"],
            to_rank=row["to_rank"],
        ))
    
    return result


def get_defense_vs_position_last_updated(conn: sqlite3.Connection) -> dict:
    """
    Get the last updated dates for each position's defense data.
    
    Returns:
        Dict mapping position to last_updated datetime and count
    """
    result = {}
    
    for position in ["PG", "SG", "SF", "PF", "C"]:
        row = conn.execute(
            """
            SELECT last_updated, records_count, notes 
            FROM data_freshness 
            WHERE data_type = ?
            """,
            (f"defense_vs_position_{position}",),
        ).fetchone()
        
        if row:
            result[position] = {
                "last_updated": row["last_updated"],
                "records_count": row["records_count"],
                "notes": row["notes"],
            }
        else:
            result[position] = None
    
    return result


def get_worst_defenses_at_position(
    conn: sqlite3.Connection,
    position: str,
    stat_type: str = "pts",
    limit: int = 10,
) -> list[dict]:
    """
    Get the worst defenses at a specific position for a stat type.
    Higher rank = worse defense = better target for overs.
    
    Args:
        conn: Database connection
        position: Position (PG, SG, SF, PF, C)
        stat_type: One of 'pts', 'reb', 'ast'
        limit: Number of teams to return
    
    Returns:
        List of dicts with team info and stat values
    """
    stat_col = f"{stat_type}_allowed"
    rank_col = f"{stat_type}_rank"
    
    rows = conn.execute(
        f"""
        SELECT team_abbrev, position, overall_rank,
               {stat_col}, {rank_col}, as_of_date
        FROM team_defense_vs_position
        WHERE position = ? AND season = '2025-26'
        ORDER BY {rank_col} DESC
        LIMIT ?
        """,
        (position, limit),
    ).fetchall()
    
    return [dict(row) for row in rows]


def get_best_defenses_at_position(
    conn: sqlite3.Connection,
    position: str,
    stat_type: str = "pts",
    limit: int = 10,
) -> list[dict]:
    """
    Get the best defenses at a specific position for a stat type.
    Lower rank = better defense = better target for unders.
    
    Args:
        conn: Database connection
        position: Position (PG, SG, SF, PF, C)
        stat_type: One of 'pts', 'reb', 'ast'
        limit: Number of teams to return
    
    Returns:
        List of dicts with team info and stat values
    """
    stat_col = f"{stat_type}_allowed"
    rank_col = f"{stat_type}_rank"
    
    rows = conn.execute(
        f"""
        SELECT team_abbrev, position, overall_rank,
               {stat_col}, {rank_col}, as_of_date
        FROM team_defense_vs_position
        WHERE position = ? AND season = '2025-26'
        ORDER BY {rank_col} ASC
        LIMIT ?
        """,
        (position, limit),
    ).fetchall()
    
    return [dict(row) for row in rows]


def calculate_defense_factor(
    conn: sqlite3.Connection,
    opponent_abbrev: str,
    player_position: str,
    stat_type: str = "pts",
) -> Optional[dict]:
    """
    Calculate how a team's defense affects a player at a given position.
    
    Returns:
        Dict with:
        - factor: Multiplier (>1.0 means player likely to exceed average, <1.0 means likely under)
        - rank: Team's rank at defending this position (1=best, 30=worst)
        - rating: "elite", "good", "average", "poor", "terrible"
        - allowed: Average stat allowed
    """
    defense = get_defense_vs_position(conn, opponent_abbrev, player_position)
    if not defense:
        return None
    
    # Get the relevant stat and rank
    if stat_type == "pts":
        allowed = defense.pts_allowed
        rank = defense.pts_rank
    elif stat_type == "reb":
        allowed = defense.reb_allowed
        rank = defense.reb_rank
    elif stat_type == "ast":
        allowed = defense.ast_allowed
        rank = defense.ast_rank
    else:
        return None
    
    # Calculate league average for this position/stat
    # We'll get all rows for this position and average
    all_rows = conn.execute(
        f"""
        SELECT AVG({stat_type}_allowed) as avg_allowed
        FROM team_defense_vs_position
        WHERE position = ? AND season = '2025-26'
        """,
        (player_position,),
    ).fetchone()
    
    if not all_rows or not all_rows["avg_allowed"]:
        return None
    
    league_avg = all_rows["avg_allowed"]
    
    # Factor: how much above/below league average this defense allows
    factor = allowed / league_avg if league_avg > 0 else 1.0
    
    # Rating based on rank (out of 30 teams, but ranks go 1-150 cross-position)
    # For position-specific, re-rank 1-30
    position_rows = conn.execute(
        """
        SELECT team_abbrev FROM team_defense_vs_position
        WHERE position = ? AND season = '2025-26'
        ORDER BY overall_rank ASC
        """,
        (player_position,),
    ).fetchall()
    
    position_rank = 15  # default
    for i, row in enumerate(position_rows):
        if row["team_abbrev"] == opponent_abbrev:
            position_rank = i + 1
            break
    
    # Rating
    if position_rank <= 5:
        rating = "elite"
    elif position_rank <= 10:
        rating = "good"
    elif position_rank <= 20:
        rating = "average"
    elif position_rank <= 25:
        rating = "poor"
    else:
        rating = "terrible"
    
    return {
        "factor": round(factor, 3),
        "rank": position_rank,
        "rank_total": len(position_rows),
        "rating": rating,
        "allowed": allowed,
        "league_avg": round(league_avg, 1),
        "stat_type": stat_type,
        "position": player_position,
    }

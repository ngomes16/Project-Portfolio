"""
Database-backed player archetype system.

This module provides functions to manage player archetypes stored in the database,
with fallback to hard-coded defaults. The database takes precedence, allowing
manual overrides and updates without code changes.

Usage:
    # Get archetype (DB first, then fallback to defaults)
    archetype = get_player_archetype_db(conn, "LeBron James")
    
    # Seed database from defaults (run once or to refresh)
    seed_archetypes_from_defaults(conn)
    
    # Update a player's archetype
    update_player_archetype(conn, "LeBron James", team="Los Angeles Lakers", tier=2)
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

# Import default archetypes for fallback/seeding
from .roster import (
    PLAYER_DATABASE,
    PLAYER_SIMILARITY_GROUPS,
    ELITE_DEFENDERS_BY_POSITION,
    PlayerProfile,
    OffensiveRole,
    DefensiveRole,
    PlayerTier,
)


# Bet status constants
BET_STATUS_AVOID = 0   # Don't bet on this player
BET_STATUS_NEUTRAL = 1  # Okay to bet, but not prioritized
BET_STATUS_STAR = 2     # Star player - prioritize for picks


def _has_is_star_column(conn: sqlite3.Connection) -> bool:
    """Check if the is_star column exists in player_archetypes table."""
    try:
        columns = conn.execute("PRAGMA table_info(player_archetypes)").fetchall()
        column_names = [col[1] if isinstance(col, tuple) else col["name"] for col in columns]
        return "is_star" in column_names
    except Exception:
        return False


def _has_bet_status_column(conn: sqlite3.Connection) -> bool:
    """Check if the bet_status column exists in player_archetypes table."""
    try:
        columns = conn.execute("PRAGMA table_info(player_archetypes)").fetchall()
        column_names = [col[1] if isinstance(col, tuple) else col["name"] for col in columns]
        return "bet_status" in column_names
    except Exception:
        return False


@dataclass
class PlayerArchetypeDB:
    """Player archetype data from the database."""
    player_name: str
    team: Optional[str]
    season: str
    
    # Position info
    position: Optional[str]
    height: Optional[str]
    
    # Archetypes
    primary_offensive: str
    secondary_offensive: Optional[str]
    defensive_role: str
    
    # Tier
    tier: int
    
    # Metadata
    is_elite_defender: bool
    is_star: bool = False  # Legacy: Star player to target for picks
    bet_status: int = 1  # 0=avoid, 1=neutral, 2=star
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    notes: Optional[str] = None
    guards_positions: list[str] = field(default_factory=list)
    avoid_betting_against: list[str] = field(default_factory=list)
    
    # Source tracking
    source: str = "manual"
    confidence: float = 1.0
    
    # DB ID
    id: Optional[int] = None
    player_id: Optional[int] = None


def get_player_archetype_db(
    conn: sqlite3.Connection,
    player_name: str,
    season: str = "2025-26",
) -> Optional[PlayerArchetypeDB]:
    """
    Get player archetype from database, with fallback to hard-coded defaults.
    
    Priority:
    1. Check database for this player
    2. Fall back to PLAYER_DATABASE defaults
    3. Return None if not found
    """
    # Check if columns exist
    has_is_star = _has_is_star_column(conn)
    has_bet_status = _has_bet_status_column(conn)
    
    # Build query based on available columns
    select_cols = """id, player_id, player_name, team, season, position, height,
                   primary_offensive, secondary_offensive, defensive_role,
                   tier, is_elite_defender, strengths, weaknesses, notes,
                   guards_positions, avoid_betting_against, source, confidence"""
    
    if has_is_star:
        select_cols += ", is_star"
    if has_bet_status:
        select_cols += ", bet_status"
    
    sql = f"""
        SELECT {select_cols}
        FROM player_archetypes
        WHERE player_name = ? AND season = ?
    """
    
    row = conn.execute(sql, (player_name, season)).fetchone()
    
    if row:
        # Get bet_status and is_star values
        if has_bet_status:
            bet_status = row["bet_status"] if row["bet_status"] is not None else BET_STATUS_NEUTRAL
        elif has_is_star:
            # Migrate from is_star to bet_status
            bet_status = BET_STATUS_STAR if row["is_star"] else BET_STATUS_NEUTRAL
        else:
            # Default based on tier
            bet_status = BET_STATUS_STAR if (row["tier"] and row["tier"] <= 3) else BET_STATUS_NEUTRAL
        
        is_star = bet_status == BET_STATUS_STAR
        
        return PlayerArchetypeDB(
            id=row["id"],
            player_id=row["player_id"],
            player_name=row["player_name"],
            team=row["team"],
            season=row["season"],
            position=row["position"],
            height=row["height"],
            primary_offensive=row["primary_offensive"],
            secondary_offensive=row["secondary_offensive"],
            defensive_role=row["defensive_role"],
            tier=row["tier"],
            is_elite_defender=bool(row["is_elite_defender"]),
            is_star=is_star,
            bet_status=bet_status,
            strengths=json.loads(row["strengths"]) if row["strengths"] else [],
            weaknesses=json.loads(row["weaknesses"]) if row["weaknesses"] else [],
            notes=row["notes"],
            guards_positions=json.loads(row["guards_positions"]) if row["guards_positions"] else [],
            avoid_betting_against=json.loads(row["avoid_betting_against"]) if row["avoid_betting_against"] else [],
            source=row["source"],
            confidence=row["confidence"],
        )
    
    # Fall back to hard-coded defaults
    if player_name in PLAYER_DATABASE:
        profile = PLAYER_DATABASE[player_name]
        # Default to star status for tier 1-3 players
        default_bet_status = BET_STATUS_STAR if profile.tier.value <= 3 else BET_STATUS_NEUTRAL
        return PlayerArchetypeDB(
            player_name=profile.name,
            team=profile.team,
            season=season,
            position=profile.position,
            height=profile.height,
            primary_offensive=profile.primary_offensive.value,
            secondary_offensive=profile.secondary_offensive.value if profile.secondary_offensive else None,
            defensive_role=profile.defensive_role.value,
            tier=profile.tier.value,
            is_elite_defender=profile.is_elite_defender,
            is_star=default_bet_status == BET_STATUS_STAR,
            bet_status=default_bet_status,
            strengths=profile.strengths,
            weaknesses=profile.weaknesses,
            notes=profile.notes,
            guards_positions=profile.guards_positions,
            avoid_betting_against=profile.avoid_betting_against,
            source="default",
            confidence=1.0,
        )
    
    return None


def get_all_archetypes_db(
    conn: sqlite3.Connection,
    season: str = "2025-26",
    tier: Optional[int] = None,
    team: Optional[str] = None,
    elite_defenders_only: bool = False,
    stars_only: bool = False,
) -> list[PlayerArchetypeDB]:
    """Get all player archetypes from database with optional filters."""
    # Check if columns exist
    has_is_star = _has_is_star_column(conn)
    has_bet_status = _has_bet_status_column(conn)
    
    # Build query based on available columns
    select_cols = """id, player_id, player_name, team, season, position, height,
                   primary_offensive, secondary_offensive, defensive_role,
                   tier, is_elite_defender, strengths, weaknesses, notes,
                   guards_positions, avoid_betting_against, source, confidence"""
    
    if has_is_star:
        select_cols += ", is_star"
    if has_bet_status:
        select_cols += ", bet_status"
    
    sql = f"""
        SELECT {select_cols}
        FROM player_archetypes
        WHERE season = ?
    """
    params: list = [season]
    
    if tier is not None:
        sql += " AND tier = ?"
        params.append(tier)
    
    if team:
        sql += " AND team = ?"
        params.append(team)
    
    if elite_defenders_only:
        sql += " AND is_elite_defender = 1"
    
    if stars_only:
        if has_bet_status:
            sql += " AND bet_status = 2"  # BET_STATUS_STAR
        elif has_is_star:
            sql += " AND is_star = 1"
        else:
            # Fallback: tier 1-3 are stars
            sql += " AND tier <= 3"
    
    sql += " ORDER BY tier, player_name"
    
    rows = conn.execute(sql, params).fetchall()
    
    results = []
    for row in rows:
        # Determine bet_status and is_star
        if has_bet_status:
            bet_status = row["bet_status"] if row["bet_status"] is not None else BET_STATUS_NEUTRAL
        elif has_is_star:
            bet_status = BET_STATUS_STAR if row["is_star"] else BET_STATUS_NEUTRAL
        else:
            bet_status = BET_STATUS_STAR if (row["tier"] and row["tier"] <= 3) else BET_STATUS_NEUTRAL
        
        is_star = bet_status == BET_STATUS_STAR
        
        results.append(PlayerArchetypeDB(
            id=row["id"],
            player_id=row["player_id"],
            player_name=row["player_name"],
            team=row["team"],
            season=row["season"],
            position=row["position"],
            height=row["height"],
            primary_offensive=row["primary_offensive"],
            secondary_offensive=row["secondary_offensive"],
            defensive_role=row["defensive_role"],
            tier=row["tier"],
            is_elite_defender=bool(row["is_elite_defender"]),
            is_star=is_star,
            bet_status=bet_status,
            strengths=json.loads(row["strengths"]) if row["strengths"] else [],
            weaknesses=json.loads(row["weaknesses"]) if row["weaknesses"] else [],
            notes=row["notes"],
            guards_positions=json.loads(row["guards_positions"]) if row["guards_positions"] else [],
            avoid_betting_against=json.loads(row["avoid_betting_against"]) if row["avoid_betting_against"] else [],
            source=row["source"],
            confidence=row["confidence"],
        ))
    
    return results


def update_player_archetype(
    conn: sqlite3.Connection,
    player_name: str,
    season: str = "2025-26",
    **kwargs,
) -> bool:
    """
    Update or create a player archetype in the database.
    
    Args:
        conn: Database connection
        player_name: Player's name
        season: Season string
        **kwargs: Fields to update (team, position, height, primary_offensive,
                  secondary_offensive, defensive_role, tier, is_elite_defender,
                  is_star, strengths, weaknesses, notes, guards_positions, avoid_betting_against)
    
    Returns:
        True if successful
    """
    # Check if is_star column exists
    has_is_star = _has_is_star_column(conn)
    
    # Remove is_star from kwargs if column doesn't exist
    if not has_is_star and "is_star" in kwargs:
        del kwargs["is_star"]
    
    # Check if entry exists
    existing = conn.execute(
        "SELECT id FROM player_archetypes WHERE player_name = ? AND season = ?",
        (player_name, season),
    ).fetchone()
    
    # Build update fields
    fields_to_update = {}
    json_fields = {"strengths", "weaknesses", "guards_positions", "avoid_betting_against"}
    
    for key, value in kwargs.items():
        if key in json_fields and isinstance(value, list):
            fields_to_update[key] = json.dumps(value)
        else:
            fields_to_update[key] = value
    
    # Mark source as manual since user is editing
    fields_to_update["source"] = "manual"
    fields_to_update["updated_at"] = "datetime('now')"
    
    if existing:
        # Update existing
        set_clause = ", ".join(f"{k} = ?" for k in fields_to_update.keys())
        values = list(fields_to_update.values()) + [player_name, season]
        conn.execute(
            f"UPDATE player_archetypes SET {set_clause} WHERE player_name = ? AND season = ?",
            values,
        )
    else:
        # Insert new - need required fields
        if "primary_offensive" not in kwargs or "defensive_role" not in kwargs:
            # Try to get from defaults
            default = get_player_archetype_db(conn, player_name, season)
            if default:
                kwargs.setdefault("primary_offensive", default.primary_offensive)
                kwargs.setdefault("defensive_role", default.defensive_role)
                kwargs.setdefault("tier", default.tier)
            else:
                kwargs.setdefault("primary_offensive", "Connector")
                kwargs.setdefault("defensive_role", "Chaser")
                kwargs.setdefault("tier", 6)
        
        # Rebuild fields_to_update with new defaults
        for key, value in kwargs.items():
            if key in json_fields and isinstance(value, list):
                fields_to_update[key] = json.dumps(value)
            else:
                fields_to_update[key] = value
        
        fields_to_update["player_name"] = player_name
        fields_to_update["season"] = season
        fields_to_update["source"] = "manual"
        
        columns = ", ".join(fields_to_update.keys())
        placeholders = ", ".join("?" for _ in fields_to_update)
        conn.execute(
            f"INSERT INTO player_archetypes ({columns}) VALUES ({placeholders})",
            list(fields_to_update.values()),
        )
    
    conn.commit()
    return True


def delete_player_archetype(
    conn: sqlite3.Connection,
    player_name: str,
    season: str = "2025-26",
) -> bool:
    """Delete a player archetype from the database."""
    conn.execute(
        "DELETE FROM player_archetypes WHERE player_name = ? AND season = ?",
        (player_name, season),
    )
    conn.commit()
    return True


def seed_archetypes_from_defaults(
    conn: sqlite3.Connection,
    season: str = "2025-26",
    overwrite: bool = False,
) -> int:
    """
    Seed the database with archetypes from the hard-coded PLAYER_DATABASE.
    
    Args:
        conn: Database connection
        season: Season to seed
        overwrite: If True, overwrite existing entries; if False, skip existing
    
    Returns:
        Number of players seeded
    """
    count = 0
    
    for name, profile in PLAYER_DATABASE.items():
        # Check if already exists
        existing = conn.execute(
            "SELECT id FROM player_archetypes WHERE player_name = ? AND season = ?",
            (name, season),
        ).fetchone()
        
        if existing and not overwrite:
            continue
        
        # Prepare data
        data = {
            "player_name": name,
            "team": profile.team,
            "season": season,
            "position": profile.position,
            "height": profile.height,
            "primary_offensive": profile.primary_offensive.value,
            "secondary_offensive": profile.secondary_offensive.value if profile.secondary_offensive else None,
            "defensive_role": profile.defensive_role.value,
            "tier": profile.tier.value,
            "is_elite_defender": 1 if profile.is_elite_defender else 0,
            "strengths": json.dumps(profile.strengths),
            "weaknesses": json.dumps(profile.weaknesses),
            "notes": profile.notes,
            "guards_positions": json.dumps(profile.guards_positions),
            "avoid_betting_against": json.dumps(profile.avoid_betting_against),
            "source": "seed",
            "confidence": 1.0,
        }
        
        if existing:
            # Update
            set_clause = ", ".join(f"{k} = ?" for k in data.keys() if k != "player_name" and k != "season")
            values = [v for k, v in data.items() if k != "player_name" and k != "season"]
            values.extend([name, season])
            conn.execute(
                f"UPDATE player_archetypes SET {set_clause}, updated_at = datetime('now') WHERE player_name = ? AND season = ?",
                values,
            )
        else:
            # Insert
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            conn.execute(
                f"INSERT INTO player_archetypes ({columns}) VALUES ({placeholders})",
                list(data.values()),
            )
        
        count += 1
    
    # Seed similarity groups
    for group_name, players in PLAYER_SIMILARITY_GROUPS.items():
        for player_name in players:
            conn.execute(
                """
                INSERT OR IGNORE INTO player_similarity_groups (group_name, player_name, season)
                VALUES (?, ?, ?)
                """,
                (group_name, player_name, season),
            )
    
    # Seed elite defenders
    for position, defenders in ELITE_DEFENDERS_BY_POSITION.items():
        for player_name in defenders:
            conn.execute(
                """
                INSERT OR IGNORE INTO elite_defenders (player_name, position, season)
                VALUES (?, ?, ?)
                """,
                (player_name, position, season),
            )
    
    conn.commit()
    return count


def get_similarity_groups_db(
    conn: sqlite3.Connection,
    season: str = "2025-26",
) -> dict[str, list[str]]:
    """Get all similarity groups from database, falling back to defaults."""
    rows = conn.execute(
        """
        SELECT group_name, player_name
        FROM player_similarity_groups
        WHERE season = ?
        ORDER BY group_name, player_name
        """,
        (season,),
    ).fetchall()
    
    if rows:
        groups: dict[str, list[str]] = {}
        for row in rows:
            if row["group_name"] not in groups:
                groups[row["group_name"]] = []
            groups[row["group_name"]].append(row["player_name"])
        return groups
    
    # Fall back to defaults
    return PLAYER_SIMILARITY_GROUPS


def get_elite_defenders_db(
    conn: sqlite3.Connection,
    season: str = "2025-26",
) -> dict[str, list[str]]:
    """Get elite defenders by position from database, falling back to defaults."""
    rows = conn.execute(
        """
        SELECT position, player_name
        FROM elite_defenders
        WHERE season = ?
        ORDER BY position, player_name
        """,
        (season,),
    ).fetchall()
    
    if rows:
        defenders: dict[str, list[str]] = {}
        for row in rows:
            if row["position"] not in defenders:
                defenders[row["position"]] = []
            defenders[row["position"]].append(row["player_name"])
        return defenders
    
    # Fall back to defaults
    return ELITE_DEFENDERS_BY_POSITION


def get_similar_players_db(
    conn: sqlite3.Connection,
    player_name: str,
    season: str = "2025-26",
) -> list[str]:
    """Get players similar to the given player."""
    groups = get_similarity_groups_db(conn, season)
    
    similar = []
    for group_name, players in groups.items():
        if player_name in players:
            similar.extend([p for p in players if p != player_name])
    
    return list(set(similar))


def should_avoid_betting_over_db(
    conn: sqlite3.Connection,
    player_name: str,
    opponent_team: str,
    season: str = "2025-26",
) -> tuple[bool, list[str]]:
    """
    Check if we should avoid betting OVER on a player based on opponent's defenders.
    
    Returns:
        (should_avoid, list of elite defenders on opponent)
    """
    # Get player's position
    archetype = get_player_archetype_db(conn, player_name, season)
    if not archetype:
        return False, []
    
    position = archetype.position
    avoid_list = archetype.avoid_betting_against or []
    
    # Get opponent's roster archetypes
    opponent_players = get_all_archetypes_db(conn, season=season, team=opponent_team)
    opponent_names = [p.player_name for p in opponent_players]
    
    # Also check elite defenders from DB
    elite_by_pos = get_elite_defenders_db(conn, season)
    
    defenders_to_worry = []
    
    # Check specific avoid list
    for defender in avoid_list:
        if defender in opponent_names:
            defenders_to_worry.append(defender)
    
    # Check position-based elite defenders
    if position and position.upper() in elite_by_pos:
        for defender in elite_by_pos[position.upper()]:
            if defender in opponent_names and defender not in defenders_to_worry:
                defenders_to_worry.append(defender)
    
    return len(defenders_to_worry) > 0, defenders_to_worry


def get_roster_for_team_db(
    conn: sqlite3.Connection,
    team_name: str,
    season: str = "2025-26",
) -> list[PlayerArchetypeDB]:
    """Get all players in database for a team."""
    return get_all_archetypes_db(conn, season=season, team=team_name)


def get_archetype_count_db(conn: sqlite3.Connection, season: str = "2025-26") -> int:
    """Get count of archetypes in database."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM player_archetypes WHERE season = ?",
        (season,),
    ).fetchone()
    return row["n"] if row else 0


def set_bet_status(
    conn: sqlite3.Connection,
    player_name: str,
    bet_status: int,
    team: Optional[str] = None,
    season: str = "2025-26",
) -> bool:
    """
    Set the bet status for a player.
    
    Args:
        conn: Database connection
        player_name: Player's name
        bet_status: 0=avoid, 1=neutral, 2=star
        team: Team name (important for new entries)
        season: Season string
    
    Returns:
        True if successful
    """
    # Also update is_star for backwards compatibility
    is_star = 1 if bet_status == BET_STATUS_STAR else 0
    kwargs = {"bet_status": bet_status, "is_star": is_star}
    if team:
        kwargs["team"] = team
    return update_player_archetype(conn, player_name, season, **kwargs)


def toggle_star_status(
    conn: sqlite3.Connection,
    player_name: str,
    is_star: bool,
    season: str = "2025-26",
) -> bool:
    """
    Toggle the star status for a player (legacy function).
    
    Args:
        conn: Database connection
        player_name: Player's name
        is_star: Whether the player should be marked as a star
        season: Season string
    
    Returns:
        True if successful
    """
    bet_status = BET_STATUS_STAR if is_star else BET_STATUS_NEUTRAL
    return update_player_archetype(conn, player_name, season, is_star=1 if is_star else 0, bet_status=bet_status)


def get_star_players_for_team(
    conn: sqlite3.Connection,
    team_name: str,
    season: str = "2025-26",
) -> list[PlayerArchetypeDB]:
    """Get all star players for a team."""
    return get_all_archetypes_db(conn, season=season, team=team_name, stars_only=True)


def get_all_star_players(
    conn: sqlite3.Connection,
    season: str = "2025-26",
) -> list[PlayerArchetypeDB]:
    """Get all star players across all teams."""
    return get_all_archetypes_db(conn, season=season, stars_only=True)


def is_star_player(
    conn: sqlite3.Connection,
    player_name: str,
    season: str = "2025-26",
) -> bool:
    """
    Check if a player is marked as a star.
    
    Falls back to tier-based determination if player not in database.
    """
    archetype = get_player_archetype_db(conn, player_name, season)
    if archetype:
        return archetype.is_star
    return False


def get_bet_status(
    conn: sqlite3.Connection,
    player_name: str,
    season: str = "2025-26",
) -> int:
    """
    Get the bet status for a player.
    
    Returns:
        0=avoid, 1=neutral, 2=star
    """
    archetype = get_player_archetype_db(conn, player_name, season)
    if archetype:
        return archetype.bet_status
    return BET_STATUS_NEUTRAL

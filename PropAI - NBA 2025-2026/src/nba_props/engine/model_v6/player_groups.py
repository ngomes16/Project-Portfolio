"""
Player Groups - Classification System
======================================

Sophisticated player grouping system based on:
1. Player Tier (MVP, Star, Role, Specialist, etc.)
2. Offensive Archetype (Heliocentric, Slasher, Hub Big, etc.)
3. Defensive Role (POA Defender, Rim Protector, etc.)
4. Playing Style Clusters
5. Position Flexibility

These groupings allow for more nuanced analysis and matchup-based projections.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Set


# ============================================================================
# PLAYER GROUP ENUMS
# ============================================================================

class PlayerTier(Enum):
    """Player tier classification for prop betting prioritization."""
    MVP_CANDIDATE = 1      # League's best, matchup-proof
    ALL_STAR = 2           # Two-way stars, elite players
    QUALITY_STARTER = 3    # Reliable starters, consistent
    ROLE_PLAYER = 4        # Rotation pieces, situational
    SPECIALIST = 5         # Specific skills, limited role
    BENCH = 6              # Deep bench, risky props
    
    @classmethod
    def from_value(cls, val: int) -> "PlayerTier":
        for t in cls:
            if t.value == val:
                return t
        return cls.ROLE_PLAYER


class OffensiveStyle(Enum):
    """Primary offensive style groupings."""
    BALL_DOMINANT = "ball_dominant"       # High usage, creates for self/others
    MOVEMENT_BASED = "movement_based"     # Off-ball screens, cuts
    POST_ORIENTED = "post_oriented"       # Back to basket, mid-range
    CATCH_SHOOT = "catch_shoot"           # Spot-up, corner specialist
    RIM_RUNNER = "rim_runner"             # Lobs, dunker spot
    FACILITATOR = "facilitator"           # Pass-first, high assists
    VERSATILE = "versatile"               # Multiple scoring methods


class DefenseStyle(Enum):
    """Primary defensive role groupings."""
    PERIMETER_STOPPER = "perimeter_stopper"   # Guards best ball handler
    WING_DEFENDER = "wing_defender"           # Guards wings
    RIM_PROTECTOR = "rim_protector"           # Shot blocking, paint presence
    SWITCHABLE = "switchable"                 # Can guard multiple positions
    HELP_DEFENDER = "help_defender"           # Roamer, free safety
    HIDDEN = "hidden"                         # Limited defensive value
    CHASED = "chased"                         # Actively targeted on D


# ============================================================================
# ARCHETYPE GROUPS - Clusters of Similar Players
# ============================================================================

ARCHETYPE_GROUPS: Dict[str, Dict] = {
    # =========================================================================
    # BALL-DOMINANT CREATORS
    # =========================================================================
    "heliocentric": {
        "name": "Heliocentric Creators",
        "description": "Ball-dominant playmakers who control the offense",
        "offensive_style": OffensiveStyle.BALL_DOMINANT,
        "typical_tiers": [1, 2],
        "archetype_matches": [
            "Heliocentric Creator", "Primary Initiator", "PnR Maestro"
        ],
        "characteristics": {
            "usage_pct_min": 28,
            "ast_pct_min": 30,
            "typical_pts_range": (22, 35),
            "typical_ast_range": (6, 12),
        },
        "example_players": [
            "Luka Doncic", "Trae Young", "Shai Gilgeous-Alexander",
            "Ja Morant", "Cade Cunningham", "Tyrese Haliburton"
        ],
        "matchup_notes": "Struggle vs elite POA defenders. Look for matchups vs poor perimeter D.",
    },
    
    "scoring_guards": {
        "name": "Scoring Guards",
        "description": "Score-first guards who can create their own shot",
        "offensive_style": OffensiveStyle.BALL_DOMINANT,
        "typical_tiers": [2, 3, 4],
        "archetype_matches": [
            "Scoring Guard", "Shot Creator", "Isolation Scorer"
        ],
        "characteristics": {
            "usage_pct_min": 24,
            "typical_pts_range": (18, 28),
            "typical_ast_range": (3, 6),
        },
        "example_players": [
            "Donovan Mitchell", "Devin Booker", "Jalen Brunson",
            "CJ McCollum", "Zach LaVine", "Anfernee Simons"
        ],
        "matchup_notes": "Mid-range maestros. Check for matchups vs undersized guards.",
    },
    
    # =========================================================================
    # ATHLETIC WINGS
    # =========================================================================
    "slashers": {
        "name": "Athletic Slashers",
        "description": "Rim attackers who live at the basket",
        "offensive_style": OffensiveStyle.BALL_DOMINANT,
        "typical_tiers": [2, 3, 4],
        "archetype_matches": ["Slasher", "Athletic Wing"],
        "characteristics": {
            "drives_per_game_min": 8,
            "paint_pts_pct_min": 40,
            "typical_pts_range": (16, 26),
        },
        "example_players": [
            "Anthony Edwards", "Jaylen Brown", "Zion Williamson",
            "Miles Bridges", "Jalen Green", "Jonathan Kuminga"
        ],
        "matchup_notes": "Key is rim protection. Target teams with weak interior D.",
    },
    
    "two_way_wings": {
        "name": "Two-Way Wings",
        "description": "Elite defenders who also contribute offensively",
        "offensive_style": OffensiveStyle.VERSATILE,
        "typical_tiers": [2, 3, 4],
        "archetype_matches": ["3-and-D Wing", "Wing Stopper"],
        "characteristics": {
            "defensive_rating_max": 108,
            "typical_pts_range": (12, 20),
            "typical_reb_range": (4, 7),
        },
        "example_players": [
            "OG Anunoby", "Mikal Bridges", "Herbert Jones",
            "Jaden McDaniels", "Alex Caruso", "Derrick White"
        ],
        "matchup_notes": "Consistent, low variance. Good for unders vs high-scoring teams.",
    },
    
    # =========================================================================
    # MOVEMENT SHOOTERS
    # =========================================================================
    "movement_shooters": {
        "name": "Movement Shooters",
        "description": "Players who generate looks through constant movement",
        "offensive_style": OffensiveStyle.MOVEMENT_BASED,
        "typical_tiers": [1, 3, 4, 5],
        "archetype_matches": ["Movement Shooter", "Spot Up Shooter"],
        "characteristics": {
            "three_pt_attempts_min": 5,
            "off_ball_screens_min": 3,
            "typical_pts_range": (12, 24),
        },
        "example_players": [
            "Stephen Curry", "Klay Thompson", "Desmond Bane",
            "Duncan Robinson", "Buddy Hield", "Kentavious Caldwell-Pope"
        ],
        "matchup_notes": "Struggle vs good chasers. Target teams with poor help D.",
    },
    
    "corner_specialists": {
        "name": "Corner Specialists",
        "description": "Spot-up shooters who park in the corner",
        "offensive_style": OffensiveStyle.CATCH_SHOOT,
        "typical_tiers": [4, 5, 6],
        "archetype_matches": ["Spot Up Shooter", "Connector"],
        "characteristics": {
            "corner_three_pct_min": 30,
            "typical_pts_range": (8, 16),
        },
        "example_players": [
            "P.J. Tucker", "Royce O'Neale", "Torrey Craig",
            "Caleb Martin", "Dorian Finney-Smith"
        ],
        "matchup_notes": "Low volume, high variance. Better for avoiding than targeting.",
    },
    
    # =========================================================================
    # FACILITATING BIGS
    # =========================================================================
    "hub_bigs": {
        "name": "Hub Bigs",
        "description": "Playmaking centers who run offense from the post",
        "offensive_style": OffensiveStyle.FACILITATOR,
        "typical_tiers": [1, 2, 3],
        "archetype_matches": ["Hub Big", "Interior Playmaker"],
        "characteristics": {
            "ast_pct_min": 20,
            "post_touches_min": 8,
            "typical_pts_range": (14, 26),
            "typical_ast_range": (5, 10),
            "typical_reb_range": (10, 14),
        },
        "example_players": [
            "Nikola Jokic", "Domantas Sabonis", "Alperen Sengun",
            "Nikola Vucevic", "Jonas Valanciunas", "Bam Adebayo"
        ],
        "matchup_notes": "Triple-double threats. Check for help D and switching.",
    },
    
    "traditional_bigs": {
        "name": "Traditional Bigs",
        "description": "Rim-running centers focused on dunks and boards",
        "offensive_style": OffensiveStyle.RIM_RUNNER,
        "typical_tiers": [3, 4, 5],
        "archetype_matches": ["Rim Runner", "Anchor Big"],
        "characteristics": {
            "dunk_pct_min": 30,
            "typical_pts_range": (10, 18),
            "typical_reb_range": (8, 12),
        },
        "example_players": [
            "Rudy Gobert", "Clint Capela", "Jarrett Allen",
            "Daniel Gafford", "Nic Claxton", "Mitchell Robinson"
        ],
        "matchup_notes": "Rebound props safer than points. Check for matchup vs other rim protectors.",
    },
    
    "stretch_bigs": {
        "name": "Stretch Bigs",
        "description": "Floor-spacing bigs who shoot from outside",
        "offensive_style": OffensiveStyle.CATCH_SHOOT,
        "typical_tiers": [2, 3, 4, 5],
        "archetype_matches": ["Stretch Big", "Floor Spacer"],
        "characteristics": {
            "three_pt_pct_min": 33,
            "typical_pts_range": (12, 22),
            "typical_reb_range": (6, 10),
        },
        "example_players": [
            "Lauri Markkanen", "Karl-Anthony Towns", "Brook Lopez",
            "Myles Turner", "Kristaps Porzingis", "Kelly Olynyk"
        ],
        "matchup_notes": "Points volatile based on shot-making. Rebounds more stable.",
    },
    
    # =========================================================================
    # UNICORNS / POSITIONLESS
    # =========================================================================
    "unicorns": {
        "name": "Unicorns",
        "description": "Unique players who defy traditional classifications",
        "offensive_style": OffensiveStyle.VERSATILE,
        "typical_tiers": [1, 2],
        "archetype_matches": ["Point Forward", "Versatile Big"],
        "characteristics": {
            "height_min": "6'9\"",
            "playmaking_rating_min": 80,
            "typical_pts_range": (18, 32),
        },
        "example_players": [
            "Giannis Antetokounmpo", "Victor Wembanyama", "Paolo Banchero",
            "LeBron James", "Scottie Barnes", "Chet Holmgren"
        ],
        "matchup_notes": "Matchup-proof. Consistent across all opponents.",
    },
}


@dataclass
class PlayerGroup:
    """Complete player grouping classification."""
    player_name: str
    player_id: Optional[int] = None
    team_abbrev: str = ""
    
    # Tier
    tier: PlayerTier = PlayerTier.ROLE_PLAYER
    tier_value: int = 4
    
    # Archetype group
    archetype_group: str = ""           # Key from ARCHETYPE_GROUPS
    primary_archetype: str = ""         # e.g., "Heliocentric Creator"
    secondary_archetype: str = ""
    defensive_role: str = ""
    
    # Styles
    offensive_style: OffensiveStyle = OffensiveStyle.VERSATILE
    defense_style: DefenseStyle = DefenseStyle.HIDDEN
    
    # Position info
    position: str = "G"
    position_for_defense: str = "PG"    # For defense vs position lookup
    is_positionally_versatile: bool = False
    
    # Flags
    is_star: bool = False
    is_elite_defender: bool = False
    is_matchup_proof: bool = False      # Tier 1-2, performs regardless of matchup
    
    # Additional context
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    matchup_notes: str = ""


def classify_player(
    player_name: str,
    position: str,
    tier: int,
    primary_archetype: str,
    secondary_archetype: Optional[str] = None,
    defensive_role: Optional[str] = None,
    is_elite_defender: bool = False,
    team_abbrev: str = "",
    player_id: Optional[int] = None,
) -> PlayerGroup:
    """
    Classify a player into the appropriate group.
    
    Args:
        player_name: Player's name
        position: Traditional position (PG, SG, SF, PF, C)
        tier: Tier value (1-6)
        primary_archetype: Primary offensive archetype
        secondary_archetype: Secondary archetype (optional)
        defensive_role: Defensive role
        is_elite_defender: Whether player is an elite defender
        team_abbrev: Team abbreviation
        player_id: Database player ID
    
    Returns:
        PlayerGroup with full classification
    """
    from .config import POSITION_MAPPING
    
    # Determine archetype group
    archetype_group = ""
    for group_key, group_data in ARCHETYPE_GROUPS.items():
        if primary_archetype in group_data.get("archetype_matches", []):
            archetype_group = group_key
            break
    
    # If no match, try secondary archetype
    if not archetype_group and secondary_archetype:
        for group_key, group_data in ARCHETYPE_GROUPS.items():
            if secondary_archetype in group_data.get("archetype_matches", []):
                archetype_group = group_key
                break
    
    # Default group based on position if still not found
    if not archetype_group:
        pos_upper = position.upper() if position else "G"
        if pos_upper in ("PG", "SG", "G"):
            archetype_group = "scoring_guards"
        elif pos_upper in ("SF", "F"):
            archetype_group = "two_way_wings"
        elif pos_upper in ("PF", "C"):
            archetype_group = "traditional_bigs"
    
    # Get group data
    group_data = ARCHETYPE_GROUPS.get(archetype_group, {})
    
    # Determine offensive style
    offensive_style = group_data.get("offensive_style", OffensiveStyle.VERSATILE)
    
    # Determine defensive style
    defense_style = DefenseStyle.HIDDEN
    if defensive_role:
        dr_lower = defensive_role.lower()
        if "poa" in dr_lower or "perimeter" in dr_lower:
            defense_style = DefenseStyle.PERIMETER_STOPPER
        elif "wing" in dr_lower and "stopper" in dr_lower:
            defense_style = DefenseStyle.WING_DEFENDER
        elif "anchor" in dr_lower or "rim" in dr_lower:
            defense_style = DefenseStyle.RIM_PROTECTOR
        elif "switch" in dr_lower:
            defense_style = DefenseStyle.SWITCHABLE
        elif "roam" in dr_lower or "help" in dr_lower:
            defense_style = DefenseStyle.HELP_DEFENDER
        elif "chased" in dr_lower or "target" in dr_lower:
            defense_style = DefenseStyle.CHASED
    
    # Position for defense lookup
    position_for_defense = POSITION_MAPPING.get(
        position.upper() if position else "G", 
        "PG"
    )
    
    # Check positional versatility
    is_versatile = False
    if position and "-" in position:
        is_versatile = True
    elif defensive_role and ("1-5" in defensive_role or "1-4" in defensive_role):
        is_versatile = True
    
    # Tier flags
    player_tier = PlayerTier.from_value(tier)
    is_star = tier <= 3
    is_matchup_proof = tier <= 2
    
    # Get strengths/weaknesses from group
    strengths = list(group_data.get("characteristics", {}).keys())
    weaknesses = []
    if tier >= 5:
        weaknesses.append("Limited role")
    
    return PlayerGroup(
        player_name=player_name,
        player_id=player_id,
        team_abbrev=team_abbrev,
        tier=player_tier,
        tier_value=tier,
        archetype_group=archetype_group,
        primary_archetype=primary_archetype,
        secondary_archetype=secondary_archetype or "",
        defensive_role=defensive_role or "",
        offensive_style=offensive_style,
        defense_style=defense_style,
        position=position or "G",
        position_for_defense=position_for_defense,
        is_positionally_versatile=is_versatile,
        is_star=is_star,
        is_elite_defender=is_elite_defender,
        is_matchup_proof=is_matchup_proof,
        strengths=strengths,
        weaknesses=weaknesses,
        matchup_notes=group_data.get("matchup_notes", ""),
    )


def get_player_group(
    conn: sqlite3.Connection,
    player_name: str,
    season: str = "2025-26",
) -> Optional[PlayerGroup]:
    """
    Get player group classification from database.
    
    First checks archetype database, then falls back to stats-based classification.
    """
    # Try to get from archetype DB
    try:
        from ..archetype_db import get_player_archetype_db
        
        archetype = get_player_archetype_db(conn, player_name, season)
        if archetype:
            return classify_player(
                player_name=player_name,
                position=archetype.position or "G",
                tier=archetype.tier,
                primary_archetype=archetype.primary_offensive,
                secondary_archetype=archetype.secondary_offensive,
                defensive_role=archetype.defensive_role,
                is_elite_defender=archetype.is_elite_defender,
                team_abbrev=archetype.team or "",
                player_id=archetype.player_id,
            )
    except Exception:
        pass
    
    # Fall back to stats-based classification
    return _classify_from_stats(conn, player_name, season)


def _classify_from_stats(
    conn: sqlite3.Connection,
    player_name: str,
    season: str = "2025-26",
) -> Optional[PlayerGroup]:
    """
    Classify player based on their stats if not in archetype DB.
    """
    # Get player's average stats
    row = conn.execute(
        """
        SELECT 
            p.id as player_id,
            p.name,
            AVG(b.pts) as avg_pts,
            AVG(b.reb) as avg_reb,
            AVG(b.ast) as avg_ast,
            AVG(b.minutes) as avg_min,
            b.pos,
            t.name as team_name
        FROM players p
        JOIN boxscore_player b ON p.id = b.player_id
        JOIN teams t ON t.id = b.team_id
        JOIN games g ON g.id = b.game_id
        WHERE p.name = ?
          AND g.season = ?
          AND b.minutes > 10
        GROUP BY p.id
        """,
        (player_name, season),
    ).fetchone()
    
    if not row:
        return None
    
    # Determine tier based on stats
    avg_pts = row["avg_pts"] or 0
    avg_min = row["avg_min"] or 0
    avg_ast = row["avg_ast"] or 0
    
    if avg_pts >= 25 and avg_min >= 32:
        tier = 1
    elif avg_pts >= 20 and avg_min >= 30:
        tier = 2
    elif avg_pts >= 15 and avg_min >= 25:
        tier = 3
    elif avg_pts >= 10 and avg_min >= 20:
        tier = 4
    elif avg_min >= 15:
        tier = 5
    else:
        tier = 6
    
    # Determine archetype based on stats
    pos = row["pos"] or "G"
    
    if avg_ast >= 6:
        primary_arch = "PnR Maestro" if pos in ("PG", "G") else "Hub Big"
    elif avg_pts >= 20:
        primary_arch = "Scoring Guard" if pos in ("PG", "SG", "G") else "Slasher"
    elif pos in ("C", "PF"):
        primary_arch = "Rim Runner"
    else:
        primary_arch = "3-and-D Wing"
    
    from ...team_aliases import abbrev_from_team_name
    team_abbrev = abbrev_from_team_name(row["team_name"]) or ""
    
    return classify_player(
        player_name=player_name,
        position=pos,
        tier=tier,
        primary_archetype=primary_arch,
        team_abbrev=team_abbrev,
        player_id=row["player_id"],
    )


def get_players_in_group(
    conn: sqlite3.Connection,
    group_key: str,
    season: str = "2025-26",
) -> List[PlayerGroup]:
    """
    Get all players belonging to a specific archetype group.
    """
    results = []
    
    # Get group info
    group_data = ARCHETYPE_GROUPS.get(group_key)
    if not group_data:
        return results
    
    archetype_matches = group_data.get("archetype_matches", [])
    if not archetype_matches:
        return results
    
    # Query archetypes matching this group
    placeholders = ",".join(["?"] * len(archetype_matches))
    
    rows = conn.execute(
        f"""
        SELECT player_name, player_id, team, position, tier,
               primary_offensive, secondary_offensive, defensive_role,
               is_elite_defender
        FROM player_archetypes
        WHERE season = ?
          AND primary_offensive IN ({placeholders})
        ORDER BY tier, player_name
        """,
        (season, *archetype_matches),
    ).fetchall()
    
    for row in rows:
        pg = classify_player(
            player_name=row["player_name"],
            position=row["position"] or "G",
            tier=row["tier"] or 4,
            primary_archetype=row["primary_offensive"],
            secondary_archetype=row["secondary_offensive"],
            defensive_role=row["defensive_role"],
            is_elite_defender=bool(row["is_elite_defender"]),
            team_abbrev=row["team"] or "",
            player_id=row["player_id"],
        )
        results.append(pg)
    
    return results


def get_group_summary(group_key: str) -> Optional[Dict]:
    """Get summary information about an archetype group."""
    group = ARCHETYPE_GROUPS.get(group_key)
    if not group:
        return None
    
    return {
        "key": group_key,
        "name": group.get("name", group_key),
        "description": group.get("description", ""),
        "offensive_style": group.get("offensive_style", OffensiveStyle.VERSATILE).value,
        "typical_tiers": group.get("typical_tiers", []),
        "example_players": group.get("example_players", []),
        "matchup_notes": group.get("matchup_notes", ""),
        "characteristics": group.get("characteristics", {}),
    }

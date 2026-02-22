"""
Defense Analysis Module
=======================

Comprehensive defense analysis for matchup-based projections.
Integrates team defense vs position data with individual player archetypes.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

from .config import (
    ModelV6Config, 
    DEFAULT_CONFIG,
    ARCHETYPE_DEFENSE_MATRIX,
    POSITION_MAPPING,
)
from .player_groups import PlayerGroup


@dataclass
class DefenseMatchup:
    """Complete defense matchup analysis for a player vs opponent."""
    player_name: str
    opponent_abbrev: str
    position: str
    
    # Defense vs Position Analysis
    defense_rating: str              # "elite", "good", "average", "poor", "terrible"
    defense_rank: int                # 1-30 (1 = best defense)
    position_factor: float           # <1.0 = strong D, >1.0 = weak D
    
    # Stat-specific factors
    pts_factor: float
    pts_rank: int
    reb_factor: float
    reb_rank: int
    ast_factor: float
    ast_rank: int
    
    # Archetype-based adjustments
    archetype_adjustment: float      # Additional adj based on archetype vs defense
    archetype_reason: str            # Explanation
    
    # Combined adjustment
    total_pts_adjustment: float      # Final multiplier for PTS
    total_reb_adjustment: float      # Final multiplier for REB
    total_ast_adjustment: float      # Final multiplier for AST
    
    # Confidence impact
    matchup_confidence_boost: int    # 0-20 points for confidence score
    
    # Context
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def get_defense_matchup(
    conn: sqlite3.Connection,
    player_group: PlayerGroup,
    opponent_abbrev: str,
    config: ModelV6Config = DEFAULT_CONFIG,
) -> DefenseMatchup:
    """
    Get comprehensive defense matchup analysis for a player vs opponent.
    
    Args:
        conn: Database connection
        player_group: Player's group classification
        opponent_abbrev: Opponent team abbreviation
        config: Model configuration
    
    Returns:
        DefenseMatchup with all adjustment factors
    """
    notes = []
    warnings = []
    
    # Get position for defense lookup
    position = player_group.position_for_defense
    
    # Default values
    default_matchup = DefenseMatchup(
        player_name=player_group.player_name,
        opponent_abbrev=opponent_abbrev,
        position=position,
        defense_rating="average",
        defense_rank=15,
        position_factor=1.0,
        pts_factor=1.0, pts_rank=15,
        reb_factor=1.0, reb_rank=15,
        ast_factor=1.0, ast_rank=15,
        archetype_adjustment=0.0,
        archetype_reason="",
        total_pts_adjustment=1.0,
        total_reb_adjustment=1.0,
        total_ast_adjustment=1.0,
        matchup_confidence_boost=0,
        notes=notes,
        warnings=warnings,
    )
    
    # Try to get defense vs position data
    try:
        from ...ingest.defense_position_parser import (
            get_defense_vs_position,
            calculate_defense_factor,
        )
        
        # Get factors for each stat type
        pts_data = calculate_defense_factor(conn, opponent_abbrev, position, "pts")
        reb_data = calculate_defense_factor(conn, opponent_abbrev, position, "reb")
        ast_data = calculate_defense_factor(conn, opponent_abbrev, position, "ast")
        
        if not pts_data:
            warnings.append(f"No defense data for {opponent_abbrev} vs {position}")
            return default_matchup
        
        # Extract data
        pts_factor = pts_data.get("factor", 1.0)
        pts_rank = pts_data.get("rank", 15)
        reb_factor = reb_data.get("factor", 1.0) if reb_data else 1.0
        reb_rank = reb_data.get("rank", 15) if reb_data else 15
        ast_factor = ast_data.get("factor", 1.0) if ast_data else 1.0
        ast_rank = ast_data.get("rank", 15) if ast_data else 15
        
        # Overall position defense rating
        overall_rating = pts_data.get("rating", "average")
        overall_rank = pts_rank  # Use PTS rank as primary
        
        # Add notes based on ratings
        if overall_rating == "elite":
            notes.append(f"{opponent_abbrev} has ELITE defense vs {position}")
        elif overall_rating == "terrible":
            notes.append(f"{opponent_abbrev} has TERRIBLE defense vs {position}")
        
    except Exception as e:
        warnings.append(f"Could not get defense data: {str(e)}")
        pts_factor = reb_factor = ast_factor = 1.0
        pts_rank = reb_rank = ast_rank = 15
        overall_rating = "average"
        overall_rank = 15
    
    # Calculate archetype-based adjustment
    archetype_adj, arch_reason = _calculate_archetype_adjustment(
        player_group, opponent_abbrev, conn
    )
    
    if archetype_adj != 0:
        notes.append(arch_reason)
    
    # Apply star player dampening for Tier 1-2
    if player_group.is_matchup_proof:
        pts_factor = 1.0 + (pts_factor - 1.0) * config.star_player_defense_dampening
        reb_factor = 1.0 + (reb_factor - 1.0) * config.star_player_defense_dampening
        ast_factor = 1.0 + (ast_factor - 1.0) * config.star_player_defense_dampening
        archetype_adj *= config.star_player_defense_dampening
        notes.append("Star player: reduced defense impact")
    
    # Calculate total adjustments
    # Defense factor converts to adjustment (factor 1.1 = +10% projection)
    pts_def_adj = config.get_defense_adjustment(overall_rating)
    reb_def_adj = config.get_defense_adjustment(
        _rank_to_rating(reb_rank)
    )
    ast_def_adj = config.get_defense_adjustment(
        _rank_to_rating(ast_rank)
    )
    
    total_pts_adj = 1.0 + pts_def_adj + archetype_adj
    total_reb_adj = 1.0 + reb_def_adj + (archetype_adj * 0.5)  # Less impact on rebounds
    total_ast_adj = 1.0 + ast_def_adj + (archetype_adj * 0.7)  # Moderate impact on assists
    
    # Cap adjustments to reasonable range
    total_pts_adj = max(0.85, min(1.15, total_pts_adj))
    total_reb_adj = max(0.90, min(1.10, total_reb_adj))
    total_ast_adj = max(0.85, min(1.15, total_ast_adj))
    
    # Calculate confidence boost
    matchup_boost = _calculate_matchup_confidence(
        overall_rating, player_group, config
    )
    
    return DefenseMatchup(
        player_name=player_group.player_name,
        opponent_abbrev=opponent_abbrev,
        position=position,
        defense_rating=overall_rating,
        defense_rank=overall_rank,
        position_factor=pts_factor,
        pts_factor=pts_factor,
        pts_rank=pts_rank,
        reb_factor=reb_factor,
        reb_rank=reb_rank,
        ast_factor=ast_factor,
        ast_rank=ast_rank,
        archetype_adjustment=archetype_adj,
        archetype_reason=arch_reason,
        total_pts_adjustment=total_pts_adj,
        total_reb_adjustment=total_reb_adj,
        total_ast_adjustment=total_ast_adj,
        matchup_confidence_boost=matchup_boost,
        notes=notes,
        warnings=warnings,
    )


def _rank_to_rating(rank: int) -> str:
    """Convert numeric rank (1-30) to rating string."""
    if rank <= 5:
        return "elite"
    elif rank <= 10:
        return "good"
    elif rank <= 20:
        return "average"
    elif rank <= 25:
        return "poor"
    else:
        return "terrible"


def _calculate_archetype_adjustment(
    player_group: PlayerGroup,
    opponent_abbrev: str,
    conn: sqlite3.Connection,
) -> Tuple[float, str]:
    """
    Calculate adjustment based on archetype vs team's defensive style.
    
    Returns:
        (adjustment_value, reason_string)
    """
    archetype = player_group.primary_archetype
    
    # Check if we have archetype-specific adjustments
    if archetype not in ARCHETYPE_DEFENSE_MATRIX:
        return 0.0, ""
    
    arch_adjustments = ARCHETYPE_DEFENSE_MATRIX[archetype]
    
    # Try to get opponent's primary defensive players and style
    # For now, use general adjustments
    
    # Check for specific matchup patterns
    total_adj = 0.0
    reasons = []
    
    # Get opponent's elite defenders
    try:
        elite_defenders = _get_team_elite_defenders(conn, opponent_abbrev)
        
        for defender in elite_defenders:
            defender_role = defender.get("defensive_role", "")
            
            if defender_role in arch_adjustments:
                adj = arch_adjustments[defender_role]
                total_adj += adj
                if adj < 0:
                    reasons.append(f"vs {defender.get('name', 'elite defender')} ({defender_role})")
    except Exception:
        pass
    
    # Also check team-level defensive tendencies
    # (e.g., switch-heavy teams, drop coverage teams)
    
    reason = ", ".join(reasons) if reasons else ""
    if total_adj < 0 and reason:
        reason = f"Tough matchup: {reason}"
    elif total_adj > 0 and reason:
        reason = f"Favorable matchup: {reason}"
    
    return total_adj, reason


def _get_team_elite_defenders(
    conn: sqlite3.Connection,
    team_abbrev: str,
) -> List[Dict]:
    """Get elite defenders on a team."""
    try:
        from ..archetype_db import get_all_archetypes_db
        from ...team_aliases import team_name_from_abbrev
        
        team_name = team_name_from_abbrev(team_abbrev)
        if not team_name:
            return []
        
        archetypes = get_all_archetypes_db(
            conn, 
            season="2025-26", 
            team=team_name,
            elite_defenders_only=True
        )
        
        return [
            {
                "name": a.player_name,
                "defensive_role": a.defensive_role,
                "position": a.position,
            }
            for a in archetypes
        ]
    except Exception:
        return []


def _calculate_matchup_confidence(
    defense_rating: str,
    player_group: PlayerGroup,
    config: ModelV6Config,
) -> int:
    """
    Calculate confidence boost/penalty based on matchup quality.
    
    Returns points to add to confidence score (can be negative).
    """
    boost = 0
    
    # Favorable matchups boost confidence
    if defense_rating == "terrible":
        boost += 15
    elif defense_rating == "poor":
        boost += 10
    elif defense_rating == "average":
        boost += 0
    elif defense_rating == "good":
        boost -= 5
    elif defense_rating == "elite":
        boost -= 10
    
    # Star players are more matchup-proof
    if player_group.is_matchup_proof and boost < 0:
        boost = int(boost * 0.5)  # Reduce penalty for stars
    
    # Elite defenders should be wary of other elite defenders
    if player_group.is_elite_defender and defense_rating in ("elite", "good"):
        boost += 3  # Slight boost - they know how to play vs good D
    
    return boost


def get_team_defense_summary(
    conn: sqlite3.Connection,
    team_abbrev: str,
) -> Dict:
    """
    Get a summary of a team's defense across all positions.
    
    Returns:
        Dict with defense ratings by position and overall ranking
    """
    try:
        from ...ingest.defense_position_parser import (
            get_all_defense_vs_position_for_team,
        )
        
        defense_rows = get_all_defense_vs_position_for_team(conn, team_abbrev)
        
        if not defense_rows:
            return {
                "team": team_abbrev,
                "status": "no_data",
                "positions": {},
            }
        
        positions = {}
        for row in defense_rows:
            positions[row.position] = {
                "pts_allowed": row.pts_allowed,
                "pts_rank": row.pts_rank,
                "reb_allowed": row.reb_allowed,
                "reb_rank": row.reb_rank,
                "ast_allowed": row.ast_allowed,
                "ast_rank": row.ast_rank,
                "overall_rank": row.overall_rank,
            }
        
        # Calculate overall defense quality
        avg_pts_rank = sum(p.get("pts_rank", 15) for p in positions.values()) / len(positions)
        
        if avg_pts_rank <= 8:
            overall_rating = "elite"
        elif avg_pts_rank <= 13:
            overall_rating = "good"
        elif avg_pts_rank <= 18:
            overall_rating = "average"
        elif avg_pts_rank <= 23:
            overall_rating = "poor"
        else:
            overall_rating = "terrible"
        
        # Find weak spots
        weak_positions = []
        strong_positions = []
        for pos, data in positions.items():
            if data.get("pts_rank", 15) >= 23:
                weak_positions.append(pos)
            elif data.get("pts_rank", 15) <= 8:
                strong_positions.append(pos)
        
        return {
            "team": team_abbrev,
            "status": "ok",
            "overall_rating": overall_rating,
            "avg_pts_rank": round(avg_pts_rank, 1),
            "positions": positions,
            "weak_positions": weak_positions,
            "strong_positions": strong_positions,
        }
    
    except Exception as e:
        return {
            "team": team_abbrev,
            "status": "error",
            "error": str(e),
            "positions": {},
        }


def find_best_matchups(
    conn: sqlite3.Connection,
    player_groups: List[PlayerGroup],
    opponent_abbrev: str,
    config: ModelV6Config = DEFAULT_CONFIG,
) -> List[Tuple[PlayerGroup, DefenseMatchup, float]]:
    """
    Find the best matchups from a list of players vs an opponent.
    
    Returns:
        List of (player_group, matchup, matchup_score) sorted by score descending
    """
    results = []
    
    for pg in player_groups:
        matchup = get_defense_matchup(conn, pg, opponent_abbrev, config)
        
        # Calculate matchup score (higher = better for OVER)
        score = (
            (matchup.total_pts_adjustment - 1.0) * 50 +  # PTS factor weighted
            matchup.matchup_confidence_boost +
            (5 if matchup.defense_rating in ("poor", "terrible") else 0) +
            (-5 if matchup.defense_rating in ("elite", "good") else 0)
        )
        
        # Tier bonus
        if pg.tier_value <= 2:
            score += 10  # Stars more reliable
        
        results.append((pg, matchup, score))
    
    # Sort by score descending
    results.sort(key=lambda x: x[2], reverse=True)
    
    return results

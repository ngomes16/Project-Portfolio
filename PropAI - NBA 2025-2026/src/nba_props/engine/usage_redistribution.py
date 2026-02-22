"""Usage redistribution logic for when key players are out.

When a star player is injured or out, their teammates typically absorb
their production (points, assists, rebounds). This module calculates
how to adjust projections for remaining players.

Key Features:
- Calculate usage redistribution when stars are out
- Historical impact analysis
- Integrate with projector for automatic adjustments

Module Author: NBA Props Team
Last Updated: January 2026
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple

from ..team_aliases import abbrev_from_team_name, normalize_team_abbrev


# ============================================================================
# Constants
# ============================================================================

# Redistribution percentages (not all production is replaced)
PTS_REDISTRIBUTION_PCT = 0.85  # 85% of points get redistributed
REB_REDISTRIBUTION_PCT = 0.75  # 75% of rebounds
AST_REDISTRIBUTION_PCT = 0.80  # 80% of assists

# Cap on individual boosts
MAX_PTS_BOOST_PCT = 0.40  # Max 40% boost to any player's points
MAX_REB_BOOST_PCT = 0.40  # Max 40% boost to rebounds
MAX_AST_BOOST_PCT = 0.50  # Max 50% boost to assists (can spike more)
MAX_MIN_BOOST = 8  # Max 8 extra minutes

# Tier definitions
STAR_MIN_MINUTES = 30
STAR_MIN_PTS = 20
STARTER_MIN_MINUTES = 28
STARTER_MIN_PTS = 15


@dataclass
class PlayerUsageProfile:
    """Profile of a player's usage and production."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: Optional[str]
    
    # Average per-game stats (from recent games)
    avg_minutes: float
    avg_pts: float
    avg_reb: float
    avg_ast: float
    games_played: int
    
    # Usage metrics
    usage_rate: float  # Share of team's scoring
    minutes_share: float  # Share of team's minutes played
    assist_rate: float  # Share of team's assists
    
    # Role
    is_primary_scorer: bool = False
    is_primary_playmaker: bool = False
    is_primary_rebounder: bool = False
    tier: int = 5  # 1=star, 5=role player


@dataclass
class UsageRedistributionResult:
    """Result of usage redistribution calculation."""
    absent_player: str
    absent_stats: dict[str, float]  # What the absent player typically contributes
    
    # Redistribution by player
    redistributions: list[dict] = field(default_factory=list)
    
    # Summary
    total_pts_redistributed: float = 0.0
    total_reb_redistributed: float = 0.0
    total_ast_redistributed: float = 0.0


def get_team_usage_profiles(
    conn: sqlite3.Connection,
    team_abbrev: str,
    min_games: int = 3,
) -> list[PlayerUsageProfile]:
    """
    Get usage profiles for all players on a team.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
        min_games: Minimum games to include player
    
    Returns:
        List of PlayerUsageProfile sorted by usage
    """
    from ..standings import _team_ids_by_abbrev
    
    team_abbrev = normalize_team_abbrev(team_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(team_abbrev, [])
    
    if not team_ids:
        return []
    
    placeholders = ",".join(["?"] * len(team_ids))
    
    # Get player averages
    rows = conn.execute(
        f"""
        SELECT 
            b.player_id,
            p.name,
            MAX(b.pos) as pos,
            AVG(b.minutes) as avg_min,
            AVG(b.pts) as avg_pts,
            AVG(b.reb) as avg_reb,
            AVG(b.ast) as avg_ast,
            COUNT(*) as games
        FROM boxscore_player b
        JOIN players p ON p.id = b.player_id
        WHERE b.team_id IN ({placeholders})
          AND b.minutes IS NOT NULL
          AND b.minutes > 0
        GROUP BY b.player_id
        HAVING COUNT(*) >= ?
        ORDER BY avg_min DESC
        """,
        (*team_ids, min_games),
    ).fetchall()
    
    if not rows:
        return []
    
    # Calculate team totals for usage rates
    total_pts = sum(r["avg_pts"] or 0 for r in rows)
    total_reb = sum(r["avg_reb"] or 0 for r in rows)
    total_ast = sum(r["avg_ast"] or 0 for r in rows)
    total_min = sum(r["avg_min"] or 0 for r in rows)
    
    profiles = []
    for i, r in enumerate(rows):
        avg_pts = r["avg_pts"] or 0
        avg_reb = r["avg_reb"] or 0
        avg_ast = r["avg_ast"] or 0
        avg_min = r["avg_min"] or 0
        
        usage_rate = avg_pts / total_pts if total_pts > 0 else 0
        minutes_share = avg_min / total_min if total_min > 0 else 0
        assist_rate = avg_ast / total_ast if total_ast > 0 else 0
        
        # Determine role
        is_primary_scorer = i == 0 or usage_rate > 0.25
        is_primary_playmaker = assist_rate > 0.25
        is_primary_rebounder = avg_reb > 8
        
        # Assign tier based on minutes and stats
        if avg_min >= 30 and avg_pts >= 20:
            tier = 1
        elif avg_min >= 28 and avg_pts >= 15:
            tier = 2
        elif avg_min >= 25:
            tier = 3
        elif avg_min >= 18:
            tier = 4
        else:
            tier = 5
        
        profiles.append(PlayerUsageProfile(
            player_id=r["player_id"],
            player_name=r["name"],
            team_abbrev=team_abbrev,
            position=r["pos"],
            avg_minutes=round(avg_min, 1),
            avg_pts=round(avg_pts, 1),
            avg_reb=round(avg_reb, 1),
            avg_ast=round(avg_ast, 1),
            games_played=r["games"],
            usage_rate=round(usage_rate, 3),
            minutes_share=round(minutes_share, 3),
            assist_rate=round(assist_rate, 3),
            is_primary_scorer=is_primary_scorer,
            is_primary_playmaker=is_primary_playmaker,
            is_primary_rebounder=is_primary_rebounder,
            tier=tier,
        ))
    
    return profiles


def calculate_usage_redistribution(
    conn: sqlite3.Connection,
    team_abbrev: str,
    absent_player_name: str,
    min_games: int = 3,
) -> Optional[UsageRedistributionResult]:
    """
    Calculate how a player's stats would be redistributed when they're out.
    
    The redistribution algorithm:
    1. Get the absent player's average stats
    2. Find their "replacement minutes" (who plays more when they're out)
    3. Distribute their production proportionally to remaining starters/rotation
    
    Distribution rules:
    - Points: distributed by usage rate among remaining top players
    - Assists: primarily to primary playmakers
    - Rebounds: distributed by rebounding rate, favoring bigs
    """
    profiles = get_team_usage_profiles(conn, team_abbrev, min_games)
    
    if not profiles:
        return None
    
    # Find the absent player
    absent_profile = None
    remaining_profiles = []
    for p in profiles:
        if p.player_name.lower() == absent_player_name.lower():
            absent_profile = p
        else:
            remaining_profiles.append(p)
    
    if not absent_profile:
        # Player not found - try partial match
        for p in profiles:
            if absent_player_name.lower() in p.player_name.lower():
                absent_profile = p
                remaining_profiles = [x for x in profiles if x.player_id != p.player_id]
                break
    
    if not absent_profile:
        return None
    
    if not remaining_profiles:
        return None
    
    # Stats to redistribute
    pts_to_redistribute = absent_profile.avg_pts * 0.85  # Not all production is replaced
    reb_to_redistribute = absent_profile.avg_reb * 0.75
    ast_to_redistribute = absent_profile.avg_ast * 0.80
    
    # Minutes to redistribute (typically goes to starters + key bench)
    minutes_to_redistribute = absent_profile.avg_minutes
    
    # Calculate redistribution weights
    # For points: usage rate weighted, favoring high-usage players
    total_usage = sum(p.usage_rate for p in remaining_profiles[:6])  # Top 6 players
    
    # For assists: favor primary playmakers
    playmaker_weight = sum(p.assist_rate for p in remaining_profiles if p.is_primary_playmaker)
    if playmaker_weight == 0:
        # If no clear playmaker, use assist rate
        playmaker_weight = sum(p.assist_rate for p in remaining_profiles[:4])
    
    # For rebounds: favor bigs and high rebounders
    reb_weights = []
    for p in remaining_profiles[:6]:
        weight = p.avg_reb / max(sum(x.avg_reb for x in remaining_profiles[:6]), 1)
        # Extra weight for centers and power forwards
        if p.position in ('C', 'F'):
            weight *= 1.3
        reb_weights.append((p, weight))
    
    total_reb_weight = sum(w for _, w in reb_weights)
    
    result = UsageRedistributionResult(
        absent_player=absent_profile.player_name,
        absent_stats={
            "avg_pts": absent_profile.avg_pts,
            "avg_reb": absent_profile.avg_reb,
            "avg_ast": absent_profile.avg_ast,
            "avg_min": absent_profile.avg_minutes,
            "usage_rate": absent_profile.usage_rate,
        },
    )
    
    # Redistribute to top 6 remaining players
    for i, p in enumerate(remaining_profiles[:6]):
        # Points redistribution
        if total_usage > 0:
            pts_share = (p.usage_rate / total_usage) * pts_to_redistribute
        else:
            pts_share = pts_to_redistribute / min(6, len(remaining_profiles))
        
        # Extra boost for primary scorers
        if p.is_primary_scorer and absent_profile.is_primary_scorer:
            pts_share *= 1.2
        
        # Assists redistribution
        if p.is_primary_playmaker and playmaker_weight > 0:
            ast_share = (p.assist_rate / playmaker_weight) * ast_to_redistribute
        elif playmaker_weight > 0:
            ast_share = (p.assist_rate / playmaker_weight) * ast_to_redistribute * 0.3
        else:
            ast_share = ast_to_redistribute / min(6, len(remaining_profiles)) * 0.3
        
        # Rebounds redistribution
        reb_share = 0
        for rp, weight in reb_weights:
            if rp.player_id == p.player_id and total_reb_weight > 0:
                reb_share = (weight / total_reb_weight) * reb_to_redistribute
                break
        
        # Minutes redistribution (more to starters, less to bench)
        min_share = minutes_to_redistribute * (0.25 if i < 2 else 0.15 if i < 4 else 0.1)
        
        # Cap individual boosts to reasonable levels
        pts_share = min(pts_share, p.avg_pts * 0.4)  # Max 40% boost
        reb_share = min(reb_share, p.avg_reb * 0.4)
        ast_share = min(ast_share, p.avg_ast * 0.5)  # Assists can spike more
        min_share = min(min_share, 8)  # Max 8 extra minutes
        
        if pts_share > 0.5 or reb_share > 0.5 or ast_share > 0.5:
            result.redistributions.append({
                "player": p.player_name,
                "player_id": p.player_id,
                "baseline_pts": p.avg_pts,
                "baseline_reb": p.avg_reb,
                "baseline_ast": p.avg_ast,
                "pts_boost": round(pts_share, 1),
                "reb_boost": round(reb_share, 1),
                "ast_boost": round(ast_share, 1),
                "min_boost": round(min_share, 1),
                "projected_pts": round(p.avg_pts + pts_share, 1),
                "projected_reb": round(p.avg_reb + reb_share, 1),
                "projected_ast": round(p.avg_ast + ast_share, 1),
            })
            
            result.total_pts_redistributed += pts_share
            result.total_reb_redistributed += reb_share
            result.total_ast_redistributed += ast_share
    
    return result


def get_historical_impact(
    conn: sqlite3.Connection,
    team_abbrev: str,
    absent_player_name: str,
) -> Optional[dict]:
    """
    Analyze historical games where a player was absent to see actual impact.
    
    This compares games where the player played vs when they didn't play
    to see how teammates' production actually changed.
    """
    from ..standings import _team_ids_by_abbrev
    
    team_abbrev = normalize_team_abbrev(team_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(team_abbrev, [])
    
    if not team_ids:
        return None
    
    placeholders = ",".join(["?"] * len(team_ids))
    
    # Find the player
    player_row = conn.execute(
        "SELECT id, name FROM players WHERE name LIKE ?",
        (f"%{absent_player_name}%",),
    ).fetchone()
    
    if not player_row:
        return None
    
    player_id = player_row["id"]
    player_name = player_row["name"]
    
    # Find games where this player played (had minutes)
    games_played = conn.execute(
        f"""
        SELECT DISTINCT g.id
        FROM games g
        JOIN boxscore_player b ON b.game_id = g.id
        WHERE (g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders}))
          AND b.player_id = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 0
        """,
        (*team_ids, *team_ids, player_id),
    ).fetchall()
    
    games_played_ids = [r["id"] for r in games_played]
    
    if not games_played_ids:
        return None
    
    # Find games where this player was out (in inactive list or DNP)
    games_out = conn.execute(
        f"""
        SELECT DISTINCT g.id
        FROM games g
        WHERE (g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders}))
          AND g.id NOT IN ({','.join('?' * len(games_played_ids))})
        """,
        (*team_ids, *team_ids, *games_played_ids),
    ).fetchall()
    
    games_out_ids = [r["id"] for r in games_out]
    
    if not games_out_ids or len(games_out_ids) < 2:
        return None
    
    # Compare teammate performance in both scenarios
    # Get stats from games where player played
    with_player_stats = conn.execute(
        f"""
        SELECT 
            p.name,
            AVG(b.pts) as avg_pts,
            AVG(b.reb) as avg_reb,
            AVG(b.ast) as avg_ast,
            AVG(b.minutes) as avg_min,
            COUNT(*) as games
        FROM boxscore_player b
        JOIN players p ON p.id = b.player_id
        WHERE b.game_id IN ({','.join('?' * len(games_played_ids))})
          AND b.team_id IN ({placeholders})
          AND b.player_id != ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 10
        GROUP BY b.player_id
        HAVING COUNT(*) >= 3
        """,
        (*games_played_ids, *team_ids, player_id),
    ).fetchall()
    
    # Get stats from games where player was out
    without_player_stats = conn.execute(
        f"""
        SELECT 
            p.name,
            AVG(b.pts) as avg_pts,
            AVG(b.reb) as avg_reb,
            AVG(b.ast) as avg_ast,
            AVG(b.minutes) as avg_min,
            COUNT(*) as games
        FROM boxscore_player b
        JOIN players p ON p.id = b.player_id
        WHERE b.game_id IN ({','.join('?' * len(games_out_ids))})
          AND b.team_id IN ({placeholders})
          AND b.minutes IS NOT NULL
          AND b.minutes > 10
        GROUP BY b.player_id
        HAVING COUNT(*) >= 2
        """,
        (*games_out_ids, *team_ids),
    ).fetchall()
    
    # Build comparison
    with_stats = {r["name"]: dict(r) for r in with_player_stats}
    without_stats = {r["name"]: dict(r) for r in without_player_stats}
    
    comparisons = []
    for name in with_stats:
        if name in without_stats:
            w = with_stats[name]
            wo = without_stats[name]
            
            pts_diff = (wo["avg_pts"] or 0) - (w["avg_pts"] or 0)
            reb_diff = (wo["avg_reb"] or 0) - (w["avg_reb"] or 0)
            ast_diff = (wo["avg_ast"] or 0) - (w["avg_ast"] or 0)
            min_diff = (wo["avg_min"] or 0) - (w["avg_min"] or 0)
            
            if abs(pts_diff) > 1 or abs(reb_diff) > 1 or abs(ast_diff) > 1:
                comparisons.append({
                    "player": name,
                    "with_absent_player": {
                        "pts": round(w["avg_pts"] or 0, 1),
                        "reb": round(w["avg_reb"] or 0, 1),
                        "ast": round(w["avg_ast"] or 0, 1),
                        "min": round(w["avg_min"] or 0, 1),
                        "games": w["games"],
                    },
                    "without_absent_player": {
                        "pts": round(wo["avg_pts"] or 0, 1),
                        "reb": round(wo["avg_reb"] or 0, 1),
                        "ast": round(wo["avg_ast"] or 0, 1),
                        "min": round(wo["avg_min"] or 0, 1),
                        "games": wo["games"],
                    },
                    "difference": {
                        "pts": round(pts_diff, 1),
                        "reb": round(reb_diff, 1),
                        "ast": round(ast_diff, 1),
                        "min": round(min_diff, 1),
                    },
                })
    
    # Sort by points difference (biggest beneficiaries first)
    comparisons.sort(key=lambda x: -x["difference"]["pts"])
    
    return {
        "absent_player": player_name,
        "games_with_player": len(games_played_ids),
        "games_without_player": len(games_out_ids),
        "teammate_impacts": comparisons[:10],
    }


# ============================================================================
# Integration Functions for Projector
# ============================================================================

@dataclass
class UsageBoost:
    """Usage boost for a player when teammate(s) are out."""
    player_id: int
    player_name: str
    
    # Boosts to apply
    pts_boost: float
    reb_boost: float
    ast_boost: float
    min_boost: float
    
    # As multipliers (for easy application)
    pts_multiplier: float
    reb_multiplier: float
    ast_multiplier: float
    
    # Context
    absent_players: List[str]
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    reason: str


def get_usage_boost_for_player(
    conn: sqlite3.Connection,
    player_name: str,
    team_abbrev: str,
    absent_player_names: List[str],
) -> Optional[UsageBoost]:
    """
    Calculate usage boost for a specific player when teammate(s) are out.
    
    This is designed to integrate with the projector for automatic adjustments.
    
    Args:
        conn: Database connection
        player_name: Player receiving the boost
        team_abbrev: Team abbreviation
        absent_player_names: List of absent teammate names
    
    Returns:
        UsageBoost with multipliers to apply to projections, or None if no boost
    """
    if not absent_player_names:
        return None
    
    # Get team usage profiles
    profiles = get_team_usage_profiles(conn, team_abbrev)
    
    if not profiles:
        return None
    
    # Find the player we're boosting
    target_profile = None
    for p in profiles:
        if p.player_name.lower() == player_name.lower() or player_name.lower() in p.player_name.lower():
            target_profile = p
            break
    
    if not target_profile:
        return None
    
    # Calculate total boost from all absent players
    total_pts_boost = 0.0
    total_reb_boost = 0.0
    total_ast_boost = 0.0
    total_min_boost = 0.0
    
    for absent_name in absent_player_names:
        result = calculate_usage_redistribution(conn, team_abbrev, absent_name)
        
        if not result:
            continue
        
        # Find this player's share in the redistribution
        for redist in result.redistributions:
            if redist["player_id"] == target_profile.player_id:
                total_pts_boost += redist["pts_boost"]
                total_reb_boost += redist["reb_boost"]
                total_ast_boost += redist["ast_boost"]
                total_min_boost += redist["min_boost"]
                break
    
    if total_pts_boost == 0 and total_reb_boost == 0 and total_ast_boost == 0:
        return None
    
    # Calculate multipliers
    baseline_pts = target_profile.avg_pts
    baseline_reb = target_profile.avg_reb
    baseline_ast = target_profile.avg_ast
    
    pts_mult = 1.0 + (total_pts_boost / baseline_pts) if baseline_pts > 0 else 1.0
    reb_mult = 1.0 + (total_reb_boost / baseline_reb) if baseline_reb > 0 else 1.0
    ast_mult = 1.0 + (total_ast_boost / baseline_ast) if baseline_ast > 0 else 1.0
    
    # Cap multipliers at reasonable levels
    pts_mult = min(pts_mult, 1.0 + MAX_PTS_BOOST_PCT)
    reb_mult = min(reb_mult, 1.0 + MAX_REB_BOOST_PCT)
    ast_mult = min(ast_mult, 1.0 + MAX_AST_BOOST_PCT)
    
    # Determine confidence based on sample size and player tier
    if target_profile.tier <= 2 and target_profile.is_primary_scorer:
        confidence = "HIGH"
    elif target_profile.tier <= 3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    
    reason = f"Projected boost with {', '.join(absent_player_names)} out"
    
    return UsageBoost(
        player_id=target_profile.player_id,
        player_name=target_profile.player_name,
        pts_boost=round(total_pts_boost, 1),
        reb_boost=round(total_reb_boost, 1),
        ast_boost=round(total_ast_boost, 1),
        min_boost=round(total_min_boost, 1),
        pts_multiplier=round(pts_mult, 3),
        reb_multiplier=round(reb_mult, 3),
        ast_multiplier=round(ast_mult, 3),
        absent_players=absent_player_names,
        confidence=confidence,
        reason=reason
    )


def get_team_usage_boosts(
    conn: sqlite3.Connection,
    team_abbrev: str,
    absent_player_names: List[str],
) -> Dict[int, UsageBoost]:
    """
    Calculate usage boosts for all players on a team when teammate(s) are out.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
        absent_player_names: List of absent player names
    
    Returns:
        Dictionary of player_id -> UsageBoost
    """
    if not absent_player_names:
        return {}
    
    profiles = get_team_usage_profiles(conn, team_abbrev)
    
    if not profiles:
        return {}
    
    boosts = {}
    
    for profile in profiles:
        # Skip absent players
        is_absent = any(
            absent_name.lower() in profile.player_name.lower()
            for absent_name in absent_player_names
        )
        if is_absent:
            continue
        
        boost = get_usage_boost_for_player(
            conn, profile.player_name, team_abbrev, absent_player_names
        )
        
        if boost:
            boosts[profile.player_id] = boost
    
    return boosts


def is_star_out(
    conn: sqlite3.Connection,
    team_abbrev: str,
    player_name: str,
) -> bool:
    """
    Check if a player is considered a star (significant usage impact when out).
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
        player_name: Player name to check
    
    Returns:
        True if player is a star whose absence significantly impacts team
    """
    profiles = get_team_usage_profiles(conn, team_abbrev)
    
    if not profiles:
        return False
    
    for p in profiles:
        if player_name.lower() in p.player_name.lower():
            # Star criteria: tier 1-2, or high usage rate
            return p.tier <= 2 or p.usage_rate > 0.22 or p.is_primary_scorer
    
    return False

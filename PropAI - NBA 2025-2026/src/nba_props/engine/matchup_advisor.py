"""
Advanced Defense Analysis Engine (ADVISOR LAYER)
================================================

This module provides the sophisticated "Advisor" layer that transforms raw 
statistical projections into actionable betting recommendations.

Key Capabilities:
-----------------
1. **Position-Based Defense Analysis**
   - Analyze how teams defend guards, forwards, and centers
   - Calculate defensive factors and ratings by position
   - Rank teams by positional defensive strength

2. **Player vs Team Historical Analysis**
   - Track individual player performance against specific opponents
   - Identify favorable/unfavorable historical matchups
   - Weight recent games appropriately

3. **Player Trend Detection**
   - Identify hot/cold streaks
   - Calculate recent vs season performance
   - Measure consistency (standard deviation)

4. **Matchup Edge Calculation**
   - Combine all factors into actionable edges
   - Generate confidence scores and tiers
   - Provide reasoning and warnings

5. **Comprehensive Matchup Reports (MAIN ADVISOR)**
   - Categorize plays into "Best Over", "Best Under", "Avoid"
   - Generate key matchup storylines
   - Return structured ComprehensiveMatchupReport object

Usage Example:
-------------
    from nba_props.engine.matchup_advisor import generate_comprehensive_matchup_report
    
    report = generate_comprehensive_matchup_report(
        conn, "LAL", "BOS", "2026-01-03", spread=-3.5, over_under=220.5
    )
    
    for play in report.best_over_plays:
        print(f"OVER: {play.player_name} - {play.confidence_tier}")

Module Author: NBA Props Team
Last Updated: January 2026
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta

from ..team_aliases import normalize_team_abbrev, abbrev_from_team_name
from ..standings import _team_ids_by_abbrev
from ..engine.projector import project_team_players, ProjectionConfig
from ..engine.game_context import get_back_to_back_status
from ..engine.archetype_db import is_star_player, get_star_players_for_team


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PositionDefenseProfile:
    """How a team defends a specific position."""
    team_abbrev: str
    position: str  # G, F, C
    sample_size: int
    
    # Stats allowed to this position
    pts_allowed_avg: float
    reb_allowed_avg: float
    ast_allowed_avg: float
    
    # League averages for comparison
    league_pts_avg: float
    league_reb_avg: float
    league_ast_avg: float
    
    # Factors (>1 = allows more, <1 = allows less)
    pts_factor: float
    reb_factor: float
    ast_factor: float
    
    # Rankings (1 = best defense at this position)
    pts_rank: int = 0
    reb_rank: int = 0
    ast_rank: int = 0
    
    # Rating: "elite", "good", "average", "poor", "weak"
    pts_rating: str = "average"
    reb_rating: str = "average"
    ast_rating: str = "average"


@dataclass
class ArchetypeDefenseProfile:
    """How a team defends specific player archetypes."""
    team_abbrev: str
    archetype: str
    sample_size: int
    
    # Stats allowed
    pts_allowed_avg: float
    reb_allowed_avg: float
    ast_allowed_avg: float
    
    # Factors vs league average for this archetype
    pts_factor: float
    reb_factor: float
    ast_factor: float


@dataclass
class PlayerVsTeamProfile:
    """Historical performance of a player against a specific team."""
    player_name: str
    opponent_abbrev: str
    games_played: int
    
    # Stats vs this team
    pts_avg: float
    reb_avg: float
    ast_avg: float
    min_avg: float
    
    # Overall averages for comparison
    overall_pts_avg: float
    overall_reb_avg: float
    overall_ast_avg: float
    
    # Differential (positive = performs better vs this team)
    pts_diff: float
    reb_diff: float
    ast_diff: float
    
    # Last 3 games vs this team
    recent_games: list[dict] = field(default_factory=list)
    
    # Has significant history (3+ games)
    has_history: bool = False


@dataclass
class PlayerTrend:
    """Recent performance trend for a player."""
    player_name: str
    player_id: int
    team_abbrev: str
    
    # Recent averages (last 5 games)
    recent_pts: float
    recent_reb: float
    recent_ast: float
    recent_min: float
    recent_games: int
    
    # Season averages
    season_pts: float
    season_reb: float
    season_ast: float
    season_games: int
    
    # Trend direction and magnitude
    pts_trend: str  # "hot", "cold", "stable"
    reb_trend: str
    ast_trend: str
    
    # Percent change (positive = trending up)
    pts_change_pct: float
    reb_change_pct: float
    ast_change_pct: float
    
    # Consistency (standard deviation)
    pts_consistency: float
    reb_consistency: float
    ast_consistency: float
    
    # Recent game log
    game_log: list[dict] = field(default_factory=list)


@dataclass
class MatchupEdge:
    """Calculated edge for a specific player matchup."""
    player_name: str
    player_id: int
    team_abbrev: str
    opponent_abbrev: str
    
    # Prop type and direction
    prop_type: str  # PTS, REB, AST
    direction: str  # OVER, UNDER
    
    # Values
    baseline_projection: float
    adjusted_projection: float
    adjustment_pct: float
    
    # Confidence factors
    confidence_score: float  # 0-100
    confidence_tier: str  # "HIGH", "MEDIUM", "LOW"
    
    # Line value (average of last 10/7/5 games per Idea.txt)
    line: Optional[float] = None
    games_for_line: int = 0  # How many games used to calculate line
    
    # Individual factors
    factors: dict = field(default_factory=dict)
    
    # Reasoning
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    # Context
    is_close_game: bool = False
    spread: Optional[float] = None
    over_under: Optional[float] = None
    
    # Star player status
    is_star_player: bool = False


@dataclass 
class ComprehensiveMatchupReport:
    """Full matchup analysis between two teams."""
    away_abbrev: str
    home_abbrev: str
    game_date: str
    
    # Team context
    away_b2b: bool
    home_b2b: bool
    away_rest_days: int
    home_rest_days: int
    spread: Optional[float]
    over_under: Optional[float]
    is_close_game: bool
    
    # Defense profiles
    away_defense_vs_guards: Optional[PositionDefenseProfile]
    away_defense_vs_forwards: Optional[PositionDefenseProfile]
    away_defense_vs_centers: Optional[PositionDefenseProfile]
    home_defense_vs_guards: Optional[PositionDefenseProfile]
    home_defense_vs_forwards: Optional[PositionDefenseProfile]
    home_defense_vs_centers: Optional[PositionDefenseProfile]
    
    # Player projections with adjustments
    away_player_projections: list[dict] = field(default_factory=list)
    home_player_projections: list[dict] = field(default_factory=list)
    
    # Top edges
    best_over_plays: list[MatchupEdge] = field(default_factory=list)
    best_under_plays: list[MatchupEdge] = field(default_factory=list)
    
    # Players to avoid
    avoid_players: list[dict] = field(default_factory=list)
    
    # Key storylines
    key_matchups: list[str] = field(default_factory=list)


# ============================================================================
# Position-Based Defense Analysis
# ============================================================================

def get_position_defense_profile(
    conn: sqlite3.Connection,
    team_abbrev: str,
    position: str,
    min_games: int = 5,
) -> Optional[PositionDefenseProfile]:
    """
    Analyze how a team defends a specific position.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
        position: Position to analyze (G, F, C)
        min_games: Minimum games required
    
    Returns:
        PositionDefenseProfile or None if insufficient data
    """
    team_abbrev = normalize_team_abbrev(team_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(team_abbrev, [])
    
    if not team_ids:
        return None
    
    pos = position.upper()[:1] if position else ""
    if pos not in ("G", "F", "C"):
        return None
    
    placeholders = ",".join(["?"] * len(team_ids))
    
    # Get stats of players at this position AGAINST this team
    # (when this team was the opponent)
    rows = conn.execute(
        f"""
        SELECT 
            b.pts, b.reb, b.ast, b.minutes
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.pos = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 10
          AND b.team_id NOT IN ({placeholders})
          AND (g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders}))
        """,
        (pos, *team_ids, *team_ids, *team_ids),
    ).fetchall()
    
    if len(rows) < min_games:
        return None
    
    # Calculate averages allowed
    pts_allowed = [r["pts"] or 0 for r in rows]
    reb_allowed = [r["reb"] or 0 for r in rows]
    ast_allowed = [r["ast"] or 0 for r in rows]
    
    pts_avg = sum(pts_allowed) / len(pts_allowed)
    reb_avg = sum(reb_allowed) / len(reb_allowed)
    ast_avg = sum(ast_allowed) / len(ast_allowed)
    
    # Get league averages for this position
    league_row = conn.execute(
        """
        SELECT 
            AVG(pts) as league_pts,
            AVG(reb) as league_reb,
            AVG(ast) as league_ast
        FROM boxscore_player
        WHERE pos = ?
          AND minutes IS NOT NULL
          AND minutes > 10
        """,
        (pos,),
    ).fetchone()
    
    league_pts = league_row["league_pts"] or pts_avg
    league_reb = league_row["league_reb"] or reb_avg
    league_ast = league_row["league_ast"] or ast_avg
    
    # Calculate factors
    pts_factor = pts_avg / league_pts if league_pts > 0 else 1.0
    reb_factor = reb_avg / league_reb if league_reb > 0 else 1.0
    ast_factor = ast_avg / league_ast if league_ast > 0 else 1.0
    
    # Determine ratings
    def get_rating(factor):
        if factor <= 0.92:
            return "elite"
        elif factor <= 0.97:
            return "good"
        elif factor <= 1.03:
            return "average"
        elif factor <= 1.08:
            return "poor"
        else:
            return "weak"
    
    return PositionDefenseProfile(
        team_abbrev=team_abbrev,
        position=pos,
        sample_size=len(rows),
        pts_allowed_avg=round(pts_avg, 1),
        reb_allowed_avg=round(reb_avg, 1),
        ast_allowed_avg=round(ast_avg, 1),
        league_pts_avg=round(league_pts, 1),
        league_reb_avg=round(league_reb, 1),
        league_ast_avg=round(league_ast, 1),
        pts_factor=round(pts_factor, 3),
        reb_factor=round(reb_factor, 3),
        ast_factor=round(ast_factor, 3),
        pts_rating=get_rating(pts_factor),
        reb_rating=get_rating(reb_factor),
        ast_rating=get_rating(ast_factor),
    )


def get_all_position_defense_profiles(
    conn: sqlite3.Connection,
    team_abbrev: str,
) -> dict[str, PositionDefenseProfile]:
    """Get defense profiles for all positions for a team."""
    profiles = {}
    for pos in ["G", "F", "C"]:
        profile = get_position_defense_profile(conn, team_abbrev, pos)
        if profile:
            profiles[pos] = profile
    return profiles


def rank_position_defense_profiles(
    conn: sqlite3.Connection,
    position: str,
) -> list[PositionDefenseProfile]:
    """
    Rank all teams by their defense against a specific position.
    
    Returns list sorted by pts_factor (best defense first).
    """
    from ..standings import ALL_ABBREVS
    
    profiles = []
    for abbrev in ALL_ABBREVS:
        profile = get_position_defense_profile(conn, abbrev, position)
        if profile:
            profiles.append(profile)
    
    # Sort by pts_factor (lower = better defense)
    profiles.sort(key=lambda p: p.pts_factor)
    
    # Assign ranks
    for i, p in enumerate(profiles, 1):
        p.pts_rank = i
    
    profiles_by_reb = sorted(profiles, key=lambda p: p.reb_factor)
    for i, p in enumerate(profiles_by_reb, 1):
        p.reb_rank = i
    
    profiles_by_ast = sorted(profiles, key=lambda p: p.ast_factor)
    for i, p in enumerate(profiles_by_ast, 1):
        p.ast_rank = i
    
    return profiles


# ============================================================================
# Player vs Team History
# ============================================================================

def get_player_vs_team_profile(
    conn: sqlite3.Connection,
    player_name: str,
    opponent_abbrev: str,
) -> Optional[PlayerVsTeamProfile]:
    """
    Get historical performance of a player against a specific team.
    """
    opponent_abbrev = normalize_team_abbrev(opponent_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    opponent_ids = team_ids_map.get(opponent_abbrev, [])
    
    if not opponent_ids:
        return None
    
    # Find player
    player_row = conn.execute(
        "SELECT id, name FROM players WHERE name LIKE ?",
        (f"%{player_name}%",),
    ).fetchone()
    
    if not player_row:
        return None
    
    player_id = player_row["id"]
    full_name = player_row["name"]
    
    placeholders = ",".join(["?"] * len(opponent_ids))
    
    # Get games against this opponent
    vs_rows = conn.execute(
        f"""
        SELECT 
            g.game_date, b.pts, b.reb, b.ast, b.minutes
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.player_id = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 5
          AND (g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders}))
        ORDER BY g.game_date DESC
        """,
        (player_id, *opponent_ids, *opponent_ids),
    ).fetchall()
    
    if not vs_rows:
        return None
    
    # Get overall averages
    overall_row = conn.execute(
        """
        SELECT 
            AVG(pts) as avg_pts,
            AVG(reb) as avg_reb,
            AVG(ast) as avg_ast,
            AVG(minutes) as avg_min
        FROM boxscore_player
        WHERE player_id = ?
          AND minutes IS NOT NULL
          AND minutes > 5
        """,
        (player_id,),
    ).fetchone()
    
    # Calculate vs team averages
    pts_vs = sum(r["pts"] or 0 for r in vs_rows) / len(vs_rows)
    reb_vs = sum(r["reb"] or 0 for r in vs_rows) / len(vs_rows)
    ast_vs = sum(r["ast"] or 0 for r in vs_rows) / len(vs_rows)
    min_vs = sum(r["minutes"] or 0 for r in vs_rows) / len(vs_rows)
    
    overall_pts = overall_row["avg_pts"] or pts_vs
    overall_reb = overall_row["avg_reb"] or reb_vs
    overall_ast = overall_row["avg_ast"] or ast_vs
    
    return PlayerVsTeamProfile(
        player_name=full_name,
        opponent_abbrev=opponent_abbrev,
        games_played=len(vs_rows),
        pts_avg=round(pts_vs, 1),
        reb_avg=round(reb_vs, 1),
        ast_avg=round(ast_vs, 1),
        min_avg=round(min_vs, 1),
        overall_pts_avg=round(overall_pts, 1),
        overall_reb_avg=round(overall_reb, 1),
        overall_ast_avg=round(overall_ast, 1),
        pts_diff=round(pts_vs - overall_pts, 1),
        reb_diff=round(reb_vs - overall_reb, 1),
        ast_diff=round(ast_vs - overall_ast, 1),
        recent_games=[
            {
                "date": r["game_date"],
                "pts": r["pts"],
                "reb": r["reb"],
                "ast": r["ast"],
                "min": round(r["minutes"], 1) if r["minutes"] else 0,
            }
            for r in vs_rows[:5]
        ],
        has_history=len(vs_rows) >= 3,
    )


# ============================================================================
# Player Trend Analysis
# ============================================================================

def get_player_trend(
    conn: sqlite3.Connection,
    player_id: int,
    recent_games: int = 5,
) -> Optional[PlayerTrend]:
    """
    Analyze a player's recent performance trends.
    """
    # Get player info
    player_row = conn.execute(
        "SELECT id, name FROM players WHERE id = ?", (player_id,)
    ).fetchone()
    if not player_row:
        return None
    
    # Get all games
    rows = conn.execute(
        """
        SELECT 
            g.game_date, b.pts, b.reb, b.ast, b.minutes, t.name as team
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        JOIN teams t ON t.id = b.team_id
        WHERE b.player_id = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 5
        ORDER BY g.game_date DESC
        """,
        (player_id,),
    ).fetchall()
    
    if len(rows) < 3:
        return None
    
    # Get team abbrev from most recent game
    team_name = rows[0]["team"]
    team_abbrev = abbrev_from_team_name(team_name) or ""
    
    # Split into recent and season
    recent_rows = rows[:recent_games]
    all_rows = rows
    
    # Calculate recent averages
    recent_pts = sum(r["pts"] or 0 for r in recent_rows) / len(recent_rows)
    recent_reb = sum(r["reb"] or 0 for r in recent_rows) / len(recent_rows)
    recent_ast = sum(r["ast"] or 0 for r in recent_rows) / len(recent_rows)
    recent_min = sum(r["minutes"] or 0 for r in recent_rows) / len(recent_rows)
    
    # Calculate season averages
    season_pts = sum(r["pts"] or 0 for r in all_rows) / len(all_rows)
    season_reb = sum(r["reb"] or 0 for r in all_rows) / len(all_rows)
    season_ast = sum(r["ast"] or 0 for r in all_rows) / len(all_rows)
    
    # Calculate change percentages
    def pct_change(recent, season):
        if season == 0:
            return 0
        return ((recent - season) / season) * 100
    
    pts_change = pct_change(recent_pts, season_pts)
    reb_change = pct_change(recent_reb, season_reb)
    ast_change = pct_change(recent_ast, season_ast)
    
    # Determine trends
    def get_trend(change_pct):
        if change_pct >= 15:
            return "hot"
        elif change_pct <= -15:
            return "cold"
        else:
            return "stable"
    
    # Calculate consistency (std dev)
    import statistics
    pts_values = [r["pts"] or 0 for r in recent_rows]
    reb_values = [r["reb"] or 0 for r in recent_rows]
    ast_values = [r["ast"] or 0 for r in recent_rows]
    
    pts_std = statistics.stdev(pts_values) if len(pts_values) > 1 else 0
    reb_std = statistics.stdev(reb_values) if len(reb_values) > 1 else 0
    ast_std = statistics.stdev(ast_values) if len(ast_values) > 1 else 0
    
    return PlayerTrend(
        player_name=player_row["name"],
        player_id=player_id,
        team_abbrev=team_abbrev,
        recent_pts=round(recent_pts, 1),
        recent_reb=round(recent_reb, 1),
        recent_ast=round(recent_ast, 1),
        recent_min=round(recent_min, 1),
        recent_games=len(recent_rows),
        season_pts=round(season_pts, 1),
        season_reb=round(season_reb, 1),
        season_ast=round(season_ast, 1),
        season_games=len(all_rows),
        pts_trend=get_trend(pts_change),
        reb_trend=get_trend(reb_change),
        ast_trend=get_trend(ast_change),
        pts_change_pct=round(pts_change, 1),
        reb_change_pct=round(reb_change, 1),
        ast_change_pct=round(ast_change, 1),
        pts_consistency=round(pts_std, 1),
        reb_consistency=round(reb_std, 1),
        ast_consistency=round(ast_std, 1),
        game_log=[
            {
                "date": r["game_date"],
                "pts": r["pts"],
                "reb": r["reb"],
                "ast": r["ast"],
                "min": round(r["minutes"], 1) if r["minutes"] else 0,
            }
            for r in recent_rows
        ],
    )


# ============================================================================
# Comprehensive Matchup Edge Calculation
# ============================================================================

def _get_player_baseline_stats(
    conn: sqlite3.Connection,
    player_id: int,
    lookback_games: int = 20,
) -> Optional[dict]:
    """
    Get player's baseline stats for comparison.
    Returns season average, L5 average, and standard deviation.
    """
    rows = conn.execute(
        """
        SELECT b.pts, b.reb, b.ast, b.minutes
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.player_id = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 5
        ORDER BY g.game_date DESC
        LIMIT ?
        """,
        (player_id, lookback_games),
    ).fetchall()
    
    if len(rows) < 3:
        return None
    
    import statistics
    
    pts_vals = [r["pts"] or 0 for r in rows]
    reb_vals = [r["reb"] or 0 for r in rows]
    ast_vals = [r["ast"] or 0 for r in rows]
    
    l5_pts = pts_vals[:5]
    l5_reb = reb_vals[:5]
    l5_ast = ast_vals[:5]
    
    return {
        "pts_avg": sum(pts_vals) / len(pts_vals),
        "reb_avg": sum(reb_vals) / len(reb_vals),
        "ast_avg": sum(ast_vals) / len(ast_vals),
        "pts_l5": sum(l5_pts) / len(l5_pts) if l5_pts else 0,
        "reb_l5": sum(l5_reb) / len(l5_reb) if l5_reb else 0,
        "ast_l5": sum(l5_ast) / len(l5_ast) if l5_ast else 0,
        "pts_std": statistics.stdev(pts_vals) if len(pts_vals) > 1 else 0,
        "reb_std": statistics.stdev(reb_vals) if len(reb_vals) > 1 else 0,
        "ast_std": statistics.stdev(ast_vals) if len(ast_vals) > 1 else 0,
        "pts_median": statistics.median(pts_vals),
        "reb_median": statistics.median(reb_vals),
        "ast_median": statistics.median(ast_vals),
        "games": len(rows),
    }


def calculate_player_line(
    conn: sqlite3.Connection,
    player_id: int,
    prop_type: str,
) -> tuple[Optional[float], int, Optional[str]]:
    """
    Calculate the player's line as the average of their performance.
    
    Per Idea.txt:
    - Use last 10 games if available
    - If not available, use last 7 games  
    - If not available, use last 5 games
    - If not available, return warning that player hasn't played enough games
    
    Args:
        conn: Database connection
        player_id: Player ID
        prop_type: PTS, REB, or AST
        
    Returns:
        Tuple of (line_value, games_used, warning_message)
        - line_value: The calculated line (average), or None if insufficient data
        - games_used: Number of games used to calculate line
        - warning_message: Warning if fewer than 5 games available
    """
    rows = conn.execute(
        """
        SELECT b.pts, b.reb, b.ast
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.player_id = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 5
        ORDER BY g.game_date DESC
        LIMIT 10
        """,
        (player_id,),
    ).fetchall()
    
    if not rows:
        return None, 0, "⚠️ No games played - insufficient data for line calculation"
    
    # Get the appropriate stat values
    if prop_type == "PTS":
        values = [r["pts"] or 0 for r in rows]
    elif prop_type == "REB":
        values = [r["reb"] or 0 for r in rows]
    elif prop_type == "AST":
        values = [r["ast"] or 0 for r in rows]
    else:
        return None, 0, f"Unknown prop type: {prop_type}"
    
    games_available = len(values)
    warning = None
    
    # Determine which games to use for line calculation
    if games_available >= 10:
        # Use last 10 games
        line_values = values[:10]
        games_used = 10
    elif games_available >= 7:
        # Fall back to last 7 games
        line_values = values[:7]
        games_used = 7
    elif games_available >= 5:
        # Fall back to last 5 games
        line_values = values[:5]
        games_used = 5
    else:
        # Less than 5 games - use what we have but add warning
        line_values = values
        games_used = games_available
        warning = f"⚠️ Only {games_available} games played - line may be unreliable"
    
    # Calculate average (the line)
    line = round(sum(line_values) / len(line_values), 1) if line_values else None
    
    return line, games_used, warning


def calculate_matchup_edge(
    conn: sqlite3.Connection,
    player_id: int,
    player_name: str,
    team_abbrev: str,
    opponent_abbrev: str,
    prop_type: str,
    baseline_value: float,
    is_b2b: bool = False,
    rest_days: int = 1,
    spread: Optional[float] = None,
    over_under: Optional[float] = None,
    skip_factors: Optional[list[str]] = None,
    override_pos_defense: Optional[PositionDefenseProfile] = None,
) -> MatchupEdge:
    """
    Calculate comprehensive matchup edge for a player prop.
    
    FIXED LOGIC: Direction is now based on comparing adjusted projection
    to player's historical median/baseline, not just adjustment sign.
    
    Considers:
    - Position-based defensive matchup
    - Historical performance vs this team
    - Recent trend (hot/cold)
    - Back-to-back/rest factors
    - Game context (spread, expected pace)
    - Elite defender presence
    - Player consistency/volatility
    """
    factors = {}
    reasons = []
    warnings = []
    adjustment = 1.0
    skip_factors = skip_factors or []
    
    # Initialize variables that may be conditionally set
    is_close_game = spread is not None and abs(spread) <= 6
    vs_team = None
    trend = None
    pos_defense = None
    
    # Get player's baseline stats for comparison
    baseline_stats = _get_player_baseline_stats(conn, player_id)
    
    # Get player's position
    pos_row = conn.execute(
        """
        SELECT pos FROM boxscore_player 
        WHERE player_id = ? AND pos IS NOT NULL AND pos != ''
        ORDER BY game_id DESC LIMIT 1
        """,
        (player_id,),
    ).fetchone()
    position = pos_row["pos"] if pos_row else "G"
    
    # ============================
    # 1. Position Defense Factor
    # ============================
    if "position_defense" not in skip_factors:
        if override_pos_defense:
            pos_defense = override_pos_defense
        else:
            pos_defense = get_position_defense_profile(conn, opponent_abbrev, position)
            
        if pos_defense:
            if prop_type == "PTS":
                pos_factor = pos_defense.pts_factor
                rating = pos_defense.pts_rating
            elif prop_type == "REB":
                pos_factor = pos_defense.reb_factor
                rating = pos_defense.reb_rating
            else:
                pos_factor = pos_defense.ast_factor
                rating = pos_defense.ast_rating
            
            # Clamp to reasonable range
            pos_factor = max(0.85, min(1.15, pos_factor))
            factors["position_defense"] = pos_factor
            adjustment *= pos_factor
            
            if rating in ("elite", "good"):
                warnings.append(f"{opponent_abbrev} has {rating} {position} defense")
            elif rating in ("poor", "weak"):
                reasons.append(f"{opponent_abbrev} allows extra {prop_type} to {position}s (+{int((pos_factor-1)*100)}%)")
    
    # ============================
    # 2. Player vs Team History
    # ============================
    if "historical" not in skip_factors:
        vs_team = get_player_vs_team_profile(conn, player_name, opponent_abbrev)
        if vs_team and vs_team.has_history:
            if prop_type == "PTS":
                hist_diff = vs_team.pts_diff
                hist_avg = vs_team.pts_avg
            elif prop_type == "REB":
                hist_diff = vs_team.reb_diff
                hist_avg = vs_team.reb_avg
            else:
                hist_diff = vs_team.ast_diff
                hist_avg = vs_team.ast_avg
            
            # Historical performance adjustment (weighted)
            if abs(hist_diff) >= 2:
                hist_factor = 1 + (hist_diff / baseline_value * 0.5) if baseline_value > 0 else 1.0
                hist_factor = max(0.85, min(1.15, hist_factor))
                factors["historical"] = hist_factor
                adjustment *= hist_factor
                
                if hist_diff > 2:
                    reasons.append(f"Averages {hist_avg} {prop_type} vs {opponent_abbrev} (+{hist_diff:.1f} vs avg)")
                elif hist_diff < -2:
                    warnings.append(f"Only {hist_avg} {prop_type} vs {opponent_abbrev} ({hist_diff:.1f} vs avg)")
    
    # ============================
    # 3. Recent Trend
    # ============================
    trend = get_player_trend(conn, player_id)
    if trend:
        if prop_type == "PTS":
            trend_pct = trend.pts_change_pct
            trend_dir = trend.pts_trend
            consistency = trend.pts_consistency
        elif prop_type == "REB":
            trend_pct = trend.reb_change_pct
            trend_dir = trend.reb_trend
            consistency = trend.reb_consistency
        else:
            trend_pct = trend.ast_change_pct
            trend_dir = trend.ast_trend
            consistency = trend.ast_consistency
        
        # Trend adjustment (smaller weight)
        if abs(trend_pct) >= 10:
            trend_factor = 1 + (trend_pct / 100 * 0.3)
            trend_factor = max(0.90, min(1.10, trend_factor))
            factors["trend"] = trend_factor
            adjustment *= trend_factor
            
            if trend_dir == "hot":
                reasons.append(f"🔥 Hot streak: {trend_pct:+.0f}% {prop_type} over last {trend.recent_games} games")
            elif trend_dir == "cold":
                warnings.append(f"❄️ Cold streak: {trend_pct:.0f}% {prop_type} over last {trend.recent_games} games")
        
        # Consistency warning
        if consistency > baseline_value * 0.3:
            warnings.append(f"Inconsistent: ±{consistency:.1f} {prop_type} variance")
    
    # ============================
    # 4. Rest/B2B Factor
    # ============================
    if "back_to_back" not in skip_factors:
        if is_b2b:
            b2b_factor = 0.94
            factors["back_to_back"] = b2b_factor
            adjustment *= b2b_factor
            warnings.append("Playing back-to-back (-6%)")
        elif rest_days >= 3:
            rest_factor = 1.03
            factors["well_rested"] = rest_factor
            adjustment *= rest_factor
            reasons.append(f"Well rested ({rest_days} days off)")
    
    # ============================
    # 5. Game Context
    # ============================
    if "game_context" not in skip_factors:
        is_close_game = spread is not None and abs(spread) <= 6
        
        if is_close_game:
            # Close games = more playing time for starters
            close_factor = 1.03
            factors["close_game"] = close_factor
            adjustment *= close_factor
            reasons.append("Expected close game (+3% for starters)")
        elif spread is not None and abs(spread) > 10:
            # Blowout risk = potential rest
            blowout_factor = 0.95
            factors["blowout_risk"] = blowout_factor
            adjustment *= blowout_factor
            warnings.append(f"Blowout risk (spread {spread:+.1f})")
    
    # ============================
    # 6. Elite Defender Check
    # ============================
    if "elite_defender" not in skip_factors:
        from .roster import should_avoid_betting_over, get_roster_for_team, get_player_profile
        
        try:
            opponent_roster = [p.name for p in get_roster_for_team(opponent_abbrev)]
            avoid, defenders = should_avoid_betting_over(player_name, opponent_roster)
            if avoid and prop_type == "PTS":
                defender_factor = 0.94
                factors["elite_defender"] = defender_factor
                adjustment *= defender_factor
                warnings.append(f"⚠️ Elite defender: {', '.join(defenders[:2])}")
        except Exception:
            pass
    
    # ============================
    # Calculate Final Values
    # ============================
    adjusted_value = baseline_value * adjustment
    adjustment_pct = (adjustment - 1) * 100
    
    # ============================
    # FIXED: Direction Determination
    # ============================
    # Direction should be based on comparing adjusted projection to player's 
    # historical MEDIAN (not season average), accounting for factors:
    # 1. If projection is significantly ABOVE median + we have positive factors -> OVER
    # 2. If projection is significantly BELOW median + we have negative factors -> UNDER
    # 3. Compare to recent L5 performance for trend context
    
    if baseline_stats:
        if prop_type == "PTS":
            player_median = baseline_stats["pts_median"]
            player_std = baseline_stats["pts_std"]
            player_l5 = baseline_stats["pts_l5"]
        elif prop_type == "REB":
            player_median = baseline_stats["reb_median"]
            player_std = baseline_stats["reb_std"]
            player_l5 = baseline_stats["reb_l5"]
        else:
            player_median = baseline_stats["ast_median"]
            player_std = baseline_stats["ast_std"]
            player_l5 = baseline_stats["ast_l5"]
        
        # Direction is based on:
        # 1. Whether adjusted projection is above or below median
        # 2. Whether adjustment factors favor over or under
        # 3. Recent trend alignment
        
        diff_from_median = adjusted_value - player_median
        diff_pct = (diff_from_median / player_median * 100) if player_median > 0 else 0
        
        # Strong OVER signal: projection is above median AND adjustments are positive
        # Strong UNDER signal: projection is below median AND adjustments are negative
        if adjustment > 1.02 and diff_from_median > 0:
            direction = "OVER"
        elif adjustment < 0.98 and diff_from_median < 0:
            direction = "UNDER"
        elif adjustment > 1.05:  # Strong positive adjustment
            direction = "OVER"
        elif adjustment < 0.95:  # Strong negative adjustment
            direction = "UNDER"
        # Moderate signals - need consistent factors
        elif adjustment >= 1.0 and len(reasons) >= 2 and len(warnings) <= 1:
            direction = "OVER"
        elif adjustment <= 1.0 and len(warnings) >= 2 and len(reasons) <= 1:
            direction = "UNDER"
        else:
            direction = "PASS"
    else:
        # Fallback to old logic if no baseline stats
        if adjustment > 1.02:
            direction = "OVER"
        elif adjustment < 0.98:
            direction = "UNDER"
        else:
            direction = "PASS"
    
    # ============================
    # FIXED: Confidence Scoring
    # ============================
    # Confidence should be based on:
    # 1. Strength of factors (not just count)
    # 2. Alignment of multiple independent factors
    # 3. Player consistency (low variance = more predictable)
    # 4. Sample size
    
    confidence_score = 50  # Base
    
    # ============================
    # IMPROVED CONFIDENCE SCORING
    # ============================
    
    # 1. Factor alignment bonus - multiple factors pointing same direction
    positive_factors = sum(1 for f in factors.values() if f > 1.0)
    negative_factors = sum(1 for f in factors.values() if f < 1.0)
    
    if direction == "OVER" and positive_factors >= 2:
        confidence_score += 10 + (positive_factors - 2) * 5
    elif direction == "UNDER" and negative_factors >= 2:
        confidence_score += 10 + (negative_factors - 2) * 5
    
    # 2. Penalize conflicting signals
    if positive_factors > 0 and negative_factors > 0:
        confidence_score -= 10  # Mixed signals reduce confidence
    
    # 3. Warnings penalty (scaled by severity)
    confidence_score -= len(warnings) * 6
    
    # 4. Position defense alignment
    if pos_defense:
        rating = pos_defense.pts_rating if prop_type == "PTS" else pos_defense.reb_rating
        if rating in ("elite", "good") and direction == "UNDER":
            confidence_score += 12  # Good defense supports UNDER
        elif rating in ("poor", "weak") and direction == "OVER":
            confidence_score += 12  # Weak defense supports OVER
        elif rating in ("elite", "good") and direction == "OVER":
            confidence_score -= 8  # Betting OVER against good defense
        elif rating in ("poor", "weak") and direction == "UNDER":
            confidence_score -= 8  # Betting UNDER against weak defense
    
    # 5. Historical performance vs team
    if vs_team and vs_team.has_history:
        if prop_type == "PTS":
            hist_diff = vs_team.pts_diff
        elif prop_type == "REB":
            hist_diff = vs_team.reb_diff
        else:
            hist_diff = vs_team.ast_diff
            
        # Historical alignment bonus
        if (direction == "OVER" and hist_diff > 2) or (direction == "UNDER" and hist_diff < -2):
            confidence_score += 10
        elif (direction == "OVER" and hist_diff < -2) or (direction == "UNDER" and hist_diff > 2):
            confidence_score -= 8  # Going against history
    
    # 6. Trend alignment
    if trend:
        trend_dir = trend.pts_trend if prop_type == "PTS" else trend.reb_trend
        if (trend_dir == "hot" and direction == "OVER") or (trend_dir == "cold" and direction == "UNDER"):
            confidence_score += 10
        elif (trend_dir == "cold" and direction == "OVER") or (trend_dir == "hot" and direction == "UNDER"):
            confidence_score -= 8  # Going against trend
    
    # 7. Player consistency bonus
    if baseline_stats:
        if prop_type == "PTS":
            player_std = baseline_stats["pts_std"]
            player_avg = baseline_stats["pts_avg"]
        elif prop_type == "REB":
            player_std = baseline_stats["reb_std"]
            player_avg = baseline_stats["reb_avg"]
        else:
            player_std = baseline_stats["ast_std"]
            player_avg = baseline_stats["ast_avg"]
        
        # CV (coefficient of variation) = std/mean
        cv = player_std / player_avg if player_avg > 0 else 1
        if cv < 0.20:  # Very consistent player
            confidence_score += 8
            reasons.append(f"Consistent performer (CV={cv:.2f})")
        elif cv > 0.40:  # Inconsistent player
            confidence_score -= 10
            warnings.append(f"High variance player (CV={cv:.2f})")
    
    # 8. Low-integer/assist prop dampening
    is_low_integer_prop = prop_type in ["AST", "BLK", "STL"] or baseline_value < 8.0
    
    if is_low_integer_prop:
        abs_diff = abs(adjusted_value - baseline_value)
        
        # Small absolute differences on low-value props are noise
        if abs_diff < 0.5:
            confidence_score -= 15
        elif abs_diff < 1.0:
            confidence_score -= 8
            
        # Cap confidence for low-integer props
        if confidence_score > 65:
            confidence_score = 65 + (confidence_score - 65) * 0.5
    
    # 9. Require minimum adjustment magnitude
    if abs(adjustment - 1.0) < 0.02:  # Less than 2% adjustment
        confidence_score -= 10
        if direction != "PASS":
            direction = "PASS"  # Force PASS for trivial edges
    
    # Clamp confidence
    confidence_score = max(0, min(100, confidence_score))
    
    # Determine tier
    if confidence_score >= 75:
        confidence_tier = "HIGH"
    elif confidence_score >= 55:
        confidence_tier = "MEDIUM"
    else:
        confidence_tier = "LOW"
    
    # Calculate the player's line (average of last 10/7/5 games per Idea.txt)
    line, games_for_line, line_warning = calculate_player_line(conn, player_id, prop_type)
    
    # Add warning if not enough games for reliable line
    if line_warning and line_warning not in warnings:
        warnings.append(line_warning)
    
    return MatchupEdge(
        player_name=player_name,
        player_id=player_id,
        team_abbrev=team_abbrev,
        opponent_abbrev=opponent_abbrev,
        prop_type=prop_type,
        direction=direction,
        baseline_projection=round(baseline_value, 1),
        adjusted_projection=round(adjusted_value, 1),
        adjustment_pct=round(adjustment_pct, 1),
        line=line,
        games_for_line=games_for_line,
        confidence_score=confidence_score,
        confidence_tier=confidence_tier,
        factors=factors,
        reasons=reasons,
        warnings=warnings,
        is_close_game=is_close_game,
        spread=spread,
        over_under=over_under,
    )


# ============================================================================
# Team Defense Summary
# ============================================================================

def get_team_defense_summary(
    conn: sqlite3.Connection,
    team_abbrev: str,
) -> dict:
    """
    Get a comprehensive summary of a team's defensive performance.
    """
    team_abbrev = normalize_team_abbrev(team_abbrev)
    
    # Get position profiles
    guard_defense = get_position_defense_profile(conn, team_abbrev, "G")
    forward_defense = get_position_defense_profile(conn, team_abbrev, "F")
    center_defense = get_position_defense_profile(conn, team_abbrev, "C")
    
    # Overall rating
    all_factors = []
    if guard_defense:
        all_factors.append(guard_defense.pts_factor)
    if forward_defense:
        all_factors.append(forward_defense.pts_factor)
    if center_defense:
        all_factors.append(center_defense.pts_factor)
    
    overall_factor = sum(all_factors) / len(all_factors) if all_factors else 1.0
    
    def get_overall_rating(factor):
        if factor <= 0.94:
            return "Elite Defense"
        elif factor <= 0.98:
            return "Good Defense"
        elif factor <= 1.02:
            return "Average Defense"
        elif factor <= 1.06:
            return "Below Average Defense"
        else:
            return "Weak Defense"
    
    # Find strengths and weaknesses
    strengths = []
    weaknesses = []
    
    for name, profile in [("Guards", guard_defense), ("Forwards", forward_defense), ("Centers", center_defense)]:
        if not profile:
            continue
        
        if profile.pts_rating in ("elite", "good"):
            strengths.append(f"vs {name} ({profile.pts_rating})")
        elif profile.pts_rating in ("poor", "weak"):
            weaknesses.append(f"vs {name} ({profile.pts_rating})")
    
    return {
        "team_abbrev": team_abbrev,
        "overall_rating": get_overall_rating(overall_factor),
        "overall_factor": round(overall_factor, 3),
        "guard_defense": {
            "rating": guard_defense.pts_rating if guard_defense else "unknown",
            "pts_factor": guard_defense.pts_factor if guard_defense else 1.0,
            "reb_factor": guard_defense.reb_factor if guard_defense else 1.0,
            "ast_factor": guard_defense.ast_factor if guard_defense else 1.0,
        } if guard_defense else None,
        "forward_defense": {
            "rating": forward_defense.pts_rating if forward_defense else "unknown",
            "pts_factor": forward_defense.pts_factor if forward_defense else 1.0,
            "reb_factor": forward_defense.reb_factor if forward_defense else 1.0,
            "ast_factor": forward_defense.ast_factor if forward_defense else 1.0,
        } if forward_defense else None,
        "center_defense": {
            "rating": center_defense.pts_rating if center_defense else "unknown",
            "pts_factor": center_defense.pts_factor if center_defense else 1.0,
            "reb_factor": center_defense.reb_factor if center_defense else 1.0,
            "ast_factor": center_defense.ast_factor if center_defense else 1.0,
        } if center_defense else None,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


# ============================================================================
# Injury Report Helpers
# ============================================================================

def _get_team_injury_report(
    conn: sqlite3.Connection,
    team_abbrev: str,
    game_date: str,
) -> dict[str, str]:
    """
    Get injury statuses for a team on a given date.
    Returns dict mapping player_name -> status (OUT, DOUBTFUL, QUESTIONABLE, PROBABLE)
    """
    from ..standings import _team_ids_by_abbrev
    
    team_abbrev = normalize_team_abbrev(team_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(team_abbrev, [])
    
    if not team_ids:
        return {}
    
    placeholders = ",".join(["?"] * len(team_ids))
    
    rows = conn.execute(
        f"""
        SELECT ir.player_name, ir.status, p.name as matched_name
        FROM injury_report ir
        LEFT JOIN players p ON p.id = ir.player_id
        WHERE ir.team_id IN ({placeholders})
          AND ir.game_date = ?
        """,
        (*team_ids, game_date),
    ).fetchall()
    
    result = {}
    for row in rows:
        name = row["matched_name"] or row["player_name"]
        if name:
            result[name] = row["status"]
    
    return result


def _is_player_available(injury_status: Optional[str]) -> bool:
    """Check if a player is likely to play based on injury status."""
    if not injury_status:
        return True
    status = injury_status.upper()
    # OUT and DOUBTFUL players are likely not playing
    return status not in ("OUT", "DOUBTFUL")


# ============================================================================
# Comprehensive Matchup Report Generation (MAIN ADVISOR FUNCTION)
# ============================================================================

def generate_comprehensive_matchup_report(
    conn: sqlite3.Connection,
    away_abbrev: str,
    home_abbrev: str,
    game_date: str,
    spread: Optional[float] = None,
    over_under: Optional[float] = None,
    stars_only: bool = False,
) -> ComprehensiveMatchupReport:
    """
    Generate a full matchup analysis report with actionable betting recommendations.
    
    This is the MAIN ADVISOR FUNCTION that transforms raw statistical projections
    into structured recommendations with confidence scores.
    
    Args:
        conn: Database connection
        away_abbrev: Away team abbreviation (e.g., "LAL")
        home_abbrev: Home team abbreviation (e.g., "BOS")
        game_date: Date of the game (YYYY-MM-DD format)
        spread: Point spread for the game (negative = home favored)
        over_under: Total points over/under line
        stars_only: If True, prioritize star players but still allow non-stars with high confidence
    
    Returns:
        ComprehensiveMatchupReport containing:
        - Team context (B2B status, rest days, spread info)
        - Defense profiles for both teams by position
        - Player projections with adjustments
        - best_over_plays: List of recommended OVER bets
        - best_under_plays: List of recommended UNDER bets
        - avoid_players: Players to avoid betting on
        - key_matchups: Important storylines for the game
    
    Example:
        report = generate_comprehensive_matchup_report(
            conn, "LAL", "BOS", "2026-01-03", spread=-3.5, over_under=220.5
        )
        
        # Access best plays
        for play in report.best_over_plays[:5]:
            print(f"{play.player_name} {play.prop_type}: {play.confidence_tier}")
            for reason in play.reasons:
                print(f"  - {reason}")
    """
    
    # 1. Get Context (B2B, Rest)
    away_b2b = get_back_to_back_status(conn, away_abbrev, game_date)
    home_b2b = get_back_to_back_status(conn, home_abbrev, game_date)
    
    is_close_game = spread is not None and abs(spread) <= 6.5
    
    # 1b. Get Injury Reports for both teams
    away_injuries = _get_team_injury_report(conn, away_abbrev, game_date)
    home_injuries = _get_team_injury_report(conn, home_abbrev, game_date)
    
    # 2. Get Defense Profiles
    away_def_g = get_position_defense_profile(conn, away_abbrev, "G")
    away_def_f = get_position_defense_profile(conn, away_abbrev, "F")
    away_def_c = get_position_defense_profile(conn, away_abbrev, "C")
    
    home_def_g = get_position_defense_profile(conn, home_abbrev, "G")
    home_def_f = get_position_defense_profile(conn, home_abbrev, "F")
    home_def_c = get_position_defense_profile(conn, home_abbrev, "C")
    
    # 3. Project Players
    config = ProjectionConfig(
        use_position_defense=True,
        use_archetype_adjustments=True,
        top_n_players=10  # Target top 10 as requested
    )
    
    # Project Away players (vs Home defense)
    away_projections = project_team_players(
        conn, away_abbrev, config, 
        opponent_abbrev=home_abbrev,
        is_back_to_back=away_b2b.is_back_to_back,
        rest_days=away_b2b.rest_days
    )
    
    # Project Home players (vs Away defense)
    home_projections = project_team_players(
        conn, home_abbrev, config,
        opponent_abbrev=away_abbrev,
        is_back_to_back=home_b2b.is_back_to_back,
        rest_days=home_b2b.rest_days
    )
    
    # 4. Identify Edges - This is the ADVISOR logic
    best_over = []
    best_under = []
    avoid_players = []
    
    # High confidence threshold for allowing non-star players
    NON_STAR_CONFIDENCE_THRESHOLD = 70  # Only allow non-stars with very high confidence
    
    def process_projections(projections, team_abbrev, opponent_abbrev, opp_def_g, opp_def_f, opp_def_c, team_injuries):
        """
        Process player projections to find betting edges.
        
        This helper function:
        1. Filters out injured (OUT/DOUBTFUL) players
        2. Checks for elite defender warnings
        3. Identifies defensive matchup advantages/disadvantages based on opponent defense profiles
        4. Calculates MatchupEdge objects for significant factors
        5. Applies star player filtering (prioritizes stars, allows exceptional non-star picks)
        """
        # Get team's full name for star player lookup
        from ..team_aliases import team_name_from_abbrev
        team_full_name = team_name_from_abbrev(team_abbrev)
        
        for p in projections:
            # Check injury status - skip OUT/DOUBTFUL players entirely
            injury_status = team_injuries.get(p.player_name)
            if injury_status and injury_status.upper() in ("OUT", "DOUBTFUL"):
                avoid_players.append({
                    "player": p.player_name,
                    "team": team_abbrev,
                    "warnings": [f"⚠️ {injury_status.upper()} - Do not bet on this player"]
                })
                continue  # Skip to next player
            
            # Skip if minutes are too low
            if p.proj_minutes < 15:
                continue
            
            # Check star player status
            player_is_star = is_star_player(conn, p.player_name)
            
            # Determine the player's position defense profile
            pos = (p.position or "G").upper()[:1]
            if pos == "G":
                pos_def = opp_def_g
            elif pos == "F":
                pos_def = opp_def_f
            else:
                pos_def = opp_def_c
                
            # Check for avoid conditions
            warnings = []
            
            # Add warning for questionable players
            if injury_status and injury_status.upper() == "QUESTIONABLE":
                warnings.append(f"⚠️ QUESTIONABLE - Check status before betting")
            
            if "elite_defender" in p.adjustments:
                warnings.append(f"Guarded by elite defender ({', '.join(p.adjustments.get('elite_defender_names', []))})")
            
            if pos_def and pos_def.pts_rating in ("elite", "good"):
                warnings.append(f"Opponent has {pos_def.pts_rating} defense vs {pos}s")
                
            if warnings:
                avoid_players.append({
                    "player": p.player_name,
                    "team": team_abbrev,
                    "warnings": warnings
                })
            
            # Calculate Edges using robust logic
            for stat in ["PTS", "REB", "AST"]:
                baseline = getattr(p, f"proj_{stat.lower()}")
                
                # We skip back_to_back and elite_defender because they are already applied
                # in the projection generation phase ("Project Players" step above).
                # We let calculate_matchup_edge handle Position Defense, History, Trends, Close Game.
                edge = calculate_matchup_edge(
                    conn=conn,
                    player_id=p.player_id,
                    player_name=p.player_name,
                    team_abbrev=team_abbrev,
                    opponent_abbrev=opponent_abbrev,
                    prop_type=stat,
                    baseline_value=baseline,
                    is_b2b=False, # Handled by projector
                    rest_days=0,  # Handled by projector
                    spread=spread,
                    over_under=over_under,
                    skip_factors=["back_to_back", "elite_defender"],
                    override_pos_defense=pos_def
                )
                
                # Track bad matchup conditions for explanation
                has_elite_defender = "elite_defender" in p.adjustments and stat == "PTS"
                has_elite_defense = pos_def and pos_def.pts_rating in ("elite", "good") and stat == "PTS"
                is_bad_matchup = has_elite_defender or has_elite_defense
                
                # Add warnings from projector context (like elite defender)
                if has_elite_defender:
                    msg = f"Guarded by elite defender ({', '.join(p.adjustments.get('elite_defender_names', []))})"
                    if msg not in edge.warnings:
                        edge.warnings.append(msg)
                
                # Add star player status to reasons
                edge.is_star_player = player_is_star
                
                # Star player filtering logic:
                # - Star players: Include with normal confidence threshold (55+)
                # - Non-star players: Only include with very high confidence (70+) and add explanation
                # - Bad matchups: Still include with explanation if confidence is high enough
                if edge.direction != "PASS" and edge.confidence_score >= 55:
                    # Handle bad matchup explanation
                    if is_bad_matchup and edge.direction == "OVER":
                        # Bad matchup for OVER pick - add explanation if still being included
                        if has_elite_defender:
                            edge.reasons.append(f"⚠️ Bad matchup vs elite defender BUT strong value (conf: {edge.confidence_score:.0f}%)")
                        elif has_elite_defense:
                            edge.reasons.append(f"⚠️ Facing {pos_def.pts_rating} defense BUT player advantage outweighs")
                    
                    if player_is_star:
                        # Star player - always include if passes normal threshold
                        edge.reasons.insert(0, "⭐ Star player target")
                        if edge.direction == "OVER":
                            best_over.append(edge)
                        elif edge.direction == "UNDER":
                            best_under.append(edge)
                    elif not stars_only or edge.confidence_score >= NON_STAR_CONFIDENCE_THRESHOLD:
                        # Non-star player with exceptional confidence
                        if edge.confidence_score >= NON_STAR_CONFIDENCE_THRESHOLD:
                            edge.reasons.insert(0, f"🔥 High-value non-star pick (confidence: {edge.confidence_score:.0f}%)")
                        if edge.direction == "OVER":
                            best_over.append(edge)
                        elif edge.direction == "UNDER":
                            best_under.append(edge)

    # Process both teams
    # Away players face Home defense, use away_injuries to filter
    process_projections(away_projections, away_abbrev, home_abbrev, home_def_g, home_def_f, home_def_c, away_injuries)
    # Home players face Away defense, use home_injuries to filter
    process_projections(home_projections, home_abbrev, away_abbrev, away_def_g, away_def_f, away_def_c, home_injuries)
    
    # Sort edges: Prioritize star players first, then by confidence score
    def edge_sort_key(e):
        star_priority = 0 if getattr(e, 'is_star_player', False) else 1
        return (star_priority, -e.confidence_score, -abs(e.adjustment_pct))
    
    best_over.sort(key=edge_sort_key)
    best_under.sort(key=edge_sort_key)
    
    # 5. Generate Key Matchups / Storylines
    key_matchups = []
    
    if is_close_game:
        key_matchups.append("🎯 Close game expected - Starters should play full minutes")
    if away_b2b.is_back_to_back:
        key_matchups.append(f"⚠️ {away_abbrev} on B2B - Watch for fatigue (-6% typical)")
    if home_b2b.is_back_to_back:
        key_matchups.append(f"⚠️ {home_abbrev} on B2B - Watch for fatigue (-6% typical)")
    if away_b2b.rest_days >= 3:
        key_matchups.append(f"✅ {away_abbrev} well rested ({away_b2b.rest_days} days off)")
    if home_b2b.rest_days >= 3:
        key_matchups.append(f"✅ {home_abbrev} well rested ({home_b2b.rest_days} days off)")
    
    # Add defensive weakness storylines
    if home_def_g and home_def_g.pts_rating in ("poor", "weak"):
        key_matchups.append(f"📈 {away_abbrev} guards advantage: {home_abbrev} weak vs guards")
    if home_def_f and home_def_f.pts_rating in ("poor", "weak"):
        key_matchups.append(f"📈 {away_abbrev} forwards advantage: {home_abbrev} weak vs forwards")
    if home_def_c and home_def_c.pts_rating in ("poor", "weak"):
        key_matchups.append(f"📈 {away_abbrev} centers advantage: {home_abbrev} weak vs centers")
    if away_def_g and away_def_g.pts_rating in ("poor", "weak"):
        key_matchups.append(f"📈 {home_abbrev} guards advantage: {away_abbrev} weak vs guards")
    if away_def_f and away_def_f.pts_rating in ("poor", "weak"):
        key_matchups.append(f"📈 {home_abbrev} forwards advantage: {away_abbrev} weak vs forwards")
    if away_def_c and away_def_c.pts_rating in ("poor", "weak"):
        key_matchups.append(f"📈 {home_abbrev} centers advantage: {away_abbrev} weak vs centers")
    
    # Add injury storylines
    away_out_players = [name for name, status in away_injuries.items() if status.upper() == "OUT"]
    home_out_players = [name for name, status in home_injuries.items() if status.upper() == "OUT"]
    
    if away_out_players:
        key_matchups.append(f"🏥 {away_abbrev} missing: {', '.join(away_out_players[:3])}")
    if home_out_players:
        key_matchups.append(f"🏥 {home_abbrev} missing: {', '.join(home_out_players[:3])}")
    
    # 6. Build and return the report
    return ComprehensiveMatchupReport(
        away_abbrev=away_abbrev,
        home_abbrev=home_abbrev,
        game_date=game_date,
        away_b2b=away_b2b.is_back_to_back,
        home_b2b=home_b2b.is_back_to_back,
        away_rest_days=away_b2b.rest_days,
        home_rest_days=home_b2b.rest_days,
        spread=spread,
        over_under=over_under,
        is_close_game=is_close_game,
        away_defense_vs_guards=away_def_g,
        away_defense_vs_forwards=away_def_f,
        away_defense_vs_centers=away_def_c,
        home_defense_vs_guards=home_def_g,
        home_defense_vs_forwards=home_def_f,
        home_defense_vs_centers=home_def_c,
        away_player_projections=[vars(p) for p in away_projections],
        home_player_projections=[vars(p) for p in home_projections],
        best_over_plays=best_over,
        best_under_plays=best_under,
        avoid_players=avoid_players,
        key_matchups=key_matchups
    )

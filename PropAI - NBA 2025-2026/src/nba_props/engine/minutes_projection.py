"""
Minutes-First Projection Module
===============================

Minutes are the strongest predictor of counting stats. This module implements
a minutes-first projection approach where:

1. Project minutes based on recent performance, context, and matchup
2. Calculate per-minute rates for each stat
3. Multiply to get final projections

Key Features:
- B2B and rest day adjustments
- Blowout risk based on spread
- Teammate injury boost
- Player status (questionable, returning from injury)
- Minutes variance tracking

Module Author: NBA Props Team
Last Updated: January 2026
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from ..team_aliases import normalize_team_abbrev


# ============================================================================
# Constants
# ============================================================================

# Adjustment factors
B2B_MINUTES_FACTOR = 0.94  # 6% reduction on back-to-backs
REST_ADVANTAGE_FACTOR = 1.02  # 2% boost with 3+ days rest
HEAVY_FAVORITE_FACTOR = 0.92  # 8% reduction when spread > 12
MODERATE_FAVORITE_FACTOR = 0.96  # 4% reduction when spread > 8

# Injury-related
MAX_INJURY_BOOST_MINUTES = 6  # Cap on minutes boost from injuries
MINUTES_PER_INJURED_STAR = 2  # Minutes boost per injured star

# Status adjustments
QUESTIONABLE_FACTOR = 0.90  # 10% reduction
RETURNING_FACTOR = 0.85  # 15% reduction (minutes restriction)

# Sample size thresholds
MIN_GAMES_REQUIRED = 5
GOOD_SAMPLE_SIZE = 20
MARGINAL_SAMPLE_SIZE = 10

# Variance thresholds
LOW_VARIANCE_THRESHOLD = 25  # Variance below this = high confidence
MINIMUM_STD_FLOOR_PCT = 0.10  # 10% of projection as minimum std


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MinutesProjection:
    """Projected minutes with context and confidence."""
    base_minutes: float  # Baseline from recent games
    adjusted_minutes: float  # After all adjustments
    minutes_std: float  # Standard deviation
    confidence: str  # "HIGH", "MEDIUM", "LOW", "NONE"
    
    # What adjustments were applied
    adjustments_applied: Dict[str, float] = field(default_factory=dict)
    
    # Warnings
    warnings: List[str] = field(default_factory=list)


@dataclass
class PerMinuteRates:
    """Per-minute production rates for a player."""
    pts_rate: float  # Points per minute
    reb_rate: float  # Rebounds per minute
    ast_rate: float  # Assists per minute
    
    pts_std: float  # Standard deviation of pts rate
    reb_std: float  # Standard deviation of reb rate
    ast_std: float  # Standard deviation of ast rate
    
    games_used: int
    data_quality: str  # "good", "limited", "marginal"


@dataclass
class FullStatProjection:
    """Complete stat projection using minutes-first approach."""
    player_id: int
    player_name: str
    team_abbrev: str
    
    # Minutes projection
    minutes: MinutesProjection
    
    # Stat projections
    pts: float
    reb: float
    ast: float
    
    # Standard deviations (combined from minutes and rate uncertainty)
    pts_std: float
    reb_std: float
    ast_std: float
    
    # Per-minute rates (for analysis)
    pts_per_min: float
    reb_per_min: float
    ast_per_min: float
    
    # Defense factors applied
    defense_factors: Dict[str, float] = field(default_factory=dict)
    
    # Overall confidence
    confidence: str = "MEDIUM"
    data_quality: str = "good"
    games_used: int = 0
    
    # Warnings
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# Minutes Projection
# ============================================================================

def project_minutes(
    player_games: List[Dict],
    is_back_to_back: bool = False,
    rest_days: int = 1,
    spread: float = 0.0,
    teammate_injuries: Optional[List[str]] = None,
    player_status: str = "healthy",  # "healthy", "questionable", "returning"
) -> MinutesProjection:
    """
    Project minutes for upcoming game.
    
    This is the foundation of all projections - minutes drive everything.
    
    Args:
        player_games: Recent game data with 'minutes' field (most recent first)
        is_back_to_back: True if second game of B2B
        rest_days: Days since last game
        spread: Game spread (negative = underdog, positive = favorite)
        teammate_injuries: List of injured teammate names (stars)
        player_status: Player's health status
    
    Returns:
        MinutesProjection with adjusted minutes and confidence
    """
    teammate_injuries = teammate_injuries or []
    warnings = []
    adjustments = {}
    
    # Handle empty or insufficient data
    if not player_games:
        return MinutesProjection(
            base_minutes=0.0,
            adjusted_minutes=0.0,
            minutes_std=0.0,
            confidence="NONE",
            adjustments_applied={"error": "No games data"},
            warnings=["No game data available"]
        )
    
    # Extract minutes values
    recent_mins = [g.get('minutes', 0) for g in player_games[:15]]
    
    if not recent_mins or all(m == 0 for m in recent_mins):
        return MinutesProjection(
            base_minutes=0.0,
            adjusted_minutes=0.0,
            minutes_std=0.0,
            confidence="NONE",
            adjustments_applied={"error": "No minutes data"},
            warnings=["No minutes data in game logs"]
        )
    
    # Weight recent games more heavily (exponential decay)
    # Weights for up to 15 games: [0.15, 0.13, 0.12, 0.11, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.02, 0.01, 0.01, ...]
    n = len(recent_mins)
    weights = []
    for i in range(n):
        if i < 5:
            weights.append(0.15 - i * 0.01)
        elif i < 10:
            weights.append(0.10 - (i - 5) * 0.01)
        else:
            weights.append(0.02 - min((i - 10) * 0.005, 0.015))
    
    total_weight = sum(weights)
    base_minutes = sum(m * w for m, w in zip(recent_mins, weights)) / total_weight
    adjusted_minutes = base_minutes
    
    # Calculate variance for std dev
    variance = _calculate_variance(recent_mins[:10])
    minutes_std = math.sqrt(variance) if variance > 0 else base_minutes * 0.1
    
    # =========================================================================
    # Apply Adjustments
    # =========================================================================
    
    # 1. Back-to-back adjustment
    if is_back_to_back:
        adjusted_minutes *= B2B_MINUTES_FACTOR
        adjustments["b2b"] = round((B2B_MINUTES_FACTOR - 1) * 100, 1)
        warnings.append("Back-to-back game: -6% minutes expected")
    
    # 2. Rest advantage
    if rest_days >= 3:
        adjusted_minutes *= REST_ADVANTAGE_FACTOR
        adjustments["rest_advantage"] = round((REST_ADVANTAGE_FACTOR - 1) * 100, 1)
    
    # 3. Blowout risk (spread-based)
    abs_spread = abs(spread)
    if abs_spread > 12:
        # Big favorite/underdog = potential blowout = bench time
        adjusted_minutes *= HEAVY_FAVORITE_FACTOR
        adjustments["blowout_risk"] = round((HEAVY_FAVORITE_FACTOR - 1) * 100, 1)
        warnings.append(f"Large spread ({spread:+.1f}): increased blowout risk")
    elif abs_spread > 8:
        adjusted_minutes *= MODERATE_FAVORITE_FACTOR
        adjustments["blowout_risk"] = round((MODERATE_FAVORITE_FACTOR - 1) * 100, 1)
    
    # 4. Injury boost (if teammate is out, might play more)
    if teammate_injuries:
        injury_boost = min(len(teammate_injuries) * MINUTES_PER_INJURED_STAR, MAX_INJURY_BOOST_MINUTES)
        adjusted_minutes += injury_boost
        adjustments["teammate_injuries"] = injury_boost
        warnings.append(f"Teammate(s) out: +{injury_boost:.1f} minutes expected")
    
    # 5. Player status
    if player_status == "questionable":
        adjusted_minutes *= QUESTIONABLE_FACTOR
        adjustments["questionable_status"] = round((QUESTIONABLE_FACTOR - 1) * 100, 1)
        warnings.append("Player questionable: may be limited")
    elif player_status == "returning":
        adjusted_minutes *= RETURNING_FACTOR
        adjustments["returning_from_injury"] = round((RETURNING_FACTOR - 1) * 100, 1)
        warnings.append("Returning from injury: likely minutes restriction")
    
    # =========================================================================
    # Determine Confidence
    # =========================================================================
    games_count = len(player_games)
    
    if games_count >= GOOD_SAMPLE_SIZE and variance < LOW_VARIANCE_THRESHOLD:
        confidence = "HIGH"
    elif games_count >= MARGINAL_SAMPLE_SIZE:
        confidence = "MEDIUM"
    elif games_count >= MIN_GAMES_REQUIRED:
        confidence = "LOW"
    else:
        confidence = "NONE"
        warnings.append(f"Limited sample size: only {games_count} games")
    
    # Apply minimum std floor
    min_std = adjusted_minutes * MINIMUM_STD_FLOOR_PCT
    minutes_std = max(minutes_std, min_std)
    
    return MinutesProjection(
        base_minutes=round(base_minutes, 1),
        adjusted_minutes=round(adjusted_minutes, 1),
        minutes_std=round(minutes_std, 2),
        confidence=confidence,
        adjustments_applied=adjustments,
        warnings=warnings
    )


# ============================================================================
# Per-Minute Rate Calculation
# ============================================================================

def calculate_per_minute_rates(
    player_games: List[Dict],
    min_minutes_threshold: int = 5
) -> Optional[PerMinuteRates]:
    """
    Calculate per-minute production rates.
    
    Args:
        player_games: Recent game logs with pts, reb, ast, minutes
        min_minutes_threshold: Minimum minutes to include a game
    
    Returns:
        PerMinuteRates or None if insufficient data
    """
    if not player_games:
        return None
    
    # Filter games where player actually played meaningful minutes
    valid_games = [g for g in player_games if g.get('minutes', 0) >= min_minutes_threshold]
    
    if len(valid_games) < MIN_GAMES_REQUIRED:
        return None
    
    # Calculate rates for each game
    pts_rates = []
    reb_rates = []
    ast_rates = []
    
    for g in valid_games:
        mins = g.get('minutes', 0)
        if mins > 0:
            pts_rates.append((g.get('pts', 0) or 0) / mins)
            reb_rates.append((g.get('reb', 0) or 0) / mins)
            ast_rates.append((g.get('ast', 0) or 0) / mins)
    
    if not pts_rates:
        return None
    
    # Calculate mean and std for each rate
    pts_mean = sum(pts_rates) / len(pts_rates)
    reb_mean = sum(reb_rates) / len(reb_rates)
    ast_mean = sum(ast_rates) / len(ast_rates)
    
    pts_std = _calculate_std(pts_rates)
    reb_std = _calculate_std(reb_rates)
    ast_std = _calculate_std(ast_rates)
    
    # Determine data quality
    n = len(valid_games)
    if n >= GOOD_SAMPLE_SIZE:
        data_quality = "good"
    elif n >= MARGINAL_SAMPLE_SIZE:
        data_quality = "limited"
    else:
        data_quality = "marginal"
    
    return PerMinuteRates(
        pts_rate=round(pts_mean, 4),
        reb_rate=round(reb_mean, 4),
        ast_rate=round(ast_mean, 4),
        pts_std=round(pts_std, 4),
        reb_std=round(reb_std, 4),
        ast_std=round(ast_std, 4),
        games_used=n,
        data_quality=data_quality
    )


# ============================================================================
# Full Stat Projection
# ============================================================================

def project_full_stat_line(
    player_id: int,
    player_name: str,
    team_abbrev: str,
    player_games: List[Dict],
    game_context: Dict,
) -> Optional[FullStatProjection]:
    """
    Full stat projection using minutes-first approach.
    
    Args:
        player_id: Player ID
        player_name: Player name
        team_abbrev: Team abbreviation
        player_games: Recent game history
        game_context: Dictionary with:
            - is_b2b: bool
            - rest_days: int
            - spread: float
            - teammate_injuries: List[str]
            - player_status: str
            - defense_factors: {"pts": 1.05, "reb": 0.95, "ast": 1.02}
    
    Returns:
        FullStatProjection or None if insufficient data
    """
    if len(player_games) < MIN_GAMES_REQUIRED:
        return None
    
    # Step 1: Project minutes
    mins_proj = project_minutes(
        player_games=player_games,
        is_back_to_back=game_context.get("is_b2b", False),
        rest_days=game_context.get("rest_days", 1),
        spread=game_context.get("spread", 0.0),
        teammate_injuries=game_context.get("teammate_injuries", []),
        player_status=game_context.get("player_status", "healthy")
    )
    
    if mins_proj.adjusted_minutes == 0 or mins_proj.confidence == "NONE":
        return None
    
    # Step 2: Get per-minute rates
    per_min = calculate_per_minute_rates(player_games)
    
    if per_min is None:
        return None
    
    # Step 3: Project stats = rate * minutes
    defense_factors = game_context.get("defense_factors", {})
    warnings = list(mins_proj.warnings)
    
    # Base projections
    base_pts = per_min.pts_rate * mins_proj.adjusted_minutes
    base_reb = per_min.reb_rate * mins_proj.adjusted_minutes
    base_ast = per_min.ast_rate * mins_proj.adjusted_minutes
    
    # Apply defense factors
    pts_def_factor = defense_factors.get("pts", 1.0)
    reb_def_factor = defense_factors.get("reb", 1.0)
    ast_def_factor = defense_factors.get("ast", 1.0)
    
    final_pts = base_pts * pts_def_factor
    final_reb = base_reb * reb_def_factor
    final_ast = base_ast * ast_def_factor
    
    # Calculate combined standard deviations
    # Using error propagation: std(rate * mins) ≈ sqrt((mins*rate_std)² + (rate*mins_std)²)
    pts_std = _combine_uncertainty(
        mins_proj.adjusted_minutes, per_min.pts_std,
        per_min.pts_rate, mins_proj.minutes_std
    )
    reb_std = _combine_uncertainty(
        mins_proj.adjusted_minutes, per_min.reb_std,
        per_min.reb_rate, mins_proj.minutes_std
    )
    ast_std = _combine_uncertainty(
        mins_proj.adjusted_minutes, per_min.ast_std,
        per_min.ast_rate, mins_proj.minutes_std
    )
    
    # Apply minimum std floor (15% of projection)
    pts_std = max(pts_std, final_pts * 0.15)
    reb_std = max(reb_std, final_reb * 0.15)
    ast_std = max(ast_std, final_ast * 0.15)
    
    # Add defense factor warnings
    for stat, factor in [("pts", pts_def_factor), ("reb", reb_def_factor), ("ast", ast_def_factor)]:
        if factor > 1.08:
            warnings.append(f"Weak defense vs {stat.upper()}: +{(factor-1)*100:.0f}%")
        elif factor < 0.92:
            warnings.append(f"Strong defense vs {stat.upper()}: {(factor-1)*100:.0f}%")
    
    # Determine overall confidence
    if mins_proj.confidence == "HIGH" and per_min.data_quality == "good":
        confidence = "HIGH"
    elif mins_proj.confidence in ("HIGH", "MEDIUM") and per_min.data_quality in ("good", "limited"):
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    
    return FullStatProjection(
        player_id=player_id,
        player_name=player_name,
        team_abbrev=team_abbrev,
        minutes=mins_proj,
        pts=round(final_pts, 1),
        reb=round(final_reb, 1),
        ast=round(final_ast, 1),
        pts_std=round(pts_std, 2),
        reb_std=round(reb_std, 2),
        ast_std=round(ast_std, 2),
        pts_per_min=per_min.pts_rate,
        reb_per_min=per_min.reb_rate,
        ast_per_min=per_min.ast_rate,
        defense_factors=defense_factors,
        confidence=confidence,
        data_quality=per_min.data_quality,
        games_used=per_min.games_used,
        warnings=warnings
    )


# ============================================================================
# Database Integration
# ============================================================================

def project_player_minutes_first(
    conn: sqlite3.Connection,
    player_id: int,
    game_context: Dict,
    games_lookback: int = 15,
) -> Optional[FullStatProjection]:
    """
    Project player stats using minutes-first approach from database.
    
    Args:
        conn: Database connection
        player_id: Player ID
        game_context: Game context dictionary
        games_lookback: Number of games to look back
    
    Returns:
        FullStatProjection or None if insufficient data
    """
    # Get player info
    player_row = conn.execute(
        "SELECT id, name FROM players WHERE id = ?", (player_id,)
    ).fetchone()
    
    if not player_row:
        return None
    
    player_name = player_row["name"]
    
    # Get recent game logs
    logs = conn.execute(
        """
        SELECT 
            g.game_date,
            b.minutes, b.pts, b.reb, b.ast,
            t.name as team_name
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        JOIN teams t ON t.id = b.team_id
        WHERE b.player_id = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 0
        ORDER BY g.game_date DESC
        LIMIT ?
        """,
        (player_id, games_lookback),
    ).fetchall()
    
    if not logs:
        return None
    
    player_games = [dict(r) for r in logs]
    
    # Get team abbreviation
    from ..team_aliases import abbrev_from_team_name
    team_name = player_games[0].get("team_name", "") if player_games else ""
    team_abbrev = abbrev_from_team_name(team_name) or ""
    
    return project_full_stat_line(
        player_id=player_id,
        player_name=player_name,
        team_abbrev=team_abbrev,
        player_games=player_games,
        game_context=game_context
    )


# ============================================================================
# Helper Functions
# ============================================================================

def _calculate_variance(values: List[float]) -> float:
    """Calculate variance of a list."""
    if not values or len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def _calculate_std(values: List[float]) -> float:
    """Calculate standard deviation of a list."""
    return math.sqrt(_calculate_variance(values))


def _combine_uncertainty(
    value1: float, std1: float,
    value2: float, std2: float
) -> float:
    """
    Combine uncertainties for multiplication: std(a*b).
    
    Using first-order error propagation:
    std(a*b) ≈ sqrt((b*std_a)² + (a*std_b)²)
    """
    term1 = (value2 * std1) ** 2
    term2 = (value1 * std2) ** 2
    return math.sqrt(term1 + term2)

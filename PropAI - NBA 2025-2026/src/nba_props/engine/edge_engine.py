"""
The Edge Engine - Main Orchestrator
====================================

This is the main entry point for the NBA Props prediction system.
It orchestrates all layers of the model:

1. Data Validation Layer - Check data freshness and quality
2. Minutes Projection Layer - Project playing time
3. Per-Minute Rate Layer - Calculate production rates
4. Matchup Adjustment Layer - Apply defense and context factors
5. Probability & Edge Layer - Calculate betting edges
6. Recommendation Filter Layer - Filter and rank picks

Model Name: "The Edge Engine"

Module Author: NBA Props Team
Last Updated: January 2026
"""
from __future__ import annotations

import sqlite3
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

from ..paths import get_paths
from ..team_aliases import normalize_team_abbrev, abbrev_from_team_name


# ============================================================================
# Constants
# ============================================================================

# Thresholds
MIN_EDGE_THRESHOLD = 0.06  # 6% minimum edge to recommend
MIN_PROBABILITY = 0.55  # 55% minimum probability
MIN_GAMES_REQUIRED = 5  # Minimum games for projection
MAX_PICKS_PER_SLATE = 8  # Maximum picks to recommend per day

# Confidence thresholds
HIGH_CONFIDENCE_EDGE = 0.12  # 12%+ edge
MEDIUM_CONFIDENCE_EDGE = 0.08  # 8%+ edge

# Data freshness (in days)
MAX_DEFENSE_DATA_AGE = 14  # Defense data older than 14 days is stale


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class DataQualityReport:
    """Report on data quality and freshness."""
    is_valid: bool
    player_games_available: int
    defense_data_fresh: bool
    defense_data_age_days: int
    has_b2b_detection: bool
    warnings: List[str] = field(default_factory=list)
    

@dataclass
class EdgeResult:
    """Result of edge calculation for a single prop."""
    player_id: int
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    
    # Prop details
    prop_type: str  # PTS, REB, AST
    direction: str  # OVER, UNDER
    line: float
    
    # Projection
    projected_value: float
    projected_std: float
    
    # Edge calculations
    probability: float  # P(over) or P(under)
    edge_pct: float  # Edge as percentage
    z_score: float
    
    # Confidence
    confidence_tier: str  # HIGH, MEDIUM, LOW
    confidence_score: float  # 0-100
    
    # Actionability
    is_actionable: bool
    
    # Context
    games_sample: int
    data_quality: str
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Factors used
    factors: Dict[str, float] = field(default_factory=dict)


@dataclass
class SlateRecommendation:
    """Full slate of recommended picks."""
    game_date: str
    generated_at: str
    
    # Summary
    total_edges_analyzed: int
    picks_recommended: int
    
    # Picks by confidence
    high_confidence_picks: List[EdgeResult] = field(default_factory=list)
    medium_confidence_picks: List[EdgeResult] = field(default_factory=list)
    low_confidence_picks: List[EdgeResult] = field(default_factory=list)
    
    # All picks (sorted by edge)
    all_picks: List[EdgeResult] = field(default_factory=list)
    
    # Data quality warnings
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# Layer 1: Data Validation
# ============================================================================

def validate_data_quality(
    conn: sqlite3.Connection,
    player_id: int,
    opponent_abbrev: str,
    game_date: str,
) -> DataQualityReport:
    """
    Validate data quality before making projections.
    
    Checks:
    - Player has enough games for reliable projection
    - Defense data is fresh
    - B2B detection is possible
    """
    warnings = []
    
    # Check player games
    row = conn.execute("""
        SELECT COUNT(*) as games
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.player_id = ?
          AND b.minutes > 0
    """, (player_id,)).fetchone()
    
    games_available = row["games"] if row else 0
    
    if games_available < MIN_GAMES_REQUIRED:
        warnings.append(f"Only {games_available} games available (need {MIN_GAMES_REQUIRED})")
    
    # Check defense data freshness
    opponent_abbrev = normalize_team_abbrev(opponent_abbrev)
    defense_fresh = False
    defense_age = 999
    
    # Get most recent game for opponent
    from ..standings import _team_ids_by_abbrev
    team_ids_map = _team_ids_by_abbrev(conn)
    opponent_ids = team_ids_map.get(opponent_abbrev, [])
    
    if opponent_ids:
        placeholders = ",".join(["?"] * len(opponent_ids))
        row = conn.execute(f"""
            SELECT MAX(g.game_date) as last_game
            FROM games g
            WHERE g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders})
        """, (*opponent_ids, *opponent_ids)).fetchone()
        
        if row and row["last_game"]:
            try:
                last_game_dt = datetime.strptime(row["last_game"], "%Y-%m-%d")
                game_dt = datetime.strptime(game_date, "%Y-%m-%d")
                defense_age = (game_dt - last_game_dt).days
                defense_fresh = defense_age <= MAX_DEFENSE_DATA_AGE
            except ValueError:
                warnings.append("Could not parse game dates for defense freshness")
    
    if not defense_fresh:
        warnings.append(f"Defense data is {defense_age} days old (max {MAX_DEFENSE_DATA_AGE})")
    
    # Check B2B detection capability
    has_b2b = True
    try:
        from .game_context import get_back_to_back_status
        # Just checking if we can import it
    except ImportError:
        has_b2b = False
        warnings.append("B2B detection module not available")
    
    return DataQualityReport(
        is_valid=games_available >= MIN_GAMES_REQUIRED,
        player_games_available=games_available,
        defense_data_fresh=defense_fresh,
        defense_data_age_days=defense_age,
        has_b2b_detection=has_b2b,
        warnings=warnings
    )


# ============================================================================
# Layer 2-3: Minutes & Rate Projection
# ============================================================================

def get_projection_with_context(
    conn: sqlite3.Connection,
    player_id: int,
    opponent_abbrev: str,
    game_date: str,
    spread: float = 0.0,
    injured_teammates: Optional[List[str]] = None,
) -> Optional[Dict]:
    """
    Get full projection with all context applied.
    
    Uses minutes-first approach from minutes_projection module.
    """
    from .game_context import get_back_to_back_status
    from .minutes_projection import project_player_minutes_first
    
    # Build game context
    game_context = {
        "is_b2b": False,
        "rest_days": 1,
        "spread": spread,
        "teammate_injuries": injured_teammates or [],
        "player_status": "healthy",
        "defense_factors": {"pts": 1.0, "reb": 1.0, "ast": 1.0}
    }
    
    # Get player's team
    row = conn.execute("""
        SELECT t.name as team_name
        FROM boxscore_player b
        JOIN teams t ON t.id = b.team_id
        JOIN players p ON p.id = b.player_id
        WHERE b.player_id = ?
          AND b.minutes > 0
        ORDER BY b.game_id DESC
        LIMIT 1
    """, (player_id,)).fetchone()
    
    if row:
        team_name = row["team_name"]
        team_abbrev = abbrev_from_team_name(team_name) or ""
        
        # Get B2B status
        b2b_status = get_back_to_back_status(conn, team_abbrev, game_date)
        game_context["is_b2b"] = b2b_status.is_back_to_back
        game_context["rest_days"] = b2b_status.rest_days
    
    # Get defense factors
    defense_factors = _get_defense_factors(conn, player_id, opponent_abbrev)
    game_context["defense_factors"] = defense_factors
    
    # Get projection using minutes-first approach
    projection = project_player_minutes_first(conn, player_id, game_context)
    
    if projection is None:
        return None
    
    return {
        "player_id": projection.player_id,
        "player_name": projection.player_name,
        "team_abbrev": projection.team_abbrev,
        "pts": projection.pts,
        "reb": projection.reb,
        "ast": projection.ast,
        "pts_std": projection.pts_std,
        "reb_std": projection.reb_std,
        "ast_std": projection.ast_std,
        "minutes": projection.minutes.adjusted_minutes,
        "confidence": projection.confidence,
        "data_quality": projection.data_quality,
        "games_used": projection.games_used,
        "warnings": projection.warnings,
        "defense_factors": defense_factors,
        "game_context": game_context
    }


def _get_defense_factors(
    conn: sqlite3.Connection,
    player_id: int,
    opponent_abbrev: str
) -> Dict[str, float]:
    """Get defense factors for player vs opponent, including archetype adjustments."""
    default_factors = {"pts": 1.0, "reb": 1.0, "ast": 1.0}
    
    # Get player info
    row = conn.execute("""
        SELECT p.name, b.pos FROM boxscore_player b
        JOIN players p ON p.id = b.player_id
        WHERE b.player_id = ? AND b.pos IS NOT NULL AND b.pos != ''
        ORDER BY b.game_id DESC LIMIT 1
    """, (player_id,)).fetchone()
    
    if not row:
        return default_factors
    
    position = row["pos"]
    player_name = row["name"]
    
    # Get base defense factors from position defense
    try:
        from ..ingest.defense_position_parser import calculate_defense_factor
        
        factors = {}
        for stat in ["pts", "reb", "ast"]:
            defense_info = calculate_defense_factor(conn, opponent_abbrev, position, stat)
            if defense_info:
                # Apply dampened adjustment (45% of raw factor)
                raw_factor = defense_info["factor"]
                if raw_factor > 1.02:
                    factors[stat] = 1.0 + (raw_factor - 1.0) * 0.45
                elif raw_factor < 0.98:
                    factors[stat] = 1.0 + (raw_factor - 1.0) * 0.45
                else:
                    factors[stat] = 1.0
            else:
                factors[stat] = 1.0
    except ImportError:
        factors = default_factors.copy()
    
    # Apply archetype-based adjustments
    try:
        from .archetypes import get_player_archetype, get_archetype_matchup_factor
        
        player_arch = get_player_archetype(player_name)
        
        if player_arch:
            # Determine opponent's likely defensive archetype based on team style
            # This is a simplification - ideally would look at specific defender
            opponent_defense_style = _get_team_defense_style(conn, opponent_abbrev)
            
            archetype_factor = get_archetype_matchup_factor(
                player_arch.primary_offensive,
                opponent_defense_style
            )
            
            # Apply archetype factor primarily to points
            if archetype_factor != 1.0:
                factors["pts"] *= archetype_factor
                # Smaller effect on other stats
                factors["ast"] *= 1 + (archetype_factor - 1) * 0.3
    except ImportError:
        pass
    
    return factors


def _get_team_defense_style(conn: sqlite3.Connection, team_abbrev: str) -> str:
    """
    Determine a team's primary defensive style.
    
    Returns one of: "Wing Stopper", "Anchor Big", "Switch Big", "POA Defender", "Chaser"
    """
    from ..team_aliases import normalize_team_abbrev
    team_abbrev = normalize_team_abbrev(team_abbrev)
    
    # Known defensive identities (simplified)
    # In production, this would be calculated from data
    elite_rim_protection = {"CLE", "MIN", "OKC", "BOS", "MIA"}
    switching_teams = {"BOS", "GSW", "MIA", "LAC", "PHO"}
    
    if team_abbrev in elite_rim_protection:
        return "Anchor Big"
    elif team_abbrev in switching_teams:
        return "Switch Big"
    else:
        return "Wing Stopper"


# ============================================================================
# Layer 4-5: Edge Calculation
# ============================================================================

def calculate_edge_for_prop(
    projection: Dict,
    prop_type: str,
    line: float,
    opponent_abbrev: str = "",
) -> EdgeResult:
    """
    Calculate betting edge for a single prop.
    
    Uses improved edge calculation with proper thresholds.
    """
    # Get projection value and std
    stat_key = prop_type.lower()
    proj_value = projection.get(stat_key, 0)
    proj_std = projection.get(f"{stat_key}_std", proj_value * 0.2)
    
    # Ensure minimum std (floor at 15% of value)
    proj_std = max(proj_std, proj_value * 0.15, 1.0)
    
    # Calculate z-score
    z_score = (proj_value - line) / proj_std if proj_std > 0 else 0
    
    # Calculate probabilities
    p_over = _normal_cdf_approx(-z_score)  # P(X > line)
    p_under = 1 - p_over
    
    # Determine direction and edge
    if p_over > p_under:
        direction = "OVER"
        probability = p_over
        edge = 2 * p_over - 1  # For -110 odds
    else:
        direction = "UNDER"
        probability = p_under
        edge = 2 * p_under - 1
    
    edge_pct = edge * 100
    
    # Build reasons
    reasons = []
    warnings = list(projection.get("warnings", []))
    
    # Add defense factor reasoning
    defense_factors = projection.get("defense_factors", {})
    def_factor = defense_factors.get(stat_key, 1.0)
    if def_factor > 1.05:
        reasons.append(f"Weak opponent defense vs {prop_type} ({(def_factor-1)*100:+.0f}%)")
    elif def_factor < 0.95:
        reasons.append(f"Strong opponent defense vs {prop_type} ({(def_factor-1)*100:.0f}%)")
    
    # Add projection reasoning
    diff = proj_value - line
    if abs(diff) > 2:
        reasons.append(f"Projection ({proj_value:.1f}) {'above' if diff > 0 else 'below'} line ({line}) by {abs(diff):.1f}")
    
    # Determine confidence tier
    data_quality = projection.get("data_quality", "limited")
    games_used = projection.get("games_used", 0)
    
    if edge >= HIGH_CONFIDENCE_EDGE and data_quality == "good" and games_used >= 15:
        confidence_tier = "HIGH"
        confidence_score = 80 + min(edge_pct, 20)
    elif edge >= MEDIUM_CONFIDENCE_EDGE and games_used >= 10:
        confidence_tier = "MEDIUM"
        confidence_score = 60 + min(edge_pct, 20)
    elif edge >= MIN_EDGE_THRESHOLD:
        confidence_tier = "LOW"
        confidence_score = 40 + min(edge_pct, 20)
    else:
        confidence_tier = "NONE"
        confidence_score = 20
    
    # Determine actionability
    is_actionable = (
        edge >= MIN_EDGE_THRESHOLD and
        probability >= MIN_PROBABILITY and
        confidence_tier != "NONE" and
        games_used >= MIN_GAMES_REQUIRED
    )
    
    if not is_actionable and edge > 0:
        if edge < MIN_EDGE_THRESHOLD:
            warnings.append(f"Edge ({edge_pct:.1f}%) below threshold ({MIN_EDGE_THRESHOLD*100:.0f}%)")
        if probability < MIN_PROBABILITY:
            warnings.append(f"Probability ({probability:.1%}) below threshold ({MIN_PROBABILITY:.0%})")
        if games_used < MIN_GAMES_REQUIRED:
            warnings.append(f"Insufficient sample size ({games_used} games)")
    
    return EdgeResult(
        player_id=projection.get("player_id", 0),
        player_name=projection.get("player_name", ""),
        team_abbrev=projection.get("team_abbrev", ""),
        opponent_abbrev=opponent_abbrev,
        prop_type=prop_type,
        direction=direction,
        line=line,
        projected_value=round(proj_value, 1),
        projected_std=round(proj_std, 2),
        probability=round(probability, 3),
        edge_pct=round(edge_pct, 1),
        z_score=round(z_score, 2),
        confidence_tier=confidence_tier,
        confidence_score=round(confidence_score, 1),
        is_actionable=is_actionable,
        games_sample=games_used,
        data_quality=data_quality,
        reasons=reasons,
        warnings=warnings,
        factors=defense_factors
    )


def _normal_cdf_approx(z: float) -> float:
    """Approximate normal CDF without scipy."""
    # Abramowitz and Stegun approximation
    a1 =  0.254829592
    a2 = -0.284496736
    a3 =  1.421413741
    a4 = -1.453152027
    a5 =  1.061405429
    p  =  0.3275911
    
    sign = 1 if z >= 0 else -1
    z = abs(z) / math.sqrt(2)
    
    t = 1.0 / (1.0 + p * z)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-z * z)
    
    return 0.5 * (1.0 + sign * y)


# ============================================================================
# Layer 6: Recommendation Filter
# ============================================================================

def filter_and_rank_picks(
    edges: List[EdgeResult],
    max_picks: int = MAX_PICKS_PER_SLATE,
    avoid_correlated: bool = True,
) -> SlateRecommendation:
    """
    Filter and rank picks to create final slate.
    
    Args:
        edges: List of calculated edges
        max_picks: Maximum picks to include
        avoid_correlated: Avoid multiple picks on same player
    """
    # Filter to actionable picks only
    actionable = [e for e in edges if e.is_actionable]
    
    # Sort by edge (highest first)
    actionable.sort(key=lambda e: -e.edge_pct)
    
    # Remove correlated picks (same player, different props)
    if avoid_correlated:
        seen_players = set()
        filtered = []
        for edge in actionable:
            if edge.player_id not in seen_players:
                filtered.append(edge)
                seen_players.add(edge.player_id)
        actionable = filtered
    
    # Take top picks
    top_picks = actionable[:max_picks]
    
    # Categorize by confidence
    high_conf = [e for e in top_picks if e.confidence_tier == "HIGH"]
    med_conf = [e for e in top_picks if e.confidence_tier == "MEDIUM"]
    low_conf = [e for e in top_picks if e.confidence_tier == "LOW"]
    
    # Build warnings
    warnings = []
    if len(actionable) < 3:
        warnings.append("Limited actionable picks found - consider waiting for better slate")
    
    high_variance_count = sum(1 for e in top_picks if e.data_quality != "good")
    if high_variance_count > len(top_picks) / 2:
        warnings.append("Many picks have limited sample sizes")
    
    return SlateRecommendation(
        game_date=datetime.now().strftime("%Y-%m-%d"),
        generated_at=datetime.now().isoformat(),
        total_edges_analyzed=len(edges),
        picks_recommended=len(top_picks),
        high_confidence_picks=high_conf,
        medium_confidence_picks=med_conf,
        low_confidence_picks=low_conf,
        all_picks=top_picks,
        warnings=warnings
    )


# ============================================================================
# Main Entry Points
# ============================================================================

def analyze_matchup(
    conn: sqlite3.Connection,
    away_abbrev: str,
    home_abbrev: str,
    game_date: str,
    spread: float = 0.0,
    lines: Optional[Dict[int, Dict[str, float]]] = None,
) -> SlateRecommendation:
    """
    Full matchup analysis using The Edge Engine.
    
    Args:
        conn: Database connection
        away_abbrev: Away team abbreviation
        home_abbrev: Home team abbreviation
        game_date: Game date (YYYY-MM-DD)
        spread: Point spread (negative = home favored)
        lines: Optional dict of {player_id: {"pts": line, "reb": line, "ast": line}}
    
    Returns:
        SlateRecommendation with ranked picks
    """
    from .projector import project_team_players, ProjectionConfig
    
    all_edges = []
    
    # Get team projections
    config = ProjectionConfig()
    
    # Away team vs home defense
    away_projs = project_team_players(
        conn=conn,
        team_abbrev=away_abbrev,
        config=config,
        opponent_abbrev=home_abbrev,
    )
    
    # Home team vs away defense  
    home_projs = project_team_players(
        conn=conn,
        team_abbrev=home_abbrev,
        config=config,
        opponent_abbrev=away_abbrev,
    )
    
    all_projs = away_projs + home_projs
    
    # Calculate edges for each player and prop type
    for proj in all_projs:
        # Determine opponent
        opponent = home_abbrev if proj.team_abbrev == away_abbrev else away_abbrev
        
        # Build projection dict
        proj_dict = {
            "player_id": proj.player_id,
            "player_name": proj.player_name,
            "team_abbrev": proj.team_abbrev,
            "pts": proj.proj_pts,
            "reb": proj.proj_reb,
            "ast": proj.proj_ast,
            "pts_std": proj.pts_std,
            "reb_std": proj.reb_std,
            "ast_std": proj.ast_std,
            "data_quality": "good" if proj.games_played >= 15 else "limited",
            "games_used": proj.games_played,
            "warnings": [],
            "defense_factors": {}
        }
        
        # Get lines for this player
        player_lines = {}
        if lines and proj.player_id in lines:
            player_lines = lines[proj.player_id]
        else:
            # Use projection as pseudo-line for analysis
            player_lines = {
                "pts": proj.proj_pts,
                "reb": proj.proj_reb,
                "ast": proj.proj_ast
            }
        
        # Calculate edge for each prop
        for prop_type in ["PTS", "REB", "AST"]:
            line = player_lines.get(prop_type.lower(), 0)
            if line > 0:
                edge = calculate_edge_for_prop(
                    projection=proj_dict,
                    prop_type=prop_type,
                    line=line,
                    opponent_abbrev=opponent
                )
                all_edges.append(edge)
    
    # Filter and rank
    return filter_and_rank_picks(all_edges)


def quick_edge_check(
    conn: sqlite3.Connection,
    player_name: str,
    prop_type: str,
    line: float,
    opponent_abbrev: str,
    game_date: str,
) -> Optional[EdgeResult]:
    """
    Quick edge check for a single prop.
    
    Args:
        conn: Database connection
        player_name: Player name
        prop_type: PTS, REB, or AST
        line: Sportsbook line
        opponent_abbrev: Opponent team abbreviation
        game_date: Game date
    
    Returns:
        EdgeResult or None if player not found
    """
    # Find player
    row = conn.execute(
        "SELECT id FROM players WHERE name LIKE ?",
        (f"%{player_name}%",)
    ).fetchone()
    
    if not row:
        return None
    
    player_id = row["id"]
    
    # Get projection with context
    projection = get_projection_with_context(
        conn=conn,
        player_id=player_id,
        opponent_abbrev=opponent_abbrev,
        game_date=game_date
    )
    
    if projection is None:
        return None
    
    # Calculate edge
    return calculate_edge_for_prop(
        projection=projection,
        prop_type=prop_type.upper(),
        line=line,
        opponent_abbrev=opponent_abbrev
    )


# ============================================================================
# Integration with Accuracy Tracking
# ============================================================================

def analyze_and_track(
    conn: sqlite3.Connection,
    away_abbrev: str,
    home_abbrev: str,
    game_date: str,
    spread: float = 0.0,
    lines: Optional[Dict[int, Dict[str, float]]] = None,
    track_predictions: bool = True,
) -> SlateRecommendation:
    """
    Analyze matchup and optionally track predictions for accuracy.
    """
    # Get recommendations
    slate = analyze_matchup(conn, away_abbrev, home_abbrev, game_date, spread, lines)
    
    if track_predictions:
        try:
            from .accuracy_tracker import record_prediction, PredictionRecord, create_tracking_tables
            
            # Ensure tables exist
            create_tracking_tables(conn)
            
            # Record each actionable pick
            for edge in slate.all_picks:
                pred = PredictionRecord(
                    id=None,
                    created_at=datetime.now().isoformat(),
                    game_date=game_date,
                    player_id=edge.player_id,
                    player_name=edge.player_name,
                    team_abbrev=edge.team_abbrev,
                    opponent_abbrev=edge.opponent_abbrev,
                    prop_type=edge.prop_type,
                    direction=edge.direction,
                    line=edge.line,
                    projected_value=edge.projected_value,
                    projected_std=edge.projected_std,
                    edge_pct=edge.edge_pct,
                    confidence_score=edge.confidence_score,
                    confidence_tier=edge.confidence_tier,
                    is_b2b=False,  # Would need to extract from factors
                    rest_days=1,
                    spread=spread,
                    defense_factor=edge.factors.get(edge.prop_type.lower(), 1.0)
                )
                
                record_prediction(conn, pred, edge.factors)
        except Exception:
            # Don't fail analysis if tracking fails
            slate.warnings.append("Could not record predictions for accuracy tracking")
    
    return slate

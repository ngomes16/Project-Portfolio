"""
Prop Bet Edge Calculation Module
================================

This module provides probability-based edge calculations for player prop bets.

Key Features:
-------------
1. **Edge Calculation**
   - Calculate over/under probabilities using normal distribution
   - Convert American odds to implied probabilities
   - Determine edge percentage vs sportsbook line

2. **Prop Ranking**
   - Rank all prop opportunities by edge
   - Filter by minimum edge threshold
   - Focus on significant players (top 10)

3. **Basic Prop Reports**
   - Generate basic matchup projections
   - Include team defense adjustments
   - Provide recommendation list

Note on Comprehensive Reports:
-----------------------------
For the full "Advisor" style reports with Best Over/Under plays,
players to avoid, and key matchups, use:

    from nba_props.engine.matchup_advisor import generate_comprehensive_matchup_report

That function returns a structured ComprehensiveMatchupReport object
with actionable betting recommendations.

Module Author: NBA Props Team
Last Updated: January 2026
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from typing import Optional

from .projector import PlayerProjection


@dataclass
class PropEdge:
    """Calculated edge for a player prop bet."""
    player_id: int
    player_name: str
    team_abbrev: str
    
    # Prop details
    prop_type: str  # PTS, REB, AST
    line: float
    odds_american: Optional[int]
    book: Optional[str]
    
    # Projection
    projected_value: float
    projected_std: float
    
    # Edge calculations
    over_probability: float  # Probability of going over the line
    under_probability: float
    edge_over: float  # Expected edge if betting over
    edge_under: float
    
    # Recommendation
    recommendation: str  # "OVER", "UNDER", or "PASS"
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    edge_pct: float  # Best edge as percentage
    
    # Context
    games_sample: int
    is_top_7: bool


def _normal_cdf(x: float, mean: float, std: float) -> float:
    """
    Calculate cumulative distribution function for normal distribution.
    P(X <= x) for X ~ N(mean, std^2)
    """
    if std <= 0:
        return 1.0 if x >= mean else 0.0
    
    z = (x - mean) / std
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds >= 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def _american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal odds."""
    if odds >= 0:
        return (odds / 100) + 1
    else:
        return (100 / abs(odds)) + 1


def calculate_prop_edge(
    projection: PlayerProjection,
    prop_type: str,
    line: float,
    odds_american: Optional[int] = None,
    book: Optional[str] = None,
) -> PropEdge:
    """
    Calculate the edge for a player prop bet.
    
    Args:
        projection: Player projection with stats and uncertainty
        prop_type: Type of prop (PTS, REB, AST)
        line: Sportsbook line
        odds_american: American odds (e.g., -110, +100)
        book: Sportsbook name
    
    Returns:
        PropEdge with calculated probabilities and recommendation
    """
    # Get projected value and std based on prop type
    if prop_type == "PTS":
        proj_value = projection.proj_pts
        proj_std = projection.pts_std
    elif prop_type == "REB":
        proj_value = projection.proj_reb
        proj_std = projection.reb_std
    elif prop_type == "AST":
        proj_value = projection.proj_ast
        proj_std = projection.ast_std
    else:
        raise ValueError(f"Unknown prop type: {prop_type}")
    
    # Ensure minimum std (floor at 10% of value or 1.0)
    proj_std = max(proj_std, proj_value * 0.1, 1.0)
    
    # Calculate over/under probabilities using normal distribution
    # P(over) = P(X > line) = 1 - P(X <= line)
    under_prob = _normal_cdf(line, proj_value, proj_std)
    over_prob = 1 - under_prob
    
    # Calculate expected value / edge
    # Default to -110 odds (fair odds for 50/50) if not provided
    implied_prob = _american_to_implied_prob(odds_american if odds_american else -110)
    
    # Edge = Our probability - Implied probability
    edge_over = over_prob - implied_prob
    edge_under = under_prob - implied_prob
    
    # Determine recommendation
    threshold_high = 0.10  # 10% edge
    threshold_medium = 0.05  # 5% edge
    
    if edge_over > edge_under:
        best_edge = edge_over
        recommendation = "OVER" if best_edge > 0.02 else "PASS"
    else:
        best_edge = edge_under
        recommendation = "UNDER" if best_edge > 0.02 else "PASS"
    
    if recommendation != "PASS":
        if best_edge >= threshold_high:
            confidence = "HIGH"
        elif best_edge >= threshold_medium:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
    else:
        confidence = "LOW"
    
    return PropEdge(
        player_id=projection.player_id,
        player_name=projection.player_name,
        team_abbrev=projection.team_abbrev,
        prop_type=prop_type,
        line=line,
        odds_american=odds_american,
        book=book,
        projected_value=proj_value,
        projected_std=proj_std,
        over_probability=round(over_prob, 3),
        under_probability=round(under_prob, 3),
        edge_over=round(edge_over, 3),
        edge_under=round(edge_under, 3),
        recommendation=recommendation,
        confidence=confidence,
        edge_pct=round(best_edge * 100, 1),
        games_sample=projection.games_played,
        is_top_7=projection.is_top_7,
    )


def rank_prop_opportunities(
    conn: sqlite3.Connection,
    projections: list[PlayerProjection],
    as_of_date: str,
    min_edge: float = 0.03,
    top_7_only: bool = False,  # Deprecated, use top_10_only
    top_10_only: bool = True,
) -> list[PropEdge]:
    """
    Rank prop opportunities by edge.
    
    Args:
        conn: Database connection
        projections: List of player projections
        as_of_date: Date to look up lines for
        min_edge: Minimum edge to include (default 3%)
        top_7_only: Only include top 7 players per team
    
    Returns:
        List of PropEdge objects sorted by edge (best first)
    """
    # Get lines for this date
    lines = conn.execute(
        """
        SELECT sl.player_id, p.name as player_name, sl.prop_type, sl.line, sl.odds_american, sl.book
        FROM sportsbook_lines sl
        JOIN players p ON p.id = sl.player_id
        WHERE sl.as_of_date = ?
        """,
        (as_of_date,),
    ).fetchall()
    
    # Create lookup by player_id and prop_type
    lines_lookup = {}
    for line in lines:
        key = (line["player_id"], line["prop_type"])
        lines_lookup[key] = {
            "line": line["line"],
            "odds_american": line["odds_american"],
            "book": line["book"],
        }
    
    # Calculate edges for all projections with matching lines
    edges = []
    for proj in projections:
        # Check top 10 filter (with legacy top 7 support)
        if top_10_only and not getattr(proj, 'is_top_10', proj.is_top_7):
            continue
        
        for prop_type in ["PTS", "REB", "AST"]:
            key = (proj.player_id, prop_type)
            if key not in lines_lookup:
                continue
            
            line_data = lines_lookup[key]
            
            edge = calculate_prop_edge(
                projection=proj,
                prop_type=prop_type,
                line=line_data["line"],
                odds_american=line_data["odds_american"],
                book=line_data["book"],
            )
            
            # Filter by minimum edge
            if abs(edge.edge_over) >= min_edge or abs(edge.edge_under) >= min_edge:
                edges.append(edge)
    
    # Sort by absolute edge (best opportunities first)
    edges.sort(key=lambda e: -e.edge_pct)
    
    return edges


def _projection_to_dict(p: PlayerProjection) -> dict:
    """Convert a projection to a dict, including archetype info."""
    from .archetypes import get_player_archetype
    
    arch = get_player_archetype(p.player_name)
    archetype_info = None
    if arch:
        archetype_info = {
            "tier": arch.tier,
            "primary": arch.primary_offensive,
            "secondary": arch.secondary_offensive,
            "defensive": arch.defensive_role,
        }
    
    return {
        "player": p.player_name,
        "minutes": p.proj_minutes,
        "pts": p.proj_pts,
        "reb": p.proj_reb,
        "ast": p.proj_ast,
        "games": p.games_played,
        "is_top_7": p.is_top_7,
        "archetype": archetype_info,
    }


def generate_prop_report(
    conn: sqlite3.Connection,
    away_abbrev: str,
    home_abbrev: str,
    game_date: str,
    lines_date: Optional[str] = None,
) -> dict:
    """
    Generate a comprehensive prop report for a matchup.
    
    Args:
        conn: Database connection
        away_abbrev: Away team abbreviation
        home_abbrev: Home team abbreviation
        game_date: Game date
        lines_date: Date for sportsbook lines (defaults to game_date)
    
    Returns:
        Dictionary with projections and recommendations
    """
    from .projector import project_team_players, ProjectionConfig
    from .game_context import get_back_to_back_status, get_team_defense_rating, apply_matchup_adjustments
    from .archetypes import get_player_archetype
    
    config = ProjectionConfig()
    lines_date = lines_date or game_date
    
    # Get back-to-back status
    away_b2b = get_back_to_back_status(conn, away_abbrev, game_date)
    home_b2b = get_back_to_back_status(conn, home_abbrev, game_date)
    
    # Get defense ratings
    away_defense = get_team_defense_rating(conn, away_abbrev)
    home_defense = get_team_defense_rating(conn, home_abbrev)
    
    # Project players (away team plays against home defense)
    away_projections = project_team_players(
        conn=conn,
        team_abbrev=away_abbrev,
        config=config,
        opponent_abbrev=home_abbrev,
        is_back_to_back=away_b2b.is_back_to_back,
        rest_days=away_b2b.rest_days,
    )
    
    # Apply opponent adjustments
    for proj in away_projections:
        adj_pts, adj_reb, adj_ast, adj_info = apply_matchup_adjustments(
            proj.proj_pts, proj.proj_reb, proj.proj_ast, home_defense
        )
        proj.proj_pts = adj_pts
        proj.proj_reb = adj_reb
        proj.proj_ast = adj_ast
        proj.adjustments.update(adj_info)
    
    # Project home team
    home_projections = project_team_players(
        conn=conn,
        team_abbrev=home_abbrev,
        config=config,
        opponent_abbrev=away_abbrev,
        is_back_to_back=home_b2b.is_back_to_back,
        rest_days=home_b2b.rest_days,
    )
    
    # Apply opponent adjustments
    for proj in home_projections:
        adj_pts, adj_reb, adj_ast, adj_info = apply_matchup_adjustments(
            proj.proj_pts, proj.proj_reb, proj.proj_ast, away_defense
        )
        proj.proj_pts = adj_pts
        proj.proj_reb = adj_reb
        proj.proj_ast = adj_ast
        proj.adjustments.update(adj_info)
    
    # Get prop edges
    all_projections = away_projections + home_projections
    edges = rank_prop_opportunities(
        conn=conn,
        projections=all_projections,
        as_of_date=lines_date,
        min_edge=0.02,
        top_10_only=True,
    )
    
    return {
        "matchup": {
            "away": away_abbrev,
            "home": home_abbrev,
            "date": game_date,
        },
        "context": {
            "away_b2b": away_b2b.is_back_to_back,
            "away_rest_days": away_b2b.rest_days,
            "home_b2b": home_b2b.is_back_to_back,
            "home_rest_days": home_b2b.rest_days,
        },
        "defense_ratings": {
            "away": {
                "pts_factor": away_defense.pts_factor if away_defense else 1.0,
                "reb_factor": away_defense.reb_factor if away_defense else 1.0,
                "ast_factor": away_defense.ast_factor if away_defense else 1.0,
            } if away_defense else None,
            "home": {
                "pts_factor": home_defense.pts_factor if home_defense else 1.0,
                "reb_factor": home_defense.reb_factor if home_defense else 1.0,
                "ast_factor": home_defense.ast_factor if home_defense else 1.0,
            } if home_defense else None,
        },
        "away_projections": [
            _projection_to_dict(p)
            for p in away_projections
        ],
        "home_projections": [
            _projection_to_dict(p)
            for p in home_projections
        ],
        "recommendations": [
            {
                "player": e.player_name,
                "team": e.team_abbrev,
                "prop": e.prop_type,
                "line": e.line,
                "projected": e.projected_value,
                "recommendation": e.recommendation,
                "confidence": e.confidence,
                "edge_pct": e.edge_pct,
                "over_prob": e.over_probability,
                "under_prob": e.under_probability,
                "book": e.book,
            }
            for e in edges
        ],
    }


# ============================================================================
# DEPRECATED: Use defense_analysis.generate_comprehensive_matchup_report instead
# ============================================================================

def generate_comprehensive_matchup_report(
    conn: sqlite3.Connection,
    away_abbrev: str,
    home_abbrev: str,
    game_date: str,
    spread: Optional[float] = None,
    over_under: Optional[float] = None,
) -> dict:
    """
    DEPRECATED: This function has been moved to defense_analysis.py.
    
    For new code, use:
        from nba_props.engine.matchup_advisor import generate_comprehensive_matchup_report
    
    That version returns a structured ComprehensiveMatchupReport dataclass
    with proper best_over_plays, best_under_plays, and avoid_players lists.
    
    This wrapper function is kept for backwards compatibility but will
    convert the new dataclass to a dictionary format.
    
    Args:
        conn: Database connection
        away_abbrev: Away team abbreviation
        home_abbrev: Home team abbreviation  
        game_date: Date of the game (YYYY-MM-DD)
        spread: Point spread (negative = home favored)
        over_under: Total points over/under line
    
    Returns:
        Dictionary with matchup analysis (legacy format)
    """
    import warnings
    warnings.warn(
        "generate_comprehensive_matchup_report in props.py is deprecated. "
        "Use defense_analysis.generate_comprehensive_matchup_report instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Import and call the new implementation
    from .matchup_advisor import generate_comprehensive_matchup_report as new_report
    from dataclasses import asdict
    
    report = new_report(conn, away_abbrev, home_abbrev, game_date, spread, over_under)
    
    # Convert dataclass to dict for backwards compatibility
    result = asdict(report)
    
    # Convert MatchupEdge objects to dicts
    result["best_over_plays"] = [
        {
            "player": e.player_name if hasattr(e, 'player_name') else e.get("player_name"),
            "team": e.team_abbrev if hasattr(e, 'team_abbrev') else e.get("team_abbrev"),
            "opponent": e.opponent_abbrev if hasattr(e, 'opponent_abbrev') else e.get("opponent_abbrev"),
            "prop": e.prop_type if hasattr(e, 'prop_type') else e.get("prop_type"),
            "direction": e.direction if hasattr(e, 'direction') else e.get("direction"),
            "adjusted": e.adjusted_projection if hasattr(e, 'adjusted_projection') else e.get("adjusted_projection"),
            "adjustment_pct": e.adjustment_pct if hasattr(e, 'adjustment_pct') else e.get("adjustment_pct"),
            "confidence": e.confidence_tier if hasattr(e, 'confidence_tier') else e.get("confidence_tier"),
            "confidence_score": e.confidence_score if hasattr(e, 'confidence_score') else e.get("confidence_score"),
            "reasons": e.reasons if hasattr(e, 'reasons') else e.get("reasons", []),
            "warnings": e.warnings if hasattr(e, 'warnings') else e.get("warnings", []),
        }
        for e in report.best_over_plays
    ]
    
    result["best_under_plays"] = [
        {
            "player": e.player_name if hasattr(e, 'player_name') else e.get("player_name"),
            "team": e.team_abbrev if hasattr(e, 'team_abbrev') else e.get("team_abbrev"),
            "opponent": e.opponent_abbrev if hasattr(e, 'opponent_abbrev') else e.get("opponent_abbrev"),
            "prop": e.prop_type if hasattr(e, 'prop_type') else e.get("prop_type"),
            "direction": e.direction if hasattr(e, 'direction') else e.get("direction"),
            "adjusted": e.adjusted_projection if hasattr(e, 'adjusted_projection') else e.get("adjusted_projection"),
            "adjustment_pct": e.adjustment_pct if hasattr(e, 'adjustment_pct') else e.get("adjustment_pct"),
            "confidence": e.confidence_tier if hasattr(e, 'confidence_tier') else e.get("confidence_tier"),
            "confidence_score": e.confidence_score if hasattr(e, 'confidence_score') else e.get("confidence_score"),
            "reasons": e.reasons if hasattr(e, 'reasons') else e.get("reasons", []),
            "warnings": e.warnings if hasattr(e, 'warnings') else e.get("warnings", []),
        }
        for e in report.best_under_plays
    ]
    
    # Add matchup summary for compatibility
    result["matchup"] = {
        "away": away_abbrev,
        "home": home_abbrev,
        "date": game_date,
        "spread": spread,
        "over_under": over_under,
        "is_close_game": report.is_close_game,
    }
    
    result["context"] = {
        "away_b2b": report.away_b2b,
        "away_rest_days": report.away_rest_days,
        "home_b2b": report.home_b2b,
        "home_rest_days": report.home_rest_days,
    }
    
    return result

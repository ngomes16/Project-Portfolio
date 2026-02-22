"""Backtesting framework for validating projection accuracy.

This module provides tools to:
1. Compare projections to actual outcomes
2. Calculate hit rates for prop recommendations
3. Track calibration (are 60% predictions hitting 60% of the time?)
4. Calculate theoretical ROI
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from ..team_aliases import normalize_team_abbrev


@dataclass
class PropResult:
    """Result of a single prop bet evaluation."""
    player_id: int
    player_name: str
    game_date: str
    prop_type: str
    
    # Projection
    projected_value: float
    projected_std: float
    
    # Line
    line: float
    odds_american: Optional[int]
    
    # Actual
    actual_value: float
    
    # Outcome
    prediction: str  # "OVER" or "UNDER"
    actual_outcome: str  # "OVER" or "UNDER"
    hit: bool
    
    # Edge info
    edge_pct: float
    confidence: str


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    start_date: str
    end_date: str
    total_props: int
    
    # Hit rates
    hits: int
    misses: int
    hit_rate: float
    
    # By prop type
    pts_hits: int = 0
    pts_total: int = 0
    reb_hits: int = 0
    reb_total: int = 0
    ast_hits: int = 0
    ast_total: int = 0
    
    # By confidence
    high_conf_hits: int = 0
    high_conf_total: int = 0
    med_conf_hits: int = 0
    med_conf_total: int = 0
    low_conf_hits: int = 0
    low_conf_total: int = 0
    
    # By direction
    over_hits: int = 0
    over_total: int = 0
    under_hits: int = 0
    under_total: int = 0
    
    # Calibration (binned by prediction probability)
    calibration_bins: dict = field(default_factory=dict)
    
    # ROI (assuming -110 odds if not specified)
    theoretical_profit: float = 0.0
    theoretical_wagers: float = 0.0
    
    # Individual results
    prop_results: list[PropResult] = field(default_factory=list)
    
    @property
    def theoretical_roi(self) -> float:
        if self.theoretical_wagers == 0:
            return 0.0
        return (self.theoretical_profit / self.theoretical_wagers) * 100


def get_player_actual_stats(
    conn: sqlite3.Connection,
    player_id: int,
    game_date: str,
) -> Optional[dict]:
    """Get actual stats for a player on a specific date."""
    row = conn.execute(
        """
        SELECT b.pts, b.reb, b.ast, b.minutes
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.player_id = ?
          AND g.game_date = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 0
        """,
        (player_id, game_date),
    ).fetchone()
    
    if not row:
        return None
    
    return {
        "pts": row["pts"] or 0,
        "reb": row["reb"] or 0,
        "ast": row["ast"] or 0,
        "minutes": row["minutes"] or 0,
    }


def calculate_profit_from_odds(hit: bool, odds_american: Optional[int] = None, wager: float = 100.0) -> float:
    """Calculate profit/loss from a bet result."""
    if odds_american is None:
        odds_american = -110  # Standard juice
    
    if hit:
        if odds_american >= 0:
            return wager * (odds_american / 100)
        else:
            return wager * (100 / abs(odds_american))
    else:
        return -wager


def run_backtest(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    min_edge_pct: float = 3.0,
    top_7_only: bool = True,
) -> BacktestResult:
    """
    Run a backtest comparing lines to actual outcomes.
    
    Args:
        conn: Database connection
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        min_edge_pct: Minimum edge to include
        top_7_only: Only include top 7 players per team
    
    Returns:
        BacktestResult with performance metrics
    """
    from .projector import project_player_stats, ProjectionConfig
    from .edge_calculator import calculate_prop_edge
    
    result = BacktestResult(
        start_date=start_date,
        end_date=end_date,
        total_props=0,
        hits=0,
        misses=0,
        hit_rate=0.0,
    )
    
    # Get all lines in date range
    lines_rows = conn.execute(
        """
        SELECT sl.as_of_date, sl.player_id, p.name as player_name, 
               sl.prop_type, sl.line, sl.odds_american
        FROM sportsbook_lines sl
        JOIN players p ON p.id = sl.player_id
        WHERE sl.as_of_date >= ? AND sl.as_of_date <= ?
        ORDER BY sl.as_of_date, p.name
        """,
        (start_date, end_date),
    ).fetchall()
    
    if not lines_rows:
        return result
    
    config = ProjectionConfig()
    wager_amount = 100.0
    
    # Calibration bins: we'll bin by predicted over probability
    calibration_bins = {
        "50-55": {"predicted": 0, "actual": 0},
        "55-60": {"predicted": 0, "actual": 0},
        "60-65": {"predicted": 0, "actual": 0},
        "65-70": {"predicted": 0, "actual": 0},
        "70-75": {"predicted": 0, "actual": 0},
        "75+": {"predicted": 0, "actual": 0},
    }
    
    for line_row in lines_rows:
        player_id = line_row["player_id"]
        game_date = line_row["as_of_date"]
        prop_type = line_row["prop_type"]
        line = line_row["line"]
        odds = line_row["odds_american"]
        
        # Get actual stats for this date
        actual_stats = get_player_actual_stats(conn, player_id, game_date)
        if not actual_stats:
            continue
        
        actual_value = actual_stats.get(prop_type.lower(), 0)
        
        # Generate projection (using data before game date)
        projection = project_player_stats(
            conn=conn,
            player_id=player_id,
            config=config,
        )
        
        if not projection:
            continue
        
        # Calculate edge
        edge = calculate_prop_edge(
            projection=projection,
            prop_type=prop_type,
            line=line,
            odds_american=odds,
        )
        
        # Filter by minimum edge
        if edge.edge_pct < min_edge_pct:
            continue
        
        # Determine outcome
        actual_outcome = "OVER" if actual_value > line else "UNDER"
        prediction = edge.recommendation
        
        if prediction == "PASS":
            continue
        
        hit = (prediction == actual_outcome)
        
        # Create prop result
        prop_result = PropResult(
            player_id=player_id,
            player_name=line_row["player_name"],
            game_date=game_date,
            prop_type=prop_type,
            projected_value=edge.projected_value,
            projected_std=edge.projected_std,
            line=line,
            odds_american=odds,
            actual_value=actual_value,
            prediction=prediction,
            actual_outcome=actual_outcome,
            hit=hit,
            edge_pct=edge.edge_pct,
            confidence=edge.confidence,
        )
        
        result.prop_results.append(prop_result)
        result.total_props += 1
        
        if hit:
            result.hits += 1
        else:
            result.misses += 1
        
        # Track by prop type
        if prop_type == "PTS":
            result.pts_total += 1
            if hit:
                result.pts_hits += 1
        elif prop_type == "REB":
            result.reb_total += 1
            if hit:
                result.reb_hits += 1
        elif prop_type == "AST":
            result.ast_total += 1
            if hit:
                result.ast_hits += 1
        
        # Track by confidence
        if edge.confidence == "HIGH":
            result.high_conf_total += 1
            if hit:
                result.high_conf_hits += 1
        elif edge.confidence == "MEDIUM":
            result.med_conf_total += 1
            if hit:
                result.med_conf_hits += 1
        else:
            result.low_conf_total += 1
            if hit:
                result.low_conf_hits += 1
        
        # Track by direction
        if prediction == "OVER":
            result.over_total += 1
            if hit:
                result.over_hits += 1
        else:
            result.under_total += 1
            if hit:
                result.under_hits += 1
        
        # Track calibration
        over_prob = edge.over_probability * 100
        pred_prob = over_prob if prediction == "OVER" else (100 - over_prob)
        
        if pred_prob >= 75:
            calibration_bins["75+"]["predicted"] += 1
            if hit:
                calibration_bins["75+"]["actual"] += 1
        elif pred_prob >= 70:
            calibration_bins["70-75"]["predicted"] += 1
            if hit:
                calibration_bins["70-75"]["actual"] += 1
        elif pred_prob >= 65:
            calibration_bins["65-70"]["predicted"] += 1
            if hit:
                calibration_bins["65-70"]["actual"] += 1
        elif pred_prob >= 60:
            calibration_bins["60-65"]["predicted"] += 1
            if hit:
                calibration_bins["60-65"]["actual"] += 1
        elif pred_prob >= 55:
            calibration_bins["55-60"]["predicted"] += 1
            if hit:
                calibration_bins["55-60"]["actual"] += 1
        else:
            calibration_bins["50-55"]["predicted"] += 1
            if hit:
                calibration_bins["50-55"]["actual"] += 1
        
        # Calculate profit
        profit = calculate_profit_from_odds(hit, odds, wager_amount)
        result.theoretical_profit += profit
        result.theoretical_wagers += wager_amount
    
    # Calculate final hit rate
    if result.total_props > 0:
        result.hit_rate = result.hits / result.total_props
    
    result.calibration_bins = calibration_bins
    
    return result


def compare_projection_accuracy(
    conn: sqlite3.Connection,
    player_name: str,
    prop_type: str = "PTS",
    last_n_games: int = 10,
) -> Optional[dict]:
    """
    Compare projection accuracy for a specific player.
    
    Looks at the last N games and compares what we would have projected
    (using data available at the time) vs actual outcomes.
    """
    from .projector import _calculate_weighted_average
    
    # Find player
    player_row = conn.execute(
        "SELECT id, name FROM players WHERE name LIKE ?",
        (f"%{player_name}%",),
    ).fetchone()
    
    if not player_row:
        return None
    
    player_id = player_row["id"]
    full_name = player_row["name"]
    
    # Get recent games
    games = conn.execute(
        """
        SELECT g.game_date, b.pts, b.reb, b.ast, b.minutes
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.player_id = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 0
        ORDER BY g.game_date DESC
        LIMIT ?
        """,
        (player_id, last_n_games + 10),  # Get extra for lookback
    ).fetchall()
    
    if len(games) < last_n_games + 3:
        return None
    
    stat_key = prop_type.lower()
    
    comparisons = []
    for i in range(last_n_games):
        if i + 10 > len(games):
            break
        
        actual_game = games[i]
        historical_games = games[i+1:i+11]  # 10 games before this one
        
        actual_value = actual_game[stat_key] or 0
        historical_values = [g[stat_key] or 0 for g in historical_games]
        
        if len(historical_values) < 3:
            continue
        
        projected, std = _calculate_weighted_average(historical_values)
        
        error = actual_value - projected
        abs_error = abs(error)
        within_std = abs_error <= std
        
        comparisons.append({
            "date": actual_game["game_date"],
            "actual": actual_value,
            "projected": round(projected, 1),
            "std": round(std, 1),
            "error": round(error, 1),
            "abs_error": round(abs_error, 1),
            "within_std": within_std,
        })
    
    if not comparisons:
        return None
    
    # Calculate summary stats
    total_error = sum(c["error"] for c in comparisons)
    total_abs_error = sum(c["abs_error"] for c in comparisons)
    within_std_count = sum(1 for c in comparisons if c["within_std"])
    
    avg_error = total_error / len(comparisons)
    avg_abs_error = total_abs_error / len(comparisons)
    within_std_pct = within_std_count / len(comparisons) * 100
    
    return {
        "player": full_name,
        "prop_type": prop_type,
        "games_analyzed": len(comparisons),
        "avg_error": round(avg_error, 1),  # Positive = underprojects, negative = overprojects
        "avg_abs_error": round(avg_abs_error, 1),
        "within_std_pct": round(within_std_pct, 1),
        "bias": "underprojects" if avg_error > 0.5 else "overprojects" if avg_error < -0.5 else "neutral",
        "recent_comparisons": comparisons[:5],  # Most recent 5
    }


def analyze_projection_bias(
    conn: sqlite3.Connection,
    min_games: int = 5,
) -> dict:
    """
    Analyze systematic biases in projections across all players.
    
    Returns aggregate statistics on projection accuracy.
    """
    from .projector import _calculate_weighted_average
    
    # Get all players with enough games
    players = conn.execute(
        """
        SELECT p.id, p.name, COUNT(*) as games
        FROM boxscore_player b
        JOIN players p ON p.id = b.player_id
        WHERE b.minutes IS NOT NULL AND b.minutes > 10
        GROUP BY p.id
        HAVING COUNT(*) >= ?
        """,
        (min_games + 5,),
    ).fetchall()
    
    pts_errors = []
    reb_errors = []
    ast_errors = []
    
    for player in players:
        player_id = player["id"]
        
        # Get games for this player
        games = conn.execute(
            """
            SELECT g.game_date, b.pts, b.reb, b.ast
            FROM boxscore_player b
            JOIN games g ON g.id = b.game_id
            WHERE b.player_id = ?
              AND b.minutes IS NOT NULL
              AND b.minutes > 10
            ORDER BY g.game_date DESC
            LIMIT ?
            """,
            (player_id, min_games + 5),
        ).fetchall()
        
        if len(games) < min_games + 3:
            continue
        
        # Compare projection to actual for each stat
        for i in range(min_games):
            if i + 5 > len(games):
                break
            
            actual = games[i]
            historical = games[i+1:i+6]
            
            for stat_key in ["pts", "reb", "ast"]:
                actual_val = actual[stat_key] or 0
                hist_vals = [g[stat_key] or 0 for g in historical]
                
                if len(hist_vals) < 3:
                    continue
                
                projected, _ = _calculate_weighted_average(hist_vals)
                error = actual_val - projected
                
                if stat_key == "pts":
                    pts_errors.append(error)
                elif stat_key == "reb":
                    reb_errors.append(error)
                else:
                    ast_errors.append(error)
    
    def calculate_stats(errors):
        if not errors:
            return {"count": 0, "mean": 0, "std": 0}
        n = len(errors)
        mean = sum(errors) / n
        variance = sum((e - mean) ** 2 for e in errors) / n
        std = variance ** 0.5
        return {
            "count": n,
            "mean": round(mean, 2),
            "std": round(std, 2),
            "abs_mean": round(sum(abs(e) for e in errors) / n, 2),
        }
    
    return {
        "pts": calculate_stats(pts_errors),
        "reb": calculate_stats(reb_errors),
        "ast": calculate_stats(ast_errors),
        "total_comparisons": len(pts_errors),
        "players_analyzed": len(players),
    }


"""
Model Lab - Comprehensive Model Testing & Optimization Framework
================================================================

This module provides a sophisticated framework for testing, comparing, and 
optimizing different projection models for NBA player props betting.

Key Features:
-------------
1. **Multiple Model Architectures**
   - Simple moving averages
   - Weighted recency models
   - Median-based models
   - Regression-adjusted models
   - Matchup-adjusted models

2. **Comprehensive Backtesting**
   - Hit rate calculation (actual vs predicted)
   - Edge-based evaluation
   - Calibration analysis
   - ROI simulation

3. **Parameter Optimization**
   - Grid search across configurations
   - Performance ranking and selection
   - Cross-validation support

4. **Fast Evaluation**
   - Efficient database queries
   - Batch processing
   - Caching of intermediate results

Author: NBA Props Team
Last Updated: January 2026
"""
from __future__ import annotations

import sqlite3
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable, Tuple, Any
from enum import Enum

from ..db import Db
from ..team_aliases import abbrev_from_team_name, normalize_team_abbrev


# ============================================================================
# Model Configuration Types
# ============================================================================

class ModelType(Enum):
    """Different model architectures to test."""
    SIMPLE_AVERAGE = "simple_avg"
    WEIGHTED_RECENCY = "weighted_recency"
    MEDIAN_BASED = "median_based"
    L5_L10_COMBO = "l5_l10_combo"
    ADAPTIVE = "adaptive"
    OPPONENT_ADJUSTED = "opponent_adjusted"
    TREND_FOLLOWING = "trend_following"
    CONSISTENCY_WEIGHTED = "consistency_weighted"


@dataclass
class ModelConfig:
    """Configuration for a projection model."""
    name: str
    model_type: ModelType
    
    # Weighting parameters
    weight_l5: float = 0.35
    weight_l10: float = 0.35
    weight_l20: float = 0.20
    weight_season: float = 0.10
    
    # Thresholds
    min_games: int = 5
    lookback_games: int = 20
    
    # Adjustment factors
    use_trend_adjustment: bool = True
    trend_weight: float = 0.2
    
    use_opponent_adjustment: bool = True
    opponent_adjustment_weight: float = 0.3
    
    use_consistency_bonus: bool = True
    consistency_weight: float = 0.1
    
    # Edge thresholds for picks
    min_edge_pct: float = 5.0  # Minimum edge to make a pick
    
    # Additional parameters
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['model_type'] = self.model_type.value
        return d


@dataclass
class PickResult:
    """Result of a single pick."""
    player_id: int
    player_name: str
    game_date: str
    prop_type: str
    
    # Prediction
    projected_value: float
    line: float  # Using player's average as line per Idea.txt
    direction: str  # OVER or UNDER
    edge_pct: float
    confidence_score: float
    
    # Actual outcome
    actual_value: float
    hit: bool
    
    # Additional context
    team_abbrev: str = ""
    opponent_abbrev: str = ""


@dataclass
class BacktestResults:
    """Results from running a backtest."""
    config: ModelConfig
    start_date: str
    end_date: str
    
    # Overall metrics
    total_picks: int = 0
    hits: int = 0
    misses: int = 0
    
    # By prop type
    pts_picks: int = 0
    pts_hits: int = 0
    reb_picks: int = 0
    reb_hits: int = 0
    ast_picks: int = 0
    ast_hits: int = 0
    
    # By direction
    over_picks: int = 0
    over_hits: int = 0
    under_picks: int = 0
    under_hits: int = 0
    
    # By confidence
    high_conf_picks: int = 0
    high_conf_hits: int = 0
    med_conf_picks: int = 0
    med_conf_hits: int = 0
    
    # MAE metrics (lower is better)
    mae_pts: float = 0.0
    mae_reb: float = 0.0
    mae_ast: float = 0.0
    
    # Individual results
    pick_results: List[PickResult] = field(default_factory=list)
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_picks if self.total_picks > 0 else 0.0
    
    @property
    def pts_hit_rate(self) -> float:
        return self.pts_hits / self.pts_picks if self.pts_picks > 0 else 0.0
    
    @property
    def reb_hit_rate(self) -> float:
        return self.reb_hits / self.reb_picks if self.reb_picks > 0 else 0.0
    
    @property
    def ast_hit_rate(self) -> float:
        return self.ast_hits / self.ast_picks if self.ast_picks > 0 else 0.0
    
    @property
    def over_hit_rate(self) -> float:
        return self.over_hits / self.over_picks if self.over_picks > 0 else 0.0
    
    @property
    def under_hit_rate(self) -> float:
        return self.under_hits / self.under_picks if self.under_picks > 0 else 0.0
    
    @property
    def combined_score(self) -> float:
        """Combined score for ranking models (higher is better)."""
        # Weight hit rate heavily, penalize high MAE
        base_score = self.hit_rate * 100
        
        # Bonus for balanced performance across prop types
        if self.pts_picks > 0 and self.reb_picks > 0 and self.ast_picks > 0:
            balance_bonus = min(self.pts_hit_rate, self.reb_hit_rate, self.ast_hit_rate) * 10
            base_score += balance_bonus
        
        # Penalty for high MAE (normalized)
        mae_penalty = (self.mae_pts / 5 + self.mae_reb / 2 + self.mae_ast / 1.5)
        base_score -= mae_penalty
        
        return base_score
    
    def to_dict(self) -> dict:
        return {
            "config_name": self.config.name,
            "config": self.config.to_dict(),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_picks": self.total_picks,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate * 100, 1),
            "pts_picks": self.pts_picks,
            "pts_hits": self.pts_hits,
            "pts_hit_rate": round(self.pts_hit_rate * 100, 1),
            "reb_picks": self.reb_picks,
            "reb_hits": self.reb_hits,
            "reb_hit_rate": round(self.reb_hit_rate * 100, 1),
            "ast_picks": self.ast_picks,
            "ast_hits": self.ast_hits,
            "ast_hit_rate": round(self.ast_hit_rate * 100, 1),
            "over_picks": self.over_picks,
            "over_hits": self.over_hits,
            "over_hit_rate": round(self.over_hit_rate * 100, 1),
            "under_picks": self.under_picks,
            "under_hits": self.under_hits,
            "under_hit_rate": round(self.under_hit_rate * 100, 1),
            "mae_pts": round(self.mae_pts, 2),
            "mae_reb": round(self.mae_reb, 2),
            "mae_ast": round(self.mae_ast, 2),
            "combined_score": round(self.combined_score, 2),
        }


# ============================================================================
# Data Loading Utilities
# ============================================================================

def get_player_game_history(
    conn: sqlite3.Connection,
    player_id: int,
    before_date: str,
    limit: int = 30,
) -> List[Dict]:
    """Get player's game history before a specific date."""
    rows = conn.execute(
        """
        SELECT 
            g.game_date,
            b.pts, b.reb, b.ast, b.minutes,
            b.fgm, b.fga, b.tpm, b.tpa, b.ftm, b.fta,
            t.name as team_name,
            CASE WHEN g.team1_id = b.team_id THEN t2.name ELSE t1.name END as opponent_name
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        JOIN teams t ON t.id = b.team_id
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        WHERE b.player_id = ?
          AND g.game_date < ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 5
        ORDER BY g.game_date DESC
        LIMIT ?
        """,
        (player_id, before_date, limit),
    ).fetchall()
    
    return [dict(r) for r in rows]


def get_opponent_defense_factor(
    conn: sqlite3.Connection,
    opponent_abbrev: str,
    position: str,
    prop_type: str,
) -> float:
    """Get how much the opponent allows for this position/stat vs league average."""
    from ..standings import _team_ids_by_abbrev
    
    opponent_abbrev = normalize_team_abbrev(opponent_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(opponent_abbrev, [])
    
    if not team_ids:
        return 1.0
    
    pos = position.upper()[:1] if position else "G"
    stat_col = prop_type.lower()
    
    placeholders = ",".join(["?"] * len(team_ids))
    
    # Stats allowed to this position against this team
    allowed_row = conn.execute(
        f"""
        SELECT AVG(b.{stat_col}) as allowed_avg
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.pos = ?
          AND b.minutes > 10
          AND b.team_id NOT IN ({placeholders})
          AND (g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders}))
        """,
        (pos, *team_ids, *team_ids, *team_ids),
    ).fetchone()
    
    allowed_avg = allowed_row["allowed_avg"] if allowed_row and allowed_row["allowed_avg"] else None
    
    # League average for this position
    league_row = conn.execute(
        f"""
        SELECT AVG({stat_col}) as league_avg
        FROM boxscore_player
        WHERE pos = ? AND minutes > 10
        """,
        (pos,),
    ).fetchone()
    
    league_avg = league_row["league_avg"] if league_row and league_row["league_avg"] else None
    
    if allowed_avg and league_avg and league_avg > 0:
        return allowed_avg / league_avg
    
    return 1.0


# ============================================================================
# Model Projection Functions
# ============================================================================

def project_simple_average(history: List[Dict], prop_type: str, config: ModelConfig) -> Optional[Tuple[float, float]]:
    """Simple average of last N games."""
    if len(history) < config.min_games:
        return None
    
    stat_key = prop_type.lower()
    values = [g[stat_key] or 0 for g in history[:config.lookback_games]]
    
    if not values:
        return None
    
    avg = sum(values) / len(values)
    std = statistics.stdev(values) if len(values) > 1 else avg * 0.2
    
    return avg, std


def project_weighted_recency(history: List[Dict], prop_type: str, config: ModelConfig) -> Optional[Tuple[float, float]]:
    """Weighted average with higher weights for recent games."""
    if len(history) < config.min_games:
        return None
    
    stat_key = prop_type.lower()
    values = [g[stat_key] or 0 for g in history[:config.lookback_games]]
    
    if not values:
        return None
    
    # Calculate weighted components
    l5 = values[:5]
    l10 = values[:10]
    l20 = values[:20]
    season = values
    
    l5_avg = sum(l5) / len(l5) if l5 else 0
    l10_avg = sum(l10) / len(l10) if l10 else 0
    l20_avg = sum(l20) / len(l20) if l20 else 0
    season_avg = sum(season) / len(season) if season else 0
    
    # Weighted combination (normalize weights)
    total_weight = config.weight_l5 + config.weight_l10 + config.weight_l20 + config.weight_season
    if total_weight <= 0:
        return season_avg, season_avg * 0.2
    
    weighted_avg = (
        l5_avg * config.weight_l5 +
        l10_avg * config.weight_l10 +
        l20_avg * config.weight_l20 +
        season_avg * config.weight_season
    ) / total_weight
    
    std = statistics.stdev(values) if len(values) > 1 else weighted_avg * 0.2
    
    return weighted_avg, std


def project_median_based(history: List[Dict], prop_type: str, config: ModelConfig) -> Optional[Tuple[float, float]]:
    """Use median instead of mean (more robust to outliers)."""
    if len(history) < config.min_games:
        return None
    
    stat_key = prop_type.lower()
    values = [g[stat_key] or 0 for g in history[:config.lookback_games]]
    
    if not values:
        return None
    
    # Recent median (L10)
    recent_values = values[:10]
    recent_median = statistics.median(recent_values) if recent_values else 0
    
    # Season median
    season_median = statistics.median(values)
    
    # Combine with weight towards recent
    combined = recent_median * 0.6 + season_median * 0.4
    
    std = statistics.stdev(values) if len(values) > 1 else combined * 0.2
    
    return combined, std


def project_l5_l10_combo(history: List[Dict], prop_type: str, config: ModelConfig) -> Optional[Tuple[float, float]]:
    """Focus primarily on L5 and L10 (most predictive windows)."""
    if len(history) < config.min_games:
        return None
    
    stat_key = prop_type.lower()
    values = [g[stat_key] or 0 for g in history]
    
    if not values:
        return None
    
    l5 = values[:5]
    l10 = values[:10]
    
    l5_avg = sum(l5) / len(l5) if l5 else 0
    l10_avg = sum(l10) / len(l10) if l10 else 0
    
    # 60% L5, 40% L10
    combined = l5_avg * 0.6 + l10_avg * 0.4
    
    std = statistics.stdev(l10) if len(l10) > 1 else combined * 0.2
    
    return combined, std


def project_adaptive(history: List[Dict], prop_type: str, config: ModelConfig) -> Optional[Tuple[float, float]]:
    """Adaptive model that adjusts weights based on player consistency."""
    if len(history) < config.min_games:
        return None
    
    stat_key = prop_type.lower()
    values = [g[stat_key] or 0 for g in history[:config.lookback_games]]
    
    if not values:
        return None
    
    l5 = values[:5]
    l10 = values[:10]
    season = values
    
    l5_avg = sum(l5) / len(l5) if l5 else 0
    l10_avg = sum(l10) / len(l10) if l10 else 0
    season_avg = sum(season) / len(season) if season else 0
    
    # Calculate consistency (lower CV = more consistent)
    cv = statistics.stdev(l10) / l10_avg if l10_avg > 0 and len(l10) > 1 else 0.3
    
    # Adaptive weighting:
    # - Consistent players: weight recent data more
    # - Inconsistent players: weight season data more (regression to mean)
    if cv < 0.20:  # Very consistent
        combined = l5_avg * 0.5 + l10_avg * 0.35 + season_avg * 0.15
    elif cv < 0.35:  # Moderately consistent
        combined = l5_avg * 0.35 + l10_avg * 0.35 + season_avg * 0.30
    else:  # Inconsistent - regress to season
        combined = l5_avg * 0.25 + l10_avg * 0.30 + season_avg * 0.45
    
    std = statistics.stdev(values) if len(values) > 1 else combined * 0.2
    
    return combined, std


def project_trend_following(history: List[Dict], prop_type: str, config: ModelConfig) -> Optional[Tuple[float, float]]:
    """Follow recent trends more aggressively."""
    if len(history) < config.min_games:
        return None
    
    stat_key = prop_type.lower()
    values = [g[stat_key] or 0 for g in history[:config.lookback_games]]
    
    if not values:
        return None
    
    l3 = values[:3]
    l5 = values[:5]
    l10 = values[:10]
    
    l3_avg = sum(l3) / len(l3) if l3 else 0
    l5_avg = sum(l5) / len(l5) if l5 else 0
    l10_avg = sum(l10) / len(l10) if l10 else 0
    
    # Detect trend
    trend_pct = (l3_avg - l10_avg) / l10_avg * 100 if l10_avg > 0 else 0
    
    # Base projection
    base = l5_avg * 0.5 + l10_avg * 0.5
    
    # Apply trend adjustment (capped)
    if abs(trend_pct) > 10:
        trend_adj = 1 + (trend_pct / 100) * config.trend_weight
        trend_adj = max(0.85, min(1.15, trend_adj))
        base *= trend_adj
    
    std = statistics.stdev(l10) if len(l10) > 1 else base * 0.2
    
    return base, std


def project_consistency_weighted(history: List[Dict], prop_type: str, config: ModelConfig) -> Optional[Tuple[float, float]]:
    """Weight by consistency - trust consistent performers more."""
    if len(history) < config.min_games:
        return None
    
    stat_key = prop_type.lower()
    values = [g[stat_key] or 0 for g in history[:config.lookback_games]]
    
    if not values:
        return None
    
    l10 = values[:10]
    
    l10_avg = sum(l10) / len(l10) if l10 else 0
    l10_median = statistics.median(l10) if l10 else 0
    
    # Use combination of mean and median based on consistency
    cv = statistics.stdev(l10) / l10_avg if l10_avg > 0 and len(l10) > 1 else 0.3
    
    # Higher CV = more weight to median (more robust)
    median_weight = min(0.7, 0.3 + cv)
    mean_weight = 1 - median_weight
    
    combined = l10_avg * mean_weight + l10_median * median_weight
    
    std = statistics.stdev(l10) if len(l10) > 1 else combined * 0.2
    
    return combined, std


# ============================================================================
# Model Projection Router
# ============================================================================

MODEL_PROJECTORS = {
    ModelType.SIMPLE_AVERAGE: project_simple_average,
    ModelType.WEIGHTED_RECENCY: project_weighted_recency,
    ModelType.MEDIAN_BASED: project_median_based,
    ModelType.L5_L10_COMBO: project_l5_l10_combo,
    ModelType.ADAPTIVE: project_adaptive,
    ModelType.TREND_FOLLOWING: project_trend_following,
    ModelType.CONSISTENCY_WEIGHTED: project_consistency_weighted,
}


def project_player_stat(
    conn: sqlite3.Connection,
    player_id: int,
    prop_type: str,
    before_date: str,
    config: ModelConfig,
    opponent_abbrev: Optional[str] = None,
    position: Optional[str] = None,
) -> Optional[Tuple[float, float, float]]:
    """
    Project a player's stat using the specified model configuration.
    
    Returns: (projected_value, std_dev, line) or None
    Line is calculated as average of last 10/7/5 games per Idea.txt
    """
    # Get player history
    history = get_player_game_history(conn, player_id, before_date, limit=30)
    
    if len(history) < config.min_games:
        return None
    
    # Get base projection from model
    projector = MODEL_PROJECTORS.get(config.model_type, project_weighted_recency)
    result = projector(history, prop_type, config)
    
    if result is None:
        return None
    
    projected_value, std = result
    
    # Apply opponent adjustment if enabled
    if config.use_opponent_adjustment and opponent_abbrev and position:
        opp_factor = get_opponent_defense_factor(conn, opponent_abbrev, position, prop_type)
        # Dampen the adjustment
        adj_factor = 1 + (opp_factor - 1) * config.opponent_adjustment_weight
        adj_factor = max(0.85, min(1.15, adj_factor))
        projected_value *= adj_factor
    
    # Calculate line (average of last 10/7/5 games per Idea.txt)
    stat_key = prop_type.lower()
    values = [g[stat_key] or 0 for g in history]
    
    if len(values) >= 10:
        line = sum(values[:10]) / 10
    elif len(values) >= 7:
        line = sum(values[:7]) / 7
    elif len(values) >= 5:
        line = sum(values[:5]) / 5
    else:
        line = sum(values) / len(values)
    
    return projected_value, std, line


# ============================================================================
# Pick Generation
# ============================================================================

def generate_pick(
    projected_value: float,
    std: float,
    line: float,
    config: ModelConfig,
) -> Tuple[str, float, float]:
    """
    Determine pick direction and calculate edge/confidence.
    
    Returns: (direction, edge_pct, confidence_score)
    """
    # Calculate edge
    diff = projected_value - line
    diff_pct = (diff / line) * 100 if line > 0 else 0
    
    # Calculate Z-score for probability
    z_score = diff / std if std > 0 else 0
    
    # Determine direction based on edge
    if diff_pct >= config.min_edge_pct:
        direction = "OVER"
        edge_pct = diff_pct
    elif diff_pct <= -config.min_edge_pct:
        direction = "UNDER"
        edge_pct = abs(diff_pct)
    else:
        direction = "PASS"
        edge_pct = abs(diff_pct)
    
    # Calculate confidence (0-100)
    # Based on edge magnitude and Z-score
    confidence = 50  # Base
    
    # Edge magnitude bonus
    if edge_pct >= 15:
        confidence += 25
    elif edge_pct >= 10:
        confidence += 15
    elif edge_pct >= 5:
        confidence += 8
    
    # Z-score bonus
    abs_z = abs(z_score)
    if abs_z >= 1.5:
        confidence += 20
    elif abs_z >= 1.0:
        confidence += 12
    elif abs_z >= 0.5:
        confidence += 5
    
    # Cap confidence
    confidence = min(95, max(20, confidence))
    
    return direction, edge_pct, confidence


# ============================================================================
# Backtesting Engine
# ============================================================================

def run_model_backtest(
    config: ModelConfig,
    start_date: str,
    end_date: str,
    db_path: str = "data/db/nba_props.sqlite3",
    min_minutes: float = 20.0,
    top_n_per_team: int = 10,
) -> BacktestResults:
    """
    Run a comprehensive backtest for a model configuration.
    
    Args:
        config: Model configuration to test
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        db_path: Path to database
        min_minutes: Minimum minutes to include player
        top_n_per_team: Only evaluate top N players per team by minutes
    
    Returns:
        BacktestResults with all metrics
    """
    db = Db(db_path)
    results = BacktestResults(config=config, start_date=start_date, end_date=end_date)
    
    pts_errors = []
    reb_errors = []
    ast_errors = []
    
    with db.connect() as conn:
        # Get all games in date range
        games = conn.execute(
            """
            SELECT g.id, g.game_date, g.team1_id, g.team2_id, 
                   t1.name as team1_name, t2.name as team2_name
            FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            WHERE g.game_date BETWEEN ? AND ?
            ORDER BY g.game_date
            """,
            (start_date, end_date),
        ).fetchall()
        
        for game in games:
            game_date = game["game_date"]
            
            for team_id, team_name, opp_name in [
                (game["team1_id"], game["team1_name"], game["team2_name"]),
                (game["team2_id"], game["team2_name"], game["team1_name"]),
            ]:
                team_abbrev = abbrev_from_team_name(team_name) or ""
                opp_abbrev = abbrev_from_team_name(opp_name) or ""
                
                # Get top players for this team in this game (by minutes)
                players = conn.execute(
                    """
                    SELECT b.player_id, p.name, b.pts, b.reb, b.ast, b.minutes, b.pos
                    FROM boxscore_player b
                    JOIN players p ON p.id = b.player_id
                    WHERE b.game_id = ? AND b.team_id = ?
                      AND b.minutes >= ?
                    ORDER BY b.minutes DESC
                    LIMIT ?
                    """,
                    (game["id"], team_id, min_minutes, top_n_per_team),
                ).fetchall()
                
                for player in players:
                    player_id = player["player_id"]
                    player_name = player["name"]
                    position = player["pos"] or "G"
                    
                    for prop_type in ["PTS", "REB", "AST"]:
                        actual = player[prop_type.lower()] or 0
                        
                        # Get projection
                        projection = project_player_stat(
                            conn, player_id, prop_type, game_date, config,
                            opponent_abbrev=opp_abbrev, position=position
                        )
                        
                        if projection is None:
                            continue
                        
                        projected, std, line = projection
                        
                        # Track MAE
                        error = abs(projected - actual)
                        if prop_type == "PTS":
                            pts_errors.append(error)
                        elif prop_type == "REB":
                            reb_errors.append(error)
                        else:
                            ast_errors.append(error)
                        
                        # Generate pick
                        direction, edge_pct, confidence = generate_pick(projected, std, line, config)
                        
                        if direction == "PASS":
                            continue
                        
                        # Determine actual outcome
                        actual_outcome = "OVER" if actual > line else "UNDER"
                        hit = (direction == actual_outcome)
                        
                        # Record result
                        pick_result = PickResult(
                            player_id=player_id,
                            player_name=player_name,
                            game_date=game_date,
                            prop_type=prop_type,
                            projected_value=round(projected, 1),
                            line=round(line, 1),
                            direction=direction,
                            edge_pct=round(edge_pct, 1),
                            confidence_score=round(confidence, 1),
                            actual_value=actual,
                            hit=hit,
                            team_abbrev=team_abbrev,
                            opponent_abbrev=opp_abbrev,
                        )
                        
                        results.pick_results.append(pick_result)
                        results.total_picks += 1
                        
                        if hit:
                            results.hits += 1
                        else:
                            results.misses += 1
                        
                        # By prop type
                        if prop_type == "PTS":
                            results.pts_picks += 1
                            if hit:
                                results.pts_hits += 1
                        elif prop_type == "REB":
                            results.reb_picks += 1
                            if hit:
                                results.reb_hits += 1
                        else:
                            results.ast_picks += 1
                            if hit:
                                results.ast_hits += 1
                        
                        # By direction
                        if direction == "OVER":
                            results.over_picks += 1
                            if hit:
                                results.over_hits += 1
                        else:
                            results.under_picks += 1
                            if hit:
                                results.under_hits += 1
                        
                        # By confidence
                        if confidence >= 70:
                            results.high_conf_picks += 1
                            if hit:
                                results.high_conf_hits += 1
                        elif confidence >= 55:
                            results.med_conf_picks += 1
                            if hit:
                                results.med_conf_hits += 1
    
    # Calculate MAE
    results.mae_pts = sum(pts_errors) / len(pts_errors) if pts_errors else 0
    results.mae_reb = sum(reb_errors) / len(reb_errors) if reb_errors else 0
    results.mae_ast = sum(ast_errors) / len(ast_errors) if ast_errors else 0
    
    return results


# ============================================================================
# Model Configurations to Test
# ============================================================================

def get_test_configurations() -> List[ModelConfig]:
    """Get a comprehensive set of model configurations to test."""
    configs = []
    
    # 1. Simple Average (baseline)
    configs.append(ModelConfig(
        name="Simple Avg L10",
        model_type=ModelType.SIMPLE_AVERAGE,
        lookback_games=10,
        min_edge_pct=5.0,
    ))
    
    # 2. L5/L10 Focused (per Idea.txt preference)
    configs.append(ModelConfig(
        name="L5/L10 Focus (60/40)",
        model_type=ModelType.L5_L10_COMBO,
        min_edge_pct=5.0,
    ))
    
    # 3. Median-based (robust to outliers)
    configs.append(ModelConfig(
        name="Median Based",
        model_type=ModelType.MEDIAN_BASED,
        min_edge_pct=5.0,
    ))
    
    # 4. Adaptive (adjusts by consistency)
    configs.append(ModelConfig(
        name="Adaptive by Consistency",
        model_type=ModelType.ADAPTIVE,
        min_edge_pct=5.0,
    ))
    
    # 5. Trend Following (aggressive)
    configs.append(ModelConfig(
        name="Trend Following (0.2)",
        model_type=ModelType.TREND_FOLLOWING,
        trend_weight=0.2,
        min_edge_pct=5.0,
    ))
    
    configs.append(ModelConfig(
        name="Trend Following (0.3)",
        model_type=ModelType.TREND_FOLLOWING,
        trend_weight=0.3,
        min_edge_pct=5.0,
    ))
    
    # 6. Consistency Weighted
    configs.append(ModelConfig(
        name="Consistency Weighted",
        model_type=ModelType.CONSISTENCY_WEIGHTED,
        min_edge_pct=5.0,
    ))
    
    # 7. Weighted Recency variations
    for l5_w in [0.25, 0.35, 0.45, 0.55]:
        for l10_w in [0.25, 0.35, 0.45]:
            l20_w = (1 - l5_w - l10_w) * 0.5
            season_w = 1 - l5_w - l10_w - l20_w
            if season_w < 0:
                continue
            configs.append(ModelConfig(
                name=f"Weighted L5:{l5_w}/L10:{l10_w}",
                model_type=ModelType.WEIGHTED_RECENCY,
                weight_l5=l5_w,
                weight_l10=l10_w,
                weight_l20=l20_w,
                weight_season=season_w,
                min_edge_pct=5.0,
            ))
    
    # 8. Different edge thresholds
    for edge in [3.0, 5.0, 7.0, 10.0]:
        configs.append(ModelConfig(
            name=f"Adaptive Edge>{edge}%",
            model_type=ModelType.ADAPTIVE,
            min_edge_pct=edge,
        ))
    
    # 9. Opponent adjusted models
    configs.append(ModelConfig(
        name="Adaptive + Opp Adj (0.3)",
        model_type=ModelType.ADAPTIVE,
        use_opponent_adjustment=True,
        opponent_adjustment_weight=0.3,
        min_edge_pct=5.0,
    ))
    
    configs.append(ModelConfig(
        name="Adaptive + Opp Adj (0.5)",
        model_type=ModelType.ADAPTIVE,
        use_opponent_adjustment=True,
        opponent_adjustment_weight=0.5,
        min_edge_pct=5.0,
    ))
    
    return configs


# ============================================================================
# Main Model Lab Functions
# ============================================================================

def run_model_comparison(
    start_date: str,
    end_date: str,
    db_path: str = "data/db/nba_props.sqlite3",
    configs: Optional[List[ModelConfig]] = None,
) -> List[BacktestResults]:
    """
    Run backtests for multiple model configurations and rank them.
    
    Returns: List of BacktestResults sorted by combined_score (descending)
    """
    if configs is None:
        configs = get_test_configurations()
    
    results = []
    total = len(configs)
    
    for i, config in enumerate(configs):
        print(f"Testing {i+1}/{total}: {config.name}...")
        try:
            result = run_model_backtest(config, start_date, end_date, db_path)
            results.append(result)
            print(f"  -> Hit rate: {result.hit_rate*100:.1f}%, Picks: {result.total_picks}")
        except Exception as e:
            print(f"  -> Error: {e}")
    
    # Sort by combined score (higher is better)
    results.sort(key=lambda r: r.combined_score, reverse=True)
    
    return results


def find_best_model(
    start_date: str,
    end_date: str,
    db_path: str = "data/db/nba_props.sqlite3",
    min_hit_rate: float = 0.52,
) -> Optional[BacktestResults]:
    """
    Find the best performing model configuration.
    
    Args:
        start_date: Start date for backtest
        end_date: End date for backtest
        db_path: Path to database
        min_hit_rate: Minimum hit rate to consider valid
    
    Returns:
        Best BacktestResults or None if no models meet criteria
    """
    results = run_model_comparison(start_date, end_date, db_path)
    
    # Filter by minimum hit rate
    valid_results = [r for r in results if r.hit_rate >= min_hit_rate]
    
    if not valid_results:
        print(f"No models achieved minimum hit rate of {min_hit_rate*100}%")
        if results:
            print(f"Best was: {results[0].config.name} with {results[0].hit_rate*100:.1f}%")
            return results[0]
        return None
    
    return valid_results[0]


def print_backtest_results(results: List[BacktestResults], top_n: int = 10) -> None:
    """Print formatted backtest results."""
    print("\n" + "="*80)
    print("MODEL COMPARISON RESULTS")
    print("="*80)
    
    for i, r in enumerate(results[:top_n]):
        print(f"\n#{i+1}: {r.config.name}")
        print(f"  Hit Rate: {r.hit_rate*100:.1f}% ({r.hits}/{r.total_picks})")
        print(f"  Combined Score: {r.combined_score:.2f}")
        print(f"  PTS: {r.pts_hit_rate*100:.1f}% | REB: {r.reb_hit_rate*100:.1f}% | AST: {r.ast_hit_rate*100:.1f}%")
        print(f"  OVER: {r.over_hit_rate*100:.1f}% | UNDER: {r.under_hit_rate*100:.1f}%")
        print(f"  MAE - PTS: {r.mae_pts:.2f} | REB: {r.mae_reb:.2f} | AST: {r.mae_ast:.2f}")


# ============================================================================
# Quick Test Function
# ============================================================================

def quick_test(days_back: int = 14) -> List[BacktestResults]:
    """
    Quick test with reduced configurations for faster iteration.
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Reduced set of configs for quick testing
    configs = [
        ModelConfig(name="Simple L10", model_type=ModelType.SIMPLE_AVERAGE, lookback_games=10, min_edge_pct=5.0),
        ModelConfig(name="L5/L10 Combo", model_type=ModelType.L5_L10_COMBO, min_edge_pct=5.0),
        ModelConfig(name="Median", model_type=ModelType.MEDIAN_BASED, min_edge_pct=5.0),
        ModelConfig(name="Adaptive", model_type=ModelType.ADAPTIVE, min_edge_pct=5.0),
        ModelConfig(name="Trend 0.2", model_type=ModelType.TREND_FOLLOWING, trend_weight=0.2, min_edge_pct=5.0),
        ModelConfig(name="Consistency", model_type=ModelType.CONSISTENCY_WEIGHTED, min_edge_pct=5.0),
    ]
    
    results = run_model_comparison(start_date, end_date, configs=configs)
    print_backtest_results(results)
    
    return results


# ============================================================================
# Version Tracking Integration
# ============================================================================

def register_and_backtest_model(
    config: ModelConfig,
    start_date: str,
    end_date: str,
    db_path: str = "data/db/nba_props.sqlite3",
    set_active: bool = False,
) -> Tuple[int, BacktestResults]:
    """
    Register a model version and run backtest with full tracking.
    
    This integrates with ModelVersionTracker to store all picks and results.
    
    Args:
        config: Model configuration to test
        start_date: Backtest start date
        end_date: Backtest end date
        db_path: Database path
        set_active: Whether to set this as the active model
    
    Returns:
        Tuple of (version_id, BacktestResults)
    """
    from .model_version_tracker import (
        ModelVersionTracker, VersionPick, BacktestSummary, ModelInsight
    )
    
    # Run the backtest
    results = run_model_backtest(config, start_date, end_date, db_path)
    
    # Register the version
    tracker = ModelVersionTracker(db_path)
    version_id = tracker.register_version(
        name=config.name,
        version=f"lab_{config.model_type.value}",
        config=config.to_dict(),
        description=f"Model Lab config: {config.name}",
        set_active=set_active,
    )
    
    # Convert picks to VersionPick format
    version_picks = []
    for pick in results.pick_results:
        vp = VersionPick(
            version_id=version_id,
            pick_date=pick.game_date,
            player_id=pick.player_id,
            player_name=pick.player_name,
            team_abbrev=pick.team_abbrev,
            opponent_abbrev=pick.opponent_abbrev,
            prop_type=pick.prop_type,
            direction=pick.direction,
            line_source="derived_avg",  # Model lab uses derived lines
            line=pick.line,
            sportsbook_line=None,  # Lab doesn't have sportsbook lines
            derived_line=pick.line,
            projection=pick.projected_value,
            edge_vs_line=pick.edge_pct,
            confidence_score=pick.confidence_score,
            confidence_tier="HIGH" if pick.confidence_score >= 70 else "MEDIUM",
            actual_value=pick.actual_value,
            hit=pick.hit,
        )
        version_picks.append(vp)
    
    # Save picks
    tracker.save_picks(version_id, version_picks)
    
    # Save backtest summary
    summary = BacktestSummary(
        version_id=version_id,
        start_date=start_date,
        end_date=end_date,
        total_picks=results.total_picks,
        hits=results.hits,
        misses=results.misses,
        pts_picks=results.pts_picks,
        pts_hits=results.pts_hits,
        reb_picks=results.reb_picks,
        reb_hits=results.reb_hits,
        ast_picks=results.ast_picks,
        ast_hits=results.ast_hits,
        over_picks=results.over_picks,
        over_hits=results.over_hits,
        under_picks=results.under_picks,
        under_hits=results.under_hits,
        mae_pts=results.mae_pts,
        mae_reb=results.mae_reb,
        mae_ast=results.mae_ast,
    )
    tracker.save_backtest(summary)
    
    # Update grades
    tracker.update_grades(version_id)
    
    # Add insights
    if results.hit_rate >= 0.60:
        tracker.add_insight(ModelInsight(
            version_id=version_id,
            insight_type="strength",
            category="overall",
            insight=f"Strong overall hit rate: {results.hit_rate*100:.1f}%",
            evidence=f"{results.hits}/{results.total_picks} picks"
        ))
    
    if results.pts_hit_rate >= results.reb_hit_rate + 0.05:
        tracker.add_insight(ModelInsight(
            version_id=version_id,
            insight_type="strength",
            category="pts",
            insight="Better at predicting PTS than REB",
            evidence=f"PTS: {results.pts_hit_rate*100:.1f}% vs REB: {results.reb_hit_rate*100:.1f}%"
        ))
    elif results.reb_hit_rate >= results.pts_hit_rate + 0.05:
        tracker.add_insight(ModelInsight(
            version_id=version_id,
            insight_type="strength",
            category="reb",
            insight="Better at predicting REB than PTS",
            evidence=f"REB: {results.reb_hit_rate*100:.1f}% vs PTS: {results.pts_hit_rate*100:.1f}%"
        ))
    
    return version_id, results


def compare_all_tracked_models(
    db_path: str = "data/db/nba_props.sqlite3",
) -> str:
    """
    Generate comparison report for all tracked model versions.
    
    Returns formatted comparison report.
    """
    from .model_version_tracker import ModelVersionTracker
    
    tracker = ModelVersionTracker(db_path)
    return tracker.get_comparison_report()


def get_model_insights(
    version_id: int,
    db_path: str = "data/db/nba_props.sqlite3",
) -> List[Dict]:
    """Get all insights for a specific model version."""
    from .model_version_tracker import ModelVersionTracker
    
    tracker = ModelVersionTracker(db_path)
    insights = tracker.get_insights(version_id)
    
    return [
        {
            "type": i.insight_type,
            "category": i.category,
            "insight": i.insight,
            "evidence": i.evidence,
        }
        for i in insights
    ]


def lab_comprehensive_test(
    days_back: int = 60,
    track_versions: bool = True,
    db_path: str = "data/db/nba_props.sqlite3",
) -> Dict[str, Any]:
    """
    Run comprehensive model lab test with version tracking.
    
    This tests multiple model configurations and stores results in the
    version tracking system for later comparison.
    
    Args:
        days_back: Number of days to backtest
        track_versions: Whether to save results to version tracker
        db_path: Database path
    
    Returns:
        Dictionary with results summary and best model info
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    configs = get_test_configurations()
    
    print(f"Running comprehensive model lab test ({days_back} days)")
    print(f"Testing {len(configs)} configurations...")
    print("=" * 60)
    
    results = []
    version_ids = []
    
    for i, config in enumerate(configs):
        print(f"[{i+1}/{len(configs)}] {config.name}...")
        
        try:
            if track_versions:
                version_id, result = register_and_backtest_model(
                    config, start_date, end_date, db_path
                )
                version_ids.append(version_id)
            else:
                result = run_model_backtest(config, start_date, end_date, db_path)
            
            results.append(result)
            print(f"    Hit Rate: {result.hit_rate*100:.1f}% ({result.hits}/{result.total_picks})")
        except Exception as e:
            print(f"    Error: {e}")
    
    # Sort by hit rate
    results.sort(key=lambda r: r.hit_rate, reverse=True)
    
    # Print top models
    print("\n" + "=" * 60)
    print("TOP 5 MODELS")
    print("=" * 60)
    
    for i, r in enumerate(results[:5]):
        print(f"#{i+1}: {r.config.name}")
        print(f"    Overall: {r.hit_rate*100:.1f}%")
        print(f"    PTS: {r.pts_hit_rate*100:.1f}% | REB: {r.reb_hit_rate*100:.1f}% | AST: {r.ast_hit_rate*100:.1f}%")
    
    # Print comparison report if tracked
    if track_versions and version_ids:
        print("\n")
        print(compare_all_tracked_models(db_path))
    
    return {
        "results": results,
        "best_model": results[0] if results else None,
        "version_ids": version_ids,
        "test_period": f"{start_date} to {end_date}",
        "configs_tested": len(configs),
    }

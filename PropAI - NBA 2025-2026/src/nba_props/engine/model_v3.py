"""
Model V3 - Enhanced Prediction Model for NBA Props
===================================================

Building on Model V2, this version adds:
1. Stat-type specific weights (AST performs best, then PTS, then REB)
2. Player floor/ceiling analysis
3. Better consistency scoring
4. Opponent defense factors from database
5. Hot/cold streak detection with lookback tuning

Performance Target: 65%+ hit rate with 3+ picks per game

Author: Model Lab Optimization
Version: 3.0
Last Updated: January 2026
"""
from __future__ import annotations

import sqlite3
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from enum import Enum

from ..db import Db
from ..team_aliases import abbrev_from_team_name, normalize_team_abbrev


# ============================================================================
# Model V3 Configuration
# ============================================================================

@dataclass
class ModelV3Config:
    """Enhanced configuration for Model V3."""
    
    # === WEIGHTING (L5/L15/Season) ===
    # AST-specific (our best performer)
    ast_weight_l5: float = 0.30
    ast_weight_l15: float = 0.40
    ast_weight_season: float = 0.30
    
    # PTS-specific
    pts_weight_l5: float = 0.25
    pts_weight_l15: float = 0.45
    pts_weight_season: float = 0.30
    
    # REB-specific (more volatile, weight season more)
    reb_weight_l5: float = 0.20
    reb_weight_l15: float = 0.40
    reb_weight_season: float = 0.40
    
    # === EDGE THRESHOLDS ===
    high_edge_threshold: float = 12.0
    medium_edge_threshold: float = 8.0
    min_edge_threshold: float = 5.0
    
    # === PICK SETTINGS ===
    picks_per_game: int = 3
    max_picks_per_player: int = 2
    min_minutes_threshold: float = 22.0  # Slightly higher for quality
    min_games_required: int = 7  # Need more games for reliability
    
    # === CONSISTENCY ===
    consistency_threshold_low: float = 0.20   # Below this = very consistent
    consistency_threshold_high: float = 0.35  # Above this = volatile
    consistency_bonus: float = 12.0
    consistency_penalty: float = 8.0
    
    # === TREND DETECTION ===
    hot_streak_threshold: float = 12.0   # % above L15
    cold_streak_threshold: float = -12.0 # % below L15
    hot_streak_bonus: float = 0.03       # 3% boost
    cold_streak_penalty: float = 0.03    # 3% reduction
    
    # === FLOOR/CEILING ===
    use_floor_ceiling: bool = True
    floor_weight: float = 0.15           # Weight for player's floor games
    
    # === OPPONENT ADJUSTMENT ===
    use_opponent_adjustment: bool = True
    opponent_adjustment_strength: float = 0.40
    
    def get_weights(self, prop_type: str) -> Tuple[float, float, float]:
        """Get stat-specific weights."""
        if prop_type.upper() == "AST":
            return (self.ast_weight_l5, self.ast_weight_l15, self.ast_weight_season)
        elif prop_type.upper() == "PTS":
            return (self.pts_weight_l5, self.pts_weight_l15, self.pts_weight_season)
        else:  # REB
            return (self.reb_weight_l5, self.reb_weight_l15, self.reb_weight_season)


@dataclass
class EnhancedPlayerStats:
    """Enhanced player statistics with floor/ceiling analysis."""
    player_id: int
    player_name: str
    team_name: str
    team_abbrev: str
    position: str
    
    total_games: int
    
    # L5 averages
    l5_pts: float = 0.0
    l5_reb: float = 0.0
    l5_ast: float = 0.0
    l5_min: float = 0.0
    
    # L15 averages
    l15_pts: float = 0.0
    l15_reb: float = 0.0
    l15_ast: float = 0.0
    l15_min: float = 0.0
    
    # Season averages
    season_pts: float = 0.0
    season_reb: float = 0.0
    season_ast: float = 0.0
    season_min: float = 0.0
    
    # Standard deviations (L15)
    pts_std: float = 0.0
    reb_std: float = 0.0
    ast_std: float = 0.0
    
    # Coefficient of variation
    pts_cv: float = 0.0
    reb_cv: float = 0.0
    ast_cv: float = 0.0
    
    # Floor/Ceiling (10th and 90th percentile of L15)
    pts_floor: float = 0.0
    pts_ceiling: float = 0.0
    reb_floor: float = 0.0
    reb_ceiling: float = 0.0
    ast_floor: float = 0.0
    ast_ceiling: float = 0.0
    
    # Trend indicators
    pts_trend: str = "stable"  # hot, cold, stable
    reb_trend: str = "stable"
    ast_trend: str = "stable"
    pts_trend_pct: float = 0.0
    reb_trend_pct: float = 0.0
    ast_trend_pct: float = 0.0
    
    # Minutes stability
    min_cv: float = 0.0
    
    # Game log
    game_log: List[Dict] = field(default_factory=list)


@dataclass
class PropPick:
    """A single prop pick with full context."""
    player_id: int
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    game_date: str
    
    prop_type: str
    direction: str
    
    projected_value: float
    line: float
    edge_pct: float
    
    confidence_score: float
    confidence_tier: str
    
    # Component scores
    edge_score: float = 0.0
    consistency_score: float = 0.0
    trend_score: float = 0.0
    sample_score: float = 0.0
    
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Outcome tracking
    actual_value: Optional[float] = None
    hit: Optional[bool] = None


@dataclass
class V3BacktestResult:
    """Results from Model V3 backtest."""
    start_date: str
    end_date: str
    config_name: str = "default"
    
    total_picks: int = 0
    hits: int = 0
    
    # By type
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
    high_picks: int = 0
    high_hits: int = 0
    medium_picks: int = 0
    medium_hits: int = 0
    
    # Games
    total_games: int = 0
    games_with_target_picks: int = 0
    
    picks: List[PropPick] = field(default_factory=list)
    daily_results: List[Dict] = field(default_factory=list)
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_picks if self.total_picks > 0 else 0.0
    
    @property
    def high_hit_rate(self) -> float:
        return self.high_hits / self.high_picks if self.high_picks > 0 else 0.0
    
    @property
    def over_hit_rate(self) -> float:
        return self.over_hits / self.over_picks if self.over_picks > 0 else 0.0
    
    @property
    def under_hit_rate(self) -> float:
        return self.under_hits / self.under_picks if self.under_picks > 0 else 0.0


# ============================================================================
# Data Loading
# ============================================================================

def load_player_stats(
    conn: sqlite3.Connection,
    player_id: int,
    before_date: str,
    config: ModelV3Config,
) -> Optional[EnhancedPlayerStats]:
    """Load enhanced player statistics."""
    player_row = conn.execute(
        "SELECT id, name FROM players WHERE id = ?", (player_id,)
    ).fetchone()
    
    if not player_row:
        return None
    
    # Get game log
    rows = conn.execute(
        """
        SELECT 
            g.game_date, b.pts, b.reb, b.ast, b.minutes, b.pos,
            t.name as team_name
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        JOIN teams t ON t.id = b.team_id
        WHERE b.player_id = ?
          AND g.game_date < ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 5
        ORDER BY g.game_date DESC
        LIMIT 30
        """,
        (player_id, before_date),
    ).fetchall()
    
    if len(rows) < config.min_games_required:
        return None
    
    game_log = [dict(r) for r in rows]
    
    # Extract values
    pts_all = [g["pts"] or 0 for g in game_log]
    reb_all = [g["reb"] or 0 for g in game_log]
    ast_all = [g["ast"] or 0 for g in game_log]
    min_all = [g["minutes"] or 0 for g in game_log]
    
    # L5 and L15
    pts_l5, pts_l15 = pts_all[:5], pts_all[:15]
    reb_l5, reb_l15 = reb_all[:5], reb_all[:15]
    ast_l5, ast_l15 = ast_all[:5], ast_all[:15]
    min_l5, min_l15 = min_all[:5], min_all[:15]
    
    def safe_avg(vals): return sum(vals) / len(vals) if vals else 0.0
    def safe_std(vals): return statistics.stdev(vals) if len(vals) > 1 else 0.0
    def safe_cv(vals): 
        avg = safe_avg(vals)
        return safe_std(vals) / avg if avg > 0 else 0.0
    
    def percentile(vals, pct):
        if not vals:
            return 0.0
        sorted_vals = sorted(vals)
        idx = int(len(sorted_vals) * pct / 100)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]
    
    # Calculate trend
    def calc_trend(l5_avg, l15_avg, threshold_hot, threshold_cold):
        if l15_avg == 0:
            return "stable", 0.0
        diff_pct = (l5_avg - l15_avg) / l15_avg * 100
        if diff_pct >= threshold_hot:
            return "hot", diff_pct
        elif diff_pct <= threshold_cold:
            return "cold", diff_pct
        return "stable", diff_pct
    
    pts_trend, pts_trend_pct = calc_trend(safe_avg(pts_l5), safe_avg(pts_l15), 
                                           config.hot_streak_threshold, config.cold_streak_threshold)
    reb_trend, reb_trend_pct = calc_trend(safe_avg(reb_l5), safe_avg(reb_l15),
                                           config.hot_streak_threshold, config.cold_streak_threshold)
    ast_trend, ast_trend_pct = calc_trend(safe_avg(ast_l5), safe_avg(ast_l15),
                                           config.hot_streak_threshold, config.cold_streak_threshold)
    
    team_name = game_log[0]["team_name"] if game_log else ""
    position = game_log[0]["pos"] if game_log else "G"
    
    return EnhancedPlayerStats(
        player_id=player_id,
        player_name=player_row["name"],
        team_name=team_name,
        team_abbrev=abbrev_from_team_name(team_name) or "",
        position=position or "G",
        total_games=len(game_log),
        
        l5_pts=safe_avg(pts_l5), l5_reb=safe_avg(reb_l5), l5_ast=safe_avg(ast_l5), l5_min=safe_avg(min_l5),
        l15_pts=safe_avg(pts_l15), l15_reb=safe_avg(reb_l15), l15_ast=safe_avg(ast_l15), l15_min=safe_avg(min_l15),
        season_pts=safe_avg(pts_all), season_reb=safe_avg(reb_all), season_ast=safe_avg(ast_all), season_min=safe_avg(min_all),
        
        pts_std=safe_std(pts_l15), reb_std=safe_std(reb_l15), ast_std=safe_std(ast_l15),
        pts_cv=safe_cv(pts_l15), reb_cv=safe_cv(reb_l15), ast_cv=safe_cv(ast_l15),
        
        pts_floor=percentile(pts_l15, 10), pts_ceiling=percentile(pts_l15, 90),
        reb_floor=percentile(reb_l15, 10), reb_ceiling=percentile(reb_l15, 90),
        ast_floor=percentile(ast_l15, 10), ast_ceiling=percentile(ast_l15, 90),
        
        pts_trend=pts_trend, reb_trend=reb_trend, ast_trend=ast_trend,
        pts_trend_pct=pts_trend_pct, reb_trend_pct=reb_trend_pct, ast_trend_pct=ast_trend_pct,
        
        min_cv=safe_cv(min_l15),
        game_log=game_log,
    )


def get_opponent_defense_factor(
    conn: sqlite3.Connection,
    opponent_abbrev: str,
    position: str,
    prop_type: str,
) -> float:
    """Get opponent defense factor from database or calculate from data."""
    # Try to get from defense_vs_position table first
    try:
        from ..ingest.defense_position_parser import calculate_defense_factor
        defense_info = calculate_defense_factor(conn, opponent_abbrev, position, prop_type.lower())
        if defense_info and "factor" in defense_info:
            return defense_info["factor"]
    except:
        pass
    
    # Fallback: calculate from boxscore data
    from ..standings import _team_ids_by_abbrev
    
    opp_abbrev = normalize_team_abbrev(opponent_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(opp_abbrev, [])
    
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
          AND b.minutes > 15
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
        WHERE pos = ? AND minutes > 15
        """,
        (pos,),
    ).fetchone()
    
    league_avg = league_row["league_avg"] if league_row and league_row["league_avg"] else None
    
    if allowed_avg and league_avg and league_avg > 0:
        return allowed_avg / league_avg
    
    return 1.0


# ============================================================================
# Projection Engine
# ============================================================================

def calculate_projection(
    stats: EnhancedPlayerStats,
    prop_type: str,
    opponent_abbrev: str,
    conn: sqlite3.Connection,
    config: ModelV3Config,
) -> Tuple[float, float, float, List[str], List[str]]:
    """
    Calculate projection with all adjustments.
    
    Returns: (projected_value, line, edge_pct, reasons, warnings)
    """
    pt = prop_type.lower()
    reasons = []
    warnings = []
    
    # Get stat-specific weights
    w_l5, w_l15, w_season = config.get_weights(prop_type)
    
    # Get raw values
    l5_val = getattr(stats, f"l5_{pt}")
    l15_val = getattr(stats, f"l15_{pt}")
    season_val = getattr(stats, f"season_{pt}")
    
    # Base weighted projection
    total_w = w_l5 + w_l15 + w_season
    projected = (l5_val * w_l5 + l15_val * w_l15 + season_val * w_season) / total_w
    
    # Apply floor weighting if enabled
    if config.use_floor_ceiling:
        floor = getattr(stats, f"{pt}_floor")
        # Slightly weight towards floor for conservative estimate
        projected = projected * (1 - config.floor_weight) + floor * config.floor_weight
    
    # Trend adjustment
    trend = getattr(stats, f"{pt}_trend")
    if trend == "hot":
        projected *= (1 + config.hot_streak_bonus)
        reasons.append(f"Hot streak (+{config.hot_streak_bonus*100:.0f}%)")
    elif trend == "cold":
        projected *= (1 - config.cold_streak_penalty)
        warnings.append(f"Cold streak (-{config.cold_streak_penalty*100:.0f}%)")
    
    # Opponent adjustment
    if config.use_opponent_adjustment:
        opp_factor = get_opponent_defense_factor(conn, opponent_abbrev, stats.position, prop_type)
        if opp_factor != 1.0:
            # Dampen the adjustment
            adj = 1 + (opp_factor - 1) * config.opponent_adjustment_strength
            adj = max(0.90, min(1.10, adj))  # Cap at 10% adjustment
            projected *= adj
            if opp_factor > 1.02:
                reasons.append(f"Weak defense ({(adj-1)*100:+.0f}%)")
            elif opp_factor < 0.98:
                warnings.append(f"Strong defense ({(adj-1)*100:+.0f}%)")
    
    # Calculate line (L10/L7/L5 average per Idea.txt)
    vals = [g[pt] or 0 for g in stats.game_log]
    if len(vals) >= 10:
        line = sum(vals[:10]) / 10
    elif len(vals) >= 7:
        line = sum(vals[:7]) / 7
    elif len(vals) >= 5:
        line = sum(vals[:5]) / 5
    else:
        line = sum(vals) / len(vals) if vals else projected
    
    # Calculate edge
    edge_pct = (projected - line) / line * 100 if line > 0 else 0
    
    return projected, line, edge_pct, reasons, warnings


def generate_pick(
    stats: EnhancedPlayerStats,
    prop_type: str,
    opponent_abbrev: str,
    game_date: str,
    conn: sqlite3.Connection,
    config: ModelV3Config,
) -> Optional[PropPick]:
    """Generate a single pick with confidence scoring."""
    
    projected, line, edge_pct, reasons, warnings = calculate_projection(
        stats, prop_type, opponent_abbrev, conn, config
    )
    
    # Determine direction
    if edge_pct >= config.min_edge_threshold:
        direction = "OVER"
    elif edge_pct <= -config.min_edge_threshold:
        direction = "UNDER"
        edge_pct = abs(edge_pct)
    else:
        return None
    
    # === Calculate component scores ===
    
    # Edge score (0-30)
    if edge_pct >= 20:
        edge_score = 30
    elif edge_pct >= 15:
        edge_score = 25
    elif edge_pct >= 12:
        edge_score = 20
    elif edge_pct >= 10:
        edge_score = 15
    elif edge_pct >= 7:
        edge_score = 10
    else:
        edge_score = 5
    
    # Consistency score (0-25)
    cv = getattr(stats, f"{prop_type.lower()}_cv")
    if cv < config.consistency_threshold_low:
        consistency_score = 25
        reasons.append("Very consistent")
    elif cv < 0.28:
        consistency_score = 18
    elif cv < config.consistency_threshold_high:
        consistency_score = 12
    else:
        consistency_score = 5
        warnings.append("High variance")
    
    # Trend score (0-15)
    trend = getattr(stats, f"{prop_type.lower()}_trend")
    if (direction == "OVER" and trend == "hot") or (direction == "UNDER" and trend == "cold"):
        trend_score = 15
    elif trend == "stable":
        trend_score = 10
    else:
        trend_score = 3
    
    # Sample score (0-15)
    if stats.total_games >= 20:
        sample_score = 15
    elif stats.total_games >= 15:
        sample_score = 12
    elif stats.total_games >= 10:
        sample_score = 8
    else:
        sample_score = 4
        warnings.append(f"Limited data ({stats.total_games} games)")
    
    # Minutes stability bonus (0-10)
    if stats.min_cv < 0.12:
        minutes_bonus = 10
        reasons.append("Stable minutes")
    elif stats.min_cv < 0.18:
        minutes_bonus = 6
    else:
        minutes_bonus = 0
    
    # Total confidence (capped at 95)
    confidence = min(95, edge_score + consistency_score + trend_score + sample_score + minutes_bonus)
    
    # Determine tier
    if edge_pct >= config.high_edge_threshold and confidence >= 70:
        tier = "HIGH"
    elif edge_pct >= config.medium_edge_threshold and confidence >= 55:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    
    # Add key stats to reasons
    reasons.insert(0, f"{edge_pct:.1f}% edge")
    reasons.append(f"L5:{getattr(stats, f'l5_{prop_type.lower()}'):.1f} L15:{getattr(stats, f'l15_{prop_type.lower()}'):.1f} Proj:{projected:.1f}")
    
    return PropPick(
        player_id=stats.player_id,
        player_name=stats.player_name,
        team_abbrev=stats.team_abbrev,
        opponent_abbrev=opponent_abbrev,
        game_date=game_date,
        prop_type=prop_type,
        direction=direction,
        projected_value=round(projected, 1),
        line=round(line, 1),
        edge_pct=round(edge_pct, 1),
        confidence_score=round(confidence, 1),
        confidence_tier=tier,
        edge_score=edge_score,
        consistency_score=consistency_score,
        trend_score=trend_score,
        sample_score=sample_score,
        reasons=reasons,
        warnings=warnings,
    )


# ============================================================================
# Game Pick Generation
# ============================================================================

def generate_game_picks(
    conn: sqlite3.Connection,
    game_id: int,
    game_date: str,
    team1_name: str,
    team2_name: str,
    config: ModelV3Config,
) -> List[PropPick]:
    """Generate picks for a single game."""
    
    team1_abbrev = abbrev_from_team_name(team1_name) or ""
    team2_abbrev = abbrev_from_team_name(team2_name) or ""
    
    all_picks = []
    
    # Get top players from each team
    for team_name, opp_abbrev in [(team1_name, team2_abbrev), (team2_name, team1_abbrev)]:
        team_row = conn.execute("SELECT id FROM teams WHERE name = ?", (team_name,)).fetchone()
        if not team_row:
            continue
        
        # Get players with most minutes
        players = conn.execute(
            """
            SELECT b.player_id, AVG(b.minutes) as avg_min
            FROM boxscore_player b
            JOIN games g ON g.id = b.game_id
            WHERE b.team_id = ?
              AND g.game_date < ?
              AND b.minutes > ?
            GROUP BY b.player_id
            HAVING COUNT(*) >= ?
            ORDER BY avg_min DESC
            LIMIT 10
            """,
            (team_row["id"], game_date, config.min_minutes_threshold, config.min_games_required),
        ).fetchall()
        
        for player_row in players:
            stats = load_player_stats(conn, player_row["player_id"], game_date, config)
            if not stats or stats.season_min < config.min_minutes_threshold:
                continue
            
            for prop_type in ["AST", "PTS", "REB"]:  # AST first (best performer)
                pick = generate_pick(stats, prop_type, opp_abbrev, game_date, conn, config)
                if pick and pick.confidence_tier in ("HIGH", "MEDIUM"):
                    all_picks.append(pick)
    
    # Sort by confidence
    all_picks.sort(key=lambda p: (p.confidence_score, p.edge_pct), reverse=True)
    
    # Select picks with variety
    selected = []
    player_counts = {}
    
    for pick in all_picks:
        if player_counts.get(pick.player_id, 0) >= config.max_picks_per_player:
            continue
        
        selected.append(pick)
        player_counts[pick.player_id] = player_counts.get(pick.player_id, 0) + 1
        
        if len(selected) >= config.picks_per_game:
            break
    
    # If not enough picks, relax criteria
    if len(selected) < config.picks_per_game:
        for pick in all_picks:
            if pick in selected:
                continue
            if player_counts.get(pick.player_id, 0) >= config.max_picks_per_player:
                continue
            
            selected.append(pick)
            player_counts[pick.player_id] = player_counts.get(pick.player_id, 0) + 1
            
            if len(selected) >= config.picks_per_game:
                break
    
    return selected


# ============================================================================
# Backtesting
# ============================================================================

def run_backtest_v3(
    start_date: str,
    end_date: str,
    config: Optional[ModelV3Config] = None,
    db_path: str = "data/db/nba_props.sqlite3",
    verbose: bool = True,
) -> V3BacktestResult:
    """Run comprehensive backtest of Model V3."""
    
    if config is None:
        config = ModelV3Config()
    
    db = Db(db_path)
    result = V3BacktestResult(start_date=start_date, end_date=end_date)
    
    with db.connect() as conn:
        # Get all games
        games = conn.execute(
            """
            SELECT g.id, g.game_date, t1.name as team1_name, t2.name as team2_name
            FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            WHERE g.game_date BETWEEN ? AND ?
            ORDER BY g.game_date
            """,
            (start_date, end_date),
        ).fetchall()
        
        result.total_games = len(games)
        
        if verbose:
            print(f"Model V3 Backtest: {len(games)} games from {start_date} to {end_date}")
        
        for game in games:
            picks = generate_game_picks(
                conn, game["id"], game["game_date"],
                game["team1_name"], game["team2_name"], config
            )
            
            if len(picks) >= config.picks_per_game:
                result.games_with_target_picks += 1
            
            for pick in picks:
                # Get actual stats
                actual = conn.execute(
                    """
                    SELECT b.pts, b.reb, b.ast
                    FROM boxscore_player b
                    JOIN games g ON g.id = b.game_id
                    WHERE b.player_id = ? AND g.game_date = ? AND b.minutes > 0
                    """,
                    (pick.player_id, game["game_date"]),
                ).fetchone()
                
                if not actual:
                    continue
                
                actual_val = actual[pick.prop_type.lower()] or 0
                pick.actual_value = actual_val
                
                hit = (actual_val > pick.line) if pick.direction == "OVER" else (actual_val < pick.line)
                pick.hit = hit
                
                result.picks.append(pick)
                result.total_picks += 1
                
                if hit:
                    result.hits += 1
                
                # Track by type
                if pick.prop_type == "PTS":
                    result.pts_picks += 1
                    if hit: result.pts_hits += 1
                elif pick.prop_type == "REB":
                    result.reb_picks += 1
                    if hit: result.reb_hits += 1
                else:
                    result.ast_picks += 1
                    if hit: result.ast_hits += 1
                
                # Track by direction
                if pick.direction == "OVER":
                    result.over_picks += 1
                    if hit: result.over_hits += 1
                else:
                    result.under_picks += 1
                    if hit: result.under_hits += 1
                
                # Track by confidence
                if pick.confidence_tier == "HIGH":
                    result.high_picks += 1
                    if hit: result.high_hits += 1
                else:
                    result.medium_picks += 1
                    if hit: result.medium_hits += 1
        
        if verbose:
            print_v3_results(result)
    
    return result


def print_v3_results(result: V3BacktestResult):
    """Print formatted Model V3 results."""
    print("\n" + "=" * 65)
    print("MODEL V3 BACKTEST RESULTS")
    print("=" * 65)
    print(f"Period: {result.start_date} to {result.end_date}")
    print(f"Games: {result.total_games} ({result.games_with_target_picks} with target picks)")
    print()
    print(f"OVERALL HIT RATE: {result.hit_rate*100:.1f}% ({result.hits}/{result.total_picks})")
    print()
    print("BY PROP TYPE:")
    if result.pts_picks: print(f"  PTS: {result.pts_hits}/{result.pts_picks} = {result.pts_hits/result.pts_picks*100:.1f}%")
    if result.reb_picks: print(f"  REB: {result.reb_hits}/{result.reb_picks} = {result.reb_hits/result.reb_picks*100:.1f}%")
    if result.ast_picks: print(f"  AST: {result.ast_hits}/{result.ast_picks} = {result.ast_hits/result.ast_picks*100:.1f}%")
    print()
    print("BY DIRECTION:")
    if result.over_picks: print(f"  OVER:  {result.over_hits}/{result.over_picks} = {result.over_hit_rate*100:.1f}%")
    if result.under_picks: print(f"  UNDER: {result.under_hits}/{result.under_picks} = {result.under_hit_rate*100:.1f}%")
    print()
    print("BY CONFIDENCE:")
    if result.high_picks: print(f"  HIGH:   {result.high_hits}/{result.high_picks} = {result.high_hit_rate*100:.1f}%")
    if result.medium_picks: print(f"  MEDIUM: {result.medium_hits}/{result.medium_picks} = {result.medium_hits/result.medium_picks*100:.1f}%")
    print("=" * 65)


# ============================================================================
# Quick Test & Grid Search
# ============================================================================

def quick_test_v3(days_back: int = 21) -> V3BacktestResult:
    """Quick test with default config."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    return run_backtest_v3(start_date, end_date)


def grid_search(days_back: int = 21, verbose: bool = True) -> List[Tuple[str, float, V3BacktestResult]]:
    """Run grid search over configurations."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    configs = [
        ("Default", ModelV3Config()),
        ("Higher Edge (14/10)", ModelV3Config(high_edge_threshold=14.0, medium_edge_threshold=10.0, min_edge_threshold=7.0)),
        ("Lower Edge (10/7)", ModelV3Config(high_edge_threshold=10.0, medium_edge_threshold=7.0, min_edge_threshold=4.0)),
        ("More L5", ModelV3Config(pts_weight_l5=0.35, pts_weight_l15=0.35, ast_weight_l5=0.40)),
        ("More Season", ModelV3Config(pts_weight_season=0.40, reb_weight_season=0.45, ast_weight_season=0.35)),
        ("No Floor", ModelV3Config(use_floor_ceiling=False)),
        ("Strong Opp", ModelV3Config(opponent_adjustment_strength=0.55)),
        ("Min 25 Min", ModelV3Config(min_minutes_threshold=25.0)),
    ]
    
    results = []
    
    for name, config in configs:
        r = run_backtest_v3(start_date, end_date, config, verbose=False)
        results.append((name, r.hit_rate, r))
        if verbose:
            print(f"{name}: {r.hit_rate*100:.1f}% ({r.hits}/{r.total_picks})")
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results


if __name__ == "__main__":
    quick_test_v3()

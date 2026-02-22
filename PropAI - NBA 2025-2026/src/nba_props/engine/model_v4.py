"""
Model V4 - Production NBA Props Prediction Model (IMPROVED)
============================================================

IMPROVEMENTS OVER PREVIOUS VERSION:
-----------------------------------
1. Balanced prop type distribution (ensures PTS/REB/AST variety)
2. Minimum line thresholds to avoid trivial picks
3. Star player priority (>23 min avg = star)
4. Value-weighted scoring (higher lines = more valuable)
5. Better pick selection algorithm
6. Focus on quality over quantity

KEY FEATURES:
-------------
- Minimum 3 picks per game with prop type variety
- HIGH confidence = high edge + high line value + consistency
- Blocks trivial picks (AST OVER 1.5, etc.)
- Prioritizes star players while avoiding bench players
- Balanced OVER/UNDER distribution

USAGE:
------
    from src.nba_props.engine.model_v4 import (
        get_daily_picks, run_full_backtest, ModelV4Config
    )
    
    picks = get_daily_picks("2026-01-07")
    result = run_full_backtest("2025-12-15", "2026-01-07")

Version: 4.0
Last Updated: January 2026
"""
from __future__ import annotations

import sqlite3
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any

from ..db import Db
from ..team_aliases import abbrev_from_team_name, normalize_team_abbrev


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class ModelV4Config:
    """
    Production configuration with balanced settings.
    """
    # === STAT-SPECIFIC WEIGHTS ===
    # Balanced for stability without over-relying on season
    pts_weight_l5: float = 0.30
    pts_weight_l15: float = 0.40
    pts_weight_season: float = 0.30
    
    reb_weight_l5: float = 0.25
    reb_weight_l15: float = 0.45
    reb_weight_season: float = 0.30
    
    ast_weight_l5: float = 0.30
    ast_weight_l15: float = 0.40
    ast_weight_season: float = 0.30
    
    # === EDGE THRESHOLDS (Optimized via backtesting) ===
    high_edge_threshold: float = 10.0      # For HIGH confidence
    medium_edge_threshold: float = 6.5     # For MEDIUM confidence
    min_edge_threshold: float = 5.0        # Minimum to consider
    
    # === MINIMUM LINE THRESHOLDS ===
    # Avoid trivial picks like "AST OVER 1.5" - key to balanced distribution
    min_pts_line: float = 5.0              # Minimum PTS line to consider
    min_reb_line: float = 2.0              # Minimum REB line to consider
    min_ast_line: float = 2.5              # Raised to balance prop types
    
    # === CONFIDENCE SCORING (Optimized) ===
    high_confidence_min: float = 64.0      # Lowered for more HIGH picks
    medium_confidence_min: float = 50.0
    
    # === PICK SELECTION ===
    picks_per_game: int = 3
    max_picks_per_player: int = 2
    min_minutes_threshold: float = 22.0    # Star players only
    star_minutes_threshold: float = 28.0   # >28 min = star player
    min_games_required: int = 7
    
    # === PROP TYPE BALANCE ===
    # Ensure variety in picks
    min_pts_per_day: int = 1               # At least 1 PTS pick per day (if 6+ games)
    min_reb_per_day: int = 1
    min_ast_per_day: int = 1
    
    # === VALUE SCORING ===
    # Higher lines = more valuable
    pts_value_thresholds: Tuple[float, float, float] = (15.0, 20.0, 28.0)  # Good, Great, Elite
    reb_value_thresholds: Tuple[float, float, float] = (5.0, 7.0, 10.0)
    ast_value_thresholds: Tuple[float, float, float] = (4.0, 6.0, 8.0)
    
    # === ADJUSTMENTS ===
    use_trend_adjustment: bool = True
    use_opponent_adjustment: bool = True
    use_consistency_scoring: bool = True
    
    hot_streak_threshold: float = 15.0     # % above L15 (stricter)
    cold_streak_threshold: float = -15.0   # % below L15
    hot_streak_boost: float = 0.025        # 2.5% boost
    cold_streak_penalty: float = 0.025     # 2.5% penalty
    
    opponent_adj_strength: float = 0.35    # Slightly reduced
    
    low_cv_threshold: float = 0.25         # Relaxed - basketball has natural variance
    high_cv_threshold: float = 0.40        # Relaxed for better balance
    
    def get_weights(self, prop_type: str) -> Tuple[float, float, float]:
        """Get weights for a specific prop type."""
        pt = prop_type.upper()
        if pt == "PTS":
            return (self.pts_weight_l5, self.pts_weight_l15, self.pts_weight_season)
        elif pt == "REB":
            return (self.reb_weight_l5, self.reb_weight_l15, self.reb_weight_season)
        else:  # AST
            return (self.ast_weight_l5, self.ast_weight_l15, self.ast_weight_season)
    
    def get_min_line(self, prop_type: str) -> float:
        """Get minimum line for prop type."""
        pt = prop_type.upper()
        if pt == "PTS":
            return self.min_pts_line
        elif pt == "REB":
            return self.min_reb_line
        return self.min_ast_line
    
    def get_value_thresholds(self, prop_type: str) -> Tuple[float, float, float]:
        """Get value thresholds for prop type."""
        pt = prop_type.upper()
        if pt == "PTS":
            return self.pts_value_thresholds
        elif pt == "REB":
            return self.reb_value_thresholds
        return self.ast_value_thresholds


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PlayerGameLog:
    """Player's historical game data."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: str
    
    # Player tier
    is_star: bool              # True if avg minutes > star threshold
    
    # Counts
    games_played: int
    
    # L5 averages
    l5_pts: float
    l5_reb: float
    l5_ast: float
    l5_min: float
    
    # L15 averages
    l15_pts: float
    l15_reb: float
    l15_ast: float
    l15_min: float
    
    # Season averages
    season_pts: float
    season_reb: float
    season_ast: float
    season_min: float
    
    # Variability (L15 CV)
    pts_cv: float
    reb_cv: float
    ast_cv: float
    min_cv: float
    
    # Trends
    pts_trend: str
    reb_trend: str
    ast_trend: str
    pts_trend_pct: float
    reb_trend_pct: float
    ast_trend_pct: float
    
    # Raw game log
    games: List[Dict] = field(default_factory=list)


@dataclass
class PropPick:
    """A single prop bet recommendation."""
    # Identity
    player_id: int
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    game_date: str
    
    # Pick details
    prop_type: str              # PTS, REB, AST
    direction: str              # OVER, UNDER
    projected_value: float      # Model's projection
    line: float                 # Line (L10/L7/L5 average)
    edge_pct: float             # Edge percentage
    
    # Confidence
    confidence_score: float     # 0-100
    confidence_tier: str        # HIGH, MEDIUM, LOW
    
    # Value (higher lines = more valuable)
    value_score: float          # 0-20
    is_star_player: bool
    
    # Scoring breakdown
    edge_component: float
    consistency_component: float
    trend_component: float
    sample_component: float
    value_component: float
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Result tracking
    actual_value: Optional[float] = None
    hit: Optional[bool] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "player_name": self.player_name,
            "team": self.team_abbrev,
            "opponent": self.opponent_abbrev,
            "date": self.game_date,
            "prop_type": self.prop_type,
            "direction": self.direction,
            "projection": self.projected_value,
            "line": self.line,
            "edge": f"{self.edge_pct:.1f}%",
            "confidence": self.confidence_score,
            "tier": self.confidence_tier,
            "value_score": self.value_score,
            "is_star": self.is_star_player,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "actual": self.actual_value,
            "hit": self.hit,
        }
    
    @property
    def rank_score(self) -> float:
        """Combined score for ranking (used in pick selection)."""
        # Combine confidence + value + star bonus
        star_bonus = 5 if self.is_star_player else 0
        return self.confidence_score + self.value_score + star_bonus


@dataclass
class DailyPicks:
    """All picks for a single day."""
    date: str
    games: int
    picks: List[PropPick] = field(default_factory=list)
    
    @property
    def high_confidence_picks(self) -> List[PropPick]:
        return [p for p in self.picks if p.confidence_tier == "HIGH"]
    
    @property
    def picks_count(self) -> int:
        return len(self.picks)
    
    @property
    def high_count(self) -> int:
        return len(self.high_confidence_picks)
    
    def by_prop_type(self, prop_type: str) -> List[PropPick]:
        return [p for p in self.picks if p.prop_type == prop_type.upper()]


@dataclass
class BacktestResult:
    """Comprehensive backtest results."""
    start_date: str
    end_date: str
    config: ModelV4Config
    
    # Overall
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
    games_with_picks: int = 0
    
    # All picks
    all_picks: List[PropPick] = field(default_factory=list)
    
    # Daily breakdown
    daily_results: List[Dict] = field(default_factory=list)
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_picks if self.total_picks > 0 else 0.0
    
    @property
    def high_hit_rate(self) -> float:
        return self.high_hits / self.high_picks if self.high_picks > 0 else 0.0
    
    @property
    def medium_hit_rate(self) -> float:
        return self.medium_hits / self.medium_picks if self.medium_picks > 0 else 0.0
    
    @property
    def pts_hit_rate(self) -> float:
        return self.pts_hits / self.pts_picks if self.pts_picks > 0 else 0.0
    
    @property
    def reb_hit_rate(self) -> float:
        return self.reb_hits / self.reb_picks if self.reb_picks > 0 else 0.0
    
    @property
    def ast_hit_rate(self) -> float:
        return self.ast_hits / self.ast_picks if self.ast_picks > 0 else 0.0
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            "=" * 65,
            "MODEL V4 - BACKTEST RESULTS",
            "=" * 65,
            f"Period: {self.start_date} to {self.end_date}",
            f"Games: {self.total_games} ({self.games_with_picks} with picks)",
            "",
            f"OVERALL: {self.hit_rate*100:.1f}% ({self.hits}/{self.total_picks})",
            "",
            "BY CONFIDENCE:",
            f"  HIGH:   {self.high_hit_rate*100:.1f}% ({self.high_hits}/{self.high_picks})",
            f"  MEDIUM: {self.medium_hit_rate*100:.1f}% ({self.medium_hits}/{self.medium_picks})",
            "",
            "BY PROP TYPE:",
            f"  PTS: {self.pts_hit_rate*100:.1f}% ({self.pts_hits}/{self.pts_picks})",
            f"  REB: {self.reb_hit_rate*100:.1f}% ({self.reb_hits}/{self.reb_picks})",
            f"  AST: {self.ast_hit_rate*100:.1f}% ({self.ast_hits}/{self.ast_picks})",
            "",
            "PROP DISTRIBUTION:",
            f"  PTS: {self.pts_picks} ({self.pts_picks/max(1,self.total_picks)*100:.1f}%)",
            f"  REB: {self.reb_picks} ({self.reb_picks/max(1,self.total_picks)*100:.1f}%)",
            f"  AST: {self.ast_picks} ({self.ast_picks/max(1,self.total_picks)*100:.1f}%)",
            "=" * 65,
        ]
        
        return "\n".join(lines)


# ============================================================================
# Core Functions
# ============================================================================

def _load_player_game_log(
    conn: sqlite3.Connection,
    player_id: int,
    before_date: str,
    config: ModelV4Config,
) -> Optional[PlayerGameLog]:
    """Load player's game history."""
    
    player = conn.execute(
        "SELECT id, name FROM players WHERE id = ?", (player_id,)
    ).fetchone()
    
    if not player:
        return None
    
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
    
    games = [dict(r) for r in rows]
    
    # Extract stat arrays
    pts = [g["pts"] or 0 for g in games]
    reb = [g["reb"] or 0 for g in games]
    ast = [g["ast"] or 0 for g in games]
    mins = [g["minutes"] or 0 for g in games]
    
    # Calculate averages
    def avg(vals, n=None):
        subset = vals[:n] if n else vals
        return sum(subset) / len(subset) if subset else 0.0
    
    def cv(vals):
        if len(vals) < 2:
            return 0.0
        mean = sum(vals) / len(vals)
        if mean == 0:
            return 0.0
        std = statistics.stdev(vals)
        return std / mean
    
    def trend(l5_avg, l15_avg, hot_th, cold_th):
        if l15_avg == 0:
            return "stable", 0.0
        pct = (l5_avg - l15_avg) / l15_avg * 100
        if pct >= hot_th:
            return "hot", pct
        elif pct <= cold_th:
            return "cold", pct
        return "stable", pct
    
    pts_trend, pts_trend_pct = trend(avg(pts, 5), avg(pts, 15), 
                                      config.hot_streak_threshold, config.cold_streak_threshold)
    reb_trend, reb_trend_pct = trend(avg(reb, 5), avg(reb, 15),
                                      config.hot_streak_threshold, config.cold_streak_threshold)
    ast_trend, ast_trend_pct = trend(avg(ast, 5), avg(ast, 15),
                                      config.hot_streak_threshold, config.cold_streak_threshold)
    
    team_name = games[0]["team_name"] if games else ""
    position = games[0]["pos"] if games else "G"
    avg_min = avg(mins)
    
    return PlayerGameLog(
        player_id=player_id,
        player_name=player["name"],
        team_abbrev=abbrev_from_team_name(team_name) or "",
        position=position or "G",
        is_star=avg_min >= config.star_minutes_threshold,
        games_played=len(games),
        
        l5_pts=avg(pts, 5), l5_reb=avg(reb, 5), l5_ast=avg(ast, 5), l5_min=avg(mins, 5),
        l15_pts=avg(pts, 15), l15_reb=avg(reb, 15), l15_ast=avg(ast, 15), l15_min=avg(mins, 15),
        season_pts=avg(pts), season_reb=avg(reb), season_ast=avg(ast), season_min=avg(mins),
        
        pts_cv=cv(pts[:15]), reb_cv=cv(reb[:15]), ast_cv=cv(ast[:15]), min_cv=cv(mins[:15]),
        
        pts_trend=pts_trend, reb_trend=reb_trend, ast_trend=ast_trend,
        pts_trend_pct=pts_trend_pct, reb_trend_pct=reb_trend_pct, ast_trend_pct=ast_trend_pct,
        
        games=games,
    )


def _get_opponent_defense_factor(
    conn: sqlite3.Connection,
    opponent_abbrev: str,
    position: str,
    prop_type: str,
) -> float:
    """Get opponent's defense factor for this position/stat."""
    from ..standings import _team_ids_by_abbrev
    
    opp = normalize_team_abbrev(opponent_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(opp, [])
    
    if not team_ids:
        return 1.0
    
    pos = position.upper()[:1] if position else "G"
    stat = prop_type.lower()
    ph = ",".join(["?"] * len(team_ids))
    
    # Stats allowed
    allowed = conn.execute(
        f"""
        SELECT AVG(b.{stat}) as val
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.pos = ?
          AND b.minutes > 15
          AND b.team_id NOT IN ({ph})
          AND (g.team1_id IN ({ph}) OR g.team2_id IN ({ph}))
        """,
        (pos, *team_ids, *team_ids, *team_ids),
    ).fetchone()
    
    # League avg
    league = conn.execute(
        f"SELECT AVG({stat}) as val FROM boxscore_player WHERE pos = ? AND minutes > 15",
        (pos,),
    ).fetchone()
    
    if allowed and league and allowed["val"] and league["val"] and league["val"] > 0:
        return allowed["val"] / league["val"]
    
    return 1.0


def _calculate_projection(
    plog: PlayerGameLog,
    prop_type: str,
    opponent_abbrev: str,
    conn: sqlite3.Connection,
    config: ModelV4Config,
) -> Tuple[float, float, float, List[str], List[str]]:
    """
    Calculate projection with adjustments.
    
    Returns: (projected, line, edge_pct, reasons, warnings)
    """
    pt = prop_type.lower()
    reasons = []
    warnings = []
    
    # Get weights
    w5, w15, ws = config.get_weights(prop_type)
    total_w = w5 + w15 + ws
    
    # Raw values
    l5 = getattr(plog, f"l5_{pt}")
    l15 = getattr(plog, f"l15_{pt}")
    season = getattr(plog, f"season_{pt}")
    
    # Base projection
    projected = (l5 * w5 + l15 * w15 + season * ws) / total_w
    
    # Trend adjustment
    if config.use_trend_adjustment:
        trend = getattr(plog, f"{pt}_trend")
        if trend == "hot":
            projected *= (1 + config.hot_streak_boost)
            reasons.append(f"Hot streak (+{config.hot_streak_boost*100:.0f}%)")
        elif trend == "cold":
            projected *= (1 - config.cold_streak_penalty)
            warnings.append(f"Cold streak")
    
    # Opponent adjustment
    if config.use_opponent_adjustment:
        factor = _get_opponent_defense_factor(conn, opponent_abbrev, plog.position, prop_type)
        if factor != 1.0:
            adj = 1 + (factor - 1) * config.opponent_adj_strength
            adj = max(0.92, min(1.08, adj))
            projected *= adj
            if factor > 1.04:
                reasons.append("Favorable matchup")
            elif factor < 0.96:
                warnings.append("Tough matchup")
    
    # Calculate line (L10/L7/L5 average)
    vals = [g[pt] or 0 for g in plog.games]
    if len(vals) >= 10:
        line = sum(vals[:10]) / 10
    elif len(vals) >= 7:
        line = sum(vals[:7]) / 7
    elif len(vals) >= 5:
        line = sum(vals[:5]) / 5
    else:
        line = sum(vals) / len(vals) if vals else projected
    
    edge_pct = (projected - line) / line * 100 if line > 0 else 0
    
    return projected, line, edge_pct, reasons, warnings


def _calculate_value_score(
    line: float,
    prop_type: str,
    config: ModelV4Config,
) -> float:
    """
    Calculate value score based on line size.
    Higher lines = more valuable (harder to hit).
    
    Returns: 0-20 value score
    """
    thresholds = config.get_value_thresholds(prop_type)
    low, mid, high = thresholds
    
    if line >= high:
        return 20.0  # Elite line
    elif line >= mid:
        return 15.0  # Great line
    elif line >= low:
        return 10.0  # Good line
    else:
        return 5.0   # Low value


def _generate_pick(
    plog: PlayerGameLog,
    prop_type: str,
    opponent_abbrev: str,
    game_date: str,
    conn: sqlite3.Connection,
    config: ModelV4Config,
) -> Optional[PropPick]:
    """Generate a single pick with confidence scoring."""
    
    projected, line, edge_pct, reasons, warnings = _calculate_projection(
        plog, prop_type, opponent_abbrev, conn, config
    )
    
    # Skip if line is below minimum threshold
    min_line = config.get_min_line(prop_type)
    if line < min_line:
        return None
    
    # Determine direction
    if edge_pct >= config.min_edge_threshold:
        direction = "OVER"
    elif edge_pct <= -config.min_edge_threshold:
        direction = "UNDER"
        edge_pct = abs(edge_pct)
    else:
        return None
    
    # === CONFIDENCE SCORING ===
    
    # Edge component (0-30)
    if edge_pct >= 20:
        edge_comp = 30
    elif edge_pct >= 15:
        edge_comp = 25
    elif edge_pct >= 12:
        edge_comp = 20
    elif edge_pct >= 9:
        edge_comp = 15
    elif edge_pct >= 7:
        edge_comp = 10
    else:
        edge_comp = 5
    
    # Consistency component (0-25)
    cv = getattr(plog, f"{prop_type.lower()}_cv")
    if cv < config.low_cv_threshold:
        cons_comp = 25
        reasons.append("Very consistent")
    elif cv < 0.25:
        cons_comp = 18
    elif cv < config.high_cv_threshold:
        cons_comp = 12
    else:
        cons_comp = 5
        warnings.append("High variance")
    
    # Trend component (0-15)
    trend = getattr(plog, f"{prop_type.lower()}_trend")
    if (direction == "OVER" and trend == "hot") or (direction == "UNDER" and trend == "cold"):
        trend_comp = 15
    elif trend == "stable":
        trend_comp = 10
    else:
        trend_comp = 3
    
    # Sample component (0-12)
    if plog.games_played >= 20:
        sample_comp = 12
    elif plog.games_played >= 15:
        sample_comp = 9
    elif plog.games_played >= 10:
        sample_comp = 6
    else:
        sample_comp = 3
        warnings.append(f"Limited data ({plog.games_played}g)")
    
    # Minutes stability bonus (0-8)
    if plog.min_cv < 0.10:
        min_bonus = 8
        reasons.append("Stable minutes")
    elif plog.min_cv < 0.15:
        min_bonus = 5
    else:
        min_bonus = 0
    
    # Value score
    value_score = _calculate_value_score(line, prop_type, config)
    
    # Star player bonus (already factored into rank_score)
    if plog.is_star:
        reasons.append("Star player")
    
    confidence = min(95, edge_comp + cons_comp + trend_comp + sample_comp + min_bonus)
    
    # Determine tier (stricter criteria)
    if edge_pct >= config.high_edge_threshold and confidence >= config.high_confidence_min:
        tier = "HIGH"
    elif edge_pct >= config.medium_edge_threshold and confidence >= config.medium_confidence_min:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    
    reasons.insert(0, f"{edge_pct:.1f}% edge ({direction})")
    
    return PropPick(
        player_id=plog.player_id,
        player_name=plog.player_name,
        team_abbrev=plog.team_abbrev,
        opponent_abbrev=opponent_abbrev,
        game_date=game_date,
        prop_type=prop_type,
        direction=direction,
        projected_value=round(projected, 1),
        line=round(line, 1),
        edge_pct=round(edge_pct, 1),
        confidence_score=round(confidence, 1),
        confidence_tier=tier,
        value_score=value_score,
        is_star_player=plog.is_star,
        edge_component=edge_comp,
        consistency_component=cons_comp,
        trend_component=trend_comp,
        sample_component=sample_comp,
        value_component=value_score,
        reasons=reasons,
        warnings=warnings,
    )


def generate_game_picks(
    conn: sqlite3.Connection,
    game_id: int,
    game_date: str,
    team1_name: str,
    team2_name: str,
    config: ModelV4Config,
) -> List[PropPick]:
    """Generate picks for a single game."""
    
    t1_abbrev = abbrev_from_team_name(team1_name) or ""
    t2_abbrev = abbrev_from_team_name(team2_name) or ""
    
    all_picks = []
    
    for team_name, opp_abbrev in [(team1_name, t2_abbrev), (team2_name, t1_abbrev)]:
        team = conn.execute("SELECT id FROM teams WHERE name = ?", (team_name,)).fetchone()
        if not team:
            continue
        
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
            LIMIT 12
            """,
            (team["id"], game_date, config.min_minutes_threshold, config.min_games_required),
        ).fetchall()
        
        for p in players:
            plog = _load_player_game_log(conn, p["player_id"], game_date, config)
            if not plog or plog.season_min < config.min_minutes_threshold:
                continue
            
            # Process PTS first (most important), then REB, then AST
            for pt in ["PTS", "REB", "AST"]:
                pick = _generate_pick(plog, pt, opp_abbrev, game_date, conn, config)
                if pick and pick.confidence_tier in ("HIGH", "MEDIUM"):
                    all_picks.append(pick)
    
    # Sort by rank_score (confidence + value + star bonus)
    all_picks.sort(key=lambda p: (p.rank_score, p.edge_pct), reverse=True)
    
    # Select with variety and balance
    selected = []
    player_counts = {}
    prop_counts = {"PTS": 0, "REB": 0, "AST": 0}
    
    for pick in all_picks:
        if player_counts.get(pick.player_id, 0) >= config.max_picks_per_player:
            continue
        selected.append(pick)
        player_counts[pick.player_id] = player_counts.get(pick.player_id, 0) + 1
        prop_counts[pick.prop_type] += 1
        if len(selected) >= config.picks_per_game:
            break
    
    # If we don't have 3 picks, relax constraints
    if len(selected) < config.picks_per_game:
        for pick in all_picks:
            if pick in selected:
                continue
            if player_counts.get(pick.player_id, 0) >= config.max_picks_per_player:
                continue
            selected.append(pick)
            player_counts[pick.player_id] = player_counts.get(pick.player_id, 0) + 1
            prop_counts[pick.prop_type] += 1
            if len(selected) >= config.picks_per_game:
                break
    
    return selected


# ============================================================================
# Public API
# ============================================================================

def get_daily_picks(
    game_date: str,
    config: Optional[ModelV4Config] = None,
    db_path: str = "data/db/nba_props.sqlite3",
) -> DailyPicks:
    """
    Generate picks for all games on a given date.
    
    Args:
        game_date: Date string (YYYY-MM-DD)
        config: Model configuration (uses default if None)
        db_path: Path to database
    
    Returns:
        DailyPicks object with all picks for the day
    """
    if config is None:
        config = ModelV4Config()
    
    db = Db(db_path)
    daily = DailyPicks(date=game_date, games=0)
    
    with db.connect() as conn:
        # First try completed games (games table)
        games = conn.execute(
            """
            SELECT g.id, t1.name as team1, t2.name as team2
            FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            WHERE g.game_date = ?
            """,
            (game_date,),
        ).fetchall()
        
        if games:
            # Use completed games
            daily.games = len(games)
            
            all_picks = []
            for game in games:
                picks = generate_game_picks(
                    conn, game["id"], game_date, game["team1"], game["team2"], config
                )
                all_picks.extend(picks)
        else:
            # Fall back to scheduled games (for future dates)
            scheduled = conn.execute(
                """
                SELECT sg.id, t1.name as away_team, t2.name as home_team
                FROM scheduled_games sg
                JOIN teams t1 ON t1.id = sg.away_team_id
                JOIN teams t2 ON t2.id = sg.home_team_id
                WHERE sg.game_date = ?
                """,
                (game_date,),
            ).fetchall()
            
            daily.games = len(scheduled)
            
            all_picks = []
            for game in scheduled:
                # For scheduled games, use away_team as team1 and home_team as team2
                picks = generate_game_picks(
                    conn, game["id"], game_date, game["away_team"], game["home_team"], config
                )
                all_picks.extend(picks)
        
        # Sort all picks by rank score
        all_picks.sort(key=lambda p: (p.rank_score, p.edge_pct), reverse=True)
        
        daily.picks = all_picks
    
    return daily


def run_full_backtest(
    start_date: str,
    end_date: str,
    config: Optional[ModelV4Config] = None,
    db_path: str = "data/db/nba_props.sqlite3",
    verbose: bool = True,
) -> BacktestResult:
    """
    Run comprehensive backtest of the production model.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        config: Model configuration
        db_path: Path to database
        verbose: Print progress
    
    Returns:
        BacktestResult with all metrics
    """
    if config is None:
        config = ModelV4Config()
    
    db = Db(db_path)
    result = BacktestResult(start_date=start_date, end_date=end_date, config=config)
    
    with db.connect() as conn:
        games = conn.execute(
            """
            SELECT g.id, g.game_date, t1.name as team1, t2.name as team2
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
            print(f"Backtesting {len(games)} games from {start_date} to {end_date}...")
        
        for game in games:
            picks = generate_game_picks(
                conn, game["id"], game["game_date"], game["team1"], game["team2"], config
            )
            
            if picks:
                result.games_with_picks += 1
            
            for pick in picks:
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
                
                result.all_picks.append(pick)
                result.total_picks += 1
                
                if hit:
                    result.hits += 1
                
                # By type
                if pick.prop_type == "PTS":
                    result.pts_picks += 1
                    if hit: result.pts_hits += 1
                elif pick.prop_type == "REB":
                    result.reb_picks += 1
                    if hit: result.reb_hits += 1
                else:
                    result.ast_picks += 1
                    if hit: result.ast_hits += 1
                
                # By direction
                if pick.direction == "OVER":
                    result.over_picks += 1
                    if hit: result.over_hits += 1
                else:
                    result.under_picks += 1
                    if hit: result.under_hits += 1
                
                # By confidence
                if pick.confidence_tier == "HIGH":
                    result.high_picks += 1
                    if hit: result.high_hits += 1
                else:
                    result.medium_picks += 1
                    if hit: result.medium_hits += 1
        
        if verbose:
            print(result.summary())
    
    return result


def quick_backtest(days: int = 21, verbose: bool = True) -> BacktestResult:
    """Quick backtest over recent days."""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return run_full_backtest(start, end, verbose=verbose)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("Running Model V4 quick backtest...")
    quick_backtest()

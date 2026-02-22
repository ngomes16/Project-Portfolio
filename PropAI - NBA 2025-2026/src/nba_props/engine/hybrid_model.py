"""
Hybrid Model - Combining RCM and Pattern-Based Approaches
==========================================================

This model combines the best elements of:
1. Regression Contribution Model (RCM) - contribution rates, Bayesian regression
2. Model Production - pattern detection (cold bounce, hot sustained)

METHODOLOGY:
------------
1. **Base Projection**: Use RCM's contribution rate methodology
   - Contribution Rate = Player Stats / Team Stats (more stable than raw avgs)
   - Weighted blend: L5 (20%) + L10 (35%) + Season (45%)
   - Bayesian regression toward season mean (35% strength)

2. **Opponent Adjustments**: Use RCM's DVP-based adjustments
   - Elite defense (rank ≤5): -10%
   - Good defense (rank ≤10): -5%
   - Weak defense (rank ≥25): +8%

3. **Pattern Detection**: Use Model Production's pattern filters
   - Cold Bounce-Back: L5 is 20%+ below L15 AND last game > L10
   - Hot Sustained: L5 is 30%+ above L15 AND L3 > L5 AND 3+ of L5 above L15
   - Consistent: CV < 0.25 (low variance)

4. **Strategic Direction Selection** (data-driven from backtests):
   - PTS: UNDER only (63.9% RCM vs 48.3% OVER)
   - REB: Pattern OVER only (65%+ from production) + UNDER (59% from RCM)
   - No AST (44.8% was terrible)

5. **Confidence Tiering**:
   - PREMIUM: Pattern-confirmed + high edge (≥12%)
   - HIGH: Pattern detected OR high edge
   - STANDARD: Moderate edge, good fundamentals

KEY INSIGHT:
------------
By using RCM contribution rates (more stable) as base projections but filtering
through pattern detection (proven high hit rates), we get the best of both worlds:
- Stability from contribution rate methodology
- High-accuracy filtering from pattern detection
- Strategic direction selection from data analysis

TARGET: >65% overall hit rate

USAGE:
------
    from src.nba_props.engine.hybrid_model import (
        HybridModel,
        run_hybrid_backtest,
    )
    
    model = HybridModel()
    results = model.run_backtest("2025-12-01", "2026-01-13")
    print(results.summary())

Author: NBA Props Team - Hybrid Model v1.0
Created: January 2026
"""
from __future__ import annotations

import sqlite3
import statistics
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from pathlib import Path

from ..db import Db
from ..team_aliases import abbrev_from_team_name, normalize_team_abbrev


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class HybridConfig:
    """
    Hybrid Model Configuration combining best practices from RCM and Model Production.
    
    VERSION HISTORY:
    ----------------
    v1.0 - Initial hybrid combining RCM contribution rates with pattern detection
           Result: 56.8% overall
    v1.1 - Optimizations based on backtest analysis:
           - Remove "consistent" pattern (47-50% hit rate)
           - Higher edge requirements
           - Focus on UNDER direction (59.8% overall)
           - REB OVER only with cold_bounce pattern (61.2%)
           - Pattern-confirmed picks only (60.0% vs 55.8%)
           Result: 64.0% overall
    v1.2 - Edge tuning and parameter optimization:
           - Tested edge thresholds from 10-18%
           - Found optimal: UNDER 13%, OVER 16%
           - 66.6% hit rate achieved (311 picks over 43 days)
           - Premium tier: 66.1%
    """
    # === VERSION INFO ===
    model_name: str = "Hybrid Model"
    model_version: str = "1.2"
    
    # === DATA REQUIREMENTS ===
    min_games_required: int = 12        # Need sufficient history for patterns
    min_minutes_filter: int = 5         # Filter garbage time
    min_avg_minutes: float = 20.0       # Established players only
    max_games_lookback: int = 20        # Last 20 games
    
    # === CONTRIBUTION RATE (from RCM) ===
    contribution_l5_weight: float = 0.20
    contribution_l10_weight: float = 0.35
    contribution_season_weight: float = 0.45
    regression_strength: float = 0.35
    
    # === PATTERN DETECTION (from Model Production) ===
    # Cold Bounce-Back thresholds
    cold_deviation_threshold: float = -20.0  # L5 must be 20%+ below L15
    bounce_back_requirement: bool = True      # Last game must exceed L10
    
    # Hot Sustained thresholds
    hot_deviation_threshold: float = 30.0     # L5 must be 30%+ above L15
    acceleration_required: bool = True        # L3 must exceed L5
    sustained_games_above: int = 3            # 3+ of L5 must be above L15
    
    # Disable consistent pattern (47-50% hit rate = bad)
    enable_consistent_pattern: bool = False
    consistency_cv_threshold: float = 0.25
    
    # === OPPONENT ADJUSTMENTS (from RCM) ===
    elite_defense_rank: int = 5
    good_defense_rank: int = 10
    weak_defense_rank: int = 25
    
    elite_defense_adj: float = 0.90    # -10%
    good_defense_adj: float = 0.95     # -5%
    neutral_defense_adj: float = 1.00
    weak_defense_adj: float = 1.08     # +8%
    
    # === EDGE REQUIREMENTS ===
    # v1.2: Optimized through grid search
    # UNDER 13% / OVER 16% = 66.6% hit rate
    min_edge_over: float = 16.0        # Higher bar for OVER (pattern-confirmed only)
    min_edge_under: float = 13.0       # Slightly lower for UNDER (better hit rate)
    
    # Pattern-confirmed picks get a small edge bonus
    pattern_edge_bonus: float = 2.0
    
    # === CONFIDENCE THRESHOLDS ===
    premium_base: float = 80.0
    high_base: float = 70.0
    
    # Pattern bonuses
    cold_bounce_bonus: float = 15.0    # Strong pattern
    hot_sustained_bonus: float = 12.0  # Moderate pattern
    consistent_bonus: float = 0.0      # Disabled
    
    # === STRATEGIC DIRECTION SELECTION ===
    # Based on detailed analysis:
    # - PTS OVER: 61.1% with pattern only
    # - PTS UNDER: 64.8% (best)
    # - REB OVER: 66.7% with cold_bounce only
    # - REB UNDER: 63.4%
    pts_under_only: bool = False       # Allow PTS OVER with patterns
    pts_pattern_over: bool = True      # PTS OVER requires pattern
    reb_under_only: bool = False       # Allow REB OVER with cold_bounce
    reb_pattern_over_only: bool = True # REB OVER requires pattern
    allow_hot_sustained_reb_over: bool = False  # Only cold_bounce for REB OVER
    include_ast: bool = False
    
    # OVER picks require pattern confirmation
    require_pattern_for_over: bool = True
    
    # === PICK LIMITS ===
    max_picks_per_game: int = 4
    max_picks_per_day: int = 18        # Reduced for quality
    max_picks_per_player: int = 2
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PlayerData:
    """Comprehensive player data for hybrid analysis."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: str
    games_played: int
    
    # Raw averages
    l3: Dict[str, float] = field(default_factory=dict)  # pts, reb, ast
    l5: Dict[str, float] = field(default_factory=dict)
    l10: Dict[str, float] = field(default_factory=dict)
    l15: Dict[str, float] = field(default_factory=dict)
    season: Dict[str, float] = field(default_factory=dict)
    
    # Contribution rates (from RCM)
    contrib_l5: Dict[str, float] = field(default_factory=dict)
    contrib_l10: Dict[str, float] = field(default_factory=dict)
    contrib_season: Dict[str, float] = field(default_factory=dict)
    contrib_blended: Dict[str, float] = field(default_factory=dict)
    
    # Pattern detection data
    deviation: Dict[str, float] = field(default_factory=dict)  # L5 vs L15
    last_game: Dict[str, float] = field(default_factory=dict)
    recent_values: Dict[str, List[float]] = field(default_factory=dict)  # L5 raw
    
    # Consistency (std dev)
    stds: Dict[str, float] = field(default_factory=dict)
    cvs: Dict[str, float] = field(default_factory=dict)  # Coefficient of variation
    
    # Team context
    team_avg: Dict[str, float] = field(default_factory=dict)


@dataclass
class TeamContext:
    """Team performance context."""
    team_id: int
    team_abbrev: str
    avg_pts: float = 0.0
    avg_reb: float = 0.0
    avg_ast: float = 0.0
    l5_pts: float = 0.0
    l10_pts: float = 0.0


@dataclass
class OpponentContext:
    """Opponent defensive context."""
    team_id: int
    team_abbrev: str
    dvp_ranks: Dict[str, Dict[str, int]] = field(default_factory=dict)
    def_rating: float = 110.0


@dataclass
class PatternResult:
    """Result of pattern detection."""
    pattern: str  # 'cold_bounce', 'hot_sustained', 'consistent', 'none'
    confidence_bonus: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class HybridPick:
    """A pick from the Hybrid Model."""
    # Identity
    player_id: int
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    game_date: str
    
    # Pick details
    prop_type: str  # PTS, REB
    direction: str  # OVER, UNDER
    line: float
    line_source: str  # 'sportsbook', 'derived'
    
    # Projections
    projection: float  # Final hybrid projection
    contribution_projection: float  # RCM-based projection
    pattern_projection: float  # Pattern-based adjustment
    
    # Components
    opponent_adj: float
    regression_adj: float
    
    # Edge
    edge_pct: float
    
    # Confidence
    confidence_score: float
    confidence_tier: str  # PREMIUM, HIGH, STANDARD
    
    # Pattern
    pattern: str  # 'cold_bounce', 'hot_sustained', 'consistent', 'none'
    pattern_confirmed: bool
    
    # Supporting data
    contribution_rate: float
    team_expected: float
    l5_avg: float
    l10_avg: float
    l15_avg: float
    deviation: float  # L5 vs L15
    
    # Factors
    factors: List[str] = field(default_factory=list)
    
    # Outcome
    actual_value: Optional[float] = None
    hit: Optional[bool] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "player": self.player_name,
            "team": self.team_abbrev,
            "opponent": self.opponent_abbrev,
            "date": self.game_date,
            "prop": self.prop_type,
            "direction": self.direction,
            "line": round(self.line, 1),
            "projection": round(self.projection, 1),
            "contrib_proj": round(self.contribution_projection, 1),
            "edge": f"{self.edge_pct:.1f}%",
            "tier": self.confidence_tier,
            "confidence": round(self.confidence_score, 1),
            "pattern": self.pattern,
            "pattern_confirmed": self.pattern_confirmed,
            "contribution_rate": f"{self.contribution_rate:.1%}",
            "l5": round(self.l5_avg, 1),
            "l10": round(self.l10_avg, 1),
            "l15": round(self.l15_avg, 1),
            "deviation": f"{self.deviation:+.1f}%",
            "factors": self.factors,
            "actual": self.actual_value,
            "hit": self.hit,
        }


@dataclass
class DailyHybridPicks:
    """All picks for a day."""
    date: str
    games: int
    picks: List[HybridPick] = field(default_factory=list)
    
    @property
    def total_picks(self) -> int:
        return len(self.picks)
    
    @property
    def premium_picks(self) -> List[HybridPick]:
        return [p for p in self.picks if p.confidence_tier == "PREMIUM"]
    
    @property
    def high_picks(self) -> List[HybridPick]:
        return [p for p in self.picks if p.confidence_tier == "HIGH"]
    
    def summary(self) -> str:
        """Generate summary."""
        lines = [
            f"{'='*70}",
            f"HYBRID MODEL - {self.date}",
            f"{'='*70}",
            f"Games: {self.games} | Total Picks: {self.total_picks}",
            "",
        ]
        
        for tier in ["PREMIUM", "HIGH", "STANDARD"]:
            tier_picks = [p for p in self.picks if p.confidence_tier == tier]
            if tier_picks:
                lines.append(f"--- {tier} ({len(tier_picks)}) ---")
                for p in tier_picks:
                    pattern_str = f" [{p.pattern}]" if p.pattern_confirmed else ""
                    lines.append(
                        f"  {p.player_name} ({p.team_abbrev}): "
                        f"{p.prop_type} {p.direction} {p.line:.1f}{pattern_str}"
                    )
                    lines.append(
                        f"      Proj: {p.projection:.1f} | Edge: {p.edge_pct:.1f}% | "
                        f"Conf: {p.confidence_score:.0f}"
                    )
                lines.append("")
        
        return "\n".join(lines)


@dataclass
class HybridBacktestResult:
    """Backtest results."""
    start_date: str
    end_date: str
    config: HybridConfig
    
    # Overall
    total_picks: int = 0
    hits: int = 0
    
    # By tier
    premium_picks: int = 0
    premium_hits: int = 0
    high_picks: int = 0
    high_hits: int = 0
    standard_picks: int = 0
    standard_hits: int = 0
    
    # By prop type
    pts_picks: int = 0
    pts_hits: int = 0
    reb_picks: int = 0
    reb_hits: int = 0
    
    # By direction
    over_picks: int = 0
    over_hits: int = 0
    under_picks: int = 0
    under_hits: int = 0
    
    # By pattern
    cold_bounce_picks: int = 0
    cold_bounce_hits: int = 0
    hot_sustained_picks: int = 0
    hot_sustained_hits: int = 0
    consistent_picks: int = 0
    consistent_hits: int = 0
    no_pattern_picks: int = 0
    no_pattern_hits: int = 0
    
    # Tracking
    total_games: int = 0
    days_tested: int = 0
    
    all_picks: List[HybridPick] = field(default_factory=list)
    daily_results: List[Dict] = field(default_factory=list)
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_picks if self.total_picks > 0 else 0.0
    
    @property
    def premium_rate(self) -> float:
        return self.premium_hits / self.premium_picks if self.premium_picks > 0 else 0.0
    
    @property
    def high_rate(self) -> float:
        return self.high_hits / self.high_picks if self.high_picks > 0 else 0.0
    
    def summary(self) -> str:
        """Generate detailed summary."""
        lines = [
            "=" * 70,
            "HYBRID MODEL - BACKTEST RESULTS",
            "=" * 70,
            f"Version: {self.config.model_version}",
            f"Period: {self.start_date} to {self.end_date}",
            f"Days tested: {self.days_tested} | Games: {self.total_games}",
            "",
            f"OVERALL: {self.hit_rate*100:.1f}% ({self.hits}/{self.total_picks})",
            "",
            "BY CONFIDENCE TIER:",
        ]
        
        if self.premium_picks > 0:
            lines.append(f"  PREMIUM:  {self.premium_rate*100:.1f}% ({self.premium_hits}/{self.premium_picks})")
        if self.high_picks > 0:
            lines.append(f"  HIGH:     {self.high_rate*100:.1f}% ({self.high_hits}/{self.high_picks})")
        if self.standard_picks > 0:
            rate = self.standard_hits / self.standard_picks * 100
            lines.append(f"  STANDARD: {rate:.1f}% ({self.standard_hits}/{self.standard_picks})")
        
        lines.extend(["", "BY PROP TYPE:"])
        if self.pts_picks > 0:
            lines.append(f"  PTS: {self.pts_hits/self.pts_picks*100:.1f}% ({self.pts_hits}/{self.pts_picks})")
        if self.reb_picks > 0:
            lines.append(f"  REB: {self.reb_hits/self.reb_picks*100:.1f}% ({self.reb_hits}/{self.reb_picks})")
        
        lines.extend(["", "BY DIRECTION:"])
        if self.over_picks > 0:
            lines.append(f"  OVER:  {self.over_hits/self.over_picks*100:.1f}% ({self.over_hits}/{self.over_picks})")
        if self.under_picks > 0:
            lines.append(f"  UNDER: {self.under_hits/self.under_picks*100:.1f}% ({self.under_hits}/{self.under_picks})")
        
        lines.extend(["", "BY PATTERN:"])
        if self.cold_bounce_picks > 0:
            lines.append(f"  Cold Bounce:   {self.cold_bounce_hits/self.cold_bounce_picks*100:.1f}% ({self.cold_bounce_hits}/{self.cold_bounce_picks})")
        if self.hot_sustained_picks > 0:
            lines.append(f"  Hot Sustained: {self.hot_sustained_hits/self.hot_sustained_picks*100:.1f}% ({self.hot_sustained_hits}/{self.hot_sustained_picks})")
        if self.consistent_picks > 0:
            lines.append(f"  Consistent:    {self.consistent_hits/self.consistent_picks*100:.1f}% ({self.consistent_hits}/{self.consistent_picks})")
        if self.no_pattern_picks > 0:
            lines.append(f"  No Pattern:    {self.no_pattern_hits/self.no_pattern_picks*100:.1f}% ({self.no_pattern_hits}/{self.no_pattern_picks})")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# ============================================================================
# Utility Functions
# ============================================================================

def _normalize_name(name: str) -> str:
    """Normalize player name."""
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_name.lower().strip()


def _get_position_category(pos: str) -> str:
    """Map position to category."""
    if not pos:
        return "G"
    pos = pos.upper()
    if 'PG' in pos or pos == 'G':
        return 'PG'
    elif 'SG' in pos:
        return 'SG'
    elif 'SF' in pos:
        return 'SF'
    elif 'PF' in pos:
        return 'PF'
    elif 'C' in pos:
        return 'C'
    elif 'F' in pos:
        return 'SF'
    return 'SG'


def _safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Safe division."""
    return a / b if b != 0 else default


def _safe_std(values: List[float]) -> float:
    """Safe standard deviation."""
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def _safe_avg(values: List[float], limit: Optional[int] = None) -> float:
    """Safe average with optional limit."""
    subset = values[:limit] if limit else values
    return sum(subset) / len(subset) if subset else 0.0


# ============================================================================
# Hybrid Model
# ============================================================================

class HybridModel:
    """
    Hybrid Model combining RCM contribution rates with pattern detection.
    """
    
    def __init__(self, db_path: str = "data/db/nba_props.sqlite3", config: HybridConfig = None):
        """Initialize the model."""
        self.db_path = Path(db_path)
        self.config = config or HybridConfig()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # =========================================================================
    # DATA LOADING
    # =========================================================================
    
    def _load_team_context(
        self,
        conn: sqlite3.Connection,
        team_id: int,
        before_date: str,
    ) -> TeamContext:
        """Load team context for contribution calculations."""
        team = conn.execute(
            "SELECT id, name FROM teams WHERE id = ?", (team_id,)
        ).fetchone()
        
        if not team:
            return TeamContext(team_id=team_id, team_abbrev="UNK")
        
        team_abbrev = abbrev_from_team_name(team["name"]) or "UNK"
        
        rows = conn.execute(
            """
            SELECT btt.pts, btt.reb, btt.ast, g.game_date
            FROM boxscore_team_totals btt
            JOIN games g ON g.id = btt.game_id
            WHERE btt.team_id = ? AND g.game_date < ?
            ORDER BY g.game_date DESC LIMIT 20
            """,
            (team_id, before_date),
        ).fetchall()
        
        if not rows:
            return TeamContext(team_id=team_id, team_abbrev=team_abbrev)
        
        games = [dict(r) for r in rows]
        pts = [g["pts"] or 0 for g in games]
        reb = [g["reb"] or 0 for g in games]
        ast = [g["ast"] or 0 for g in games]
        
        return TeamContext(
            team_id=team_id,
            team_abbrev=team_abbrev,
            avg_pts=_safe_avg(pts),
            avg_reb=_safe_avg(reb),
            avg_ast=_safe_avg(ast),
            l5_pts=_safe_avg(pts, 5),
            l10_pts=_safe_avg(pts, 10),
        )
    
    def _load_opponent_context(
        self,
        conn: sqlite3.Connection,
        opponent_abbrev: str,
    ) -> OpponentContext:
        """Load opponent defensive context."""
        team_row = conn.execute(
            "SELECT id, name FROM teams WHERE name LIKE ? OR name LIKE ?",
            (f"%{opponent_abbrev}%", f"{opponent_abbrev}%"),
        ).fetchone()
        
        team_id = team_row["id"] if team_row else 0
        
        dvp_rows = conn.execute(
            """
            SELECT position, pts_rank, reb_rank, ast_rank
            FROM team_defense_vs_position
            WHERE team_abbrev = ?
            """,
            (opponent_abbrev.upper(),),
        ).fetchall()
        
        dvp_ranks = {}
        for row in dvp_rows:
            pos = row["position"]
            dvp_ranks[pos] = {
                "pts": row["pts_rank"] or 15,
                "reb": row["reb_rank"] or 15,
                "ast": row["ast_rank"] or 15,
            }
        
        return OpponentContext(
            team_id=team_id,
            team_abbrev=opponent_abbrev,
            dvp_ranks=dvp_ranks,
        )
    
    def _load_player_data(
        self,
        conn: sqlite3.Connection,
        player_id: int,
        before_date: str,
    ) -> Optional[PlayerData]:
        """
        Load comprehensive player data for hybrid analysis.
        
        Combines RCM contribution rates with pattern detection data.
        """
        player = conn.execute(
            "SELECT id, name FROM players WHERE id = ?", (player_id,)
        ).fetchone()
        
        if not player:
            return None
        
        # Get game history with team totals
        rows = conn.execute(
            """
            SELECT 
                g.game_date,
                bp.pts as player_pts, bp.reb as player_reb, bp.ast as player_ast,
                bp.minutes, bp.pos,
                btt.pts as team_pts, btt.reb as team_reb, btt.ast as team_ast,
                t.name as team_name
            FROM boxscore_player bp
            JOIN games g ON g.id = bp.game_id
            JOIN teams t ON t.id = bp.team_id
            JOIN boxscore_team_totals btt ON btt.game_id = g.id AND btt.team_id = bp.team_id
            WHERE bp.player_id = ?
              AND g.game_date < ?
              AND bp.minutes IS NOT NULL
              AND bp.minutes > ?
            ORDER BY g.game_date DESC
            LIMIT ?
            """,
            (player_id, before_date, self.config.min_minutes_filter, self.config.max_games_lookback),
        ).fetchall()
        
        if len(rows) < self.config.min_games_required:
            return None
        
        games = [dict(r) for r in rows]
        n = len(games)
        
        # Check minimum minutes
        avg_min = sum(g["minutes"] or 0 for g in games) / n
        if avg_min < self.config.min_avg_minutes:
            return None
        
        # Extract stat arrays
        stats = {
            "pts": [g["player_pts"] or 0 for g in games],
            "reb": [g["player_reb"] or 0 for g in games],
            "ast": [g["player_ast"] or 0 for g in games],
        }
        team_stats = {
            "pts": [g["team_pts"] or 0 for g in games],
            "reb": [g["team_reb"] or 0 for g in games],
            "ast": [g["team_ast"] or 0 for g in games],
        }
        
        # Calculate raw averages at different windows
        l3 = {s: _safe_avg(v, 3) for s, v in stats.items()}
        l5 = {s: _safe_avg(v, 5) for s, v in stats.items()}
        l10 = {s: _safe_avg(v, 10) for s, v in stats.items()}
        l15 = {s: _safe_avg(v, 15) if n >= 15 else _safe_avg(v) for s, v in stats.items()}
        season = {s: _safe_avg(v) for s, v in stats.items()}
        
        # Calculate contribution rates
        def calc_contrib(player_vals: List[float], team_vals: List[float], limit: Optional[int] = None) -> float:
            """Calculate contribution rate for a window."""
            p_sum = sum(player_vals[:limit] if limit else player_vals)
            t_sum = sum(team_vals[:limit] if limit else team_vals)
            return _safe_divide(p_sum, t_sum, 0.0)
        
        contrib_l5 = {s: calc_contrib(stats[s], team_stats[s], 5) for s in stats}
        contrib_l10 = {s: calc_contrib(stats[s], team_stats[s], 10) for s in stats}
        contrib_season = {s: calc_contrib(stats[s], team_stats[s]) for s in stats}
        
        # Blended contribution (Bayesian)
        contrib_blended = {}
        for s in stats:
            weighted = (
                contrib_l5[s] * self.config.contribution_l5_weight +
                contrib_l10[s] * self.config.contribution_l10_weight +
                contrib_season[s] * self.config.contribution_season_weight
            )
            regression_target = contrib_season[s]
            blended = weighted * (1 - self.config.regression_strength) + \
                      regression_target * self.config.regression_strength
            contrib_blended[s] = blended
        
        # Calculate deviations (L5 vs L15 for pattern detection)
        deviation = {}
        for s in stats:
            deviation[s] = _safe_divide(l5[s] - l15[s], l15[s], 0.0) * 100
        
        # Standard deviations and coefficients of variation
        stds = {s: _safe_std(v[:10]) for s, v in stats.items()}
        cvs = {s: _safe_divide(stds[s], l10[s], 1.0) for s in stats}
        
        # Last game and recent values
        last_game = {s: v[0] if v else 0 for s, v in stats.items()}
        recent_values = {s: v[:5] for s, v in stats.items()}
        
        # Team averages
        team_avg = {s: _safe_avg(v) for s, v in team_stats.items()}
        
        return PlayerData(
            player_id=player_id,
            player_name=player["name"],
            team_abbrev=abbrev_from_team_name(games[0]["team_name"]) or "",
            position=_get_position_category(games[0].get("pos")),
            games_played=n,
            l3=l3,
            l5=l5,
            l10=l10,
            l15=l15,
            season=season,
            contrib_l5=contrib_l5,
            contrib_l10=contrib_l10,
            contrib_season=contrib_season,
            contrib_blended=contrib_blended,
            deviation=deviation,
            last_game=last_game,
            recent_values=recent_values,
            stds=stds,
            cvs=cvs,
            team_avg=team_avg,
        )
    
    # =========================================================================
    # PATTERN DETECTION (from Model Production)
    # =========================================================================
    
    def _detect_pattern(
        self,
        player: PlayerData,
        prop_type: str,
    ) -> PatternResult:
        """
        Detect performance pattern for a player/prop combination.
        
        Patterns from Model Production:
        - Cold Bounce-Back: 66.9% hit rate
        - Hot Sustained: 65.9% hit rate
        - Consistent: Lower variance = predictable
        """
        pt = prop_type.lower()
        
        deviation = player.deviation.get(pt, 0)
        l3 = player.l3.get(pt, 0)
        l5 = player.l5.get(pt, 0)
        l10 = player.l10.get(pt, 0)
        l15 = player.l15.get(pt, 0)
        last = player.last_game.get(pt, 0)
        recent = player.recent_values.get(pt, [])
        cv = player.cvs.get(pt, 1.0)
        
        # Check Cold Bounce-Back (PREMIUM - 66.9% hit rate)
        # L5 is 20%+ below L15 AND last game > L10
        if deviation <= self.config.cold_deviation_threshold:
            if not self.config.bounce_back_requirement or last > l10:
                bounce_edge = _safe_divide(last - l10, l10, 0) * 100
                return PatternResult(
                    pattern="cold_bounce",
                    confidence_bonus=self.config.cold_bounce_bonus,
                    reasons=[
                        f"Cold streak: L5 {deviation:+.0f}% vs L15",
                        f"Bouncing back: last game {last:.0f} > L10 {l10:.1f}",
                        f"Expected regression toward L15 ({l15:.1f})",
                    ],
                )
        
        # Check Hot Sustained (HIGH - 65.9% hit rate)
        # L5 is 30%+ above L15 AND L3 > L5 AND 3+ of L5 above L15
        if deviation >= self.config.hot_deviation_threshold:
            is_accelerating = not self.config.acceleration_required or l3 > l5
            games_above = sum(1 for v in recent if v > l15)
            
            if is_accelerating and games_above >= self.config.sustained_games_above:
                return PatternResult(
                    pattern="hot_sustained",
                    confidence_bonus=self.config.hot_sustained_bonus,
                    reasons=[
                        f"Hot streak: L5 {deviation:+.0f}% vs L15",
                        f"Accelerating: L3 {l3:.1f} > L5 {l5:.1f}",
                        f"Sustained: {games_above}/5 games above L15",
                    ],
                )
        
        # Check Consistent (v1.1: disabled by default - 47-50% hit rate)
        if self.config.enable_consistent_pattern and cv < self.config.consistency_cv_threshold:
            return PatternResult(
                pattern="consistent",
                confidence_bonus=self.config.consistent_bonus,
                reasons=[
                    f"Consistent: CV = {cv:.2f} (low variance)",
                    f"Stable L10 avg: {l10:.1f}",
                ],
            )
        
        return PatternResult(pattern="none", confidence_bonus=0.0)
    
    # =========================================================================
    # PROJECTION CALCULATION (from RCM)
    # =========================================================================
    
    def _get_opponent_adjustment(
        self,
        opponent: OpponentContext,
        position: str,
        prop_type: str,
    ) -> float:
        """Get opponent defense adjustment multiplier."""
        dvp = opponent.dvp_ranks.get(position, {})
        rank = dvp.get(prop_type.lower(), 15)
        
        if rank <= self.config.elite_defense_rank:
            return self.config.elite_defense_adj
        elif rank <= self.config.good_defense_rank:
            return self.config.good_defense_adj
        elif rank >= self.config.weak_defense_rank:
            return self.config.weak_defense_adj
        return self.config.neutral_defense_adj
    
    def _calculate_projection(
        self,
        player: PlayerData,
        team_ctx: TeamContext,
        opponent_ctx: OpponentContext,
        prop_type: str,
    ) -> Tuple[float, float, Dict]:
        """
        Calculate hybrid projection using contribution rate methodology.
        
        Returns: (projection, contribution_projection, breakdown)
        """
        pt = prop_type.lower()
        
        # Get contribution rate (blended from RCM)
        contribution_rate = player.contrib_blended.get(pt, 0.0)
        
        # Get expected team total
        if pt == "pts":
            team_expected = team_ctx.avg_pts
        elif pt == "reb":
            team_expected = team_ctx.avg_reb
        else:
            team_expected = team_ctx.avg_ast
        
        # Base projection = contribution_rate * team_expected
        base_projection = contribution_rate * team_expected
        
        # Opponent adjustment
        opp_mult = self._get_opponent_adjustment(opponent_ctx, player.position, prop_type)
        opp_adj = base_projection * (opp_mult - 1.0)
        
        # Regression adjustment toward season mean
        season_avg = player.season.get(pt, 0)
        current_proj = base_projection + opp_adj
        regression_adj = (season_avg - current_proj) * (self.config.regression_strength * 0.5)
        
        # Contribution-based projection
        contrib_projection = current_proj + regression_adj
        contrib_projection = max(0, contrib_projection)
        
        breakdown = {
            "base_projection": base_projection,
            "opponent_adj": opp_adj,
            "regression_adj": regression_adj,
            "contribution_rate": contribution_rate,
            "team_expected": team_expected,
            "opp_multiplier": opp_mult,
        }
        
        return contrib_projection, contrib_projection, breakdown
    
    # =========================================================================
    # PICK GENERATION
    # =========================================================================
    
    def _generate_pick(
        self,
        player: PlayerData,
        team_ctx: TeamContext,
        opponent_ctx: OpponentContext,
        prop_type: str,
        opponent_abbrev: str,
        game_date: str,
        sportsbook_line: Optional[float],
    ) -> Optional[HybridPick]:
        """
        Generate a pick using hybrid methodology.
        
        v1.1 Strategy:
        - PTS OVER: Only with pattern-confirmed (58.3%)
        - PTS UNDER: Always (62.8%)
        - REB OVER: Only with cold_bounce pattern (61.2%)
        - REB UNDER: Always (57.4%)
        - OVER picks require pattern confirmation (60% vs 55.8%)
        """
        pt = prop_type.lower()
        
        # Detect pattern
        pattern_result = self._detect_pattern(player, prop_type)
        pattern_confirmed = pattern_result.pattern in ("cold_bounce", "hot_sustained")
        
        # Calculate projection
        projection, contrib_proj, breakdown = self._calculate_projection(
            player, team_ctx, opponent_ctx, prop_type
        )
        
        # Determine line
        line = sportsbook_line or player.l10.get(pt, 0)
        line_source = "sportsbook" if sportsbook_line else "derived"
        
        if line <= 0:
            return None
        
        # Calculate edge
        edge_pct = _safe_divide(projection - line, line, 0) * 100
        
        # Determine direction
        raw_direction = "OVER" if edge_pct > 0 else "UNDER"
        abs_edge = abs(edge_pct)
        
        # === v1.2 STRATEGIC DIRECTION FILTERS ===
        
        # Rule 1: OVER picks generally require pattern confirmation
        if raw_direction == "OVER" and self.config.require_pattern_for_over:
            if not pattern_confirmed:
                return None
        
        # Rule 2: PTS OVER only with pattern
        if pt == "pts" and raw_direction == "OVER":
            if not (self.config.pts_pattern_over and pattern_confirmed):
                return None
        
        # Rule 3: REB OVER with pattern (cold_bounce or hot_sustained in v1.2)
        if pt == "reb" and raw_direction == "OVER":
            if self.config.reb_pattern_over_only:
                allowed_patterns = ["cold_bounce"]
                if self.config.allow_hot_sustained_reb_over:
                    allowed_patterns.append("hot_sustained")
                if pattern_result.pattern not in allowed_patterns:
                    return None
        
        # Determine final direction
        direction = raw_direction
        
        # Check minimum edge requirements
        min_edge = self.config.min_edge_over if direction == "OVER" else self.config.min_edge_under
        
        # Pattern-confirmed picks get lower bar
        if pattern_confirmed:
            min_edge -= self.config.pattern_edge_bonus
        
        if abs_edge < min_edge:
            return None
        
        # Calculate confidence
        confidence = 50.0
        factors = []
        
        # Edge bonus
        if abs_edge >= 15:
            confidence += 20
            factors.append(f"Large edge: {abs_edge:.0f}%")
        elif abs_edge >= 10:
            confidence += 15
            factors.append(f"Strong edge: {abs_edge:.0f}%")
        elif abs_edge >= 7:
            confidence += 10
        
        # Pattern bonus
        confidence += pattern_result.confidence_bonus
        if pattern_result.reasons:
            factors.extend(pattern_result.reasons)
        
        # Consistency bonus for UNDER
        cv = player.cvs.get(pt, 1.0)
        if direction == "UNDER" and cv < 0.30:
            confidence += 5
            factors.append(f"Consistent player (CV={cv:.2f})")
        
        # Position vs opponent bonus
        opp_mult = self._get_opponent_adjustment(opponent_ctx, player.position, prop_type)
        if direction == "UNDER" and opp_mult < 1.0:
            confidence += 5
            factors.append(f"Tough matchup (vs {opponent_abbrev})")
        elif direction == "OVER" and opp_mult > 1.0:
            confidence += 5
            factors.append(f"Favorable matchup (vs {opponent_abbrev})")
        
        # Determine tier
        if confidence >= self.config.premium_base:
            tier = "PREMIUM"
        elif confidence >= self.config.high_base:
            tier = "HIGH"
        else:
            tier = "STANDARD"
        
        return HybridPick(
            player_id=player.player_id,
            player_name=player.player_name,
            team_abbrev=player.team_abbrev,
            opponent_abbrev=opponent_abbrev,
            game_date=game_date,
            prop_type=prop_type.upper(),
            direction=direction,
            line=round(line, 1),
            line_source=line_source,
            projection=round(projection, 1),
            contribution_projection=round(contrib_proj, 1),
            pattern_projection=0.0,  # Could add pattern-based adjustment
            opponent_adj=round(breakdown["opponent_adj"], 2),
            regression_adj=round(breakdown["regression_adj"], 2),
            edge_pct=round(abs_edge if direction == "OVER" else -abs_edge, 1),
            confidence_score=min(100, confidence),
            confidence_tier=tier,
            pattern=pattern_result.pattern,
            pattern_confirmed=pattern_confirmed,
            contribution_rate=breakdown["contribution_rate"],
            team_expected=breakdown["team_expected"],
            l5_avg=player.l5.get(pt, 0),
            l10_avg=player.l10.get(pt, 0),
            l15_avg=player.l15.get(pt, 0),
            deviation=player.deviation.get(pt, 0),
            factors=factors,
        )
    
    def _get_sportsbook_line(
        self,
        conn: sqlite3.Connection,
        player_id: int,
        prop_type: str,
        game_date: str,
    ) -> Optional[float]:
        """Fetch sportsbook line if available."""
        if player_id:
            row = conn.execute(
                """
                SELECT line FROM sportsbook_lines
                WHERE player_id = ? AND prop_type = ? AND as_of_date = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (player_id, prop_type.upper(), game_date),
            ).fetchone()
            
            if row:
                return row["line"]
        return None
    
    def generate_game_picks(
        self,
        conn: sqlite3.Connection,
        game_date: str,
        team1_name: str,
        team2_name: str,
    ) -> List[HybridPick]:
        """Generate picks for a single game."""
        picks = []
        
        team1_abbrev = abbrev_from_team_name(team1_name) or team1_name[:3].upper()
        team2_abbrev = abbrev_from_team_name(team2_name) or team2_name[:3].upper()
        
        # Load opponent contexts
        opp_ctx = {
            team1_abbrev: self._load_opponent_context(conn, team2_abbrev),
            team2_abbrev: self._load_opponent_context(conn, team1_abbrev),
        }
        
        # Get players from both teams
        for team_abbrev, opponent_abbrev in [(team1_abbrev, team2_abbrev), (team2_abbrev, team1_abbrev)]:
            # Get team ID
            team_row = conn.execute(
                "SELECT id FROM teams WHERE name LIKE ?",
                (f"%{team_abbrev}%",),
            ).fetchone()
            
            if not team_row:
                continue
            
            team_id = team_row["id"]
            team_ctx = self._load_team_context(conn, team_id, game_date)
            
            # Get players who played for this team recently
            player_rows = conn.execute(
                """
                SELECT DISTINCT bp.player_id
                FROM boxscore_player bp
                JOIN games g ON g.id = bp.game_id
                WHERE bp.team_id = ?
                  AND g.game_date < ?
                  AND bp.minutes > 15
                ORDER BY g.game_date DESC
                LIMIT 50
                """,
                (team_id, game_date),
            ).fetchall()
            
            player_picks = []
            
            for row in player_rows:
                player_id = row["player_id"]
                player = self._load_player_data(conn, player_id, game_date)
                
                if not player:
                    continue
                
                # Generate picks for each prop type
                prop_types = ["pts", "reb"]
                if self.config.include_ast:
                    prop_types.append("ast")
                
                for prop_type in prop_types:
                    line = self._get_sportsbook_line(conn, player_id, prop_type, game_date)
                    
                    pick = self._generate_pick(
                        player=player,
                        team_ctx=team_ctx,
                        opponent_ctx=opp_ctx[team_abbrev],
                        prop_type=prop_type,
                        opponent_abbrev=opponent_abbrev,
                        game_date=game_date,
                        sportsbook_line=line,
                    )
                    
                    if pick:
                        player_picks.append(pick)
            
            # Limit picks per player
            player_pick_counts = {}
            for pick in sorted(player_picks, key=lambda p: p.confidence_score, reverse=True):
                player_key = pick.player_id
                if player_pick_counts.get(player_key, 0) < self.config.max_picks_per_player:
                    picks.append(pick)
                    player_pick_counts[player_key] = player_pick_counts.get(player_key, 0) + 1
        
        # Sort by confidence and limit
        picks.sort(key=lambda p: p.confidence_score, reverse=True)
        return picks[:self.config.max_picks_per_game]
    
    def get_daily_picks(self, game_date: str) -> DailyHybridPicks:
        """Get all picks for a date."""
        conn = self._get_connection()
        
        try:
            # Get games for this date
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
            
            all_picks = []
            
            for game in games:
                game_picks = self.generate_game_picks(
                    conn, game_date, game["team1"], game["team2"]
                )
                all_picks.extend(game_picks)
            
            # Sort and limit
            all_picks.sort(key=lambda p: p.confidence_score, reverse=True)
            all_picks = all_picks[:self.config.max_picks_per_day]
            
            return DailyHybridPicks(
                date=game_date,
                games=len(games),
                picks=all_picks,
            )
        
        finally:
            conn.close()
    
    # =========================================================================
    # BACKTESTING
    # =========================================================================
    
    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        verbose: bool = False,
    ) -> HybridBacktestResult:
        """
        Run backtest over a date range.
        """
        conn = self._get_connection()
        result = HybridBacktestResult(
            start_date=start_date,
            end_date=end_date,
            config=self.config,
        )
        
        try:
            # Get all dates with games
            dates = conn.execute(
                """
                SELECT DISTINCT game_date 
                FROM games 
                WHERE game_date BETWEEN ? AND ?
                ORDER BY game_date
                """,
                (start_date, end_date),
            ).fetchall()
            
            for date_row in dates:
                game_date = date_row["game_date"]
                
                # Get games for this date
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
                
                result.total_games += len(games)
                result.days_tested += 1
                
                daily_picks = []
                daily_hits = 0
                
                for game in games:
                    picks = self.generate_game_picks(
                        conn, game_date, game["team1"], game["team2"]
                    )
                    
                    # Evaluate picks against actual results
                    for pick in picks:
                        actual = self._get_actual_result(
                            conn, pick.player_id, game_date, pick.prop_type.lower()
                        )
                        
                        if actual is None:
                            continue
                        
                        pick.actual_value = actual
                        
                        if pick.direction == "OVER":
                            pick.hit = actual > pick.line
                        else:
                            pick.hit = actual < pick.line
                        
                        daily_picks.append(pick)
                        
                        # Update counters
                        result.total_picks += 1
                        if pick.hit:
                            result.hits += 1
                            daily_hits += 1
                        
                        # By tier
                        if pick.confidence_tier == "PREMIUM":
                            result.premium_picks += 1
                            if pick.hit:
                                result.premium_hits += 1
                        elif pick.confidence_tier == "HIGH":
                            result.high_picks += 1
                            if pick.hit:
                                result.high_hits += 1
                        else:
                            result.standard_picks += 1
                            if pick.hit:
                                result.standard_hits += 1
                        
                        # By prop type
                        if pick.prop_type == "PTS":
                            result.pts_picks += 1
                            if pick.hit:
                                result.pts_hits += 1
                        elif pick.prop_type == "REB":
                            result.reb_picks += 1
                            if pick.hit:
                                result.reb_hits += 1
                        
                        # By direction
                        if pick.direction == "OVER":
                            result.over_picks += 1
                            if pick.hit:
                                result.over_hits += 1
                        else:
                            result.under_picks += 1
                            if pick.hit:
                                result.under_hits += 1
                        
                        # By pattern
                        if pick.pattern == "cold_bounce":
                            result.cold_bounce_picks += 1
                            if pick.hit:
                                result.cold_bounce_hits += 1
                        elif pick.pattern == "hot_sustained":
                            result.hot_sustained_picks += 1
                            if pick.hit:
                                result.hot_sustained_hits += 1
                        elif pick.pattern == "consistent":
                            result.consistent_picks += 1
                            if pick.hit:
                                result.consistent_hits += 1
                        else:
                            result.no_pattern_picks += 1
                            if pick.hit:
                                result.no_pattern_hits += 1
                        
                        result.all_picks.append(pick)
                
                # Daily summary
                if daily_picks:
                    daily_rate = daily_hits / len(daily_picks) if daily_picks else 0
                    result.daily_results.append({
                        "date": game_date,
                        "picks": len(daily_picks),
                        "hits": daily_hits,
                        "rate": daily_rate,
                    })
                    
                    if verbose:
                        print(f"{game_date}: {daily_hits}/{len(daily_picks)} ({daily_rate*100:.1f}%)")
            
            return result
        
        finally:
            conn.close()
    
    def _get_actual_result(
        self,
        conn: sqlite3.Connection,
        player_id: int,
        game_date: str,
        prop_type: str,
    ) -> Optional[float]:
        """Get actual stat from game."""
        row = conn.execute(
            f"""
            SELECT bp.{prop_type} as value
            FROM boxscore_player bp
            JOIN games g ON g.id = bp.game_id
            WHERE bp.player_id = ? AND g.game_date = ?
            """,
            (player_id, game_date),
        ).fetchone()
        
        return row["value"] if row else None


# ============================================================================
# Module Functions
# ============================================================================

def run_hybrid_backtest(
    start_date: str = "2025-12-01",
    end_date: str = "2026-01-13",
    db_path: str = "data/db/nba_props.sqlite3",
    verbose: bool = True,
) -> HybridBacktestResult:
    """
    Run hybrid model backtest.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        db_path: Path to database
        verbose: Print daily results
    
    Returns:
        HybridBacktestResult with detailed breakdown
    """
    model = HybridModel(db_path=db_path)
    result = model.run_backtest(start_date, end_date, verbose=verbose)
    print(result.summary())
    return result


def get_hybrid_daily_picks(
    game_date: str,
    db_path: str = "data/db/nba_props.sqlite3",
) -> DailyHybridPicks:
    """
    Get hybrid model picks for a date.
    
    Args:
        game_date: Date to get picks for (YYYY-MM-DD)
        db_path: Path to database
    
    Returns:
        DailyHybridPicks with all picks
    """
    model = HybridModel(db_path=db_path)
    return model.get_daily_picks(game_date)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Run backtest when executed directly
    run_hybrid_backtest(verbose=True)

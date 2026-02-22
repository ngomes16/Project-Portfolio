"""
Regression Contribution Model (RCM) - NBA Props Prediction
============================================================

A comprehensive model that predicts player performance by analyzing:
1. Player contribution rates relative to team totals
2. Expected team totals based on matchup context
3. Bayesian regression toward season/career means
4. Opponent defensive adjustments by position
5. Usage redistribution when teammates are injured

CORE METHODOLOGY:
-----------------
The RCM takes a fundamentally different approach than simple rolling averages:

1. **Contribution Rate Calculation**:
   - Instead of raw averages, calculate % of team totals each player contributes
   - Example: Player A averages 25 PPG on a team that scores 110 PPG = 22.7% contribution
   - More stable metric than raw stats as team totals fluctuate

2. **Expected Team Performance**:
   - Project team totals based on:
     a) Team's rolling average pace and efficiency
     b) Opponent's defensive ratings
     c) Home/away adjustment
   - Then apply contribution rate to get player projection

3. **Bayesian Regression**:
   - Blend recent performance with season/historical baseline
   - Weight recent games more, but regress toward mean
   - This captures "true talent" better than pure rolling average
   
4. **Opponent Adjustments**:
   - Use defense vs position data to adjust projections
   - If opponent is elite at defending PGs, reduce PG projections
   
5. **Injury-Based Usage Boost**:
   - When high-usage teammates are out, remaining players see increased opportunity
   - Quantify this boost based on historical redistribution

CONFIDENCE TIERS:
-----------------
- PREMIUM: High-confidence picks with multiple convergent factors
- HIGH: Strong single-factor picks with good historical accuracy
- STANDARD: Moderate confidence picks

USAGE:
------
    from src.nba_props.engine.regression_contribution_model import (
        RegressionContributionModel,
        get_rcm_daily_picks,
        run_rcm_backtest,
    )
    
    # Initialize model
    rcm = RegressionContributionModel(db_path="data/db/nba_props.sqlite3")
    
    # Get picks for a date
    picks = rcm.get_daily_picks("2026-01-14")
    
    # Run backtest
    results = rcm.run_backtest("2025-12-01", "2026-01-13")

Author: NBA Props Team - Regression Contribution Model v1.0
Created: January 2026
"""
from __future__ import annotations

import sqlite3
import statistics
import unicodedata
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any, Set
from pathlib import Path

from ..db import Db
from ..team_aliases import abbrev_from_team_name, normalize_team_abbrev


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class RCMConfig:
    """
    Regression Contribution Model Configuration.
    
    This model focuses on contribution rates and Bayesian regression rather
    than simple rolling averages.
    
    VERSION HISTORY:
    ----------------
    v1.0 - Initial implementation
    v1.1 - Tuned based on backtest (lower bar for UNDERs)
    v1.2 - Higher edge requirements (10%+ for OVERs)
           Overall: 55.9% hit rate
    v1.3 - Focus on REB (59% hit rate) and UNDER (61.5%)
           Reduce AST picks (50.8% was worst)
    v1.4 - Strategic direction selection:
           PTS UNDER only (63.9% hit rate vs 48.3% OVER)
           REB both directions (59% both ways)
           No AST (44.8% OVER terrible)
    """
    # === VERSION INFO ===
    model_name: str = "Regression Contribution Model"
    model_version: str = "1.4"
    
    # === DATA REQUIREMENTS ===
    min_games_required: int = 10        # Need sufficient history
    min_minutes_filter: int = 5         # Filter garbage time
    min_avg_minutes: float = 20.0       # Increased - more established players
    max_games_lookback: int = 20        # Use last 20 games
    
    # === CONTRIBUTION RATE WINDOWS ===
    # We calculate contribution rates at different windows
    # v1.1: More weight on longer-term to reduce noise
    contribution_l5_weight: float = 0.20    # Reduced from 0.30
    contribution_l10_weight: float = 0.35   # Same
    contribution_season_weight: float = 0.45  # Increased from 0.35
    
    # === BAYESIAN REGRESSION PARAMS ===
    # How much to regress recent performance toward mean
    # v1.1: More regression for stability
    regression_strength: float = 0.35  # Increased from 0.25
    
    # Confidence in season baseline (pseudo-observations)
    season_prior_games: int = 10  # Season avg weighted like 10 games
    
    # === TEAM CONTEXT PARAMS ===
    # Expected team scoring adjustments
    league_avg_pts: float = 115.0  # League average points per game
    home_advantage_pts: float = 2.5  # Home teams score ~2.5 more
    
    # === OPPONENT ADJUSTMENTS ===
    # Defense vs position rank thresholds
    elite_defense_rank: int = 5     # Top 5 = elite
    good_defense_rank: int = 10     # Top 10 = good
    weak_defense_rank: int = 25     # Bottom 5 = weak
    
    # Adjustment multipliers for opponent defense
    # v1.1: More aggressive adjustments for matchups
    elite_defense_adj: float = 0.90   # -10% vs elite defense (was -8%)
    good_defense_adj: float = 0.95    # -5% vs good defense (was -4%)
    neutral_defense_adj: float = 1.00 # No change
    weak_defense_adj: float = 1.08    # +8% vs weak defense (was +6%)
    
    # === INJURY/USAGE BOOST ===
    # When a high-usage teammate is out
    high_usage_threshold: float = 20.0  # Players averaging 20+ pts
    usage_boost_per_player: float = 0.04  # Reduced to 4% (was 5%)
    max_usage_boost: float = 0.12  # Cap at 12% (was 15%)
    
    # === CONFIDENCE SCORING ===
    premium_threshold: float = 82.0    # Increased from 80
    high_threshold: float = 72.0       # Increased from 70
    
    # Edge requirements - v1.2: Higher bar based on backtest analysis
    # Backtest showed: 5-7% edge = 38.1% hit rate, 15%+ edge = 58.3% hit rate
    # We need higher edge to have positive expected value
    min_edge_pct: float = 10.0         # Increased from 6% (was getting 38% hit rate)
    min_edge_premium: float = 15.0     # Increased from 10%
    min_edge_under: float = 8.0        # UNDERs can have slightly lower bar
    
    # === PROP SELECTION ===
    # v1.4: Strategic prop/direction selection based on backtest
    # PTS: UNDER only (63.9% vs 48.3% OVER)
    # REB: Both directions (59% both)
    # AST: Excluded (44.8% OVER)
    prop_types: List[str] = field(default_factory=lambda: ['reb', 'pts'])
    include_ast: bool = False  # Disabled - poor performance
    pts_under_only: bool = True  # Only UNDER picks for PTS
    
    # === PICK LIMITS ===
    max_picks_per_game: int = 4
    max_picks_per_day: int = 18
    max_picks_per_player: int = 2  # Allow pts + reb picks for same player
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TeamContext:
    """Team performance context for projection."""
    team_id: int
    team_abbrev: str
    
    # Team averages (for contribution rate base)
    avg_pts: float = 0.0
    avg_reb: float = 0.0
    avg_ast: float = 0.0
    
    # Recent trends
    l5_pts: float = 0.0
    l10_pts: float = 0.0
    
    # Pace (possessions per game proxy)
    pace: float = 100.0


@dataclass
class OpponentContext:
    """Opponent defensive context."""
    team_id: int
    team_abbrev: str
    
    # Defense vs position ranks (1=best, 30=worst)
    dvp_ranks: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # Format: {"PG": {"pts": 5, "reb": 12, "ast": 3}, ...}
    
    # Team defensive rating
    def_rating: float = 110.0


@dataclass
class PlayerContribution:
    """Player contribution rates and projections."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: str
    
    # Games played
    games_played: int = 0
    
    # Raw averages
    raw_avgs: Dict[str, float] = field(default_factory=dict)  # pts, reb, ast
    
    # Contribution rates (% of team totals)
    # These are more stable than raw averages
    contribution_l5: Dict[str, float] = field(default_factory=dict)
    contribution_l10: Dict[str, float] = field(default_factory=dict)
    contribution_season: Dict[str, float] = field(default_factory=dict)
    
    # Blended contribution rate (Bayesian)
    contribution_blended: Dict[str, float] = field(default_factory=dict)
    
    # Standard deviations (for consistency scoring)
    stds: Dict[str, float] = field(default_factory=dict)
    
    # Recent performance values (for pattern detection)
    recent_values: Dict[str, List[float]] = field(default_factory=dict)
    last_game: Dict[str, float] = field(default_factory=dict)


@dataclass  
class RCMPick:
    """A pick generated by the Regression Contribution Model."""
    # Identity
    player_id: int
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    game_date: str
    
    # Pick details
    prop_type: str  # PTS, REB, AST
    direction: str  # OVER, UNDER
    
    # Line information
    line: float
    line_source: str  # 'sportsbook', 'derived'
    
    # Projection breakdown
    projection: float
    projection_std: float
    
    # Components
    base_projection: float       # From contribution rate
    opponent_adj: float          # +/- from opponent defense
    usage_boost: float           # +/- from injured teammates
    regression_adj: float        # +/- from Bayesian regression
    
    # Edge
    edge_pct: float
    
    # Confidence
    confidence_score: float
    confidence_tier: str  # PREMIUM, HIGH, STANDARD
    
    # Supporting data
    contribution_rate: float     # Player's % of team total
    team_expected_total: float   # Expected team total for this stat
    
    # Historical
    l5_avg: float
    l10_avg: float
    season_avg: float
    
    # Factors
    factors: List[str] = field(default_factory=list)
    
    # Outcome (filled after game)
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
            "line_source": self.line_source,
            "projection": round(self.projection, 1),
            "projection_std": round(self.projection_std, 1),
            "base_projection": round(self.base_projection, 1),
            "opponent_adj": round(self.opponent_adj, 2),
            "usage_boost": round(self.usage_boost, 2),
            "regression_adj": round(self.regression_adj, 2),
            "edge": f"{self.edge_pct:.1f}%",
            "tier": self.confidence_tier,
            "confidence": round(self.confidence_score, 1),
            "contribution_rate": f"{self.contribution_rate:.1%}",
            "team_expected": round(self.team_expected_total, 1),
            "l5": round(self.l5_avg, 1),
            "l10": round(self.l10_avg, 1),
            "season": round(self.season_avg, 1),
            "factors": self.factors,
            "actual": self.actual_value,
            "hit": self.hit,
        }


@dataclass
class DailyRCMPicks:
    """All picks for a day from RCM."""
    date: str
    games: int
    picks: List[RCMPick] = field(default_factory=list)
    
    @property
    def total_picks(self) -> int:
        return len(self.picks)
    
    @property
    def premium_picks(self) -> List[RCMPick]:
        return [p for p in self.picks if p.confidence_tier == "PREMIUM"]
    
    @property
    def high_picks(self) -> List[RCMPick]:
        return [p for p in self.picks if p.confidence_tier == "HIGH"]
    
    def summary(self) -> str:
        """Generate summary text."""
        lines = [
            f"{'='*70}",
            f"REGRESSION CONTRIBUTION MODEL - {self.date}",
            f"{'='*70}",
            f"Games: {self.games} | Total Picks: {self.total_picks}",
            "",
        ]
        
        for tier in ["PREMIUM", "HIGH", "STANDARD"]:
            tier_picks = [p for p in self.picks if p.confidence_tier == tier]
            if tier_picks:
                lines.append(f"--- {tier} ({len(tier_picks)}) ---")
                for p in tier_picks:
                    lines.append(
                        f"  {p.player_name} ({p.team_abbrev} vs {p.opponent_abbrev}): "
                        f"{p.prop_type} {p.direction} {p.line:.1f}"
                    )
                    lines.append(
                        f"      Proj: {p.projection:.1f} | Edge: {p.edge_pct:.1f}% | "
                        f"Contribution: {p.contribution_rate:.1%}"
                    )
                lines.append("")
        
        return "\n".join(lines)


@dataclass
class RCMBacktestResult:
    """Backtest results for the RCM."""
    start_date: str
    end_date: str
    config: RCMConfig
    
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
    ast_picks: int = 0
    ast_hits: int = 0
    
    # By direction
    over_picks: int = 0
    over_hits: int = 0
    under_picks: int = 0
    under_hits: int = 0
    
    # Tracking
    total_games: int = 0
    days_tested: int = 0
    
    # All picks for detailed analysis
    all_picks: List[RCMPick] = field(default_factory=list)
    daily_results: List[Dict] = field(default_factory=list)
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_picks if self.total_picks > 0 else 0.0
    
    @property
    def premium_hit_rate(self) -> float:
        return self.premium_hits / self.premium_picks if self.premium_picks > 0 else 0.0
    
    @property
    def high_hit_rate(self) -> float:
        return self.high_hits / self.high_picks if self.high_picks > 0 else 0.0
    
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
        """Generate detailed summary."""
        lines = [
            "=" * 70,
            "REGRESSION CONTRIBUTION MODEL - BACKTEST RESULTS",
            "=" * 70,
            f"Period: {self.start_date} to {self.end_date}",
            f"Days tested: {self.days_tested} | Games: {self.total_games}",
            "",
            f"OVERALL: {self.hit_rate*100:.1f}% ({self.hits}/{self.total_picks})",
            "",
            "BY CONFIDENCE TIER:",
        ]
        
        if self.premium_picks > 0:
            lines.append(f"  PREMIUM:  {self.premium_hit_rate*100:.1f}% ({self.premium_hits}/{self.premium_picks})")
        if self.high_picks > 0:
            lines.append(f"  HIGH:     {self.high_hit_rate*100:.1f}% ({self.high_hits}/{self.high_picks})")
        if self.standard_picks > 0:
            lines.append(f"  STANDARD: {self.standard_hits/self.standard_picks*100:.1f}% ({self.standard_hits}/{self.standard_picks})")
        
        lines.extend([
            "",
            "BY PROP TYPE:",
        ])
        
        if self.pts_picks > 0:
            lines.append(f"  PTS: {self.pts_hit_rate*100:.1f}% ({self.pts_hits}/{self.pts_picks})")
        if self.reb_picks > 0:
            lines.append(f"  REB: {self.reb_hit_rate*100:.1f}% ({self.reb_hits}/{self.reb_picks})")
        if self.ast_picks > 0:
            lines.append(f"  AST: {self.ast_hit_rate*100:.1f}% ({self.ast_hits}/{self.ast_picks})")
        
        lines.extend([
            "",
            "BY DIRECTION:",
        ])
        
        if self.over_picks > 0:
            lines.append(f"  OVER:  {self.over_hits/self.over_picks*100:.1f}% ({self.over_hits}/{self.over_picks})")
        if self.under_picks > 0:
            lines.append(f"  UNDER: {self.under_hits/self.under_picks*100:.1f}% ({self.under_hits}/{self.under_picks})")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# ============================================================================
# Utility Functions
# ============================================================================

def _normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_name.lower().strip()


def _get_position_category(pos: str) -> str:
    """Map position to standard category for DVP lookup."""
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
        return 'SF'  # Default forwards to SF
    return 'SG'  # Default guards to SG


def _safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Safe division with default for zero denominator."""
    return a / b if b != 0 else default


def _safe_std(values: List[float]) -> float:
    """Calculate standard deviation safely."""
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def _calculate_cv(mean: float, std: float) -> float:
    """Calculate coefficient of variation (std/mean)."""
    return std / mean if mean > 0 else 1.0


# ============================================================================
# Core Model Class
# ============================================================================

class RegressionContributionModel:
    """
    The Regression Contribution Model predicts player performance using:
    1. Contribution rates (% of team totals)
    2. Expected team totals based on matchup
    3. Bayesian regression toward season means
    4. Opponent defensive adjustments
    5. Usage redistribution for injured teammates
    """
    
    def __init__(self, db_path: str = "data/db/nba_props.sqlite3", config: RCMConfig = None):
        """Initialize the model."""
        self.db_path = Path(db_path)
        self.config = config or RCMConfig()
        
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
        """
        Load team performance context for contribution rate calculations.
        """
        # Get team info
        team = conn.execute(
            "SELECT id, name FROM teams WHERE id = ?", (team_id,)
        ).fetchone()
        
        if not team:
            return TeamContext(team_id=team_id, team_abbrev="UNK")
        
        team_abbrev = abbrev_from_team_name(team["name"]) or "UNK"
        
        # Get team totals from recent games
        rows = conn.execute(
            """
            SELECT 
                btt.pts, btt.reb, btt.ast,
                g.game_date
            FROM boxscore_team_totals btt
            JOIN games g ON g.id = btt.game_id
            WHERE btt.team_id = ?
              AND g.game_date < ?
            ORDER BY g.game_date DESC
            LIMIT 20
            """,
            (team_id, before_date),
        ).fetchall()
        
        if not rows:
            return TeamContext(team_id=team_id, team_abbrev=team_abbrev)
        
        games = [dict(r) for r in rows]
        
        # Calculate averages
        pts_vals = [g["pts"] or 0 for g in games]
        reb_vals = [g["reb"] or 0 for g in games]
        ast_vals = [g["ast"] or 0 for g in games]
        
        ctx = TeamContext(
            team_id=team_id,
            team_abbrev=team_abbrev,
            avg_pts=sum(pts_vals) / len(pts_vals),
            avg_reb=sum(reb_vals) / len(reb_vals),
            avg_ast=sum(ast_vals) / len(ast_vals),
            l5_pts=sum(pts_vals[:5]) / min(5, len(pts_vals)),
            l10_pts=sum(pts_vals[:10]) / min(10, len(pts_vals)),
        )
        
        return ctx
    
    def _load_opponent_context(
        self,
        conn: sqlite3.Connection,
        opponent_abbrev: str,
    ) -> OpponentContext:
        """
        Load opponent defensive context including defense vs position.
        """
        # Get team ID
        team_row = conn.execute(
            """
            SELECT t.id, t.name 
            FROM teams t 
            WHERE t.name LIKE ? OR t.name LIKE ?
            """,
            (f"%{opponent_abbrev}%", f"{opponent_abbrev}%"),
        ).fetchone()
        
        team_id = team_row["id"] if team_row else 0
        
        # Load defense vs position data
        dvp_rows = conn.execute(
            """
            SELECT position, pts_allowed, pts_rank, reb_allowed, reb_rank, ast_allowed, ast_rank
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
    
    def _load_player_contribution(
        self,
        conn: sqlite3.Connection,
        player_id: int,
        before_date: str,
    ) -> Optional[PlayerContribution]:
        """
        Load player's contribution rates and statistics.
        
        This is the core data structure for the model.
        Contribution rate = player_stat / team_stat (% of team total)
        """
        # Get player info
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
        
        # Check minimum average minutes
        avg_min = sum(g["minutes"] or 0 for g in games) / n
        if avg_min < self.config.min_avg_minutes:
            return None
        
        # Calculate raw averages
        raw_avgs = {
            "pts": sum(g["player_pts"] or 0 for g in games) / n,
            "reb": sum(g["player_reb"] or 0 for g in games) / n,
            "ast": sum(g["player_ast"] or 0 for g in games) / n,
            "min": avg_min,
        }
        
        # Calculate contribution rates at different windows
        def calc_contribution_rates(game_subset: List[Dict]) -> Dict[str, float]:
            """Calculate contribution rate (player/team) for a subset of games."""
            rates = {}
            for stat in ["pts", "reb", "ast"]:
                player_total = sum(g[f"player_{stat}"] or 0 for g in game_subset)
                team_total = sum(g[f"team_{stat}"] or 0 for g in game_subset)
                rates[stat] = _safe_divide(player_total, team_total, 0.0)
            return rates
        
        # Contribution rates at L5, L10, season
        contrib_l5 = calc_contribution_rates(games[:5])
        contrib_l10 = calc_contribution_rates(games[:10])
        contrib_season = calc_contribution_rates(games)
        
        # Calculate blended contribution rate (Bayesian approach)
        # Weight recent more but anchor to season baseline
        contrib_blended = {}
        for stat in ["pts", "reb", "ast"]:
            # Weighted average of contribution rates
            weighted = (
                contrib_l5[stat] * self.config.contribution_l5_weight +
                contrib_l10[stat] * self.config.contribution_l10_weight +
                contrib_season[stat] * self.config.contribution_season_weight
            )
            
            # Apply Bayesian regression toward season mean
            regression_target = contrib_season[stat]
            blended = weighted * (1 - self.config.regression_strength) + \
                      regression_target * self.config.regression_strength
            
            contrib_blended[stat] = blended
        
        # Calculate standard deviations for consistency
        stds = {
            "pts": _safe_std([g["player_pts"] or 0 for g in games[:10]]),
            "reb": _safe_std([g["player_reb"] or 0 for g in games[:10]]),
            "ast": _safe_std([g["player_ast"] or 0 for g in games[:10]]),
        }
        
        # Recent values and last game
        recent_values = {
            "pts": [g["player_pts"] or 0 for g in games[:5]],
            "reb": [g["player_reb"] or 0 for g in games[:5]],
            "ast": [g["player_ast"] or 0 for g in games[:5]],
        }
        last_game = {
            "pts": games[0]["player_pts"] or 0 if games else 0,
            "reb": games[0]["player_reb"] or 0 if games else 0,
            "ast": games[0]["player_ast"] or 0 if games else 0,
        }
        
        return PlayerContribution(
            player_id=player_id,
            player_name=player["name"],
            team_abbrev=abbrev_from_team_name(games[0]["team_name"]) or "",
            position=_get_position_category(games[0].get("pos")),
            games_played=n,
            raw_avgs=raw_avgs,
            contribution_l5=contrib_l5,
            contribution_l10=contrib_l10,
            contribution_season=contrib_season,
            contribution_blended=contrib_blended,
            stds=stds,
            recent_values=recent_values,
            last_game=last_game,
        )
    
    def _get_injured_players(
        self,
        conn: sqlite3.Connection,
        game_date: str,
        team_abbrev: str,
    ) -> List[Dict]:
        """
        Get injured players for a team on a date.
        Returns list of {"player_id", "player_name", "status", "avg_pts"}
        """
        # Get team ID
        team_row = conn.execute(
            """
            SELECT t.id FROM teams t 
            WHERE t.name LIKE ?
            """,
            (f"%{team_abbrev}%",),
        ).fetchone()
        
        if not team_row:
            return []
        
        team_id = team_row["id"]
        
        # Get injured players
        injured = conn.execute(
            """
            SELECT 
                ir.player_id, ir.player_name, ir.status,
                p.id as resolved_player_id, p.name as resolved_name
            FROM injury_report ir
            LEFT JOIN players p ON ir.player_id = p.id OR LOWER(p.name) = LOWER(ir.player_name)
            WHERE ir.game_date = ?
              AND ir.team_id = ?
              AND ir.status IN ('OUT', 'DOUBTFUL')
            """,
            (game_date, team_id),
        ).fetchall()
        
        result = []
        for row in injured:
            pid = row["player_id"] or row["resolved_player_id"]
            pname = row["player_name"] or row["resolved_name"]
            
            # Get player's average points to assess usage impact
            avg_pts = 0.0
            if pid:
                avg_row = conn.execute(
                    """
                    SELECT AVG(bp.pts) as avg_pts
                    FROM boxscore_player bp
                    JOIN games g ON g.id = bp.game_id
                    WHERE bp.player_id = ?
                      AND g.game_date < ?
                      AND bp.minutes > 10
                    """,
                    (pid, game_date),
                ).fetchone()
                avg_pts = avg_row["avg_pts"] or 0 if avg_row else 0
            
            result.append({
                "player_id": pid,
                "player_name": pname,
                "status": row["status"],
                "avg_pts": avg_pts,
            })
        
        return result
    
    def _get_sportsbook_line(
        self,
        conn: sqlite3.Connection,
        player_id: int,
        player_name: str,
        prop_type: str,
        game_date: str,
    ) -> Optional[float]:
        """Fetch sportsbook line if available."""
        # Try by player_id
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
    
    # =========================================================================
    # PROJECTION CALCULATION
    # =========================================================================
    
    def _calculate_opponent_adjustment(
        self,
        opponent: OpponentContext,
        position: str,
        prop_type: str,
    ) -> float:
        """
        Calculate adjustment multiplier based on opponent defense.
        
        Returns: multiplier (e.g., 0.92 for elite defense, 1.06 for weak)
        """
        # Get DVP rank for this position and stat
        dvp = opponent.dvp_ranks.get(position, {})
        rank = dvp.get(prop_type.lower(), 15)  # Default to average (15)
        
        # Map rank to adjustment
        if rank <= self.config.elite_defense_rank:
            return self.config.elite_defense_adj
        elif rank <= self.config.good_defense_rank:
            return self.config.good_defense_adj
        elif rank >= self.config.weak_defense_rank:
            return self.config.weak_defense_adj
        else:
            return self.config.neutral_defense_adj
    
    def _calculate_usage_boost(
        self,
        injured_teammates: List[Dict],
    ) -> float:
        """
        Calculate usage boost when high-usage teammates are injured.
        
        Returns: boost multiplier (e.g., 0.10 for 10% boost)
        """
        # Count high-usage players out
        high_usage_out = sum(
            1 for p in injured_teammates 
            if p.get("avg_pts", 0) >= self.config.high_usage_threshold
        )
        
        boost = high_usage_out * self.config.usage_boost_per_player
        return min(boost, self.config.max_usage_boost)
    
    def _project_player_stat(
        self,
        player: PlayerContribution,
        team_ctx: TeamContext,
        opponent_ctx: OpponentContext,
        prop_type: str,
        injured_teammates: List[Dict],
    ) -> Tuple[float, Dict]:
        """
        Calculate projection using the RCM methodology.
        
        Returns: (projection, breakdown_dict)
        """
        pt = prop_type.lower()
        
        # 1. Get contribution rate (blended/Bayesian)
        contribution_rate = player.contribution_blended.get(pt, 0.0)
        
        # 2. Calculate expected team total
        # Start with team's average
        if pt == "pts":
            team_expected = team_ctx.avg_pts
        elif pt == "reb":
            team_expected = team_ctx.avg_reb
        elif pt == "ast":
            team_expected = team_ctx.avg_ast
        else:
            team_expected = 0.0
        
        # 3. Base projection = contribution_rate * expected_team_total
        base_projection = contribution_rate * team_expected
        
        # 4. Apply opponent adjustment
        opp_adj_mult = self._calculate_opponent_adjustment(
            opponent_ctx, player.position, prop_type
        )
        opp_adj = base_projection * (opp_adj_mult - 1.0)  # e.g., -8% = -0.08 * base
        
        # 5. Apply usage boost for injured teammates
        usage_boost_mult = self._calculate_usage_boost(injured_teammates)
        usage_boost = base_projection * usage_boost_mult
        
        # 6. Calculate regression adjustment
        # Pull projection toward season average based on regression strength
        season_avg = player.raw_avgs.get(pt, 0)
        current_proj = base_projection + opp_adj + usage_boost
        regression_adj = (season_avg - current_proj) * (self.config.regression_strength * 0.5)
        
        # 7. Final projection
        projection = current_proj + regression_adj
        
        # Clamp to reasonable range (can't be negative)
        projection = max(0, projection)
        
        breakdown = {
            "base_projection": base_projection,
            "opponent_adj": opp_adj,
            "usage_boost": usage_boost,
            "regression_adj": regression_adj,
            "contribution_rate": contribution_rate,
            "team_expected": team_expected,
            "opp_adj_multiplier": opp_adj_mult,
        }
        
        return projection, breakdown
    
    # =========================================================================
    # PICK GENERATION
    # =========================================================================
    
    def _evaluate_pick(
        self,
        player: PlayerContribution,
        projection: float,
        breakdown: Dict,
        line: float,
        prop_type: str,
    ) -> Tuple[str, float, float, List[str]]:
        """
        Evaluate if projection makes a good pick.
        
        Returns: (direction, edge_pct, confidence_score, factors)
        """
        pt = prop_type.lower()
        factors = []
        
        # Calculate edge
        edge_pct = _safe_divide((projection - line), line, 0) * 100
        
        # Determine direction
        direction = "OVER" if edge_pct > 0 else "UNDER"
        abs_edge = abs(edge_pct)
        
        # Start with base confidence
        confidence = 50.0
        
        # Factor 1: Edge magnitude
        if abs_edge >= 15:
            confidence += 20
            factors.append(f"Large edge: {abs_edge:.0f}%")
        elif abs_edge >= 10:
            confidence += 15
            factors.append(f"Strong edge: {abs_edge:.0f}%")
        elif abs_edge >= 5:
            confidence += 8
            factors.append(f"Moderate edge: {abs_edge:.0f}%")
        
        # Factor 2: Consistency (low CV = more reliable)
        cv = _calculate_cv(player.raw_avgs.get(pt, 0), player.stds.get(pt, 0))
        if cv < 0.20:
            confidence += 10
            factors.append(f"High consistency (CV={cv:.2f})")
        elif cv < 0.30:
            confidence += 5
            factors.append("Good consistency")
        elif cv > 0.50:
            confidence -= 10
            factors.append("High variance player")
        
        # Factor 3: Recent trend alignment
        recent = player.recent_values.get(pt, [])
        if recent:
            recent_avg = sum(recent) / len(recent)
            l10_avg = player.raw_avgs.get(pt, 0)
            
            if direction == "OVER":
                # For OVER, recent performance above average is good
                if recent_avg > l10_avg * 1.10:
                    confidence += 8
                    factors.append("Hot streak supports OVER")
                elif recent_avg < l10_avg * 0.90:
                    confidence -= 5
                    factors.append("Recent slump (caution for OVER)")
            else:  # UNDER
                if recent_avg < l10_avg * 0.90:
                    confidence += 8
                    factors.append("Cold streak supports UNDER")
                elif recent_avg > l10_avg * 1.10:
                    confidence -= 5
                    factors.append("Hot streak (caution for UNDER)")
        
        # Factor 4: Contribution rate stability
        # If L5 and season contribution rates are similar, more confident
        l5_rate = player.contribution_l5.get(pt, 0)
        season_rate = player.contribution_season.get(pt, 0)
        rate_stability = abs(_safe_divide(l5_rate - season_rate, season_rate, 0))
        
        if rate_stability < 0.10:
            confidence += 5
            factors.append("Stable contribution rate")
        elif rate_stability > 0.30:
            confidence -= 5
            factors.append("Volatile contribution rate")
        
        # Factor 5: Opponent defense impact
        opp_mult = breakdown.get("opp_adj_multiplier", 1.0)
        if direction == "OVER" and opp_mult >= 1.04:
            confidence += 8
            factors.append("Favorable matchup (weak defense)")
        elif direction == "OVER" and opp_mult <= 0.94:
            confidence -= 10  # Increased penalty for OVER vs elite D
            factors.append("Tough matchup (elite defense)")
        elif direction == "UNDER" and opp_mult <= 0.94:
            confidence += 12  # Increased boost for UNDER vs elite D (v1.1)
            factors.append("Elite defense supports UNDER")
        elif direction == "UNDER" and opp_mult <= 0.97:
            confidence += 6  # Good defense also helps UNDER
            factors.append("Good defense supports UNDER")
        
        # Factor 6: Usage boost
        usage_boost = breakdown.get("usage_boost", 0)
        if usage_boost > 0 and direction == "OVER":
            confidence += 5
            factors.append("Usage boost from injuries")
        
        # Clamp confidence
        confidence = max(min(confidence, 100), 20)
        
        return direction, abs_edge, confidence, factors
    
    def _generate_pick_for_player(
        self,
        conn: sqlite3.Connection,
        player: PlayerContribution,
        team_ctx: TeamContext,
        opponent_ctx: OpponentContext,
        prop_type: str,
        injured_teammates: List[Dict],
        game_date: str,
    ) -> Optional[RCMPick]:
        """Generate a pick for a player/prop if it meets criteria."""
        pt = prop_type.lower()
        
        # Calculate projection
        projection, breakdown = self._project_player_stat(
            player, team_ctx, opponent_ctx, prop_type, injured_teammates
        )
        
        # Get projection std
        projection_std = player.stds.get(pt, 0)
        
        # Get line
        sportsbook_line = self._get_sportsbook_line(
            conn, player.player_id, player.player_name, prop_type, game_date
        )
        
        if sportsbook_line:
            line = sportsbook_line
            line_source = "sportsbook"
        else:
            # Use L10 average as derived line (with adjustment)
            line = player.raw_avgs.get(pt, 0) * 1.02  # Slight adjustment
            line_source = "derived"
        
        if line <= 0:
            return None
        
        # Evaluate pick
        direction, abs_edge, confidence, factors = self._evaluate_pick(
            player, projection, breakdown, line, prop_type
        )
        
        # v1.4: Strategic direction filtering
        # PTS: UNDER only (63.9% vs 48.3% OVER)
        if pt == 'pts' and getattr(self.config, 'pts_under_only', False):
            if direction == "OVER":
                return None  # Skip PTS OVER picks
        
        # Check minimum edge
        # v1.1: Use asymmetric edge requirements (UNDER picks have lower bar)
        min_edge = self.config.min_edge_pct
        if direction == "UNDER":
            min_edge = getattr(self.config, 'min_edge_under', self.config.min_edge_pct)
        
        if abs_edge < min_edge:
            return None
        
        # Determine tier
        if abs_edge >= self.config.min_edge_premium and confidence >= self.config.premium_threshold:
            tier = "PREMIUM"
        elif confidence >= self.config.high_threshold:
            tier = "HIGH"
        else:
            tier = "STANDARD"
        
        # v1.2: Lower bar for UNDER picks (they historically hit better)
        # For UNDER picks with lower edge, still allow if confidence is decent
        if direction == "UNDER":
            # UNDERs with 8%+ edge and 70+ confidence are acceptable
            if abs_edge < 8 or confidence < 70:
                return None
        else:
            # OVERs need higher bar - 10%+ edge and 72+ confidence
            if abs_edge < 10 or confidence < 72:
                return None
        
        # Create pick
        return RCMPick(
            player_id=player.player_id,
            player_name=player.player_name,
            team_abbrev=player.team_abbrev,
            opponent_abbrev=opponent_ctx.team_abbrev,
            game_date=game_date,
            prop_type=prop_type.upper(),
            direction=direction,
            line=round(line, 1),
            line_source=line_source,
            projection=round(projection, 1),
            projection_std=round(projection_std, 1),
            base_projection=round(breakdown["base_projection"], 1),
            opponent_adj=round(breakdown["opponent_adj"], 2),
            usage_boost=round(breakdown["usage_boost"], 2),
            regression_adj=round(breakdown["regression_adj"], 2),
            edge_pct=round(abs_edge if direction == "OVER" else -abs_edge, 1),
            confidence_score=round(confidence, 1),
            confidence_tier=tier,
            contribution_rate=breakdown["contribution_rate"],
            team_expected_total=round(breakdown["team_expected"], 1),
            l5_avg=round(sum(player.recent_values.get(pt, [])) / max(len(player.recent_values.get(pt, [])), 1), 1),
            l10_avg=round(player.raw_avgs.get(pt, 0), 1),
            season_avg=round(player.raw_avgs.get(pt, 0), 1),
            factors=factors,
        )
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def get_daily_picks(self, game_date: str) -> DailyRCMPicks:
        """
        Generate picks for all games on a given date.
        """
        conn = self._get_connection()
        
        try:
            # Get games on this date
            games = conn.execute(
                """
                SELECT 
                    g.id, g.game_date,
                    t1.id as team1_id, t1.name as team1_name,
                    t2.id as team2_id, t2.name as team2_name
                FROM games g
                JOIN teams t1 ON t1.id = g.team1_id
                JOIN teams t2 ON t2.id = g.team2_id
                WHERE g.game_date = ?
                """,
                (game_date,),
            ).fetchall()
            
            all_picks: List[RCMPick] = []
            player_pick_counts: Dict[int, int] = {}
            
            for game in games:
                game_picks = []
                
                # Process both teams
                for team_id, team_name, opp_id, opp_name in [
                    (game["team1_id"], game["team1_name"], game["team2_id"], game["team2_name"]),
                    (game["team2_id"], game["team2_name"], game["team1_id"], game["team1_name"]),
                ]:
                    team_abbrev = abbrev_from_team_name(team_name) or "UNK"
                    opp_abbrev = abbrev_from_team_name(opp_name) or "UNK"
                    
                    # Load contexts
                    team_ctx = self._load_team_context(conn, team_id, game_date)
                    opponent_ctx = self._load_opponent_context(conn, opp_abbrev)
                    
                    # Get injured teammates
                    injured_teammates = self._get_injured_players(conn, game_date, team_abbrev)
                    
                    # Get players for this team
                    players = conn.execute(
                        """
                        SELECT DISTINCT bp.player_id
                        FROM boxscore_player bp
                        JOIN games g ON g.id = bp.game_id
                        WHERE bp.team_id = ?
                          AND g.game_date < ?
                          AND bp.minutes > 15
                        GROUP BY bp.player_id
                        HAVING COUNT(*) >= ?
                        """,
                        (team_id, game_date, self.config.min_games_required),
                    ).fetchall()
                    
                    for player_row in players:
                        player_id = player_row["player_id"]
                        
                        # Check player pick limit
                        if player_pick_counts.get(player_id, 0) >= self.config.max_picks_per_player:
                            continue
                        
                        # Load player contribution data
                        player = self._load_player_contribution(conn, player_id, game_date)
                        if not player:
                            continue
                        
                        # Generate picks for each prop type
                        for prop_type in self.config.prop_types:
                            pick = self._generate_pick_for_player(
                                conn, player, team_ctx, opponent_ctx,
                                prop_type, injured_teammates, game_date
                            )
                            
                            if pick:
                                game_picks.append(pick)
                                player_pick_counts[player_id] = player_pick_counts.get(player_id, 0) + 1
                        
                        # v1.3: AST only for high-assist players (5+ avg)
                        if getattr(self.config, 'include_ast', True) and player.raw_avgs.get("ast", 0) >= 5.0:
                            pick = self._generate_pick_for_player(
                                conn, player, team_ctx, opponent_ctx,
                                "ast", injured_teammates, game_date
                            )
                            if pick:
                                game_picks.append(pick)
                                player_pick_counts[player_id] = player_pick_counts.get(player_id, 0) + 1
                
                # Sort game picks by confidence and take top N
                game_picks.sort(key=lambda p: p.confidence_score, reverse=True)
                all_picks.extend(game_picks[:self.config.max_picks_per_game])
            
            # Final sort and limit
            all_picks.sort(key=lambda p: (
                0 if p.confidence_tier == "PREMIUM" else (1 if p.confidence_tier == "HIGH" else 2),
                -p.confidence_score
            ))
            all_picks = all_picks[:self.config.max_picks_per_day]
            
            return DailyRCMPicks(
                date=game_date,
                games=len(games),
                picks=all_picks,
            )
        
        finally:
            conn.close()
    
    def grade_pick(self, pick: RCMPick, conn: sqlite3.Connection = None) -> RCMPick:
        """Grade a pick by comparing to actual result."""
        should_close = False
        if conn is None:
            conn = self._get_connection()
            should_close = True
        
        try:
            # Get actual stats
            row = conn.execute(
                """
                SELECT bp.pts, bp.reb, bp.ast, bp.minutes
                FROM boxscore_player bp
                JOIN games g ON g.id = bp.game_id
                WHERE bp.player_id = ?
                  AND g.game_date = ?
                  AND bp.minutes IS NOT NULL
                """,
                (pick.player_id, pick.game_date),
            ).fetchone()
            
            if not row:
                return pick
            
            # Get actual value
            prop_map = {"PTS": "pts", "REB": "reb", "AST": "ast"}
            actual = row[prop_map.get(pick.prop_type, "pts")] or 0
            
            # Determine if hit
            if pick.direction == "OVER":
                hit = actual > pick.line
            else:
                hit = actual < pick.line
            
            pick.actual_value = actual
            pick.hit = hit
            
            return pick
        
        finally:
            if should_close:
                conn.close()
    
    def run_backtest(
        self,
        start_date: str,
        end_date: str,
    ) -> RCMBacktestResult:
        """
        Run comprehensive backtest over date range.
        """
        conn = self._get_connection()
        result = RCMBacktestResult(
            start_date=start_date,
            end_date=end_date,
            config=self.config,
        )
        
        try:
            # Get all dates in range
            dates = conn.execute(
                """
                SELECT DISTINCT game_date FROM games
                WHERE game_date >= ? AND game_date <= ?
                ORDER BY game_date
                """,
                (start_date, end_date),
            ).fetchall()
            
            for date_row in dates:
                game_date = date_row["game_date"]
                result.days_tested += 1
                
                # Generate picks for this date
                daily_picks = self.get_daily_picks(game_date)
                result.total_games += daily_picks.games
                
                daily_result = {
                    "date": game_date,
                    "games": daily_picks.games,
                    "picks": 0,
                    "hits": 0,
                }
                
                for pick in daily_picks.picks:
                    # Grade the pick
                    graded_pick = self.grade_pick(pick, conn)
                    
                    if graded_pick.actual_value is None:
                        continue  # No result available
                    
                    result.total_picks += 1
                    daily_result["picks"] += 1
                    
                    # Track hits
                    if graded_pick.hit:
                        result.hits += 1
                        daily_result["hits"] += 1
                    
                    # Track by tier
                    if graded_pick.confidence_tier == "PREMIUM":
                        result.premium_picks += 1
                        if graded_pick.hit:
                            result.premium_hits += 1
                    elif graded_pick.confidence_tier == "HIGH":
                        result.high_picks += 1
                        if graded_pick.hit:
                            result.high_hits += 1
                    else:
                        result.standard_picks += 1
                        if graded_pick.hit:
                            result.standard_hits += 1
                    
                    # Track by prop type
                    if graded_pick.prop_type == "PTS":
                        result.pts_picks += 1
                        if graded_pick.hit:
                            result.pts_hits += 1
                    elif graded_pick.prop_type == "REB":
                        result.reb_picks += 1
                        if graded_pick.hit:
                            result.reb_hits += 1
                    elif graded_pick.prop_type == "AST":
                        result.ast_picks += 1
                        if graded_pick.hit:
                            result.ast_hits += 1
                    
                    # Track by direction
                    if graded_pick.direction == "OVER":
                        result.over_picks += 1
                        if graded_pick.hit:
                            result.over_hits += 1
                    else:
                        result.under_picks += 1
                        if graded_pick.hit:
                            result.under_hits += 1
                    
                    result.all_picks.append(graded_pick)
                
                result.daily_results.append(daily_result)
            
            return result
        
        finally:
            conn.close()


# ============================================================================
# Module-Level Convenience Functions
# ============================================================================

def get_rcm_daily_picks(
    game_date: str,
    db_path: str = "data/db/nba_props.sqlite3",
    config: RCMConfig = None,
) -> DailyRCMPicks:
    """Convenience function to get daily picks."""
    model = RegressionContributionModel(db_path=db_path, config=config)
    return model.get_daily_picks(game_date)


def run_rcm_backtest(
    start_date: str,
    end_date: str,
    db_path: str = "data/db/nba_props.sqlite3",
    config: RCMConfig = None,
) -> RCMBacktestResult:
    """Convenience function to run backtest."""
    model = RegressionContributionModel(db_path=db_path, config=config)
    return model.run_backtest(start_date, end_date)


# ============================================================================
# Main (for testing)
# ============================================================================

if __name__ == "__main__":
    # Quick test
    import os
    db_path = os.path.join(os.path.dirname(__file__), "../../../data/db/nba_props.sqlite3")
    
    print("=" * 70)
    print("REGRESSION CONTRIBUTION MODEL - TEST RUN")
    print("=" * 70)
    
    model = RegressionContributionModel(db_path=db_path)
    
    # Test with a specific date
    test_date = "2026-01-10"
    print(f"\nGenerating picks for {test_date}...")
    picks = model.get_daily_picks(test_date)
    print(picks.summary())
    
    # Run a short backtest
    print("\nRunning backtest (2026-01-01 to 2026-01-10)...")
    result = model.run_backtest("2026-01-01", "2026-01-10")
    print(result.summary())

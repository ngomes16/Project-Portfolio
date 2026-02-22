"""
Model V9 - Line-Aware NBA Props Prediction Model
==================================================

This model addresses a CRITICAL flaw in previous models: using player averages
as "lines" instead of actual sportsbook betting lines. This led to inflated
success rates that don't reflect real-world betting performance.

KEY IMPROVEMENTS:
-----------------
1. **Actual Line Integration**: Uses real sportsbook lines when available
2. **Line Source Tracking**: Tracks whether line is from sportsbook or derived
3. **Realistic Edge Calculation**: Edge = projection vs actual betting line
4. **Line Discrepancy Analysis**: Tracks difference between derived and actual lines
5. **Conservative Projections**: Better calibrated to actual betting lines

THE PROBLEM WITH PREVIOUS MODELS:
---------------------------------
Previous models used:
- Cold bounce: line = L10 (player's 10-game average)
- Hot sustained: line = L15 (player's 15-game average)

Example: Peyton Watson
- Model projected: 4.9 rebounds
- Actual sportsbook line: 6.5 rebounds
- Previous model would use 4.9 as line, making OVER look attractive
- Reality: Player needs to beat 6.5, not 4.9

This version fixes this by:
1. Fetching actual sportsbook lines from database
2. Calculating edge vs REAL lines, not derived averages
3. Only making picks where projection beats the ACTUAL line

LINE SOURCING HIERARCHY:
------------------------
1. Sportsbook line (from sportsbook_lines table) - BEST
2. Derived line with adjustment factor (accounts for typical line differences)
3. Raw player average with warning flag

USAGE:
------
    from src.nba_props.engine.model_v9 import (
        get_daily_picks_v9,
        run_backtest_v9,
        ModelConfigV9,
    )
    
    # Get picks for today (will use sportsbook lines if available)
    picks = get_daily_picks_v9("2026-01-14")
    
    # Run backtest with line analysis
    result = run_backtest_v9("2025-12-01", "2026-01-13")

Author: NBA Props Team - Model V9
Last Updated: January 2026
"""
from __future__ import annotations

import sqlite3
import statistics
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any, Set

from ..db import Db
from ..team_aliases import abbrev_from_team_name, normalize_team_abbrev
from .model_version_tracker import (
    ModelVersionTracker, VersionPick, BacktestSummary, ModelInsight
)


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class ModelConfigV9:
    """
    Model V9 Configuration - Line Aware.
    
    KEY CHANGE: This model considers actual betting lines, not just player averages.
    """
    # === VERSION INFO ===
    model_name: str = "Model V9 - Line Aware"
    model_version: str = "9.0"
    
    # === DATA REQUIREMENTS ===
    min_games_required: int = 10
    min_minutes_filter: int = 5
    min_game_minutes: float = 20.0  # Min minutes to consider pick valid
    max_games_lookback: int = 20
    
    # === PROJECTION WEIGHTS ===
    # More conservative weighting - favor longer-term averages
    weight_l5: float = 0.25
    weight_l10: float = 0.25
    weight_l15: float = 0.25
    weight_season: float = 0.25
    
    # === LINE SOURCING ===
    use_sportsbook_lines: bool = True  # Prefer actual betting lines
    line_adjustment_factor: float = 1.05  # Derived lines typically 5% below actual
    min_edge_vs_actual_line: float = 5.0  # Need 5%+ edge vs ACTUAL line
    
    # === PATTERN DETECTION (REVISED) ===
    # Cold bounce - player is cold but showing signs of recovery
    cold_threshold: float = -15.0  # L5 is 15%+ below L15
    bounce_threshold: float = 5.0  # Last game at least 5% above L10
    
    # Hot sustained - player is hot and maintaining
    hot_threshold: float = 20.0  # L5 is 20%+ above L15
    sustained_games: int = 3  # 3+ of last 5 above L15
    
    # Consistency bonus
    consistency_threshold: float = 0.25  # CV < 25% = consistent
    
    # === PROP SELECTION ===
    prop_types: List[str] = field(default_factory=lambda: ['pts', 'reb'])
    include_assists: bool = False  # AST too volatile
    
    # === PICK LIMITS ===
    picks_per_game: int = 3
    max_picks_per_day: int = 15
    max_picks_per_player: int = 1  # Stricter - 1 prop per player
    
    # === CONFIDENCE SCORING ===
    premium_base_confidence: float = 80.0
    high_base_confidence: float = 70.0
    
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
class PlayerStats:
    """Player statistical profile for analysis."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: str
    games_played: int
    
    # Averages at different windows
    l3: Dict[str, float] = field(default_factory=dict)  # pts, reb, ast, min
    l5: Dict[str, float] = field(default_factory=dict)
    l10: Dict[str, float] = field(default_factory=dict)
    l15: Dict[str, float] = field(default_factory=dict)
    l20: Dict[str, float] = field(default_factory=dict)
    season: Dict[str, float] = field(default_factory=dict)
    
    # Deviations
    deviations: Dict[str, float] = field(default_factory=dict)  # L5 vs L15 for each stat
    
    # Last game values
    last_game: Dict[str, float] = field(default_factory=dict)
    
    # Standard deviations (for consistency)
    stds: Dict[str, float] = field(default_factory=dict)
    
    # Recent game values (for sustained pattern)
    recent_games: Dict[str, List[float]] = field(default_factory=dict)
    
    def get_projection(self, prop_type: str, config: ModelConfigV9) -> float:
        """Calculate weighted projection for a prop type."""
        pt = prop_type.lower()
        
        l5_val = self.l5.get(pt, 0)
        l10_val = self.l10.get(pt, 0)
        l15_val = self.l15.get(pt, 0)
        season_val = self.season.get(pt, 0)
        
        # Weighted average
        total_weight = config.weight_l5 + config.weight_l10 + config.weight_l15 + config.weight_season
        if total_weight <= 0:
            return season_val
        
        projection = (
            l5_val * config.weight_l5 +
            l10_val * config.weight_l10 +
            l15_val * config.weight_l15 +
            season_val * config.weight_season
        ) / total_weight
        
        return projection
    
    def get_cv(self, prop_type: str) -> float:
        """Get coefficient of variation (std/mean) for consistency."""
        pt = prop_type.lower()
        mean = self.l10.get(pt, 0)
        std = self.stds.get(pt, 0)
        if mean <= 0:
            return 1.0
        return std / mean


@dataclass
class PropPickV9:
    """Enhanced prop pick with line source tracking."""
    # Identity
    player_id: int
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    game_date: str
    
    # Pick details
    prop_type: str
    direction: str
    
    # LINE TRACKING (KEY IMPROVEMENT)
    line: float                      # The line we're betting against
    line_source: str                 # 'sportsbook', 'derived', 'average'
    sportsbook_line: Optional[float] # Actual sportsbook line if available
    derived_line: float              # Our calculated line (for comparison)
    
    # Projection
    projection: float
    projection_std: float
    edge_vs_line: float              # Edge vs the line we're using
    edge_vs_sportsbook: Optional[float]  # Edge vs actual sportsbook line
    
    # Pattern and confidence
    pattern: str
    confidence_tier: str
    confidence_score: float
    
    # Supporting data
    l5_avg: float
    l10_avg: float
    l15_avg: float
    l20_avg: float
    season_avg: float
    
    # Analysis
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)  # Important alerts
    
    # Results (filled after game)
    actual_value: Optional[float] = None
    hit: Optional[bool] = None
    hit_vs_sportsbook: Optional[bool] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for display/storage."""
        return {
            "player": self.player_name,
            "team": self.team_abbrev,
            "opponent": self.opponent_abbrev,
            "date": self.game_date,
            "prop": self.prop_type.upper(),
            "direction": self.direction,
            "line": round(self.line, 1),
            "line_source": self.line_source,
            "sportsbook_line": round(self.sportsbook_line, 1) if self.sportsbook_line else None,
            "derived_line": round(self.derived_line, 1),
            "projection": round(self.projection, 1),
            "edge": f"{self.edge_vs_line:.1f}%",
            "edge_vs_sb": f"{self.edge_vs_sportsbook:.1f}%" if self.edge_vs_sportsbook else "N/A",
            "pattern": self.pattern,
            "tier": self.confidence_tier,
            "confidence": round(self.confidence_score, 1),
            "reasons": self.reasons,
            "warnings": self.warnings,
            "actual": self.actual_value,
            "hit": self.hit,
        }
    
    def to_version_pick(self, version_id: int) -> VersionPick:
        """Convert to VersionPick for storage."""
        return VersionPick(
            version_id=version_id,
            pick_date=self.game_date,
            player_id=self.player_id,
            player_name=self.player_name,
            team_abbrev=self.team_abbrev,
            opponent_abbrev=self.opponent_abbrev,
            prop_type=self.prop_type,
            direction=self.direction,
            line_source=self.line_source,
            line=self.line,
            sportsbook_line=self.sportsbook_line,
            derived_line=self.derived_line,
            projection=self.projection,
            projection_std=self.projection_std,
            edge_vs_line=self.edge_vs_line,
            edge_vs_sportsbook=self.edge_vs_sportsbook,
            confidence_score=self.confidence_score,
            confidence_tier=self.confidence_tier,
            pattern=self.pattern,
            l5_avg=self.l5_avg,
            l10_avg=self.l10_avg,
            l15_avg=self.l15_avg,
            l20_avg=self.l20_avg,
            season_avg=self.season_avg,
            reasons=self.reasons,
            actual_value=self.actual_value,
            hit=self.hit,
            hit_vs_sportsbook=self.hit_vs_sportsbook,
        )


@dataclass
class DailyPicksV9:
    """All picks for a day with line analysis."""
    date: str
    games: int
    picks: List[PropPickV9] = field(default_factory=list)
    
    # Line sourcing stats
    picks_with_sportsbook_line: int = 0
    picks_with_derived_line: int = 0
    avg_line_discrepancy: float = 0.0
    
    @property
    def total_picks(self) -> int:
        return len(self.picks)
    
    @property
    def premium_picks(self) -> List[PropPickV9]:
        return [p for p in self.picks if p.confidence_tier == "PREMIUM"]
    
    @property
    def high_picks(self) -> List[PropPickV9]:
        return [p for p in self.picks if p.confidence_tier == "HIGH"]
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            f"=== {self.date} - MODEL V9 PICKS ===",
            f"Games: {self.games} | Total Picks: {self.total_picks}",
            f"Line Sources: {self.picks_with_sportsbook_line} sportsbook, {self.picks_with_derived_line} derived",
            "",
        ]
        
        for tier in ["PREMIUM", "HIGH"]:
            tier_picks = [p for p in self.picks if p.confidence_tier == tier]
            if tier_picks:
                lines.append(f"--- {tier} ({len(tier_picks)}) ---")
                for p in tier_picks:
                    sb_indicator = "📊" if p.sportsbook_line else "📈"
                    lines.append(
                        f"  {sb_indicator} {p.player_name} ({p.team_abbrev}): "
                        f"{p.prop_type.upper()} {p.direction} {p.line:.1f} | "
                        f"Proj: {p.projection:.1f} | Edge: {p.edge_vs_line:.1f}%"
                    )
                    if p.warnings:
                        lines.append(f"      ⚠️ {', '.join(p.warnings)}")
                lines.append("")
        
        return "\n".join(lines)


@dataclass
class BacktestResultV9:
    """Backtest results with line analysis."""
    start_date: str
    end_date: str
    config: ModelConfigV9
    
    # Overall
    total_picks: int = 0
    hits: int = 0
    
    # By tier
    premium_picks: int = 0
    premium_hits: int = 0
    high_picks: int = 0
    high_hits: int = 0
    
    # By prop type
    pts_picks: int = 0
    pts_hits: int = 0
    reb_picks: int = 0
    reb_hits: int = 0
    
    # LINE ANALYSIS (KEY METRICS)
    picks_with_sportsbook_line: int = 0
    hits_with_sportsbook_line: int = 0  # Hits when using actual lines
    picks_with_derived_line: int = 0
    hits_with_derived_line: int = 0
    
    total_line_discrepancy: float = 0.0  # Sum of (derived - sportsbook) differences
    line_discrepancy_count: int = 0
    
    # Games
    total_games: int = 0
    days_tested: int = 0
    
    # All picks
    all_picks: List[PropPickV9] = field(default_factory=list)
    daily_results: List[Dict] = field(default_factory=list)
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_picks if self.total_picks > 0 else 0.0
    
    @property
    def sportsbook_line_hit_rate(self) -> float:
        """Hit rate when using actual sportsbook lines."""
        if self.picks_with_sportsbook_line == 0:
            return 0.0
        return self.hits_with_sportsbook_line / self.picks_with_sportsbook_line
    
    @property
    def derived_line_hit_rate(self) -> float:
        """Hit rate when using derived lines."""
        if self.picks_with_derived_line == 0:
            return 0.0
        return self.hits_with_derived_line / self.picks_with_derived_line
    
    @property
    def avg_line_discrepancy(self) -> float:
        """Average difference between derived and actual lines."""
        if self.line_discrepancy_count == 0:
            return 0.0
        return self.total_line_discrepancy / self.line_discrepancy_count
    
    def summary(self) -> str:
        """Generate detailed summary."""
        lines = [
            "=" * 70,
            "MODEL V9 - LINE AWARE BACKTEST RESULTS",
            "=" * 70,
            f"Period: {self.start_date} to {self.end_date}",
            f"Days tested: {self.days_tested}",
            f"Total games: {self.total_games}",
            "",
            f"OVERALL: {self.hit_rate*100:.1f}% ({self.hits}/{self.total_picks})",
            "",
            "LINE SOURCE ANALYSIS (KEY METRIC):",
            f"  Sportsbook Lines: {self.sportsbook_line_hit_rate*100:.1f}% ({self.hits_with_sportsbook_line}/{self.picks_with_sportsbook_line})",
            f"  Derived Lines:    {self.derived_line_hit_rate*100:.1f}% ({self.hits_with_derived_line}/{self.picks_with_derived_line})",
            f"  Avg Line Diff:    {self.avg_line_discrepancy:.2f} (derived - sportsbook)",
            "",
            "BY TIER:",
            f"  PREMIUM: {self.premium_hits}/{self.premium_picks} ({self.premium_hits/self.premium_picks*100:.1f}%)" if self.premium_picks else "  PREMIUM: N/A",
            f"  HIGH:    {self.high_hits}/{self.high_picks} ({self.high_hits/self.high_picks*100:.1f}%)" if self.high_picks else "  HIGH: N/A",
            "",
            "BY PROP TYPE:",
            f"  PTS: {self.pts_hits}/{self.pts_picks} ({self.pts_hits/self.pts_picks*100:.1f}%)" if self.pts_picks else "  PTS: N/A",
            f"  REB: {self.reb_hits}/{self.reb_picks} ({self.reb_hits/self.reb_picks*100:.1f}%)" if self.reb_picks else "  REB: N/A",
            "=" * 70,
        ]
        return "\n".join(lines)


# ============================================================================
# Utility Functions
# ============================================================================

def _normalize_name(name: str) -> str:
    """Normalize player name for matching."""
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_name.lower().strip()


def _get_injured_players(conn: sqlite3.Connection, game_date: str) -> Set[int]:
    """Get player IDs who are OUT or DOUBTFUL."""
    rows = conn.execute(
        """
        SELECT DISTINCT COALESCE(ir.player_id, p.id) as pid
        FROM injury_report ir
        LEFT JOIN players p ON LOWER(p.name) = LOWER(ir.player_name)
        WHERE ir.game_date = ?
          AND ir.status IN ('OUT', 'DOUBTFUL')
        """,
        (game_date,),
    ).fetchall()
    
    return {r["pid"] for r in rows if r["pid"]}


def _get_sportsbook_line(
    conn: sqlite3.Connection,
    player_id: int,
    player_name: str,
    prop_type: str,
    game_date: str,
) -> Optional[float]:
    """
    Fetch actual sportsbook line for a player/prop/date.
    
    Returns None if no line available.
    """
    # Try by player_id first
    if player_id:
        row = conn.execute(
            """
            SELECT line FROM sportsbook_lines
            WHERE player_id = ? AND prop_type = ? AND as_of_date = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (player_id, prop_type.upper(), game_date)
        ).fetchone()
        
        if row:
            return row["line"]
    
    # Try by player name (fuzzy match)
    rows = conn.execute(
        """
        SELECT sl.line, p.name
        FROM sportsbook_lines sl
        JOIN players p ON p.id = sl.player_id
        WHERE sl.prop_type = ? AND sl.as_of_date = ?
        """,
        (prop_type.upper(), game_date)
    ).fetchall()
    
    norm_name = _normalize_name(player_name)
    for row in rows:
        if _normalize_name(row["name"]) == norm_name:
            return row["line"]
    
    return None


# ============================================================================
# Core Functions
# ============================================================================

def _load_player_stats(
    conn: sqlite3.Connection,
    player_id: int,
    before_date: str,
    config: ModelConfigV9,
) -> Optional[PlayerStats]:
    """Load player's complete statistical profile."""
    # Get player info
    player = conn.execute(
        "SELECT id, name FROM players WHERE id = ?", (player_id,)
    ).fetchone()
    
    if not player:
        return None
    
    # Get game history
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
          AND b.minutes > ?
        ORDER BY g.game_date DESC
        LIMIT ?
        """,
        (player_id, before_date, config.min_minutes_filter, config.max_games_lookback),
    ).fetchall()
    
    if len(rows) < config.min_games_required:
        return None
    
    games = [dict(r) for r in rows]
    n = len(games)
    
    # Extract stats
    stats = {
        'pts': [g["pts"] or 0 for g in games],
        'reb': [g["reb"] or 0 for g in games],
        'ast': [g["ast"] or 0 for g in games],
        'min': [g["minutes"] or 0 for g in games],
    }
    
    def avg(vals, limit=None):
        subset = vals[:limit] if limit else vals
        return sum(subset) / len(subset) if subset else 0.0
    
    def safe_std(vals, limit=10):
        subset = vals[:limit]
        return statistics.stdev(subset) if len(subset) >= 2 else 0.0
    
    # Calculate averages at each window
    player_stats = PlayerStats(
        player_id=player_id,
        player_name=player["name"],
        team_abbrev=abbrev_from_team_name(games[0]["team_name"]) or "",
        position=games[0].get("pos") or "G",
        games_played=n,
    )
    
    for stat in ['pts', 'reb', 'ast', 'min']:
        vals = stats[stat]
        player_stats.l3[stat] = avg(vals, 3)
        player_stats.l5[stat] = avg(vals, 5)
        player_stats.l10[stat] = avg(vals, 10)
        player_stats.l15[stat] = avg(vals, 15) if n >= 15 else avg(vals)
        player_stats.l20[stat] = avg(vals, 20) if n >= 20 else avg(vals)
        player_stats.season[stat] = avg(vals)
        player_stats.stds[stat] = safe_std(vals)
        player_stats.last_game[stat] = vals[0] if vals else 0
        player_stats.recent_games[stat] = vals[:5]
        
        # Deviation: L5 vs L15
        l15 = player_stats.l15[stat]
        if l15 > 0:
            player_stats.deviations[stat] = (player_stats.l5[stat] - l15) / l15 * 100
        else:
            player_stats.deviations[stat] = 0.0
    
    return player_stats


def _analyze_pattern(
    stats: PlayerStats,
    prop_type: str,
    config: ModelConfigV9,
) -> Optional[Tuple[str, float, List[str]]]:
    """
    Analyze patterns for a prop type.
    
    Returns: (pattern_name, confidence_bonus, reasons) or None
    """
    pt = prop_type.lower()
    
    deviation = stats.deviations.get(pt, 0)
    l3 = stats.l3.get(pt, 0)
    l5 = stats.l5.get(pt, 0)
    l10 = stats.l10.get(pt, 0)
    l15 = stats.l15.get(pt, 0)
    last_game = stats.last_game.get(pt, 0)
    recent = stats.recent_games.get(pt, [])
    
    # Check COLD BOUNCE pattern
    # Player is cold but last game shows recovery
    if deviation <= config.cold_threshold:
        # Check for bounce - last game above L10
        bounce_pct = (last_game - l10) / l10 * 100 if l10 > 0 else 0
        if bounce_pct >= config.bounce_threshold:
            reasons = [
                f"Cold streak: L5 is {deviation:.0f}% below L15",
                f"Bounce-back: Last game ({last_game:.0f}) is {bounce_pct:.0f}% above L10 ({l10:.1f})",
                f"Expecting regression toward mean ({l15:.1f})",
            ]
            confidence_bonus = min(bounce_pct, 10)  # Cap bonus
            return ("cold_bounce", confidence_bonus, reasons)
    
    # Check HOT SUSTAINED pattern
    # Player is hot and maintaining performance
    if deviation >= config.hot_threshold:
        # Check if L3 > L5 (still accelerating or maintaining)
        if l3 >= l5 * 0.95:  # Allow slight dip
            # Count games above L15
            games_above = sum(1 for v in recent if v > l15)
            if games_above >= config.sustained_games:
                reasons = [
                    f"Hot streak: L5 is {deviation:.0f}% above L15",
                    f"Maintaining: L3 ({l3:.1f}) ≥ L5 ({l5:.1f})",
                    f"Sustained: {games_above}/5 recent games above L15",
                ]
                confidence_bonus = min(deviation - config.hot_threshold, 10)
                return ("hot_sustained", confidence_bonus, reasons)
    
    # Check CONSISTENCY pattern (for reliable players)
    cv = stats.get_cv(pt)
    if cv < config.consistency_threshold:
        # Very consistent player - their average is reliable
        reasons = [
            f"Highly consistent (CV={cv:.2f})",
            f"L10 avg: {l10:.1f}, std: {stats.stds.get(pt, 0):.1f}",
        ]
        return ("consistent", 5.0, reasons)
    
    return None


def _generate_pick(
    conn: sqlite3.Connection,
    stats: PlayerStats,
    prop_type: str,
    opponent_abbrev: str,
    game_date: str,
    config: ModelConfigV9,
) -> Optional[PropPickV9]:
    """Generate a pick for a player/prop with proper line sourcing."""
    pt = prop_type.lower()
    
    # Analyze pattern
    pattern_result = _analyze_pattern(stats, prop_type, config)
    if not pattern_result:
        return None
    
    pattern, confidence_bonus, reasons = pattern_result
    
    # Calculate projection
    projection = stats.get_projection(pt, config)
    projection_std = stats.stds.get(pt, 0)
    
    # GET THE LINE (CRITICAL FIX)
    # 1. Try to get actual sportsbook line
    sportsbook_line = _get_sportsbook_line(
        conn, stats.player_id, stats.player_name, pt, game_date
    )
    
    # 2. Calculate derived line (what we'd estimate)
    # Use L10 as base, but apply adjustment factor
    derived_line = stats.l10.get(pt, 0)
    
    # 3. Determine which line to use and calculate edge
    warnings = []
    
    if sportsbook_line and config.use_sportsbook_lines:
        line = sportsbook_line
        line_source = "sportsbook"
        
        # Track discrepancy
        discrepancy = derived_line - sportsbook_line
        if abs(discrepancy) > 1.0:
            warnings.append(f"Line diff: derived {derived_line:.1f} vs actual {sportsbook_line:.1f}")
    else:
        # Apply adjustment factor to derived line
        line = derived_line * config.line_adjustment_factor
        line_source = "derived"
        warnings.append("No sportsbook line - using derived estimate")
    
    # Calculate edges
    edge_vs_line = (projection - line) / line * 100 if line > 0 else 0
    edge_vs_sportsbook = None
    if sportsbook_line:
        edge_vs_sportsbook = (projection - sportsbook_line) / sportsbook_line * 100
    
    # Check if edge is sufficient
    # When using actual lines, need edge vs that line
    # When using derived, be more conservative
    min_edge = config.min_edge_vs_actual_line
    if line_source == "derived":
        min_edge *= 1.5  # Require more edge for derived lines
    
    if edge_vs_line < min_edge:
        return None
    
    # Additional check: if sportsbook line exists, edge must be positive vs it
    if sportsbook_line and edge_vs_sportsbook is not None and edge_vs_sportsbook < 0:
        return None  # Projection doesn't beat actual line
    
    # Calculate confidence
    base_confidence = (
        config.premium_base_confidence if pattern == "cold_bounce"
        else config.high_base_confidence
    )
    
    # Adjust for consistency
    cv = stats.get_cv(pt)
    if cv < 0.20:
        confidence_bonus += 5  # Very consistent
    elif cv > 0.40:
        confidence_bonus -= 10  # Volatile
    
    # Adjust for line source
    if line_source == "sportsbook":
        confidence_bonus += 5  # More reliable edge calc
    
    confidence_score = min(base_confidence + confidence_bonus, 100)
    
    # Determine tier
    confidence_tier = "PREMIUM" if pattern == "cold_bounce" else "HIGH"
    
    return PropPickV9(
        player_id=stats.player_id,
        player_name=stats.player_name,
        team_abbrev=stats.team_abbrev,
        opponent_abbrev=opponent_abbrev,
        game_date=game_date,
        prop_type=prop_type.upper(),
        direction="OVER",
        line=round(line, 1),
        line_source=line_source,
        sportsbook_line=sportsbook_line,
        derived_line=round(derived_line, 1),
        projection=round(projection, 1),
        projection_std=round(projection_std, 1),
        edge_vs_line=round(edge_vs_line, 1),
        edge_vs_sportsbook=round(edge_vs_sportsbook, 1) if edge_vs_sportsbook else None,
        pattern=pattern,
        confidence_tier=confidence_tier,
        confidence_score=confidence_score,
        l5_avg=round(stats.l5.get(pt, 0), 1),
        l10_avg=round(stats.l10.get(pt, 0), 1),
        l15_avg=round(stats.l15.get(pt, 0), 1),
        l20_avg=round(stats.l20.get(pt, 0), 1),
        season_avg=round(stats.season.get(pt, 0), 1),
        reasons=reasons,
        warnings=warnings,
    )


def _generate_game_picks(
    conn: sqlite3.Connection,
    game_date: str,
    team1_name: str,
    team2_name: str,
    config: ModelConfigV9,
) -> List[PropPickV9]:
    """Generate picks for a single game."""
    t1_abbrev = abbrev_from_team_name(team1_name) or ""
    t2_abbrev = abbrev_from_team_name(team2_name) or ""
    
    injured = _get_injured_players(conn, game_date)
    
    all_picks = []
    
    for team_name, opp_abbrev in [(team1_name, t2_abbrev), (team2_name, t1_abbrev)]:
        team = conn.execute("SELECT id FROM teams WHERE name = ?", (team_name,)).fetchone()
        if not team:
            continue
        
        # Get team's players
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
            (team["id"], game_date, config.min_minutes_filter, config.min_games_required),
        ).fetchall()
        
        for p in players:
            player_id = p["player_id"]
            
            if player_id in injured:
                continue
            
            stats = _load_player_stats(conn, player_id, game_date, config)
            if not stats:
                continue
            
            # Generate picks for each prop type
            for pt in config.prop_types:
                pick = _generate_pick(conn, stats, pt, opp_abbrev, game_date, config)
                if pick:
                    all_picks.append(pick)
    
    return all_picks


# ============================================================================
# Public API
# ============================================================================

def get_daily_picks_v9(
    game_date: str,
    config: Optional[ModelConfigV9] = None,
    db_path: str = "data/db/nba_props.sqlite3",
) -> DailyPicksV9:
    """
    Generate picks for all games on a date.
    
    Uses actual sportsbook lines when available.
    """
    if config is None:
        config = ModelConfigV9()
    
    db = Db(db_path)
    daily = DailyPicksV9(date=game_date, games=0)
    
    all_picks = []
    
    with db.connect() as conn:
        # Try completed games
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
            daily.games = len(games)
            for game in games:
                picks = _generate_game_picks(conn, game_date, game["team1"], game["team2"], config)
                all_picks.extend(picks)
        else:
            # Try scheduled games
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
            for game in scheduled:
                picks = _generate_game_picks(conn, game_date, game["away_team"], game["home_team"], config)
                all_picks.extend(picks)
    
    # Sort by confidence
    all_picks.sort(key=lambda p: p.confidence_score, reverse=True)
    
    # Select with limits
    target_picks = min(daily.games * config.picks_per_game, config.max_picks_per_day)
    
    selected = []
    player_counts: Dict[int, int] = {}
    
    for pick in all_picks:
        if player_counts.get(pick.player_id, 0) >= config.max_picks_per_player:
            continue
        selected.append(pick)
        player_counts[pick.player_id] = player_counts.get(pick.player_id, 0) + 1
        if len(selected) >= target_picks:
            break
    
    daily.picks = selected
    
    # Calculate line stats
    daily.picks_with_sportsbook_line = sum(1 for p in selected if p.line_source == "sportsbook")
    daily.picks_with_derived_line = sum(1 for p in selected if p.line_source == "derived")
    
    discrepancies = [p.derived_line - p.sportsbook_line for p in selected if p.sportsbook_line]
    if discrepancies:
        daily.avg_line_discrepancy = sum(discrepancies) / len(discrepancies)
    
    return daily


def run_backtest_v9(
    start_date: str,
    end_date: str,
    config: Optional[ModelConfigV9] = None,
    db_path: str = "data/db/nba_props.sqlite3",
    verbose: bool = True,
    track_version: bool = True,
) -> BacktestResultV9:
    """
    Run comprehensive backtest with line analysis.
    
    Key improvement: tracks performance separately for picks with actual vs derived lines.
    """
    if config is None:
        config = ModelConfigV9()
    
    db = Db(db_path)
    result = BacktestResultV9(start_date=start_date, end_date=end_date, config=config)
    
    # Register model version if tracking
    version_id = None
    if track_version:
        tracker = ModelVersionTracker(db_path)
        version_id = tracker.register_version(
            name=config.model_name,
            version=config.model_version,
            config=config.to_dict(),
            description="Line-aware model addressing projection vs actual line discrepancy",
        )
    
    with db.connect() as conn:
        # Get all game dates
        dates = conn.execute(
            """
            SELECT DISTINCT game_date 
            FROM games 
            WHERE game_date BETWEEN ? AND ?
            ORDER BY game_date
            """,
            (start_date, end_date),
        ).fetchall()
        
        if verbose:
            print(f"Model V9 Backtest: {len(dates)} days from {start_date} to {end_date}")
        
        for date_row in dates:
            game_date = date_row["game_date"]
            
            # Get games
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
            
            num_games = len(games)
            result.total_games += num_games
            
            if num_games == 0:
                continue
            
            result.days_tested += 1
            
            # Generate picks
            all_day_picks = []
            for game in games:
                picks = _generate_game_picks(conn, game_date, game["team1"], game["team2"], config)
                all_day_picks.extend(picks)
            
            # Sort and select
            all_day_picks.sort(key=lambda p: p.confidence_score, reverse=True)
            target = min(num_games * config.picks_per_game, config.max_picks_per_day)
            
            selected = []
            player_counts: Dict[int, int] = {}
            for pick in all_day_picks:
                if player_counts.get(pick.player_id, 0) >= config.max_picks_per_player:
                    continue
                selected.append(pick)
                player_counts[pick.player_id] = player_counts.get(pick.player_id, 0) + 1
                if len(selected) >= target:
                    break
            
            # Grade picks
            day_hits = 0
            day_graded = 0
            
            for pick in selected:
                actual = conn.execute(
                    """
                    SELECT b.pts, b.reb, b.ast, b.minutes
                    FROM boxscore_player b
                    JOIN games g ON g.id = b.game_id
                    WHERE b.player_id = ? AND g.game_date = ?
                    """,
                    (pick.player_id, game_date),
                ).fetchone()
                
                # Skip if didn't play enough minutes
                if not actual or (actual['minutes'] or 0) < config.min_game_minutes:
                    continue
                
                actual_val = actual[pick.prop_type.lower()] or 0
                pick.actual_value = actual_val
                pick.hit = actual_val > pick.line
                
                # Also check if beat sportsbook line
                if pick.sportsbook_line:
                    pick.hit_vs_sportsbook = actual_val > pick.sportsbook_line
                
                result.all_picks.append(pick)
                result.total_picks += 1
                day_graded += 1
                
                if pick.hit:
                    result.hits += 1
                    day_hits += 1
                
                # Track by line source (KEY METRIC)
                if pick.line_source == "sportsbook":
                    result.picks_with_sportsbook_line += 1
                    if pick.hit:
                        result.hits_with_sportsbook_line += 1
                else:
                    result.picks_with_derived_line += 1
                    if pick.hit:
                        result.hits_with_derived_line += 1
                
                # Track line discrepancy
                if pick.sportsbook_line:
                    result.total_line_discrepancy += (pick.derived_line - pick.sportsbook_line)
                    result.line_discrepancy_count += 1
                
                # By tier
                if pick.confidence_tier == "PREMIUM":
                    result.premium_picks += 1
                    if pick.hit:
                        result.premium_hits += 1
                else:
                    result.high_picks += 1
                    if pick.hit:
                        result.high_hits += 1
                
                # By prop type
                if pick.prop_type == "PTS":
                    result.pts_picks += 1
                    if pick.hit:
                        result.pts_hits += 1
                elif pick.prop_type == "REB":
                    result.reb_picks += 1
                    if pick.hit:
                        result.reb_hits += 1
            
            result.daily_results.append({
                'date': game_date,
                'games': num_games,
                'picks': day_graded,
                'hits': day_hits,
                'rate': day_hits / day_graded * 100 if day_graded else 0,
            })
    
    # Save to version tracker if tracking
    if version_id and track_version:
        tracker = ModelVersionTracker(db_path)
        
        # Save picks
        version_picks = [p.to_version_pick(version_id) for p in result.all_picks]
        tracker.save_picks(version_id, version_picks)
        
        # Save backtest summary
        summary = BacktestSummary(
            version_id=version_id,
            start_date=start_date,
            end_date=end_date,
            days_tested=result.days_tested,
            total_games=result.total_games,
            total_picks=result.total_picks,
            hits=result.hits,
            misses=result.total_picks - result.hits,
            premium_picks=result.premium_picks,
            premium_hits=result.premium_hits,
            high_picks=result.high_picks,
            high_hits=result.high_hits,
            pts_picks=result.pts_picks,
            pts_hits=result.pts_hits,
            reb_picks=result.reb_picks,
            reb_hits=result.reb_hits,
            over_picks=result.total_picks,
            over_hits=result.hits,
            picks_with_sportsbook_line=result.picks_with_sportsbook_line,
            hits_vs_sportsbook=result.hits_with_sportsbook_line,
            avg_line_diff=result.avg_line_discrepancy,
            daily_results=result.daily_results,
        )
        tracker.save_backtest(summary)
        
        # Update grades
        tracker.update_grades(version_id)
        
        # Add insights
        if result.picks_with_sportsbook_line > 0:
            tracker.add_insight(ModelInsight(
                version_id=version_id,
                insight_type="key_finding",
                category="overall",
                insight=f"Sportsbook line hit rate: {result.sportsbook_line_hit_rate*100:.1f}%",
                evidence=f"{result.hits_with_sportsbook_line}/{result.picks_with_sportsbook_line} picks"
            ))
        
        if result.avg_line_discrepancy != 0:
            tracker.add_insight(ModelInsight(
                version_id=version_id,
                insight_type="key_finding",
                category="methodology",
                insight=f"Avg line discrepancy: {result.avg_line_discrepancy:.2f}",
                evidence="Derived line typically differs from sportsbook"
            ))
    
    if verbose:
        print(result.summary())
    
    return result


def quick_backtest_v9(days: int = 30, verbose: bool = True) -> BacktestResultV9:
    """Quick backtest over recent days."""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return run_backtest_v9(start, end, verbose=verbose)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Running Model V9 (Line-Aware) backtest...")
    result = quick_backtest_v9(days=60)

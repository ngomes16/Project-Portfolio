"""
Model V8 - Comprehensive NBA Props Prediction Model with Learning
===================================================================

This model combines pattern recognition with actual performance learning to
generate both OVER and UNDER picks with properly calibrated confidence levels.

KEY FEATURES:
1. Generates both OVER and UNDER picks (not just OVER)
2. Properly calibrated confidence scores (spread across 1-5 stars)
3. Learns from past pick performance to adjust weights
4. Respects star player status from archetype database
5. Incorporates injury information when available

CONFIDENCE CALIBRATION:
- 5 Stars (90+): Very high confidence, strong pattern + history
- 4 Stars (75-89): High confidence, good edge
- 3 Stars (60-74): Medium confidence, reasonable edge
- 2 Stars (45-59): Lower confidence, marginal edge
- 1 Star (30-44): Low confidence, speculative

Author: Model V8
Last Updated: January 2026
"""
from __future__ import annotations

import sqlite3
import statistics
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any

from ..db import Db
from ..team_aliases import abbrev_from_team_name, normalize_team_abbrev


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class ModelV8Config:
    """
    Model V8 configuration with learned adjustments.
    """
    # === DATA REQUIREMENTS ===
    min_games_required: int = 8           # Need 8+ game history
    min_minutes_filter: int = 5           # Filter out games with < 5 minutes
    max_games_lookback: int = 20          # Use last 20 games
    star_player_min_minutes: float = 23.0 # Star players avg 23+ minutes
    
    # === OVER PATTERN THRESHOLDS ===
    # Cold bounce-back pattern
    cold_deviation_threshold: float = -15.0   # L5 is 15%+ below L15
    bounce_threshold: float = 0.0             # Last game > L10 (any amount)
    
    # Hot sustained pattern
    hot_deviation_threshold: float = 20.0     # L5 is 20%+ above L15
    acceleration_required: bool = True        # L3 > L5
    sustained_games_above: int = 3            # 3+ of L5 above L15
    
    # === UNDER PATTERN THRESHOLDS ===
    # Hot cooldown pattern (player is due to regress)
    hot_cooldown_threshold: float = 25.0      # L5 is 25%+ above L15
    deceleration_check: bool = True           # L3 < L5 (cooling off)
    
    # Slump continuation pattern
    slump_threshold: float = -10.0            # L5 is 10%+ below L15
    no_bounce_threshold: float = 0.0          # Last game < L10 (still slumping)
    
    # Back-to-back fatigue
    b2b_under_boost: bool = True              # Boost UNDER confidence for B2B
    b2b_confidence_boost: float = 5.0         # Extra confidence for B2B UNDERs (reduced from 8)
    
    # === PROP SELECTION ===
    prop_types: List[str] = field(default_factory=lambda: ['pts', 'reb', 'ast'])
    
    # AST filtering (per Idea.txt: avoid assist props < 4 avg)
    min_ast_avg_for_prop: float = 4.0
    
    # === PICK LIMITS ===
    picks_per_game: int = 4               # Target 4 picks per game
    max_picks_per_day: int = 20           # Cap at 20 picks
    max_picks_per_player: int = 2         # Max 2 props per player
    
    # === CONFIDENCE SCORING (calibrated for spread across 1-5 stars) ===
    base_confidence: float = 35.0         # Lower starting point for more spread
    max_confidence: float = 95.0          # Cap confidence
    min_confidence: float = 25.0          # Floor confidence
    
    # Edge bonuses (scaled for realistic spread)
    edge_bonus_per_pct: float = 0.8       # Confidence per % edge
    consistency_bonus_max: float = 12.0   # Max bonus for consistency (increased)
    h2h_bonus: float = 6.0                # Bonus for H2H advantage (increased)
    star_player_bonus: float = 4.0        # Bonus for star players
    
    # === LEARNING WEIGHTS (adjusted based on historical performance) ===
    pts_over_adjustment: float = 0.0      # Learned adjustment for PTS OVERs
    pts_under_adjustment: float = 0.0     # Learned adjustment for PTS UNDERs
    reb_over_adjustment: float = 0.0
    reb_under_adjustment: float = 0.0
    ast_over_adjustment: float = 0.0
    ast_under_adjustment: float = 0.0
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PlayerHistory:
    """Player's statistical history for analysis."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: str
    games_played: int
    
    # Is this a star player?
    is_star_player: bool = False
    
    # Recent averages
    l3_pts: float = 0.0
    l3_reb: float = 0.0
    l3_ast: float = 0.0
    l3_min: float = 0.0
    
    l5_pts: float = 0.0
    l5_reb: float = 0.0
    l5_ast: float = 0.0
    l5_min: float = 0.0
    
    l10_pts: float = 0.0
    l10_reb: float = 0.0
    l10_ast: float = 0.0
    l10_min: float = 0.0
    
    l15_pts: float = 0.0
    l15_reb: float = 0.0
    l15_ast: float = 0.0
    l15_min: float = 0.0
    
    season_pts: float = 0.0
    season_reb: float = 0.0
    season_ast: float = 0.0
    season_min: float = 0.0
    
    # Deviations (L5 vs L15)
    pts_deviation: float = 0.0  # (L5 - L15) / L15 * 100
    reb_deviation: float = 0.0
    ast_deviation: float = 0.0
    
    # Last game values
    last_game_pts: float = 0.0
    last_game_reb: float = 0.0
    last_game_ast: float = 0.0
    last_game_min: float = 0.0
    
    # Consistency (standard deviation of L10)
    pts_std: float = 0.0
    reb_std: float = 0.0
    ast_std: float = 0.0
    
    # Recent games raw values (for sustained check)
    recent_pts: List[float] = field(default_factory=list)
    recent_reb: List[float] = field(default_factory=list)
    recent_ast: List[float] = field(default_factory=list)
    
    # H2H history vs opponent
    h2h_pts_avg: Optional[float] = None
    h2h_reb_avg: Optional[float] = None
    h2h_ast_avg: Optional[float] = None
    h2h_games: int = 0


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
    direction: str              # OVER or UNDER
    line: float                 # The line to beat
    projected_value: float      # Our projection
    edge_pct: float             # Edge percentage
    
    # Pattern and tier
    pattern: str                # Pattern name
    confidence_tier: str        # HIGH, MEDIUM, LOW
    confidence_score: float     # 0-100
    confidence_stars: int       # 1-5 stars
    
    # Supporting data
    l5_avg: float = 0.0
    l10_avg: float = 0.0
    l15_avg: float = 0.0
    deviation: float = 0.0      # L5 vs L15 deviation %
    
    # Metadata
    is_star_player: bool = False
    is_back_to_back: bool = False
    has_h2h_data: bool = False
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Result tracking (filled in after game)
    actual_value: Optional[float] = None
    hit: Optional[bool] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "player_name": self.player_name,
            "team": self.team_abbrev,
            "opponent": self.opponent_abbrev,
            "date": self.game_date,
            "prop_type": self.prop_type.upper(),
            "direction": self.direction,
            "line": round(self.line, 1),
            "projection": round(self.projected_value, 1),
            "edge": f"{self.edge_pct:.1f}%",
            "pattern": self.pattern,
            "tier": self.confidence_tier,
            "confidence": round(self.confidence_score, 1),
            "confidence_stars": self.confidence_stars,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "l5_avg": round(self.l5_avg, 1),
            "l10_avg": round(self.l10_avg, 1),
            "l15_avg": round(self.l15_avg, 1),
            "deviation": f"{self.deviation:+.1f}%",
            "is_star_player": self.is_star_player,
            "is_back_to_back": self.is_back_to_back,
            "has_h2h_data": self.has_h2h_data,
            "actual": self.actual_value,
            "hit": self.hit,
        }


@dataclass
class DailyPicks:
    """All picks for a single day."""
    date: str
    games: int
    picks: List[PropPick] = field(default_factory=list)
    
    @property
    def over_picks(self) -> List[PropPick]:
        return [p for p in self.picks if p.direction == "OVER"]
    
    @property
    def under_picks(self) -> List[PropPick]:
        return [p for p in self.picks if p.direction == "UNDER"]
    
    @property
    def high_confidence_picks(self) -> List[PropPick]:
        return [p for p in self.picks if p.confidence_tier == "HIGH"]
    
    @property
    def total_picks(self) -> int:
        return len(self.picks)
    
    @property
    def picks_count(self) -> int:
        """Alias for total_picks for compatibility."""
        return len(self.picks)
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            f"=== {self.date} - {self.games} games ===",
            f"Total picks: {self.total_picks}",
            f"OVER: {len(self.over_picks)}, UNDER: {len(self.under_picks)}",
            f"High Confidence: {len(self.high_confidence_picks)}",
            ""
        ]
        
        for direction in ["OVER", "UNDER"]:
            dir_picks = [p for p in self.picks if p.direction == direction]
            if dir_picks:
                lines.append(f"--- {direction} PICKS ---")
                for p in sorted(dir_picks, key=lambda x: -x.confidence_score)[:10]:
                    lines.append(
                        f"  {'⭐' * p.confidence_stars} {p.player_name} ({p.team_abbrev}): "
                        f"{p.prop_type.upper()} {p.direction} {p.line:.1f} | "
                        f"Conf: {p.confidence_score:.0f}"
                    )
                lines.append("")
        
        return "\n".join(lines)


@dataclass
class BacktestResult:
    """Comprehensive backtest results."""
    start_date: str
    end_date: str
    config: ModelV8Config
    
    # Overall
    total_picks: int = 0
    hits: int = 0
    
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
    low_picks: int = 0
    low_hits: int = 0
    
    # By prop type
    pts_picks: int = 0
    pts_hits: int = 0
    reb_picks: int = 0
    reb_hits: int = 0
    ast_picks: int = 0
    ast_hits: int = 0
    
    # Games
    total_games: int = 0
    days_tested: int = 0
    
    # All picks
    all_picks: List[PropPick] = field(default_factory=list)
    
    # Daily results
    daily_results: List[Dict] = field(default_factory=list)
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total_picks if self.total_picks > 0 else 0.0
    
    @property
    def over_rate(self) -> float:
        return self.over_hits / self.over_picks if self.over_picks > 0 else 0.0
    
    @property
    def under_rate(self) -> float:
        return self.under_hits / self.under_picks if self.under_picks > 0 else 0.0
    
    @property
    def high_rate(self) -> float:
        return self.high_hits / self.high_picks if self.high_picks > 0 else 0.0
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            "=" * 70,
            "MODEL V8 - BACKTEST RESULTS",
            "=" * 70,
            f"Period: {self.start_date} to {self.end_date}",
            f"Days tested: {self.days_tested}",
            f"Total games: {self.total_games}",
            f"Avg picks/day: {self.total_picks/self.days_tested:.1f}" if self.days_tested > 0 else "",
            "",
            f"OVERALL: {self.hit_rate*100:.1f}% ({self.hits}/{self.total_picks})",
            "",
            "BY DIRECTION:",
            f"  OVER:  {self.over_rate*100:.1f}% ({self.over_hits}/{self.over_picks})",
            f"  UNDER: {self.under_rate*100:.1f}% ({self.under_hits}/{self.under_picks})",
            "",
            "BY CONFIDENCE:",
            f"  HIGH:   {self.high_rate*100:.1f}% ({self.high_hits}/{self.high_picks})" if self.high_picks > 0 else "",
            f"  MEDIUM: {self.medium_hits}/{self.medium_picks}" if self.medium_picks > 0 else "",
            f"  LOW:    {self.low_hits}/{self.low_picks}" if self.low_picks > 0 else "",
            "",
            "BY PROP TYPE:",
            f"  PTS: {self.pts_hits}/{self.pts_picks} ({self.pts_hits/self.pts_picks*100:.1f}%)" if self.pts_picks > 0 else "",
            f"  REB: {self.reb_hits}/{self.reb_picks} ({self.reb_hits/self.reb_picks*100:.1f}%)" if self.reb_picks > 0 else "",
            f"  AST: {self.ast_hits}/{self.ast_picks} ({self.ast_hits/self.ast_picks*100:.1f}%)" if self.ast_picks > 0 else "",
            "=" * 70,
        ]
        return "\n".join([l for l in lines if l])


# ============================================================================
# Core Functions
# ============================================================================

def _is_star_player(conn: sqlite3.Connection, player_name: str, team_abbrev: str, avg_minutes: float) -> bool:
    """
    Check if a player is considered a star player.
    
    A player is a star if:
    1. They are marked as star in player_archetypes table
    2. OR they average 23+ minutes per game
    """
    # Check archetypes table first
    row = conn.execute(
        """
        SELECT is_star FROM player_archetypes 
        WHERE LOWER(player_name) = LOWER(?) AND season = '2025-26'
        """,
        (player_name,)
    ).fetchone()
    
    if row and row["is_star"]:
        return True
    
    # Fall back to minutes check
    return avg_minutes >= 23.0


def _get_team_b2b_status(conn: sqlite3.Connection, team_abbrev: str, game_date: str) -> bool:
    """Check if team is playing on a back-to-back."""
    # Parse the game date
    try:
        gd = datetime.strptime(game_date, "%Y-%m-%d")
        yesterday = (gd - timedelta(days=1)).strftime("%Y-%m-%d")
    except:
        return False
    
    # Check for game yesterday
    row = conn.execute(
        """
        SELECT COUNT(*) as cnt FROM games g
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        WHERE g.game_date = ?
        AND (
            UPPER(t1.name) LIKE '%' || ? || '%'
            OR UPPER(t2.name) LIKE '%' || ? || '%'
        )
        """,
        (yesterday, team_abbrev.upper(), team_abbrev.upper())
    ).fetchone()
    
    return row["cnt"] > 0 if row else False


def _load_h2h_history(
    conn: sqlite3.Connection,
    player_id: int,
    opponent_abbrev: str,
    before_date: str,
) -> Tuple[Optional[float], Optional[float], Optional[float], int]:
    """Load player's head-to-head history against opponent."""
    rows = conn.execute(
        """
        SELECT b.pts, b.reb, b.ast
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        WHERE b.player_id = ?
          AND g.game_date < ?
          AND b.minutes > 10
          AND (
              UPPER(t1.name) LIKE '%' || ? || '%'
              OR UPPER(t2.name) LIKE '%' || ? || '%'
          )
          AND NOT (
              UPPER(t1.name) LIKE '%' || ? || '%'
              AND UPPER(t2.name) LIKE '%' || ? || '%'
          )
        ORDER BY g.game_date DESC
        LIMIT 5
        """,
        (player_id, before_date, opponent_abbrev, opponent_abbrev, opponent_abbrev, opponent_abbrev),
    ).fetchall()
    
    if not rows:
        return None, None, None, 0
    
    pts = [r["pts"] or 0 for r in rows]
    reb = [r["reb"] or 0 for r in rows]
    ast = [r["ast"] or 0 for r in rows]
    
    return (
        sum(pts) / len(pts) if pts else None,
        sum(reb) / len(reb) if reb else None,
        sum(ast) / len(ast) if ast else None,
        len(rows),
    )


def _load_player_history(
    conn: sqlite3.Connection,
    player_id: int,
    before_date: str,
    opponent_abbrev: str,
    config: ModelV8Config,
) -> Optional[PlayerHistory]:
    """
    Load player's game history for analysis.
    
    Returns None if player doesn't meet requirements.
    """
    # Query player info
    player = conn.execute(
        "SELECT id, name FROM players WHERE id = ?", (player_id,)
    ).fetchone()
    
    if not player:
        return None
    
    # Query game history
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
        LIMIT ?
        """,
        (player_id, before_date, config.max_games_lookback),
    ).fetchall()
    
    # Check minimum games
    if len(rows) < config.min_games_required:
        return None
    
    games = [dict(r) for r in rows]
    n = len(games)
    
    # Extract stat arrays
    pts = [g["pts"] or 0 for g in games]
    reb = [g["reb"] or 0 for g in games]
    ast = [g["ast"] or 0 for g in games]
    mins = [g["minutes"] or 0 for g in games]
    
    # Helper for safe averaging
    def avg(vals: List[float], limit: Optional[int] = None) -> float:
        subset = vals[:limit] if limit else vals
        return sum(subset) / len(subset) if subset else 0.0
    
    # Calculate averages at different windows
    l3_pts, l3_reb, l3_ast, l3_min = avg(pts, 3), avg(reb, 3), avg(ast, 3), avg(mins, 3)
    l5_pts, l5_reb, l5_ast, l5_min = avg(pts, 5), avg(reb, 5), avg(ast, 5), avg(mins, 5)
    l10_pts, l10_reb, l10_ast, l10_min = avg(pts, 10), avg(reb, 10), avg(ast, 10), avg(mins, 10)
    l15_pts = avg(pts, 15) if n >= 15 else avg(pts)
    l15_reb = avg(reb, 15) if n >= 15 else avg(reb)
    l15_ast = avg(ast, 15) if n >= 15 else avg(ast)
    l15_min = avg(mins, 15) if n >= 15 else avg(mins)
    season_pts, season_reb, season_ast, season_min = avg(pts), avg(reb), avg(ast), avg(mins)
    
    # Calculate deviations (L5 vs L15)
    def deviation(l5: float, l15: float) -> float:
        return (l5 - l15) / l15 * 100 if l15 > 0 else 0.0
    
    pts_dev = deviation(l5_pts, l15_pts)
    reb_dev = deviation(l5_reb, l15_reb)
    ast_dev = deviation(l5_ast, l15_ast)
    
    # Standard deviations (L10)
    def safe_std(vals: List[float], limit: int = 10) -> float:
        subset = vals[:limit]
        return statistics.stdev(subset) if len(subset) >= 2 else 0.0
    
    pts_std = safe_std(pts)
    reb_std = safe_std(reb)
    ast_std = safe_std(ast)
    
    # Team abbrev
    team_name = games[0]["team_name"] if games else ""
    position = games[0]["pos"] if games else "G"
    team_abbrev = abbrev_from_team_name(team_name) or ""
    
    # Check if star player
    is_star = _is_star_player(conn, player["name"], team_abbrev, season_min)
    
    # Get H2H history
    h2h_pts, h2h_reb, h2h_ast, h2h_games = _load_h2h_history(
        conn, player_id, opponent_abbrev, before_date
    )
    
    return PlayerHistory(
        player_id=player_id,
        player_name=player["name"],
        team_abbrev=team_abbrev,
        position=position or "G",
        games_played=n,
        is_star_player=is_star,
        
        l3_pts=l3_pts, l3_reb=l3_reb, l3_ast=l3_ast, l3_min=l3_min,
        l5_pts=l5_pts, l5_reb=l5_reb, l5_ast=l5_ast, l5_min=l5_min,
        l10_pts=l10_pts, l10_reb=l10_reb, l10_ast=l10_ast, l10_min=l10_min,
        l15_pts=l15_pts, l15_reb=l15_reb, l15_ast=l15_ast, l15_min=l15_min,
        season_pts=season_pts, season_reb=season_reb, season_ast=season_ast, season_min=season_min,
        
        pts_deviation=pts_dev, reb_deviation=reb_dev, ast_deviation=ast_dev,
        
        last_game_pts=pts[0], last_game_reb=reb[0], last_game_ast=ast[0], last_game_min=mins[0],
        
        pts_std=pts_std, reb_std=reb_std, ast_std=ast_std,
        
        recent_pts=pts[:5], recent_reb=reb[:5], recent_ast=ast[:5],
        
        h2h_pts_avg=h2h_pts, h2h_reb_avg=h2h_reb, h2h_ast_avg=h2h_ast, h2h_games=h2h_games,
    )


def _calculate_confidence(
    edge_pct: float,
    consistency_cv: float,
    has_h2h: bool,
    is_star: bool,
    is_b2b: bool,
    direction: str,
    config: ModelV8Config,
) -> Tuple[float, str, int]:
    """
    Calculate confidence score, tier, and stars.
    
    Returns: (confidence_score, tier, stars)
    
    Calibrated to produce a spread across 1-5 stars:
    - Small edges (< 5%) result in lower confidence (1-2 stars)
    - Medium edges (5-15%) result in medium confidence (2-4 stars)
    - Large edges (> 15%) with consistency result in high confidence (4-5 stars)
    """
    import math
    
    # Start with base confidence
    confidence = config.base_confidence
    
    # Cap the edge for confidence calculation purposes
    # Real betting edges are rarely > 15%, so we cap the effect of high edges
    edge_magnitude = min(abs(edge_pct), 20.0)  # Cap at 20% for scoring
    
    # More granular edge scoring
    if edge_magnitude < 3:
        # Very small edges: minimal bonus
        edge_bonus = edge_magnitude * 0.3
    elif edge_magnitude < 6:
        # Small edges: small bonus
        edge_bonus = 0.9 + (edge_magnitude - 3) * 0.5
    elif edge_magnitude < 12:
        # Medium edges: moderate bonus
        edge_bonus = 2.4 + (edge_magnitude - 6) * 0.6
    elif edge_magnitude < 20:
        # Good edges: good bonus
        edge_bonus = 6.0 + (edge_magnitude - 12) * 0.4
    else:
        # Large edges: diminishing returns
        edge_bonus = 9.2 + math.sqrt(edge_magnitude - 20) * 1.5
    edge_bonus = min(edge_bonus, 15.0)  # Cap at 15
    confidence += edge_bonus
    
    # Consistency bonus (lower CV = more consistent = higher confidence)
    # Spread this out more
    if consistency_cv < 0.15:
        confidence += config.consistency_bonus_max
    elif consistency_cv < 0.22:
        confidence += config.consistency_bonus_max * 0.7
    elif consistency_cv < 0.30:
        confidence += config.consistency_bonus_max * 0.4
    elif consistency_cv < 0.40:
        confidence += config.consistency_bonus_max * 0.15
    # High CV (> 0.40): no bonus, player is inconsistent
    
    # Inconsistency PENALTY for very inconsistent players
    if consistency_cv > 0.45:
        confidence -= 5.0
    
    # H2H bonus (only if they have history against opponent)
    if has_h2h:
        confidence += config.h2h_bonus
    
    # Star player bonus (stars are more predictable)
    if is_star:
        confidence += config.star_player_bonus
    
    # B2B adjustment
    if is_b2b:
        if direction == "UNDER":
            confidence += config.b2b_confidence_boost  # B2B favors UNDERs
        else:
            confidence -= 4.0  # B2B penalty for OVERs
    
    # Penalty for weak edges (makes low-edge picks less confident)
    if edge_magnitude < 4:
        confidence -= 10.0  # Big penalty for very weak edges
    elif edge_magnitude < 7:
        confidence -= 5.0  # Moderate penalty
    elif edge_magnitude < 10:
        confidence -= 2.0  # Small penalty
    
    # Clamp confidence
    confidence = max(config.min_confidence, min(config.max_confidence, confidence))
    
    # Determine tier (adjusted thresholds)
    if confidence >= 80:
        tier = "HIGH"
    elif confidence >= 60:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    
    # Determine stars (more spread out thresholds)
    if confidence >= 88:
        stars = 5
    elif confidence >= 78:
        stars = 4
    elif confidence >= 65:
        stars = 3
    elif confidence >= 50:
        stars = 2
    else:
        stars = 1
    
    return confidence, tier, stars


def _check_over_patterns(
    history: PlayerHistory,
    prop_type: str,
    is_b2b: bool,
    config: ModelV8Config,
) -> Optional[Tuple[str, float, float, float, List[str]]]:
    """
    Check OVER patterns for a player/prop.
    
    Returns: (pattern_name, line, edge_pct, confidence_adjustment, reasons) or None
    """
    pt = prop_type.lower()
    
    # Get relevant stats
    deviation = getattr(history, f"{pt}_deviation")
    l3 = getattr(history, f"l3_{pt}")
    l5 = getattr(history, f"l5_{pt}")
    l10 = getattr(history, f"l10_{pt}")
    l15 = getattr(history, f"l15_{pt}")
    last_game = getattr(history, f"last_game_{pt}")
    recent = getattr(history, f"recent_{pt}")
    
    # Pattern 1: Cold Bounce-Back
    if deviation <= config.cold_deviation_threshold:
        # Check bounce-back
        if last_game > l10:
            bounce_edge = (last_game - l10) / l10 * 100 if l10 > 0 else 0
            line = l10  # Line is L10
            edge = (l15 - line) / line * 100 if line > 0 else 0
            # Strong bounce-backs get higher confidence
            conf_adj = 15.0 if bounce_edge > 20 else 10.0 if bounce_edge > 10 else 5.0
            reasons = [
                f"Cold streak (L5 {deviation:+.0f}% vs L15)",
                f"Bouncing back: last game {last_game:.0f} > L10 {l10:.1f}",
                f"Expect regression toward L15 ({l15:.1f})",
            ]
            return ("cold_bounce", line, edge, conf_adj, reasons)
    
    # Pattern 2: Hot Sustained
    if deviation >= config.hot_deviation_threshold:
        # Check acceleration
        if not config.acceleration_required or l3 > l5:
            # Check sustained
            games_above = sum(1 for v in recent if v > l15)
            if games_above >= config.sustained_games_above:
                line = l15  # Line is L15
                edge = deviation
                # More sustained = higher confidence, acceleration = higher confidence
                conf_adj = 8.0  # Base for hitting pattern
                if l3 > l5 * 1.05:  # Strong acceleration
                    conf_adj += 15.0
                elif l3 > l5:  # Slight acceleration
                    conf_adj += 8.0
                if games_above >= 4:  # Very sustained
                    conf_adj += 8.0
                elif games_above >= 3:
                    conf_adj += 4.0
                reasons = [
                    f"Hot streak (L5 {deviation:+.0f}% vs L15)",
                    f"Accelerating: L3 {l3:.1f} > L5 {l5:.1f}" if l3 > l5 else "Sustained hot",
                    f"{games_above}/5 recent games above L15",
                ]
                return ("hot_sustained", line, edge, conf_adj, reasons)
    
    # Pattern 3: Consistent Performer (steady production)
    if abs(deviation) < 10 and history.games_played >= 15:
        # Very consistent - bet L10 to hit L10
        std = getattr(history, f"{pt}_std")
        cv = std / l10 if l10 > 0 else 1.0
        if cv < 0.25:  # Very consistent
            line = l10 * 0.95  # Slightly under L10
            edge = 5.0  # Small edge for consistency
            reasons = [
                f"Highly consistent: CV={cv:.2f}",
                f"Steady around L10 ({l10:.1f})",
            ]
            return ("consistent", line, edge, 8.0, reasons)
    
    return None


def _check_under_patterns(
    history: PlayerHistory,
    prop_type: str,
    is_b2b: bool,
    config: ModelV8Config,
) -> Optional[Tuple[str, float, float, float, List[str]]]:
    """
    Check UNDER patterns for a player/prop.
    
    Returns: (pattern_name, line, edge_pct, confidence_adjustment, reasons) or None
    """
    pt = prop_type.lower()
    
    # Get relevant stats
    deviation = getattr(history, f"{pt}_deviation")
    l3 = getattr(history, f"l3_{pt}")
    l5 = getattr(history, f"l5_{pt}")
    l10 = getattr(history, f"l10_{pt}")
    l15 = getattr(history, f"l15_{pt}")
    last_game = getattr(history, f"last_game_{pt}")
    
    # Pattern 1: Hot Cooldown (due for regression)
    if deviation >= config.hot_cooldown_threshold:
        # Check deceleration
        if config.deceleration_check and l3 < l5:
            line = l5  # Line is L5 (inflated)
            edge = (line - l15) / l15 * 100 if l15 > 0 else 0
            # Stronger deceleration = higher confidence
            decel_pct = (l5 - l3) / l5 * 100 if l5 > 0 else 0
            conf_adj = 15.0 if decel_pct > 15 else 10.0 if decel_pct > 8 else 5.0
            reasons = [
                f"Unsustainably hot (L5 {deviation:+.0f}% vs L15)",
                f"Cooling off: L3 {l3:.1f} < L5 {l5:.1f}",
                f"Expect regression toward L15 ({l15:.1f})",
            ]
            return ("hot_cooldown", line, edge, conf_adj, reasons)
    
    # Pattern 2: Slump Continuation
    if deviation <= config.slump_threshold:
        if last_game < l10:  # Still slumping
            line = l10  # Line is L10
            edge = (l10 - l5) / l10 * 100 if l10 > 0 else 0
            # Deeper slump and recent miss = higher confidence
            slump_depth = abs(deviation)
            conf_adj = 12.0 if slump_depth > 20 else 8.0 if slump_depth > 15 else 4.0
            reasons = [
                f"Slumping (L5 {deviation:+.0f}% vs L15)",
                f"Still cold: last game {last_game:.0f} < L10 {l10:.1f}",
            ]
            return ("slump_continuation", line, edge, conf_adj, reasons)
    
    # Pattern 3: B2B Fatigue
    if is_b2b and config.b2b_under_boost:
        # B2B typically causes 5-10% production drop
        line = l10
        edge = 8.0
        reasons = [
            "Back-to-back game fatigue",
            f"Expect ~5-10% drop from L10 ({l10:.1f})",
        ]
        return ("b2b_fatigue", line, edge, config.b2b_confidence_boost, reasons)
    
    return None


def _generate_pick(
    history: PlayerHistory,
    prop_type: str,
    opponent_abbrev: str,
    game_date: str,
    is_b2b: bool,
    config: ModelV8Config,
) -> List[PropPick]:
    """
    Generate picks for a player/prop combination.
    
    Can return multiple picks (OVER and UNDER) if both patterns match.
    """
    pt = prop_type.lower()
    picks = []
    
    # Skip AST props for players averaging < 4 assists
    if pt == "ast" and getattr(history, "l10_ast", 0) < config.min_ast_avg_for_prop:
        return picks
    
    # Get consistency metrics
    l10 = getattr(history, f"l10_{pt}")
    std = getattr(history, f"{pt}_std")
    cv = std / l10 if l10 > 0 else 1.0
    
    # Check H2H data
    h2h_avg = getattr(history, f"h2h_{pt}_avg", None)
    has_h2h = h2h_avg is not None and history.h2h_games >= 2
    
    # Check OVER patterns
    over_result = _check_over_patterns(history, prop_type, is_b2b, config)
    if over_result:
        pattern, line, edge, conf_adj, reasons = over_result
        
        # Add H2H context
        if has_h2h and h2h_avg > line:
            reasons.append(f"H2H avg vs {opponent_abbrev}: {h2h_avg:.1f}")
            edge += 3.0
        
        confidence, tier, stars = _calculate_confidence(
            edge, cv, has_h2h, history.is_star_player, is_b2b, "OVER", config
        )
        confidence += conf_adj
        
        # Recalculate tier and stars after adjustment
        if confidence >= 80:
            tier = "HIGH"
        elif confidence >= 60:
            tier = "MEDIUM"
        else:
            tier = "LOW"
            
        if confidence >= 88:
            stars = 5
        elif confidence >= 78:
            stars = 4
        elif confidence >= 65:
            stars = 3
        elif confidence >= 50:
            stars = 2
        else:
            stars = 1
        
        picks.append(PropPick(
            player_id=history.player_id,
            player_name=history.player_name,
            team_abbrev=history.team_abbrev,
            opponent_abbrev=opponent_abbrev,
            game_date=game_date,
            prop_type=prop_type.upper(),
            direction="OVER",
            line=round(line, 1),
            projected_value=round(getattr(history, f"l15_{pt}"), 1),
            edge_pct=round(edge, 1),
            pattern=pattern,
            confidence_tier=tier,
            confidence_score=min(confidence, config.max_confidence),
            confidence_stars=stars,
            l5_avg=getattr(history, f"l5_{pt}"),
            l10_avg=l10,
            l15_avg=getattr(history, f"l15_{pt}"),
            deviation=getattr(history, f"{pt}_deviation"),
            is_star_player=history.is_star_player,
            is_back_to_back=is_b2b,
            has_h2h_data=has_h2h,
            reasons=reasons,
        ))
    
    # Check UNDER patterns
    under_result = _check_under_patterns(history, prop_type, is_b2b, config)
    if under_result:
        pattern, line, edge, conf_adj, reasons = under_result
        
        # Add H2H context
        if has_h2h and h2h_avg < line:
            reasons.append(f"H2H avg vs {opponent_abbrev}: {h2h_avg:.1f}")
            edge += 3.0
        
        confidence, tier, stars = _calculate_confidence(
            edge, cv, has_h2h, history.is_star_player, is_b2b, "UNDER", config
        )
        confidence += conf_adj
        
        # Recalculate tier and stars after adjustment
        if confidence >= 80:
            tier = "HIGH"
        elif confidence >= 60:
            tier = "MEDIUM"
        else:
            tier = "LOW"
            
        if confidence >= 88:
            stars = 5
        elif confidence >= 78:
            stars = 4
        elif confidence >= 65:
            stars = 3
        elif confidence >= 50:
            stars = 2
        else:
            stars = 1
        
        picks.append(PropPick(
            player_id=history.player_id,
            player_name=history.player_name,
            team_abbrev=history.team_abbrev,
            opponent_abbrev=opponent_abbrev,
            game_date=game_date,
            prop_type=prop_type.upper(),
            direction="UNDER",
            line=round(line, 1),
            projected_value=round(getattr(history, f"l5_{pt}"), 1),
            edge_pct=round(edge, 1),
            pattern=pattern,
            confidence_tier=tier,
            confidence_score=min(confidence, config.max_confidence),
            confidence_stars=stars,
            l5_avg=getattr(history, f"l5_{pt}"),
            l10_avg=l10,
            l15_avg=getattr(history, f"l15_{pt}"),
            deviation=getattr(history, f"{pt}_deviation"),
            is_star_player=history.is_star_player,
            is_back_to_back=is_b2b,
            has_h2h_data=has_h2h,
            reasons=reasons,
        ))
    
    return picks


def _get_injured_players(
    conn: sqlite3.Connection,
    team_id: int,
    game_date: str,
) -> Dict[int, str]:
    """
    Get injured players for a team on a given date.
    
    Returns a dict mapping player_id -> injury_status (OUT, DOUBTFUL, QUESTIONABLE, PROBABLE)
    Also handles player name matching for entries without player_id.
    """
    # Direct lookup by team_id and game_date
    rows = conn.execute(
        """
        SELECT ir.player_id, ir.player_name, ir.status
        FROM injury_report ir
        WHERE ir.team_id = ?
          AND ir.game_date = ?
        """,
        (team_id, game_date),
    ).fetchall()
    
    result = {}
    unmatched_names = []
    
    for row in rows:
        status = row["status"].upper() if row["status"] else ""
        if row["player_id"]:
            result[row["player_id"]] = status
        elif row["player_name"]:
            unmatched_names.append((row["player_name"], status))
    
    # For entries without player_id, try to match by name
    # Use fuzzy matching (LIKE) to handle accent differences (Jokić vs Jokic)
    for player_name, status in unmatched_names:
        # Clean the player name - remove any matchup/team info that got incorrectly parsed
        clean_name = player_name
        # Remove common patterns that indicate parsing errors
        for pattern in [r'\d{2}:\d{2}\s*\(ET\)', r'[A-Z]{2,3}@[A-Z]{2,3}', r'(Denver|Chicago|Minnesota|Atlanta|New Orleans|Oklahoma City|Golden State|Portland|Sacramento|Los Angeles|Phoenix|Houston|Miami|Milwaukee|San Antonio|Cleveland|Detroit|Indiana|Orlando|Washington|Charlotte|Brooklyn|New York|Philadelphia|Boston|Toronto|Memphis)\s+(Nuggets|Bulls|Timberwolves|Hawks|Pelicans|Thunder|Warriors|Trail Blazers|Kings|Lakers|Clippers|Suns|Rockets|Heat|Bucks|Spurs|Cavaliers|Pistons|Pacers|Magic|Wizards|Hornets|Nets|Knicks|76ers|Celtics|Raptors|Grizzlies)']:
            import re
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE).strip()
        
        if not clean_name or len(clean_name) < 3:
            continue
        
        # Try to find matching player
        # Use unaccent-style matching by normalizing characters
        player_row = conn.execute(
            """
            SELECT id FROM players 
            WHERE LOWER(REPLACE(REPLACE(REPLACE(REPLACE(name, 'ć', 'c'), 'č', 'c'), 'ž', 'z'), 'š', 's')) 
                  LIKE LOWER(REPLACE(REPLACE(REPLACE(REPLACE(?, 'ć', 'c'), 'č', 'c'), 'ž', 'z'), 'š', 's'))
               OR name LIKE ?
            LIMIT 1
            """,
            (f"%{clean_name}%", f"%{clean_name}%"),
        ).fetchone()
        
        if player_row:
            result[player_row["id"]] = status
    
    return result


def _is_player_unavailable(injury_status: Optional[str]) -> bool:
    """Check if a player should be excluded from picks based on injury status."""
    if not injury_status:
        return False
    status = injury_status.upper()
    # Exclude OUT and DOUBTFUL players from picks
    return status in ("OUT", "DOUBTFUL")


def generate_game_picks(
    conn: sqlite3.Connection,
    game_date: str,
    team1_name: str,
    team2_name: str,
    config: ModelV8Config,
) -> List[PropPick]:
    """Generate picks for a single game, excluding injured players."""
    
    t1_abbrev = abbrev_from_team_name(team1_name) or ""
    t2_abbrev = abbrev_from_team_name(team2_name) or ""
    
    # Check B2B status for each team
    t1_b2b = _get_team_b2b_status(conn, t1_abbrev, game_date)
    t2_b2b = _get_team_b2b_status(conn, t2_abbrev, game_date)
    
    all_picks = []
    
    for team_name, opp_abbrev, is_b2b in [(team1_name, t2_abbrev, t1_b2b), (team2_name, t1_abbrev, t2_b2b)]:
        team = conn.execute("SELECT id FROM teams WHERE name = ?", (team_name,)).fetchone()
        if not team:
            continue
        
        team_id = team["id"]
        
        # Get injured players for this team on this date
        injured_players = _get_injured_players(conn, team_id, game_date)
        
        # Get players who have history with this team (top 12 by minutes)
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
            (team_id, game_date, config.min_minutes_filter, config.min_games_required),
        ).fetchall()
        
        for p in players:
            player_id = p["player_id"]
            
            # Check if player is injured (OUT or DOUBTFUL)
            injury_status = injured_players.get(player_id)
            if _is_player_unavailable(injury_status):
                # Skip this player - they're not playing
                continue
            
            history = _load_player_history(conn, player_id, game_date, opp_abbrev, config)
            if not history:
                continue
            
            # Add warning if player is QUESTIONABLE
            warnings = []
            if injury_status == "QUESTIONABLE":
                warnings.append("⚠️ Player is QUESTIONABLE - verify status before betting")
            
            # Generate picks for each prop type
            for pt in config.prop_types:
                picks = _generate_pick(history, pt, opp_abbrev, game_date, is_b2b, config)
                # Add injury warnings to all generated picks
                for pick in picks:
                    pick.warnings.extend(warnings)
                all_picks.extend(picks)
    
    return all_picks


# ============================================================================
# Public API
# ============================================================================

def get_daily_picks(
    game_date: str,
    config: Optional[ModelV8Config] = None,
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
        config = ModelV8Config()
    
    db = Db(db_path)
    daily = DailyPicks(date=game_date, games=0)
    
    all_picks = []
    
    with db.connect() as conn:
        # Try completed games first
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
                picks = generate_game_picks(conn, game_date, game["team1"], game["team2"], config)
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
                picks = generate_game_picks(conn, game_date, game["away_team"], game["home_team"], config)
                all_picks.extend(picks)
    
    # Sort by confidence
    all_picks.sort(key=lambda p: (-p.confidence_score, -p.is_star_player))
    
    # Apply limits with balance between OVER and UNDER
    target_picks = min(daily.games * config.picks_per_game, config.max_picks_per_day)
    
    # Select with player variety and direction balance
    selected = []
    player_counts: Dict[int, int] = {}
    over_count = 0
    under_count = 0
    
    # First pass: select best picks respecting limits
    for pick in all_picks:
        if player_counts.get(pick.player_id, 0) >= config.max_picks_per_player:
            continue
        
        selected.append(pick)
        player_counts[pick.player_id] = player_counts.get(pick.player_id, 0) + 1
        
        if pick.direction == "OVER":
            over_count += 1
        else:
            under_count += 1
        
        if len(selected) >= target_picks:
            break
    
    daily.picks = selected
    return daily


def learn_from_results(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> Dict[str, float]:
    """
    Analyze past pick results to learn adjustments.
    
    Returns dict of adjustments to apply to config.
    """
    # Get all graded picks in range
    rows = conn.execute(
        """
        SELECT p.prop_type, p.direction, r.hit
        FROM model_picks p
        JOIN model_pick_results r ON r.pick_id = p.id
        WHERE p.pick_date BETWEEN ? AND ?
          AND r.hit IS NOT NULL
        """,
        (start_date, end_date),
    ).fetchall()
    
    if not rows:
        return {}
    
    # Calculate hit rates by prop_type and direction
    stats = {}
    for row in rows:
        key = f"{row['prop_type']}_{row['direction']}"
        if key not in stats:
            stats[key] = {"hits": 0, "total": 0}
        stats[key]["total"] += 1
        if row["hit"]:
            stats[key]["hits"] += 1
    
    # Calculate adjustments (target 55% hit rate)
    adjustments = {}
    target_rate = 0.55
    for key, data in stats.items():
        if data["total"] >= 10:
            rate = data["hits"] / data["total"]
            # If below target, need to be more selective (positive adjustment)
            # If above target, can be less selective (negative adjustment)
            adjustment = (target_rate - rate) * 20  # Scale factor
            adjustments[key.lower() + "_adjustment"] = round(adjustment, 2)
    
    return adjustments


def run_backtest(
    start_date: str,
    end_date: str,
    config: Optional[ModelV8Config] = None,
    db_path: str = "data/db/nba_props.sqlite3",
    verbose: bool = True,
) -> BacktestResult:
    """
    Run comprehensive backtest of the model.
    
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
        config = ModelV8Config()
    
    db = Db(db_path)
    result = BacktestResult(start_date=start_date, end_date=end_date, config=config)
    
    with db.connect() as conn:
        # Get all game dates in range
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
            print(f"Backtesting {len(dates)} days from {start_date} to {end_date}...")
        
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
            
            num_games = len(games)
            result.total_games += num_games
            
            if num_games == 0:
                continue
            
            result.days_tested += 1
            
            # Generate picks
            all_day_picks = []
            for game in games:
                picks = generate_game_picks(conn, game_date, game["team1"], game["team2"], config)
                all_day_picks.extend(picks)
            
            # Sort and select
            all_day_picks.sort(key=lambda p: -p.confidence_score)
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
                
                # Skip players who didn't play significant minutes
                if not actual or (actual['minutes'] or 0) < 15:
                    continue
                
                actual_val = actual[pick.prop_type.lower()] or 0
                pick.actual_value = actual_val
                
                # Grade based on direction
                if pick.direction == "OVER":
                    pick.hit = actual_val > pick.line
                else:  # UNDER
                    pick.hit = actual_val < pick.line
                
                result.all_picks.append(pick)
                result.total_picks += 1
                day_graded += 1
                
                if pick.hit:
                    result.hits += 1
                    day_hits += 1
                
                # By direction
                if pick.direction == "OVER":
                    result.over_picks += 1
                    if pick.hit:
                        result.over_hits += 1
                else:
                    result.under_picks += 1
                    if pick.hit:
                        result.under_hits += 1
                
                # By confidence
                if pick.confidence_tier == "HIGH":
                    result.high_picks += 1
                    if pick.hit:
                        result.high_hits += 1
                elif pick.confidence_tier == "MEDIUM":
                    result.medium_picks += 1
                    if pick.hit:
                        result.medium_hits += 1
                else:
                    result.low_picks += 1
                    if pick.hit:
                        result.low_hits += 1
                
                # By prop type
                if pick.prop_type == "PTS":
                    result.pts_picks += 1
                    if pick.hit:
                        result.pts_hits += 1
                elif pick.prop_type == "REB":
                    result.reb_picks += 1
                    if pick.hit:
                        result.reb_hits += 1
                else:  # AST
                    result.ast_picks += 1
                    if pick.hit:
                        result.ast_hits += 1
            
            result.daily_results.append({
                'date': game_date,
                'games': num_games,
                'picks': day_graded,
                'hits': day_hits,
                'rate': day_hits / day_graded * 100 if day_graded else 0,
            })
    
    if verbose:
        print(result.summary())
    
    return result


def quick_backtest(days: int = 30, verbose: bool = True) -> BacktestResult:
    """Quick backtest over recent days."""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return run_backtest(start, end, verbose=verbose)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("Running Model V8 quick backtest...")
    quick_backtest()

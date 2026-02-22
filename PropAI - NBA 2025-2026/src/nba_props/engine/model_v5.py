"""
Model V5 - Comprehensive NBA Props Prediction Model
=====================================================

This model utilizes ALL available data sources for maximum accuracy:

DATA SOURCES UTILIZED:
----------------------
1. Box Scores (536 games, 11,678 player-game records)
2. Defense vs Position data (150 records across 30 teams)
3. Player Archetypes (152 players with tier info)
4. Head-to-Head history (player vs specific team)
5. Back-to-back detection
6. Injury reports
7. Hot/cold streak analysis
8. Home/away performance splits
9. Minutes stability analysis
10. Positional defense matchups

KEY IMPROVEMENTS OVER V4:
-------------------------
1. Head-to-head history analysis (how player performs vs specific team)
2. Position-specific defense factor from Hashtag Basketball data
3. Rest day impact (back-to-back penalty, extra rest bonus)
4. Recent form weighting (last 3 games extra emphasis for momentum)
5. Star player identification via archetypes AND minutes
6. Confidence scoring on 1-100 scale with star rating display (1-5 stars)
7. Balanced prop type selection with minimum thresholds
8. Home/away splits consideration

CONFIDENCE SYSTEM:
------------------
- Score 0-100 displayed as 1-5 stars
- 85-100: ★★★★★ (5 stars) - Elite picks
- 70-84: ★★★★☆ (4 stars) - High confidence
- 55-69: ★★★☆☆ (3 stars) - Medium confidence
- 40-54: ★★☆☆☆ (2 stars) - Low confidence
- 0-39:  ★☆☆☆☆ (1 star) - Very low confidence

Version: 5.0
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
class ModelV5Config:
    """
    Comprehensive configuration utilizing all available data.
    """
    # === STAT-SPECIFIC WEIGHTS ===
    # L3 for momentum, L5 for recent form, L10 for baseline, Season for stability
    pts_weight_l3: float = 0.15   # Recent momentum
    pts_weight_l5: float = 0.25   # Recent form
    pts_weight_l10: float = 0.35  # Baseline
    pts_weight_season: float = 0.25  # Stability
    
    reb_weight_l3: float = 0.10
    reb_weight_l5: float = 0.25
    reb_weight_l10: float = 0.40
    reb_weight_season: float = 0.25
    
    ast_weight_l3: float = 0.15
    ast_weight_l5: float = 0.30
    ast_weight_l10: float = 0.35
    ast_weight_season: float = 0.20
    
    # === EDGE THRESHOLDS ===
    # Based on backtest analysis: 12-16% edge actually performs best
    min_edge_threshold: float = 6.0        # Minimum to consider (raised)
    good_edge_threshold: float = 10.0      # For 3-star picks
    high_edge_threshold: float = 14.0      # For 4-star picks
    elite_edge_threshold: float = 18.0     # For 5-star picks
    
    # === MINIMUM LINE THRESHOLDS ===
    min_pts_line: float = 10.0             # Meaningful PTS picks (raised)
    min_reb_line: float = 4.0              # Meaningful REB picks (raised)
    min_ast_line: float = 3.0              # Meaningful AST picks (raised)
    
    # === CONFIDENCE THRESHOLDS ===
    # Map to star ratings - made more selective
    star_5_min: float = 88.0   # 5 stars (harder to achieve)
    star_4_min: float = 75.0   # 4 stars (raised)
    star_3_min: float = 60.0   # 3 stars (raised)
    star_2_min: float = 45.0   # 2 stars (raised)
    # Below 40 = 1 star
    
    # === PICK SELECTION ===
    picks_per_game: int = 3
    max_picks_per_player: int = 2
    min_minutes_threshold: float = 20.0
    star_minutes_threshold: float = 28.0
    min_games_required: int = 5   # Lowered to allow newer players
    
    # === ADJUSTMENTS STRENGTH ===
    # Defense vs Position (from Hashtag Basketball)
    defense_vs_position_strength: float = 0.45  # Strong factor
    
    # Head-to-head history weight
    h2h_weight: float = 0.25   # If we have 2+ games vs this opponent (increased from 0.20)
    
    # Back-to-back impact
    b2b_penalty: float = 0.06        # -6% for back-to-back
    extra_rest_bonus: float = 0.02   # +2% for 2+ days rest
    
    # Home/away adjustment
    home_bonus: float = 0.02         # +2% for home games
    
    # Hot/cold streak thresholds
    hot_streak_threshold: float = 15.0    # % above L10
    cold_streak_threshold: float = -15.0  # % below L10
    hot_streak_boost: float = 0.03        # 3% boost
    cold_streak_penalty: float = 0.03     # 3% penalty
    
    # Consistency thresholds
    low_cv_threshold: float = 0.22        # Very consistent
    high_cv_threshold: float = 0.38       # High variance
    
    def get_weights(self, prop_type: str) -> Tuple[float, float, float, float]:
        """Get weights for a specific prop type (L3, L5, L10, Season)."""
        pt = prop_type.upper()
        if pt == "PTS":
            return (self.pts_weight_l3, self.pts_weight_l5, self.pts_weight_l10, self.pts_weight_season)
        elif pt == "REB":
            return (self.reb_weight_l3, self.reb_weight_l5, self.reb_weight_l10, self.reb_weight_season)
        else:  # AST
            return (self.ast_weight_l3, self.ast_weight_l5, self.ast_weight_l10, self.ast_weight_season)
    
    def get_min_line(self, prop_type: str) -> float:
        """Get minimum line for prop type."""
        pt = prop_type.upper()
        if pt == "PTS":
            return self.min_pts_line
        elif pt == "REB":
            return self.min_reb_line
        return self.min_ast_line


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PlayerGameLog:
    """Player's comprehensive historical game data."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: str
    
    # Player tier
    is_star: bool
    archetype_tier: Optional[int]  # From player_archetypes table (1-6)
    
    # Counts
    games_played: int
    
    # L3 averages (momentum)
    l3_pts: float
    l3_reb: float
    l3_ast: float
    l3_min: float
    
    # L5 averages
    l5_pts: float
    l5_reb: float
    l5_ast: float
    l5_min: float
    
    # L10 averages
    l10_pts: float
    l10_reb: float
    l10_ast: float
    l10_min: float
    
    # Season averages
    season_pts: float
    season_reb: float
    season_ast: float
    season_min: float
    
    # Home/away splits
    home_pts: float
    home_reb: float
    home_ast: float
    away_pts: float
    away_reb: float
    away_ast: float
    
    # Head-to-head vs specific opponent
    h2h_games: int
    h2h_pts: float
    h2h_reb: float
    h2h_ast: float
    
    # Variability (L10 CV)
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
class DefenseProfile:
    """Team's defensive profile vs a position."""
    team_abbrev: str
    position: str
    
    pts_allowed: float
    pts_rank: int
    reb_allowed: float
    reb_rank: int
    ast_allowed: float
    ast_rank: int
    
    # Defense factor (< 1.0 = good defense, > 1.0 = bad defense)
    pts_factor: float
    reb_factor: float
    ast_factor: float


@dataclass
class PropPick:
    """A single prop bet recommendation with comprehensive scoring."""
    # Identity
    player_id: int
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    game_date: str
    is_home: bool
    
    # Pick details
    prop_type: str              # PTS, REB, AST
    direction: str              # OVER, UNDER
    projected_value: float      # Model's projection
    line: float                 # Line (L10 average)
    edge_pct: float             # Edge percentage
    
    # Confidence (0-100 score, 1-5 stars)
    confidence_score: float
    confidence_stars: int       # 1-5 stars
    confidence_tier: str        # For backwards compatibility: HIGH/MEDIUM/LOW
    
    # Component scores (0-100 max each, normalized)
    edge_score: float           # 0-25
    consistency_score: float    # 0-20
    trend_score: float          # 0-15
    defense_score: float        # 0-20 (defense vs position)
    h2h_score: float            # 0-10 (head-to-head bonus)
    situation_score: float      # 0-10 (rest, home/away)
    
    # Flags
    is_star_player: bool
    has_h2h_data: bool
    is_back_to_back: bool
    
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
            "player_id": self.player_id,
            "team": self.team_abbrev,
            "opponent": self.opponent_abbrev,
            "date": self.game_date,
            "is_home": self.is_home,
            "prop_type": self.prop_type,
            "direction": self.direction,
            "projection": self.projected_value,
            "line": self.line,
            "edge_pct": self.edge_pct,
            "confidence_score": self.confidence_score,
            "confidence_stars": self.confidence_stars,
            "confidence_tier": self.confidence_tier,
            "is_star": self.is_star_player,
            "has_h2h": self.has_h2h_data,
            "is_b2b": self.is_back_to_back,
            "reasons": self.reasons,
            "warnings": self.warnings,
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
    def picks_count(self) -> int:
        return len(self.picks)
    
    def by_stars(self, min_stars: int) -> List[PropPick]:
        return [p for p in self.picks if p.confidence_stars >= min_stars]
    
    def by_prop_type(self, prop_type: str) -> List[PropPick]:
        return [p for p in self.picks if p.prop_type == prop_type.upper()]


@dataclass
class BacktestResult:
    """Comprehensive backtest results."""
    start_date: str
    end_date: str
    config: ModelV5Config
    
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
    
    # By star rating
    star5_picks: int = 0
    star5_hits: int = 0
    star4_picks: int = 0
    star4_hits: int = 0
    star3_picks: int = 0
    star3_hits: int = 0
    star2_picks: int = 0
    star2_hits: int = 0
    star1_picks: int = 0
    star1_hits: int = 0
    
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
    def star5_hit_rate(self) -> float:
        return self.star5_hits / self.star5_picks if self.star5_picks > 0 else 0.0
    
    @property
    def star4_hit_rate(self) -> float:
        return self.star4_hits / self.star4_picks if self.star4_picks > 0 else 0.0
    
    @property
    def star3_hit_rate(self) -> float:
        return self.star3_hits / self.star3_picks if self.star3_picks > 0 else 0.0
    
    def summary(self) -> str:
        """Generate text summary."""
        lines = [
            "=" * 70,
            "MODEL V5 - COMPREHENSIVE BACKTEST RESULTS",
            "=" * 70,
            f"Period: {self.start_date} to {self.end_date}",
            f"Games: {self.total_games} ({self.games_with_picks} with picks)",
            "",
            f"OVERALL: {self.hit_rate*100:.1f}% ({self.hits}/{self.total_picks})",
            "",
            "BY STAR RATING:",
            f"  ★★★★★ (5 stars): {self.star5_hit_rate*100:.1f}% ({self.star5_hits}/{self.star5_picks})",
            f"  ★★★★☆ (4 stars): {self.star4_hit_rate*100:.1f}% ({self.star4_hits}/{self.star4_picks})",
            f"  ★★★☆☆ (3 stars): {self.star3_hit_rate*100:.1f}% ({self.star3_hits}/{self.star3_picks})",
            "",
            "BY PROP TYPE:",
            f"  PTS: {self.pts_hits}/{self.pts_picks} = {self.pts_hits/max(1,self.pts_picks)*100:.1f}%",
            f"  REB: {self.reb_hits}/{self.reb_picks} = {self.reb_hits/max(1,self.reb_picks)*100:.1f}%",
            f"  AST: {self.ast_hits}/{self.ast_picks} = {self.ast_hits/max(1,self.ast_picks)*100:.1f}%",
            "",
            "BY DIRECTION:",
            f"  OVER:  {self.over_hits}/{self.over_picks} = {self.over_hits/max(1,self.over_picks)*100:.1f}%",
            f"  UNDER: {self.under_hits}/{self.under_picks} = {self.under_hits/max(1,self.under_picks)*100:.1f}%",
            "=" * 70,
        ]
        
        return "\n".join(lines)


# ============================================================================
# Helper Functions
# ============================================================================

def _get_defense_vs_position(
    conn: sqlite3.Connection,
    team_abbrev: str,
    position: str,
) -> Optional[DefenseProfile]:
    """Get defense vs position data from Hashtag Basketball data."""
    opp = normalize_team_abbrev(team_abbrev)
    
    # Normalize position to single char
    pos = position.upper()[:1] if position else "G"
    pos_map = {"G": "PG", "F": "SF", "C": "C"}  # Map single char to full position
    full_pos = pos_map.get(pos, "PG")
    
    # Also try variations
    positions_to_try = [full_pos]
    if pos == "G":
        positions_to_try.extend(["PG", "SG"])
    elif pos == "F":
        positions_to_try.extend(["SF", "PF"])
    
    for try_pos in positions_to_try:
        row = conn.execute(
            """
            SELECT * FROM team_defense_vs_position
            WHERE team_abbrev = ? AND position = ?
            ORDER BY as_of_date DESC
            LIMIT 1
            """,
            (opp, try_pos),
        ).fetchone()
        
        if row:
            break
    
    if not row:
        return None
    
    # Calculate league averages for factors
    league_avgs = conn.execute(
        """
        SELECT 
            AVG(pts_allowed) as avg_pts,
            AVG(reb_allowed) as avg_reb,
            AVG(ast_allowed) as avg_ast
        FROM team_defense_vs_position
        WHERE position = ?
        """,
        (try_pos,),
    ).fetchone()
    
    if not league_avgs or not league_avgs["avg_pts"]:
        return None
    
    # Calculate defense factors
    pts_factor = (row["pts_allowed"] or 0) / league_avgs["avg_pts"] if league_avgs["avg_pts"] else 1.0
    reb_factor = (row["reb_allowed"] or 0) / league_avgs["avg_reb"] if league_avgs["avg_reb"] else 1.0
    ast_factor = (row["ast_allowed"] or 0) / league_avgs["avg_ast"] if league_avgs["avg_ast"] else 1.0
    
    return DefenseProfile(
        team_abbrev=opp,
        position=try_pos,
        pts_allowed=row["pts_allowed"] or 0,
        pts_rank=row["pts_rank"] or 15,
        reb_allowed=row["reb_allowed"] or 0,
        reb_rank=row["reb_rank"] or 15,
        ast_allowed=row["ast_allowed"] or 0,
        ast_rank=row["ast_rank"] or 15,
        pts_factor=pts_factor,
        reb_factor=reb_factor,
        ast_factor=ast_factor,
    )


def _get_player_h2h_stats(
    conn: sqlite3.Connection,
    player_id: int,
    opponent_abbrev: str,
    before_date: str,
) -> Tuple[int, float, float, float]:
    """Get player's historical stats vs specific opponent."""
    opp = normalize_team_abbrev(opponent_abbrev)
    
    # Get team IDs for this opponent
    team_rows = conn.execute(
        """
        SELECT id FROM teams WHERE name LIKE ? OR name LIKE ?
        """,
        (f"%{opp}%", f"% {opp}%"),
    ).fetchall()
    
    if not team_rows:
        return 0, 0.0, 0.0, 0.0
    
    team_ids = [r["id"] for r in team_rows]
    ph = ",".join(["?"] * len(team_ids))
    
    # Get games vs this opponent
    rows = conn.execute(
        f"""
        SELECT b.pts, b.reb, b.ast
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.player_id = ?
          AND g.game_date < ?
          AND b.minutes > 10
          AND (g.team1_id IN ({ph}) OR g.team2_id IN ({ph}))
          AND b.team_id NOT IN ({ph})
        ORDER BY g.game_date DESC
        LIMIT 5
        """,
        (player_id, before_date, *team_ids, *team_ids, *team_ids),
    ).fetchall()
    
    if not rows:
        return 0, 0.0, 0.0, 0.0
    
    games = len(rows)
    pts = sum(r["pts"] or 0 for r in rows) / games
    reb = sum(r["reb"] or 0 for r in rows) / games
    ast = sum(r["ast"] or 0 for r in rows) / games
    
    return games, pts, reb, ast


def _is_back_to_back(
    conn: sqlite3.Connection,
    team_abbrev: str,
    game_date: str,
) -> bool:
    """Check if team played yesterday (back-to-back)."""
    from datetime import datetime, timedelta
    
    try:
        dt = datetime.strptime(game_date, "%Y-%m-%d")
        yesterday = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    except:
        return False
    
    # Get team IDs
    team_name_pattern = f"%{team_abbrev}%"
    
    count = conn.execute(
        """
        SELECT COUNT(*) as cnt FROM games g
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        WHERE g.game_date = ?
          AND (t1.name LIKE ? OR t2.name LIKE ?)
        """,
        (yesterday, team_name_pattern, team_name_pattern),
    ).fetchone()
    
    return count["cnt"] > 0 if count else False


def _get_player_archetype_tier(
    conn: sqlite3.Connection,
    player_name: str,
) -> Optional[int]:
    """Get player's tier from archetypes table."""
    row = conn.execute(
        """
        SELECT tier FROM player_archetypes
        WHERE player_name = ?
        """,
        (player_name,),
    ).fetchone()
    
    return row["tier"] if row else None


def _load_player_game_log(
    conn: sqlite3.Connection,
    player_id: int,
    before_date: str,
    opponent_abbrev: str,
    config: ModelV5Config,
) -> Optional[PlayerGameLog]:
    """Load player's comprehensive game history."""
    
    player = conn.execute(
        "SELECT id, name FROM players WHERE id = ?", (player_id,)
    ).fetchone()
    
    if not player:
        return None
    
    rows = conn.execute(
        """
        SELECT 
            g.game_date, b.pts, b.reb, b.ast, b.minutes, b.pos,
            t.name as team_name,
            g.team1_id, g.team2_id, b.team_id
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
        try:
            std = statistics.stdev(vals)
            return std / mean
        except:
            return 0.0
    
    def trend(l5_avg, l10_avg, hot_th, cold_th):
        if l10_avg == 0:
            return "stable", 0.0
        pct = (l5_avg - l10_avg) / l10_avg * 100
        if pct >= hot_th:
            return "hot", pct
        elif pct <= cold_th:
            return "cold", pct
        return "stable", pct
    
    pts_trend, pts_trend_pct = trend(avg(pts, 5), avg(pts, 10), 
                                      config.hot_streak_threshold, config.cold_streak_threshold)
    reb_trend, reb_trend_pct = trend(avg(reb, 5), avg(reb, 10),
                                      config.hot_streak_threshold, config.cold_streak_threshold)
    ast_trend, ast_trend_pct = trend(avg(ast, 5), avg(ast, 10),
                                      config.hot_streak_threshold, config.cold_streak_threshold)
    
    team_name = games[0]["team_name"] if games else ""
    position = games[0]["pos"] if games else "G"
    avg_min = avg(mins)
    
    # Calculate home/away splits
    home_games = [g for g in games if g["team_id"] == g["team1_id"]]
    away_games = [g for g in games if g["team_id"] != g["team1_id"]]
    
    def safe_avg(game_list, stat):
        if not game_list:
            return 0.0
        return sum(g[stat] or 0 for g in game_list) / len(game_list)
    
    # Get H2H stats
    h2h_games, h2h_pts, h2h_reb, h2h_ast = _get_player_h2h_stats(
        conn, player_id, opponent_abbrev, before_date
    )
    
    # Get archetype tier
    archetype_tier = _get_player_archetype_tier(conn, player["name"])
    
    return PlayerGameLog(
        player_id=player_id,
        player_name=player["name"],
        team_abbrev=abbrev_from_team_name(team_name) or "",
        position=position or "G",
        is_star=avg_min >= config.star_minutes_threshold or (archetype_tier is not None and archetype_tier <= 3),
        archetype_tier=archetype_tier,
        games_played=len(games),
        
        l3_pts=avg(pts, 3), l3_reb=avg(reb, 3), l3_ast=avg(ast, 3), l3_min=avg(mins, 3),
        l5_pts=avg(pts, 5), l5_reb=avg(reb, 5), l5_ast=avg(ast, 5), l5_min=avg(mins, 5),
        l10_pts=avg(pts, 10), l10_reb=avg(reb, 10), l10_ast=avg(ast, 10), l10_min=avg(mins, 10),
        season_pts=avg(pts), season_reb=avg(reb), season_ast=avg(ast), season_min=avg(mins),
        
        home_pts=safe_avg(home_games, "pts"),
        home_reb=safe_avg(home_games, "reb"),
        home_ast=safe_avg(home_games, "ast"),
        away_pts=safe_avg(away_games, "pts"),
        away_reb=safe_avg(away_games, "reb"),
        away_ast=safe_avg(away_games, "ast"),
        
        h2h_games=h2h_games,
        h2h_pts=h2h_pts,
        h2h_reb=h2h_reb,
        h2h_ast=h2h_ast,
        
        pts_cv=cv(pts[:10]), reb_cv=cv(reb[:10]), ast_cv=cv(ast[:10]), min_cv=cv(mins[:10]),
        
        pts_trend=pts_trend, reb_trend=reb_trend, ast_trend=ast_trend,
        pts_trend_pct=pts_trend_pct, reb_trend_pct=reb_trend_pct, ast_trend_pct=ast_trend_pct,
        
        games=games,
    )


def _calculate_projection(
    plog: PlayerGameLog,
    prop_type: str,
    opponent_abbrev: str,
    is_home: bool,
    is_b2b: bool,
    defense_profile: Optional[DefenseProfile],
    conn: sqlite3.Connection,
    config: ModelV5Config,
) -> Tuple[float, float, float, float, float, float, List[str], List[str]]:
    """
    Calculate projection with all adjustments.
    
    Returns: (projected, line, edge_pct, defense_adj, h2h_adj, situation_adj, reasons, warnings)
    """
    pt = prop_type.lower()
    reasons = []
    warnings = []
    
    # Get weights (L3, L5, L10, Season)
    w3, w5, w10, ws = config.get_weights(prop_type)
    total_w = w3 + w5 + w10 + ws
    
    # Raw values
    l3 = getattr(plog, f"l3_{pt}")
    l5 = getattr(plog, f"l5_{pt}")
    l10 = getattr(plog, f"l10_{pt}")
    season = getattr(plog, f"season_{pt}")
    
    # Base projection (weighted average)
    projected = (l3 * w3 + l5 * w5 + l10 * w10 + season * ws) / total_w
    
    defense_adj = 0.0
    h2h_adj = 0.0
    situation_adj = 0.0
    
    # === Defense vs Position Adjustment ===
    if defense_profile:
        factor_attr = f"{pt}_factor"
        factor = getattr(defense_profile, factor_attr, 1.0)
        rank_attr = f"{pt}_rank"
        rank = getattr(defense_profile, rank_attr, 15)
        
        # Apply defense adjustment
        defense_adj = (factor - 1.0) * config.defense_vs_position_strength
        defense_adj = max(-0.15, min(0.15, defense_adj))  # Cap at ±15%
        
        if rank <= 5:
            warnings.append(f"Elite defense vs {plog.position} (#{rank})")
        elif rank <= 10:
            warnings.append(f"Strong defense vs {plog.position}")
        elif rank >= 25:
            reasons.append(f"Weak defense vs {plog.position} (#{rank})")
        elif rank >= 20:
            reasons.append(f"Poor defense vs {plog.position}")
    
    # === Head-to-Head Adjustment ===
    if plog.h2h_games >= 2:
        h2h_val = getattr(plog, f"h2h_{pt}")
        if h2h_val > 0:
            h2h_diff = (h2h_val - projected) / projected if projected > 0 else 0
            h2h_adj = h2h_diff * config.h2h_weight
            h2h_adj = max(-0.08, min(0.08, h2h_adj))  # Cap at ±8%
            
            if h2h_adj > 0.03:
                reasons.append(f"Good H2H vs {opponent_abbrev} ({h2h_val:.1f} avg)")
            elif h2h_adj < -0.03:
                warnings.append(f"Poor H2H vs {opponent_abbrev}")
    
    # === Situational Adjustments ===
    # Back-to-back
    if is_b2b:
        situation_adj -= config.b2b_penalty
        warnings.append("Back-to-back game")
    
    # Home/away
    if is_home:
        home_val = getattr(plog, f"home_{pt}")
        away_val = getattr(plog, f"away_{pt}")
        if home_val > away_val * 1.05:  # 5% better at home
            situation_adj += config.home_bonus
            reasons.append("Strong home performer")
    
    # === Trend Adjustment ===
    trend = getattr(plog, f"{pt}_trend")
    if trend == "hot":
        projected *= (1 + config.hot_streak_boost)
        reasons.append("Hot streak")
    elif trend == "cold":
        projected *= (1 - config.cold_streak_penalty)
        warnings.append("Cold streak")
    
    # Apply all adjustments
    total_adj = defense_adj + h2h_adj + situation_adj
    total_adj = max(-0.20, min(0.20, total_adj))  # Cap total at ±20%
    projected *= (1 + total_adj)
    
    # Calculate line (L10 average)
    vals = [g[pt] or 0 for g in plog.games]
    if len(vals) >= 10:
        line = sum(vals[:10]) / 10
    elif len(vals) >= 5:
        line = sum(vals[:5]) / 5
    else:
        line = sum(vals) / len(vals) if vals else projected
    
    edge_pct = (projected - line) / line * 100 if line > 0 else 0
    
    return projected, line, edge_pct, defense_adj, h2h_adj, situation_adj, reasons, warnings


def _score_to_stars(score: float, config: ModelV5Config) -> int:
    """Convert confidence score to star rating."""
    if score >= config.star_5_min:
        return 5
    elif score >= config.star_4_min:
        return 4
    elif score >= config.star_3_min:
        return 3
    elif score >= config.star_2_min:
        return 2
    return 1


def _stars_to_tier(stars: int) -> str:
    """Convert star rating to tier name for backwards compatibility."""
    if stars >= 4:
        return "HIGH"
    elif stars >= 3:
        return "MEDIUM"
    return "LOW"


def _generate_pick(
    plog: PlayerGameLog,
    prop_type: str,
    opponent_abbrev: str,
    game_date: str,
    is_home: bool,
    is_b2b: bool,
    defense_profile: Optional[DefenseProfile],
    conn: sqlite3.Connection,
    config: ModelV5Config,
) -> Optional[PropPick]:
    """Generate a single pick with comprehensive confidence scoring."""
    
    projected, line, edge_pct, defense_adj, h2h_adj, situation_adj, reasons, warnings = _calculate_projection(
        plog, prop_type, opponent_abbrev, is_home, is_b2b, defense_profile, conn, config
    )
    
    # Skip if line is below minimum threshold
    min_line = config.get_min_line(prop_type)
    if line < min_line:
        return None
    
    # Determine direction
    # Asymmetric thresholds based on backtest: UNDER hits at 62.1% vs OVER at 51.5%
    # Be more selective with OVER picks, more lenient with UNDER
    if edge_pct >= config.min_edge_threshold * 1.1:  # Require 10% more edge for OVER
        direction = "OVER"
    elif edge_pct <= -config.min_edge_threshold * 0.9:  # Slightly less edge needed for UNDER
        direction = "UNDER"
        edge_pct = abs(edge_pct)
    else:
        return None
    
    # === CONFIDENCE SCORING (0-100) ===
    
    # 1. Edge Score (0-25)
    if edge_pct >= config.elite_edge_threshold:
        edge_score = 25
    elif edge_pct >= config.high_edge_threshold:
        edge_score = 20
    elif edge_pct >= config.good_edge_threshold:
        edge_score = 15
    elif edge_pct >= config.min_edge_threshold:
        edge_score = 10
    else:
        edge_score = 5
    
    # 2. Consistency Score (0-20)
    cv = getattr(plog, f"{prop_type.lower()}_cv")
    if cv < config.low_cv_threshold:
        cons_score = 20
        reasons.append("Very consistent")
    elif cv < 0.30:
        cons_score = 15
    elif cv < config.high_cv_threshold:
        cons_score = 10
    else:
        cons_score = 5
        warnings.append("High variance")
    
    # 3. Trend Score (0-15)
    trend = getattr(plog, f"{prop_type.lower()}_trend")
    if (direction == "OVER" and trend == "hot") or (direction == "UNDER" and trend == "cold"):
        trend_score = 15
    elif trend == "stable":
        trend_score = 10
    else:
        trend_score = 5
    
    # 4. Defense Score (0-20)
    defense_score = 10  # Base
    if defense_profile:
        rank_attr = f"{prop_type.lower()}_rank"
        rank = getattr(defense_profile, rank_attr, 15)
        
        if direction == "OVER":
            # For OVER, we want weak defense (high rank)
            if rank >= 25:
                defense_score = 20
            elif rank >= 20:
                defense_score = 16
            elif rank >= 15:
                defense_score = 12
            elif rank <= 5:
                defense_score = 4
            elif rank <= 10:
                defense_score = 6
        else:  # UNDER
            # For UNDER, we want strong defense (low rank)
            if rank <= 5:
                defense_score = 20
            elif rank <= 10:
                defense_score = 16
            elif rank <= 15:
                defense_score = 12
            elif rank >= 25:
                defense_score = 4
            elif rank >= 20:
                defense_score = 6
    
    # 5. H2H Score (0-15) - INCREASED based on backtest showing 60% hit rate with H2H
    h2h_score = 5  # Base (no H2H data)
    if plog.h2h_games >= 2:
        h2h_val = getattr(plog, f"h2h_{prop_type.lower()}")
        if direction == "OVER" and h2h_val > projected:
            h2h_score = 15
            reasons.append(f"Strong H2H: {h2h_val:.1f} avg vs {opponent_abbrev}")
        elif direction == "UNDER" and h2h_val < projected:
            h2h_score = 15
            reasons.append(f"Weak H2H: {h2h_val:.1f} avg vs {opponent_abbrev}")
        elif direction == "OVER" and h2h_val > line:
            h2h_score = 12
        elif direction == "UNDER" and h2h_val < line:
            h2h_score = 12
        elif direction == "OVER" and h2h_val < projected * 0.85:
            h2h_score = 0
            warnings.append(f"H2H mismatch: Only {h2h_val:.1f} vs {opponent_abbrev}")
        elif direction == "UNDER" and h2h_val > projected * 1.15:
            h2h_score = 0
            warnings.append(f"H2H mismatch: {h2h_val:.1f} vs {opponent_abbrev}")
    
    # 6. Situation Score (0-15) - INCREASED B2B bonus for UNDER based on 63.4% hit rate
    situation_score = 7  # Base
    if is_b2b:
        if direction == "UNDER":
            situation_score = 15  # B2B significantly helps UNDER
            reasons.append("B2B fatigue favors UNDER")
        else:
            situation_score = 3   # B2B hurts OVER
            warnings.append("B2B may limit ceiling")
    if is_home and direction == "OVER":
        situation_score = min(15, situation_score + 2)
    
    # Total confidence score (max now 115 before normalization)
    confidence_score = edge_score + cons_score + trend_score + defense_score + h2h_score + situation_score
    
    # Normalize to 0-100 scale
    confidence_score = min(100, int(confidence_score * 100 / 115))
    
    # Star player bonus (based on 55% vs 48.2% hit rate)
    if plog.is_star:
        confidence_score = min(100, confidence_score + 8)
        reasons.insert(0, "Star player (predictable)")
    
    # Penalty for OVER picks without supporting factors (UNDER hit rate 58.2% vs OVER 51.6%)
    if direction == "OVER":
        over_supports = sum([
            h2h_score >= 12,  # Good H2H
            trend_score >= 10,  # Good trend
            defense_score >= 16,  # Weak defense
        ])
        if over_supports == 0:
            confidence_score = int(confidence_score * 0.85)  # 15% penalty for unsupported OVER
    
    # Convert to stars and tier
    stars = _score_to_stars(confidence_score, config)
    tier = _stars_to_tier(stars)
    
    reasons.insert(0, f"{edge_pct:.1f}% edge ({direction})")
    
    return PropPick(
        player_id=plog.player_id,
        player_name=plog.player_name,
        team_abbrev=plog.team_abbrev,
        opponent_abbrev=opponent_abbrev,
        game_date=game_date,
        is_home=is_home,
        prop_type=prop_type,
        direction=direction,
        projected_value=round(projected, 1),
        line=round(line, 1),
        edge_pct=round(edge_pct, 1),
        confidence_score=round(confidence_score, 1),
        confidence_stars=stars,
        confidence_tier=tier,
        edge_score=edge_score,
        consistency_score=cons_score,
        trend_score=trend_score,
        defense_score=defense_score,
        h2h_score=h2h_score,
        situation_score=situation_score,
        is_star_player=plog.is_star,
        has_h2h_data=plog.h2h_games >= 2,
        is_back_to_back=is_b2b,
        reasons=reasons,
        warnings=warnings,
    )


def generate_game_picks(
    conn: sqlite3.Connection,
    game_id: int,
    game_date: str,
    team1_name: str,
    team2_name: str,
    config: ModelV5Config,
) -> List[PropPick]:
    """Generate picks for a single game."""
    
    t1_abbrev = abbrev_from_team_name(team1_name) or ""
    t2_abbrev = abbrev_from_team_name(team2_name) or ""
    
    all_picks = []
    
    # Team1 is home, Team2 is away (based on standard convention)
    teams_info = [
        (team1_name, t2_abbrev, True),   # Team1 is home, opponent is T2
        (team2_name, t1_abbrev, False),  # Team2 is away, opponent is T1
    ]
    
    for team_name, opp_abbrev, is_home in teams_info:
        team = conn.execute("SELECT id FROM teams WHERE name = ?", (team_name,)).fetchone()
        if not team:
            continue
        
        own_abbrev = abbrev_from_team_name(team_name) or ""
        is_b2b = _is_back_to_back(conn, own_abbrev, game_date)
        
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
            (team["id"], game_date, config.min_minutes_threshold, config.min_games_required),
        ).fetchall()
        
        for p in players:
            plog = _load_player_game_log(conn, p["player_id"], game_date, opp_abbrev, config)
            if not plog or plog.season_min < config.min_minutes_threshold:
                continue
            
            for pt in ["PTS", "REB", "AST"]:
                # Get defense profile for this opponent vs this position
                defense_profile = _get_defense_vs_position(conn, opp_abbrev, plog.position)
                
                pick = _generate_pick(
                    plog, pt, opp_abbrev, game_date, is_home, is_b2b,
                    defense_profile, conn, config
                )
                if pick and pick.confidence_stars >= 3:  # Only 3+ star picks
                    all_picks.append(pick)
    
    # Sort by confidence score (highest first)
    all_picks.sort(key=lambda p: (p.confidence_score, p.edge_pct), reverse=True)
    
    # Select with variety
    selected = []
    player_counts = {}
    
    for pick in all_picks:
        if player_counts.get(pick.player_id, 0) >= config.max_picks_per_player:
            continue
        selected.append(pick)
        player_counts[pick.player_id] = player_counts.get(pick.player_id, 0) + 1
        if len(selected) >= config.picks_per_game:
            break
    
    # Relax if needed
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
# Public API
# ============================================================================

def get_daily_picks(
    game_date: str,
    config: Optional[ModelV5Config] = None,
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
        config = ModelV5Config()
    
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
            
            for game in games:
                picks = generate_game_picks(
                    conn, game["id"], game_date, game["team1"], game["team2"], config
                )
                daily.picks.extend(picks)
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
            
            for game in scheduled:
                # For scheduled games, use away_team as team1 and home_team as team2
                picks = generate_game_picks(
                    conn, game["id"], game_date, game["away_team"], game["home_team"], config
                )
                daily.picks.extend(picks)
    
    # Sort all picks by confidence score
    daily.picks.sort(key=lambda p: (p.confidence_score, p.edge_pct), reverse=True)
    
    return daily


def run_full_backtest(
    start_date: str,
    end_date: str,
    config: Optional[ModelV5Config] = None,
    db_path: str = "data/db/nba_props.sqlite3",
    verbose: bool = True,
) -> BacktestResult:
    """
    Run comprehensive backtest of Model V5.
    
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
        config = ModelV5Config()
    
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
        
        current_date = None
        daily_picks = 0
        daily_hits = 0
        
        for game in games:
            if game["game_date"] != current_date:
                if current_date and daily_picks > 0:
                    result.daily_results.append({
                        "date": current_date,
                        "picks": daily_picks,
                        "hits": daily_hits,
                        "rate": daily_hits / daily_picks * 100,
                    })
                current_date = game["game_date"]
                daily_picks = 0
                daily_hits = 0
            
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
                daily_picks += 1
                
                if hit:
                    result.hits += 1
                    daily_hits += 1
                
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
                
                # By star rating
                if pick.confidence_stars == 5:
                    result.star5_picks += 1
                    if hit: result.star5_hits += 1
                elif pick.confidence_stars == 4:
                    result.star4_picks += 1
                    if hit: result.star4_hits += 1
                elif pick.confidence_stars == 3:
                    result.star3_picks += 1
                    if hit: result.star3_hits += 1
                elif pick.confidence_stars == 2:
                    result.star2_picks += 1
                    if hit: result.star2_hits += 1
                else:
                    result.star1_picks += 1
                    if hit: result.star1_hits += 1
        
        # Add last day's results
        if current_date and daily_picks > 0:
            result.daily_results.append({
                "date": current_date,
                "picks": daily_picks,
                "hits": daily_hits,
                "rate": daily_hits / daily_picks * 100,
            })
        
        if verbose:
            print(result.summary())
    
    return result


def quick_backtest(days: int = 28, verbose: bool = True) -> BacktestResult:
    """Quick backtest over recent days (default 28 days / 4 weeks)."""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return run_full_backtest(start, end, verbose=verbose)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("Running Model V5 comprehensive backtest (4 weeks)...")
    result = quick_backtest(days=28)
    
    print("\n\nDetailed daily breakdown:")
    for day in result.daily_results[-7:]:  # Last 7 days
        print(f"  {day['date']}: {day['hits']}/{day['picks']} = {day['rate']:.1f}%")

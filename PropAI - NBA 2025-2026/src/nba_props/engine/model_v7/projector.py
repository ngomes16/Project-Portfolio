"""
Ensemble Projector - Multi-Model Signal Integration
===================================================

Combines projections from multiple signal sources:
1. Statistical projections (weighted averages)
2. Defense matchup analysis
3. Head-to-head historical performance
4. Player archetype analysis
5. Trend detection
6. Back-to-back/rest analysis

Each signal contributes to the final projection and confidence score.
"""
from __future__ import annotations

import sqlite3
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

from .config import ModelV7Config, DEFAULT_CONFIG
from ...team_aliases import abbrev_from_team_name, normalize_team_abbrev


@dataclass
class PlayerStats:
    """Comprehensive player statistics for projection."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: str
    games_played: int
    
    # Raw game data
    games: List[Dict] = field(default_factory=list)
    
    # Averages at different lookbacks
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
    
    l20_pts: float = 0.0
    l20_reb: float = 0.0
    l20_ast: float = 0.0
    l20_min: float = 0.0
    
    season_pts: float = 0.0
    season_reb: float = 0.0
    season_ast: float = 0.0
    season_min: float = 0.0
    
    # Variability (Coefficient of Variation)
    pts_cv: float = 0.0
    reb_cv: float = 0.0
    ast_cv: float = 0.0
    min_cv: float = 0.0
    
    # Standard deviations
    pts_std: float = 0.0
    reb_std: float = 0.0
    ast_std: float = 0.0
    
    # Floor/Ceiling (10th/90th percentile)
    pts_floor: float = 0.0
    pts_ceiling: float = 0.0
    reb_floor: float = 0.0
    reb_ceiling: float = 0.0
    ast_floor: float = 0.0
    ast_ceiling: float = 0.0
    
    # Trends
    pts_trend: str = "stable"  # "hot", "cold", "stable"
    reb_trend: str = "stable"
    ast_trend: str = "stable"
    pts_trend_pct: float = 0.0
    reb_trend_pct: float = 0.0
    ast_trend_pct: float = 0.0
    
    # Home/Away splits
    home_pts: float = 0.0
    home_reb: float = 0.0
    home_ast: float = 0.0
    away_pts: float = 0.0
    away_reb: float = 0.0
    away_ast: float = 0.0


@dataclass
class H2HStats:
    """Head-to-head statistics vs specific opponent."""
    games_count: int = 0
    pts_avg: float = 0.0
    reb_avg: float = 0.0
    ast_avg: float = 0.0
    min_avg: float = 0.0
    pts_list: List[float] = field(default_factory=list)
    reb_list: List[float] = field(default_factory=list)
    ast_list: List[float] = field(default_factory=list)


@dataclass 
class DefenseProfile:
    """Defense vs position profile for opponent."""
    team_abbrev: str
    position: str
    
    pts_allowed: float = 0.0
    pts_rank: int = 15
    pts_factor: float = 1.0
    
    reb_allowed: float = 0.0
    reb_rank: int = 15
    reb_factor: float = 1.0
    
    ast_allowed: float = 0.0
    ast_rank: int = 15
    ast_factor: float = 1.0
    
    overall_rating: str = "average"  # elite, good, average, poor, terrible


@dataclass
class SignalStrength:
    """Tracks agreement between different signals."""
    stat_projection: float = 0.0
    defense_adjusted: float = 0.0
    h2h_projection: Optional[float] = None
    trend_direction: str = "stable"
    
    # Agreement tracking
    signals_agree_over: int = 0
    signals_agree_under: int = 0
    
    @property
    def consensus_direction(self) -> str:
        """Get consensus direction from signals."""
        if self.signals_agree_over > self.signals_agree_under:
            return "OVER"
        elif self.signals_agree_under > self.signals_agree_over:
            return "UNDER"
        return "NEUTRAL"
    
    @property
    def signal_agreement(self) -> int:
        """Count of agreeing signals."""
        return max(self.signals_agree_over, self.signals_agree_under)


@dataclass
class EnsembleProjection:
    """Complete ensemble projection with all signals."""
    player_name: str
    player_id: int
    team_abbrev: str
    opponent_abbrev: str
    game_date: str
    is_home: bool
    prop_type: str
    
    # Base statistical projection
    stat_projection: float
    
    # Individual signal projections
    defense_projection: float
    h2h_projection: Optional[float]
    trend_adjustment: float
    rest_adjustment: float
    
    # Final combined projection
    final_projection: float
    
    # Line (player's recent average)
    line: float
    
    # Edge
    edge_pct: float
    direction: str  # "OVER" or "UNDER"
    
    # Signal agreement
    signal_strength: SignalStrength = field(default_factory=SignalStrength)
    
    # Player context
    player_stats: Optional[PlayerStats] = None
    defense_profile: Optional[DefenseProfile] = None
    h2h_stats: Optional[H2HStats] = None
    
    # Archetype info
    archetype_group: str = ""
    player_tier: int = 4
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def load_player_stats(
    conn: sqlite3.Connection,
    player_id: int,
    before_date: str,
    limit: int = 30,
) -> Optional[PlayerStats]:
    """
    Load comprehensive player statistics for projection.
    
    Includes:
    - Multi-window averages (L3, L5, L10, L20, Season)
    - Variability metrics (CV, std dev)
    - Floor/ceiling (percentiles)
    - Trend detection
    - Home/away splits
    """
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
            g.game_date,
            b.pts, b.reb, b.ast, b.minutes, b.pos,
            b.fgm, b.fga, b.tpm, b.tpa, b.ftm, b.fta,
            t.name as team_name,
            g.team1_id, g.team2_id,
            b.team_id
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
        (player_id, before_date, limit),
    ).fetchall()
    
    if len(rows) < 5:
        return None
    
    games = [dict(r) for r in rows]
    
    # Extract stat arrays
    pts = [g["pts"] or 0 for g in games]
    reb = [g["reb"] or 0 for g in games]
    ast = [g["ast"] or 0 for g in games]
    mins = [g["minutes"] or 0 for g in games]
    
    # Helper functions
    def avg(vals: List[float], n: Optional[int] = None) -> float:
        subset = vals[:n] if n else vals
        return sum(subset) / len(subset) if subset else 0.0
    
    def cv(vals: List[float]) -> float:
        """Coefficient of Variation (std/mean)."""
        if len(vals) < 2:
            return 0.0
        mean = sum(vals) / len(vals)
        if mean == 0:
            return 0.0
        std = statistics.stdev(vals)
        return std / mean
    
    def std(vals: List[float]) -> float:
        if len(vals) < 2:
            return 0.0
        return statistics.stdev(vals)
    
    def percentile(vals: List[float], pct: int) -> float:
        if not vals:
            return 0.0
        sorted_vals = sorted(vals)
        idx = int(len(sorted_vals) * pct / 100)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]
    
    def detect_trend(l5_avg: float, l10_avg: float, threshold: float = 15.0) -> Tuple[str, float]:
        """Detect if player is hot/cold based on L5 vs L10."""
        if l10_avg == 0:
            return "stable", 0.0
        pct_diff = (l5_avg - l10_avg) / l10_avg * 100
        if pct_diff >= threshold:
            return "hot", pct_diff
        elif pct_diff <= -threshold:
            return "cold", pct_diff
        return "stable", pct_diff
    
    # Detect trends
    pts_trend, pts_trend_pct = detect_trend(avg(pts, 5), avg(pts, 10))
    reb_trend, reb_trend_pct = detect_trend(avg(reb, 5), avg(reb, 10))
    ast_trend, ast_trend_pct = detect_trend(avg(ast, 5), avg(ast, 10))
    
    # Home/away splits
    home_pts, home_reb, home_ast = [], [], []
    away_pts, away_reb, away_ast = [], [], []
    
    for g in games[:15]:  # Use last 15 for splits
        is_home = g["team_id"] == g["team2_id"]  # team2 is typically home
        if is_home:
            home_pts.append(g["pts"] or 0)
            home_reb.append(g["reb"] or 0)
            home_ast.append(g["ast"] or 0)
        else:
            away_pts.append(g["pts"] or 0)
            away_reb.append(g["reb"] or 0)
            away_ast.append(g["ast"] or 0)
    
    team_name = games[0]["team_name"] if games else ""
    position = games[0]["pos"] if games else "G"
    
    # Use L15 for variability calculations (more stable)
    pts_l15 = pts[:15]
    reb_l15 = reb[:15]
    ast_l15 = ast[:15]
    
    return PlayerStats(
        player_id=player_id,
        player_name=player["name"],
        team_abbrev=abbrev_from_team_name(team_name) or "",
        position=position or "G",
        games_played=len(games),
        games=games,
        
        # Averages
        l3_pts=avg(pts, 3), l3_reb=avg(reb, 3), l3_ast=avg(ast, 3), l3_min=avg(mins, 3),
        l5_pts=avg(pts, 5), l5_reb=avg(reb, 5), l5_ast=avg(ast, 5), l5_min=avg(mins, 5),
        l10_pts=avg(pts, 10), l10_reb=avg(reb, 10), l10_ast=avg(ast, 10), l10_min=avg(mins, 10),
        l20_pts=avg(pts, 20), l20_reb=avg(reb, 20), l20_ast=avg(ast, 20), l20_min=avg(mins, 20),
        season_pts=avg(pts), season_reb=avg(reb), season_ast=avg(ast), season_min=avg(mins),
        
        # Variability
        pts_cv=cv(pts_l15), reb_cv=cv(reb_l15), ast_cv=cv(ast_l15), min_cv=cv(mins[:15]),
        pts_std=std(pts_l15), reb_std=std(reb_l15), ast_std=std(ast_l15),
        
        # Floor/Ceiling
        pts_floor=percentile(pts_l15, 10), pts_ceiling=percentile(pts_l15, 90),
        reb_floor=percentile(reb_l15, 10), reb_ceiling=percentile(reb_l15, 90),
        ast_floor=percentile(ast_l15, 10), ast_ceiling=percentile(ast_l15, 90),
        
        # Trends
        pts_trend=pts_trend, reb_trend=reb_trend, ast_trend=ast_trend,
        pts_trend_pct=pts_trend_pct, reb_trend_pct=reb_trend_pct, ast_trend_pct=ast_trend_pct,
        
        # Home/Away
        home_pts=avg(home_pts) if home_pts else avg(pts),
        home_reb=avg(home_reb) if home_reb else avg(reb),
        home_ast=avg(home_ast) if home_ast else avg(ast),
        away_pts=avg(away_pts) if away_pts else avg(pts),
        away_reb=avg(away_reb) if away_reb else avg(reb),
        away_ast=avg(away_ast) if away_ast else avg(ast),
    )


def get_h2h_stats(
    conn: sqlite3.Connection,
    player_id: int,
    opponent_abbrev: str,
    before_date: str,
    config: ModelV7Config,
) -> Optional[H2HStats]:
    """Get head-to-head statistics vs specific opponent."""
    if not config.h2h_enabled:
        return None
    
    opp = normalize_team_abbrev(opponent_abbrev)
    
    # Get opponent team IDs - search by name containing the abbreviation
    opp_teams = conn.execute(
        "SELECT id FROM teams WHERE name LIKE ? OR name LIKE ?",
        (f"%{opp}%", f"%{opponent_abbrev}%"),
    ).fetchall()
    
    if not opp_teams:
        return None
    
    opp_ids = [t["id"] for t in opp_teams]
    ph = ",".join(["?"] * len(opp_ids))
    
    # Calculate date cutoff
    try:
        date_obj = datetime.strptime(before_date, "%Y-%m-%d")
        cutoff = date_obj - timedelta(days=config.h2h_max_lookback_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
    except:
        cutoff_str = "2020-01-01"
    
    # Get H2H games
    rows = conn.execute(
        f"""
        SELECT b.pts, b.reb, b.ast, b.minutes
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.player_id = ?
          AND g.game_date < ?
          AND g.game_date > ?
          AND b.minutes > 10
          AND (g.team1_id IN ({ph}) OR g.team2_id IN ({ph}))
        ORDER BY g.game_date DESC
        LIMIT 10
        """,
        (player_id, before_date, cutoff_str, *opp_ids, *opp_ids),
    ).fetchall()
    
    if len(rows) < config.h2h_min_games:
        return None
    
    pts_list = [r["pts"] or 0 for r in rows]
    reb_list = [r["reb"] or 0 for r in rows]
    ast_list = [r["ast"] or 0 for r in rows]
    
    return H2HStats(
        games_count=len(rows),
        pts_avg=sum(pts_list) / len(pts_list),
        reb_avg=sum(reb_list) / len(reb_list),
        ast_avg=sum(ast_list) / len(ast_list),
        min_avg=sum(r["minutes"] or 0 for r in rows) / len(rows),
        pts_list=pts_list,
        reb_list=reb_list,
        ast_list=ast_list,
    )


def get_defense_profile(
    conn: sqlite3.Connection,
    opponent_abbrev: str,
    position: str,
) -> DefenseProfile:
    """Get opponent's defense vs position profile."""
    opp = normalize_team_abbrev(opponent_abbrev)
    
    # Map single-letter position to full position
    pos = position.upper()[:1] if position else "G"
    pos_map = {"G": "PG", "F": "SF", "C": "C"}
    full_pos = pos_map.get(pos, "PG")
    
    default = DefenseProfile(team_abbrev=opp, position=full_pos)
    
    # Try to get from defense_vs_position table
    try:
        row = conn.execute(
            """
            SELECT * FROM team_defense_vs_position
            WHERE team_abbrev = ? AND position = ?
            ORDER BY as_of_date DESC
            LIMIT 1
            """,
            (opp, full_pos),
        ).fetchone()
        
        if not row:
            # Try alternate positions
            for try_pos in ["PG", "SG", "SF", "PF", "C"]:
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
            return default
        
        # Get league averages
        league_avgs = conn.execute(
            """
            SELECT 
                AVG(pts_allowed) as avg_pts,
                AVG(reb_allowed) as avg_reb,
                AVG(ast_allowed) as avg_ast
            FROM team_defense_vs_position
            WHERE position = ?
            """,
            (full_pos,),
        ).fetchone()
        
        if not league_avgs or not league_avgs["avg_pts"]:
            return default
        
        # Calculate factors
        pts_factor = (row["pts_allowed"] or 0) / league_avgs["avg_pts"] if league_avgs["avg_pts"] else 1.0
        reb_factor = (row["reb_allowed"] or 0) / league_avgs["avg_reb"] if league_avgs["avg_reb"] else 1.0
        ast_factor = (row["ast_allowed"] or 0) / league_avgs["avg_ast"] if league_avgs["avg_ast"] else 1.0
        
        # Determine overall rating based on PTS rank
        pts_rank = row["pts_rank"] or 15
        if pts_rank <= 5:
            rating = "elite"
        elif pts_rank <= 10:
            rating = "good"
        elif pts_rank <= 20:
            rating = "average"
        elif pts_rank <= 25:
            rating = "poor"
        else:
            rating = "terrible"
        
        return DefenseProfile(
            team_abbrev=opp,
            position=full_pos,
            pts_allowed=row["pts_allowed"] or 0,
            pts_rank=pts_rank,
            pts_factor=pts_factor,
            reb_allowed=row["reb_allowed"] or 0,
            reb_rank=row["reb_rank"] or 15,
            reb_factor=reb_factor,
            ast_allowed=row["ast_allowed"] or 0,
            ast_rank=row["ast_rank"] or 15,
            ast_factor=ast_factor,
            overall_rating=rating,
        )
        
    except Exception:
        return default


def get_player_archetype(
    conn: sqlite3.Connection,
    player_id: int,
    player_name: str,
) -> Tuple[str, int]:
    """Get player's archetype group and tier from database."""
    try:
        # First try exact name match
        row = conn.execute(
            """
            SELECT primary_offensive, tier
            FROM player_archetypes
            WHERE player_name = ?
            """,
            (player_name,),
        ).fetchone()
        
        # If not found, try fuzzy match
        if not row:
            # Try matching last name
            parts = player_name.split()
            if len(parts) >= 2:
                last_name = parts[-1]
                row = conn.execute(
                    """
                    SELECT primary_offensive, tier
                    FROM player_archetypes
                    WHERE player_name LIKE ?
                    """,
                    (f"%{last_name}%",),
                ).fetchone()
        
        if row:
            archetype = row["primary_offensive"] or ""
            tier = row["tier"] or 4
            
            # Map to archetype group
            archetype_lower = archetype.lower()
            if "heliocentric" in archetype_lower or "initiator" in archetype_lower:
                return "heliocentric", tier
            elif "scoring" in archetype_lower and "guard" in archetype_lower:
                return "scoring_guards", tier
            elif "slash" in archetype_lower:
                return "slashers", tier
            elif "two-way" in archetype_lower or "3-and-d" in archetype_lower:
                return "two_way_wings", tier
            elif "movement" in archetype_lower or "shooter" in archetype_lower:
                return "movement_shooters", tier
            elif "corner" in archetype_lower or "spot" in archetype_lower:
                return "corner_specialists", tier
            elif "hub" in archetype_lower:
                return "hub_bigs", tier
            elif "stretch" in archetype_lower:
                return "stretch_bigs", tier
            elif "traditional" in archetype_lower or "rim" in archetype_lower:
                return "traditional_bigs", tier
            
            return archetype_lower, tier
        
        return "", 4  # Default role player
        
    except Exception:
        return "", 4


def is_back_to_back(
    conn: sqlite3.Connection,
    team_abbrev: str,
    game_date: str,
) -> Tuple[bool, int]:
    """Check if team is playing back-to-back, return rest days."""
    try:
        date_obj = datetime.strptime(game_date, "%Y-%m-%d")
        yesterday = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Check if team played yesterday - search by name pattern
        team = normalize_team_abbrev(team_abbrev)
        teams = conn.execute(
            "SELECT id FROM teams WHERE name LIKE ? OR name LIKE ?",
            (f"%{team}%", f"%{team_abbrev}%"),
        ).fetchall()
        
        if not teams:
            return False, 1
        
        team_ids = [t["id"] for t in teams]
        ph = ",".join(["?"] * len(team_ids))
        
        # Check yesterday
        yesterday_game = conn.execute(
            f"""
            SELECT id FROM games
            WHERE game_date = ?
              AND (team1_id IN ({ph}) OR team2_id IN ({ph}))
            """,
            (yesterday, *team_ids, *team_ids),
        ).fetchone()
        
        if yesterday_game:
            return True, 0
        
        # Check days since last game
        last_game = conn.execute(
            f"""
            SELECT game_date FROM games
            WHERE game_date < ?
              AND (team1_id IN ({ph}) OR team2_id IN ({ph}))
            ORDER BY game_date DESC
            LIMIT 1
            """,
            (game_date, *team_ids, *team_ids),
        ).fetchone()
        
        if last_game:
            last_date = datetime.strptime(last_game["game_date"], "%Y-%m-%d")
            rest_days = (date_obj - last_date).days - 1
            return False, rest_days
        
        return False, 3  # Assume well-rested
        
    except Exception:
        return False, 1


def calculate_projection(
    player_stats: PlayerStats,
    prop_type: str,
    opponent_abbrev: str,
    game_date: str,
    is_home: bool,
    defense_profile: DefenseProfile,
    h2h_stats: Optional[H2HStats],
    b2b: bool,
    rest_days: int,
    config: ModelV7Config,
) -> EnsembleProjection:
    """
    Calculate ensemble projection combining all signals.
    
    Signals:
    1. Statistical projection (weighted averages)
    2. Defense adjustment
    3. Head-to-head projection
    4. Trend adjustment
    5. Rest adjustment
    6. Home/away adjustment
    """
    pt = prop_type.upper()
    reasons = []
    warnings = []
    
    # Get stat-specific data
    if pt == "PTS":
        l3, l5, l10, l20, season = (
            player_stats.l3_pts, player_stats.l5_pts, 
            player_stats.l10_pts, player_stats.l20_pts,
            player_stats.season_pts
        )
        def_factor = defense_profile.pts_factor
        def_rank = defense_profile.pts_rank
        h2h_avg = h2h_stats.pts_avg if h2h_stats else None
        trend = player_stats.pts_trend
        trend_pct = player_stats.pts_trend_pct
        home_avg = player_stats.home_pts
        away_avg = player_stats.away_pts
    elif pt == "REB":
        l3, l5, l10, l20, season = (
            player_stats.l3_reb, player_stats.l5_reb,
            player_stats.l10_reb, player_stats.l20_reb,
            player_stats.season_reb
        )
        def_factor = defense_profile.reb_factor
        def_rank = defense_profile.reb_rank
        h2h_avg = h2h_stats.reb_avg if h2h_stats else None
        trend = player_stats.reb_trend
        trend_pct = player_stats.reb_trend_pct
        home_avg = player_stats.home_reb
        away_avg = player_stats.away_reb
    else:  # AST
        l3, l5, l10, l20, season = (
            player_stats.l3_ast, player_stats.l5_ast,
            player_stats.l10_ast, player_stats.l20_ast,
            player_stats.season_ast
        )
        def_factor = defense_profile.ast_factor
        def_rank = defense_profile.ast_rank
        h2h_avg = h2h_stats.ast_avg if h2h_stats else None
        trend = player_stats.ast_trend
        trend_pct = player_stats.ast_trend_pct
        home_avg = player_stats.home_ast
        away_avg = player_stats.away_ast
    
    # 1. STATISTICAL PROJECTION (weighted average)
    weights = config.get_weights(pt)
    stat_projection = (
        l3 * weights[0] +
        l5 * weights[1] +
        l10 * weights[2] +
        l20 * weights[3] +
        season * weights[4]
    )
    reasons.append(f"Base projection: {stat_projection:.1f}")
    
    # Initialize signal tracker
    signal = SignalStrength(stat_projection=stat_projection)
    
    # 2. DEFENSE ADJUSTMENT
    def_rating = defense_profile.overall_rating
    def_adj = config.get_defense_adjustment(def_rating)
    defense_projection = stat_projection * (1 + def_adj)
    signal.defense_adjusted = defense_projection
    
    if def_rating in ["elite", "good"]:
        reasons.append(f"Strong defense ({def_rating}, rank {def_rank})")
        signal.signals_agree_under += 1
    elif def_rating in ["poor", "terrible"]:
        reasons.append(f"Weak defense ({def_rating}, rank {def_rank})")
        signal.signals_agree_over += 1
    
    # 3. HEAD-TO-HEAD ADJUSTMENT
    h2h_projection = None
    if h2h_stats and h2h_avg is not None:
        h2h_projection = h2h_avg
        signal.h2h_projection = h2h_projection
        
        if h2h_avg > l10:
            reasons.append(f"Strong H2H history ({h2h_avg:.1f} avg in {h2h_stats.games_count} games)")
            signal.signals_agree_over += 1
        elif h2h_avg < l10:
            reasons.append(f"Weak H2H history ({h2h_avg:.1f} avg in {h2h_stats.games_count} games)")
            signal.signals_agree_under += 1
    
    # 4. TREND ADJUSTMENT
    trend_adj = 1.0
    signal.trend_direction = trend
    
    if trend == "hot":
        trend_adj = 1 + config.trend_aligned_boost
        signal.signals_agree_over += 1
        reasons.append(f"Hot streak (+{trend_pct:.0f}%)")
    elif trend == "cold":
        trend_adj = 1 - config.trend_opposed_penalty
        signal.signals_agree_under += 1
        reasons.append(f"Cold streak ({trend_pct:.0f}%)")
    
    # 5. REST ADJUSTMENT
    rest_adj = 1.0
    if b2b:
        rest_adj = 1 - config.b2b_penalty
        warnings.append("Back-to-back game")
        signal.signals_agree_under += 1
    elif rest_days >= 2:
        rest_adj = 1 + config.rest_bonus
        reasons.append(f"{rest_days} days rest")
    
    # 6. HOME/AWAY ADJUSTMENT (slight)
    location_avg = home_avg if is_home else away_avg
    location_adj = 1.0
    if abs(location_avg - l10) > l10 * 0.1:  # >10% difference
        if (is_home and home_avg > away_avg) or (not is_home and away_avg > home_avg):
            location_adj = 1.02
            reasons.append("Favorable location")
    
    # COMBINE ALL SIGNALS
    # Start with defense-adjusted projection
    combined = defense_projection
    
    # Blend H2H if available (25% weight)
    if h2h_projection is not None:
        combined = combined * (1 - config.h2h_weight) + h2h_projection * config.h2h_weight
    
    # Apply remaining adjustments
    combined *= trend_adj * rest_adj * location_adj
    
    # Calculate line (use L10 as baseline)
    line = l10
    
    # Determine edge and direction
    edge_pct = ((combined - line) / line * 100) if line > 0 else 0
    
    if edge_pct >= config.min_edge_threshold:
        direction = "OVER"
    elif edge_pct <= -config.min_edge_threshold:
        direction = "UNDER"
        edge_pct = abs(edge_pct)
    else:
        direction = "SKIP"  # Not enough edge
    
    return EnsembleProjection(
        player_name=player_stats.player_name,
        player_id=player_stats.player_id,
        team_abbrev=player_stats.team_abbrev,
        opponent_abbrev=opponent_abbrev,
        game_date=game_date,
        is_home=is_home,
        prop_type=pt,
        stat_projection=stat_projection,
        defense_projection=defense_projection,
        h2h_projection=h2h_projection,
        trend_adjustment=trend_adj,
        rest_adjustment=rest_adj,
        final_projection=combined,
        line=line,
        edge_pct=edge_pct,
        direction=direction,
        signal_strength=signal,
        player_stats=player_stats,
        defense_profile=defense_profile,
        h2h_stats=h2h_stats,
        reasons=reasons,
        warnings=warnings,
    )


def project_all_props(
    conn: sqlite3.Connection,
    player_id: int,
    opponent_abbrev: str,
    game_date: str,
    is_home: bool,
    config: ModelV7Config = DEFAULT_CONFIG,
) -> List[EnsembleProjection]:
    """Generate projections for all prop types for a player."""
    projections = []
    
    # Load player stats
    player_stats = load_player_stats(conn, player_id, game_date)
    if not player_stats:
        return []
    
    # Check minimum minutes
    if player_stats.season_min < config.min_minutes_threshold:
        return []
    
    # Get defense profile
    defense_profile = get_defense_profile(conn, opponent_abbrev, player_stats.position)
    
    # Get H2H stats
    h2h_stats = get_h2h_stats(conn, player_id, opponent_abbrev, game_date, config)
    
    # Get archetype
    archetype, tier = get_player_archetype(conn, player_id, player_stats.player_name)
    
    # Check back-to-back
    b2b, rest_days = is_back_to_back(conn, player_stats.team_abbrev, game_date)
    
    # Generate projections for each prop type
    for prop_type in ["PTS", "REB", "AST"]:
        # Check minimum line
        min_line = config.get_min_line(prop_type)
        
        if prop_type == "PTS" and player_stats.l10_pts < min_line:
            continue
        elif prop_type == "REB" and player_stats.l10_reb < min_line:
            continue
        elif prop_type == "AST" and player_stats.l10_ast < min_line:
            continue
        
        proj = calculate_projection(
            player_stats=player_stats,
            prop_type=prop_type,
            opponent_abbrev=opponent_abbrev,
            game_date=game_date,
            is_home=is_home,
            defense_profile=defense_profile,
            h2h_stats=h2h_stats,
            b2b=b2b,
            rest_days=rest_days,
            config=config,
        )
        
        if proj.direction != "SKIP":
            proj.archetype_group = archetype
            proj.player_tier = tier
            projections.append(proj)
    
    return projections

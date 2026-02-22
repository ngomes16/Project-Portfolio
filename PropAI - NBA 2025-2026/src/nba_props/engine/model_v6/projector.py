"""
Core Projection Engine
======================

Generates player stat projections using:
1. Historical weighted averages (L5/L10/L20/Season)
2. Defense matchup adjustments
3. Archetype-based factors
4. Trend detection and adjustment
5. Back-to-back and rest considerations
"""
from __future__ import annotations

import sqlite3
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

from .config import ModelV6Config, DEFAULT_CONFIG
from .player_groups import PlayerGroup, get_player_group
from .defense_analysis import DefenseMatchup, get_defense_matchup


@dataclass
class PlayerStats:
    """Player's historical stats for projection."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: str
    games_played: int
    
    # Raw game data
    games: List[Dict] = field(default_factory=list)
    
    # L5 Averages
    l5_pts: float = 0.0
    l5_reb: float = 0.0
    l5_ast: float = 0.0
    l5_min: float = 0.0
    
    # L10 Averages
    l10_pts: float = 0.0
    l10_reb: float = 0.0
    l10_ast: float = 0.0
    l10_min: float = 0.0
    
    # L20 Averages
    l20_pts: float = 0.0
    l20_reb: float = 0.0
    l20_ast: float = 0.0
    l20_min: float = 0.0
    
    # Season Averages
    season_pts: float = 0.0
    season_reb: float = 0.0
    season_ast: float = 0.0
    season_min: float = 0.0
    
    # Variability (Coefficient of Variation)
    pts_cv: float = 0.0
    reb_cv: float = 0.0
    ast_cv: float = 0.0
    min_cv: float = 0.0
    
    # Trends
    pts_trend: str = "stable"  # "hot", "cold", "stable"
    reb_trend: str = "stable"
    ast_trend: str = "stable"
    pts_trend_pct: float = 0.0
    reb_trend_pct: float = 0.0
    ast_trend_pct: float = 0.0
    
    # Per-minute rates (more stable)
    pts_per_min: float = 0.0
    reb_per_min: float = 0.0
    ast_per_min: float = 0.0


@dataclass
class Projection:
    """Complete projection for a player/stat combination."""
    player_name: str
    player_id: int
    team_abbrev: str
    opponent_abbrev: str
    game_date: str
    prop_type: str
    
    # Base projection
    base_projection: float
    
    # Adjustments applied
    defense_adjustment: float      # Multiplier from defense matchup
    trend_adjustment: float        # Multiplier from trend
    rest_adjustment: float         # Multiplier from B2B/rest
    archetype_adjustment: float    # Multiplier from archetype
    
    # Final projection
    final_projection: float
    
    # Line (player's recent average)
    line: float
    
    # Edge
    edge_pct: float
    direction: str  # "OVER" or "UNDER"
    
    # Player context
    player_group: Optional[PlayerGroup] = None
    defense_matchup: Optional[DefenseMatchup] = None
    player_stats: Optional[PlayerStats] = None
    
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
    Load a player's historical stats for projection.
    
    Args:
        conn: Database connection
        player_id: Player's database ID
        before_date: Only include games before this date
        limit: Maximum games to load
    
    Returns:
        PlayerStats with all historical data, or None if insufficient data
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
    
    def detect_trend(l5_avg: float, l10_avg: float, threshold: float = 12.0) -> Tuple[str, float]:
        """Detect if player is hot/cold based on L5 vs L10."""
        if l10_avg == 0:
            return "stable", 0.0
        pct_diff = (l5_avg - l10_avg) / l10_avg * 100
        if pct_diff >= threshold:
            return "hot", pct_diff
        elif pct_diff <= -threshold:
            return "cold", pct_diff
        return "stable", pct_diff
    
    # Calculate all averages
    l5_pts, l5_reb, l5_ast, l5_min = avg(pts, 5), avg(reb, 5), avg(ast, 5), avg(mins, 5)
    l10_pts, l10_reb, l10_ast, l10_min = avg(pts, 10), avg(reb, 10), avg(ast, 10), avg(mins, 10)
    l20_pts, l20_reb, l20_ast, l20_min = avg(pts, 20), avg(reb, 20), avg(ast, 20), avg(mins, 20)
    season_pts, season_reb, season_ast, season_min = avg(pts), avg(reb), avg(ast), avg(mins)
    
    # Detect trends
    pts_trend, pts_trend_pct = detect_trend(l5_pts, l10_pts)
    reb_trend, reb_trend_pct = detect_trend(l5_reb, l10_reb)
    ast_trend, ast_trend_pct = detect_trend(l5_ast, l10_ast)
    
    # Calculate per-minute rates
    pts_per_min = season_pts / season_min if season_min > 0 else 0
    reb_per_min = season_reb / season_min if season_min > 0 else 0
    ast_per_min = season_ast / season_min if season_min > 0 else 0
    
    # Get team abbrev and position
    from ...team_aliases import abbrev_from_team_name
    team_name = games[0]["team_name"] if games else ""
    team_abbrev = abbrev_from_team_name(team_name) or ""
    position = games[0]["pos"] if games else "G"
    
    return PlayerStats(
        player_id=player_id,
        player_name=player["name"],
        team_abbrev=team_abbrev,
        position=position or "G",
        games_played=len(games),
        games=games,
        
        l5_pts=l5_pts, l5_reb=l5_reb, l5_ast=l5_ast, l5_min=l5_min,
        l10_pts=l10_pts, l10_reb=l10_reb, l10_ast=l10_ast, l10_min=l10_min,
        l20_pts=l20_pts, l20_reb=l20_reb, l20_ast=l20_ast, l20_min=l20_min,
        season_pts=season_pts, season_reb=season_reb, season_ast=season_ast, season_min=season_min,
        
        pts_cv=cv(pts[:15]), reb_cv=cv(reb[:15]), ast_cv=cv(ast[:15]), min_cv=cv(mins[:15]),
        
        pts_trend=pts_trend, reb_trend=reb_trend, ast_trend=ast_trend,
        pts_trend_pct=pts_trend_pct, reb_trend_pct=reb_trend_pct, ast_trend_pct=ast_trend_pct,
        
        pts_per_min=pts_per_min, reb_per_min=reb_per_min, ast_per_min=ast_per_min,
    )


def calculate_projection(
    conn: sqlite3.Connection,
    player_stats: PlayerStats,
    player_group: PlayerGroup,
    opponent_abbrev: str,
    game_date: str,
    prop_type: str,
    config: ModelV6Config = DEFAULT_CONFIG,
) -> Optional[Projection]:
    """
    Calculate a projection for a player/stat combination.
    
    Args:
        conn: Database connection
        player_stats: Player's historical stats
        player_group: Player's archetype group
        opponent_abbrev: Opponent team abbreviation
        game_date: Date of the game
        prop_type: Stat type (PTS, REB, AST)
        config: Model configuration
    
    Returns:
        Projection with all adjustments applied
    """
    pt = prop_type.lower()
    reasons = []
    warnings = []
    
    # Get stat-specific values
    l5 = getattr(player_stats, f"l5_{pt}")
    l10 = getattr(player_stats, f"l10_{pt}")
    l20 = getattr(player_stats, f"l20_{pt}")
    season = getattr(player_stats, f"season_{pt}")
    trend = getattr(player_stats, f"{pt}_trend")
    trend_pct = getattr(player_stats, f"{pt}_trend_pct")
    cv = getattr(player_stats, f"{pt}_cv")
    
    # Get weights for this stat type
    w5, w10, w20, w_season = config.get_weights(prop_type)
    
    # Calculate base projection
    base_projection = (
        l5 * w5 +
        l10 * w10 +
        l20 * w20 +
        season * w_season
    )
    
    # === DEFENSE ADJUSTMENT ===
    defense_matchup = get_defense_matchup(conn, player_group, opponent_abbrev, config)
    
    if pt == "pts":
        defense_adj = defense_matchup.total_pts_adjustment
    elif pt == "reb":
        defense_adj = defense_matchup.total_reb_adjustment
    else:  # ast
        defense_adj = defense_matchup.total_ast_adjustment
    
    if defense_adj > 1.02:
        reasons.append(f"Weak {pt.upper()} defense (+{(defense_adj-1)*100:.0f}%)")
    elif defense_adj < 0.98:
        warnings.append(f"Strong {pt.upper()} defense ({(defense_adj-1)*100:.0f}%)")
    
    reasons.extend(defense_matchup.notes)
    warnings.extend(defense_matchup.warnings)
    
    # === TREND ADJUSTMENT ===
    trend_adj = 1.0
    if trend == "hot":
        trend_adj = 1.0 + config.hot_streak_boost
        reasons.append(f"Hot streak (+{config.hot_streak_boost*100:.0f}%)")
    elif trend == "cold":
        trend_adj = 1.0 - config.cold_streak_penalty
        warnings.append(f"Cold streak ({-config.cold_streak_penalty*100:.0f}%)")
    
    # === REST ADJUSTMENT ===
    rest_adj = _get_rest_adjustment(conn, player_stats.team_abbrev, game_date, config)
    if rest_adj != 1.0:
        if rest_adj < 1.0:
            warnings.append(f"B2B game ({(rest_adj-1)*100:.0f}%)")
        else:
            reasons.append(f"Well-rested (+{(rest_adj-1)*100:.0f}%)")
    
    # === ARCHETYPE ADJUSTMENT ===
    archetype_adj = 1.0 + defense_matchup.archetype_adjustment
    
    # === FINAL PROJECTION ===
    final_projection = base_projection * defense_adj * trend_adj * rest_adj * archetype_adj
    final_projection = round(final_projection, 1)
    
    # === CALCULATE LINE ===
    # Use L10/L7/L5 average as the "line"
    vals = [g[pt] or 0 for g in player_stats.games]
    if len(vals) >= 10:
        line = sum(vals[:10]) / 10
    elif len(vals) >= 7:
        line = sum(vals[:7]) / 7
    else:
        line = sum(vals[:5]) / 5 if len(vals) >= 5 else base_projection
    
    line = round(line, 1)
    
    # === EDGE CALCULATION ===
    if line > 0:
        edge_pct = (final_projection - line) / line * 100
    else:
        edge_pct = 0.0
    
    # Determine direction
    if edge_pct >= config.min_edge_threshold:
        direction = "OVER"
    elif edge_pct <= -config.min_edge_threshold:
        direction = "UNDER"
        edge_pct = abs(edge_pct)
    else:
        direction = "PASS"  # Not enough edge
    
    return Projection(
        player_name=player_stats.player_name,
        player_id=player_stats.player_id,
        team_abbrev=player_stats.team_abbrev,
        opponent_abbrev=opponent_abbrev,
        game_date=game_date,
        prop_type=prop_type.upper(),
        base_projection=round(base_projection, 1),
        defense_adjustment=defense_adj,
        trend_adjustment=trend_adj,
        rest_adjustment=rest_adj,
        archetype_adjustment=archetype_adj,
        final_projection=final_projection,
        line=line,
        edge_pct=round(edge_pct, 1),
        direction=direction,
        player_group=player_group,
        defense_matchup=defense_matchup,
        player_stats=player_stats,
        reasons=reasons,
        warnings=warnings,
    )


def _get_rest_adjustment(
    conn: sqlite3.Connection,
    team_abbrev: str,
    game_date: str,
    config: ModelV6Config,
) -> float:
    """
    Calculate rest adjustment based on team's recent schedule.
    
    Returns:
        Multiplier (e.g., 0.95 for B2B, 1.02 for well-rested)
    """
    try:
        from ...team_aliases import normalize_team_abbrev
        from ...standings import _team_ids_by_abbrev
        
        team_abbrev = normalize_team_abbrev(team_abbrev)
        team_ids_map = _team_ids_by_abbrev(conn)
        team_ids = team_ids_map.get(team_abbrev, [])
        
        if not team_ids:
            return 1.0
        
        # Parse target date
        target_dt = datetime.strptime(game_date, "%Y-%m-%d")
        yesterday = (target_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        day_before = (target_dt - timedelta(days=2)).strftime("%Y-%m-%d")
        
        placeholders = ",".join(["?"] * len(team_ids))
        
        # Check if team played yesterday
        yesterday_game = conn.execute(
            f"""
            SELECT COUNT(*) as cnt FROM games 
            WHERE (team1_id IN ({placeholders}) OR team2_id IN ({placeholders}))
              AND game_date = ?
            """,
            (*team_ids, *team_ids, yesterday),
        ).fetchone()
        
        if yesterday_game and yesterday_game["cnt"] > 0:
            return 1.0 - config.b2b_second_game_penalty
        
        # Check if team played day before yesterday
        two_days_game = conn.execute(
            f"""
            SELECT COUNT(*) as cnt FROM games 
            WHERE (team1_id IN ({placeholders}) OR team2_id IN ({placeholders}))
              AND game_date = ?
            """,
            (*team_ids, *team_ids, day_before),
        ).fetchone()
        
        if two_days_game and two_days_game["cnt"] == 0:
            # At least 2 days rest
            return 1.0 + config.rest_advantage_boost
        
        return 1.0
        
    except Exception:
        return 1.0


def project_all_props(
    conn: sqlite3.Connection,
    player_id: int,
    opponent_abbrev: str,
    game_date: str,
    config: ModelV6Config = DEFAULT_CONFIG,
) -> List[Projection]:
    """
    Generate projections for all prop types for a player.
    
    Returns:
        List of Projections (PTS, REB, AST)
    """
    projections = []
    
    # Load player stats
    player_stats = load_player_stats(conn, player_id, game_date)
    if not player_stats:
        return projections
    
    # Check minimum minutes
    if player_stats.season_min < config.min_minutes_threshold:
        return projections
    
    # Get player group
    player_group = get_player_group(conn, player_stats.player_name)
    if not player_group:
        # Create basic group
        from .player_groups import classify_player
        player_group = classify_player(
            player_name=player_stats.player_name,
            position=player_stats.position,
            tier=4,  # Default to role player
            primary_archetype="Connector",
            team_abbrev=player_stats.team_abbrev,
            player_id=player_id,
        )
    
    # Generate projections for each prop type
    for prop_type in ["PTS", "REB", "AST"]:
        # Skip AST for low-assist players
        if prop_type == "AST" and player_stats.season_ast < config.min_ast_for_ast_props:
            continue
        
        proj = calculate_projection(
            conn=conn,
            player_stats=player_stats,
            player_group=player_group,
            opponent_abbrev=opponent_abbrev,
            game_date=game_date,
            prop_type=prop_type,
            config=config,
        )
        
        if proj and proj.direction != "PASS":
            projections.append(proj)
    
    return projections

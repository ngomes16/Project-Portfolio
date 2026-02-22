"""Player stats projection engine.

Integrates:
- Historical game logs with recency weighting
- Back-to-back and rest day adjustments  
- Player archetype matchup analysis
- Elite defender impact on projections
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from ..team_aliases import abbrev_from_team_name, normalize_team_abbrev


@dataclass
class ProjectionConfig:
    """Configuration for projection calculations."""
    # Number of recent games to consider for baseline
    games_lookback: int = 10
    # Minimum games required for reliable projection
    min_games: int = 3
    # Weight for recency (more recent games weighted higher)
    recency_weight: float = 0.1
    
    # Weight settings
    # Optimized defaults based on backtesting (favoring Season durability more)
    weight_l5: float = 0.20
    weight_l10: float = 0.0
    weight_l20: float = 0.40
    weight_season: float = 0.40
    
    # Adjustment factor for back-to-back games
    back_to_back_factor: float = 0.94
    # Adjustment factor for rest advantage (3+ days)
    rest_advantage_factor: float = 1.03
    # Maximum players to project per team (top N by minutes)
    top_n_players: int = 10
    # Enable archetype-based matchup adjustments
    use_archetype_adjustments: bool = True
    # Elite defender adjustment factor
    elite_defender_factor: float = 0.94
    # Enable position-based defense adjustments
    use_position_defense: bool = True
    # Enable trend-based adjustments
    use_trend_adjustments: bool = True


@dataclass
class PlayerProjection:
    """Projected stats for a player."""
    player_id: int
    player_name: str
    team_abbrev: str
    
    # Projected minutes
    proj_minutes: float
    minutes_std: float
    
    # Projected stats
    proj_pts: float
    proj_reb: float
    proj_ast: float
    
    # Standard deviations for uncertainty
    pts_std: float
    reb_std: float
    ast_std: float
    
    # Per-minute rates (for analysis)
    pts_per_min: float
    reb_per_min: float
    ast_per_min: float
    
    # Context
    games_played: int
    position: Optional[str] = None
    is_top_7: bool = True  # Legacy - kept for compatibility
    is_top_10: bool = True
    
    # Trend indicators
    pts_trend: str = "stable"  # "hot", "cold", "stable"
    reb_trend: str = "stable"
    ast_trend: str = "stable"
    pts_trend_pct: float = 0.0
    reb_trend_pct: float = 0.0
    ast_trend_pct: float = 0.0
    
    # Matchup adjustments applied
    adjustments: dict = field(default_factory=dict)
    
    # Matchup edge info (populated after analysis)
    matchup_edges: dict = field(default_factory=dict)


def _get_player_game_logs(
    conn: sqlite3.Connection,
    player_id: int,
    limit: int = 10,
    before_date: Optional[str] = None,
) -> list[dict]:
    """Get recent game logs for a player."""
    query = """
        SELECT 
            g.game_date,
            b.minutes, b.pts, b.reb, b.ast,
            b.fgm, b.fga, b.tpm, b.tpa, b.ftm, b.fta,
            t.name as team_name
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        JOIN teams t ON t.id = b.team_id
        WHERE b.player_id = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 0
    """
    params = [player_id]
    
    if before_date:
        query += " AND g.game_date < ?"
        params.append(before_date)
        
    query += " ORDER BY g.game_date DESC LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    
    return [dict(r) for r in rows]


def _calculate_weighted_average(
    values: list[float],
    recency_weight: float = 0.1,
) -> tuple[float, float]:
    """
    Calculate weighted average with more recent values weighted higher.
    Returns (mean, std_dev).
    """
    if not values:
        return 0.0, 0.0
    
    n = len(values)
    if n == 1:
        return values[0], values[0] * 0.2  # Assume 20% std for single value
    
    # Create weights (more recent = higher weight)
    weights = [(1 + recency_weight * (n - i - 1)) for i in range(n)]
    total_weight = sum(weights)
    
    # Weighted mean
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    mean = weighted_sum / total_weight
    
    # Weighted standard deviation
    variance = sum(w * (v - mean) ** 2 for v, w in zip(values, weights)) / total_weight
    std = variance ** 0.5
    
    return mean, max(std, mean * 0.1)  # Minimum 10% std


def project_player_stats(
    conn: sqlite3.Connection,
    player_id: int,
    config: Optional[ProjectionConfig] = None,
    opponent_abbrev: Optional[str] = None,
    is_back_to_back: bool = False,
    rest_days: int = 1,
    before_date: Optional[str] = None,
) -> Optional[PlayerProjection]:
    """
    Project a player's PTS/REB/AST for an upcoming game.
    
    Args:
        conn: Database connection
        player_id: Player ID to project
        config: Projection configuration
        opponent_abbrev: Opponent team abbreviation (for matchup adjustments)
        is_back_to_back: Whether this is a back-to-back game
        rest_days: Days of rest before this game
        before_date: If provided, only use games before this date (for backtesting)
    
    Returns:
        PlayerProjection or None if insufficient data
    """
    if config is None:
        config = ProjectionConfig()
    
    # Get player info
    player_row = conn.execute(
        "SELECT id, name FROM players WHERE id = ?", (player_id,)
    ).fetchone()
    if not player_row:
        return None
    
    player_name = player_row["name"]
    
    # Get recent game logs
    logs = _get_player_game_logs(conn, player_id, config.games_lookback, before_date=before_date)
    
    if len(logs) < config.min_games:
        return None
    
    # Extract values
    minutes = [log["minutes"] for log in logs]
    pts = [log["pts"] or 0 for log in logs]
    reb = [log["reb"] or 0 for log in logs]
    ast = [log["ast"] or 0 for log in logs]
    
    # Calculate weighted averages using specific L5/L20 weights
    # Requested Weights: Configurable in ProjectionConfig
    def calculate_custom_weighted_average(values_list):
        if not values_list:
            return 0.0, 0.0
        
        # Season Average (all available logs from query)
        season_avg = sum(values_list) / len(values_list)
        
        # Last 20 Games
        l20_values = values_list[:20]
        l20_avg = sum(l20_values) / len(l20_values) if l20_values else season_avg
        
        # Last 5 Games
        l5_values = values_list[:5]
        l5_avg = sum(l5_values) / len(l5_values) if l5_values else season_avg
        
        # Weighted Combination
        # If we have very few games, adjust weights dynamically
        if len(values_list) < 5:
            weighted_mean = season_avg
        elif len(values_list) < 20:
            # Shift L20 weight to Season/L5 since L20 is impartial
            # Re-normalize L5 and Season weights
            w_sum = config.weight_l5 + config.weight_season
            if w_sum <= 0:
                 weighted_mean = season_avg
            else:
                 w_l5 = config.weight_l5 / w_sum
                 w_season = config.weight_season / w_sum
                 weighted_mean = (l5_avg * w_l5) + (season_avg * w_season)
        else:
            # Normalize all three to ensure they sum to 1.0 (or close to it)
            # This allows the optimizer to provide raw scores like 1.0, 2.0, 3.0
            w_sum = config.weight_l5 + config.weight_l20 + config.weight_season
            if w_sum <= 0:
                 weighted_mean = season_avg
            else:
                 weighted_mean = (l5_avg * config.weight_l5 + 
                                  l20_avg * config.weight_l20 + 
                                  season_avg * config.weight_season) / w_sum
            
        # Std Dev (simplified)
        variance = sum((x - weighted_mean) ** 2 for x in values_list) / len(values_list)
        std = variance ** 0.5
        
        return weighted_mean, max(std, weighted_mean * 0.1)

    avg_min, std_min = calculate_custom_weighted_average(minutes)
    avg_pts, std_pts = calculate_custom_weighted_average(pts)
    avg_reb, std_reb = calculate_custom_weighted_average(reb)
    avg_ast, std_ast = calculate_custom_weighted_average(ast)
    
    # Calculate per-minute rates
    pts_per_min = avg_pts / avg_min if avg_min > 0 else 0
    reb_per_min = avg_reb / avg_min if avg_min > 0 else 0
    ast_per_min = avg_ast / avg_min if avg_min > 0 else 0
    
    # Get team info from most recent game
    team_name = logs[0]["team_name"] if logs else ""
    team_abbrev = abbrev_from_team_name(team_name) or ""
    
    # Get position
    pos_row = conn.execute(
        """
        SELECT pos FROM boxscore_player 
        WHERE player_id = ? AND pos IS NOT NULL AND pos != ''
        ORDER BY game_id DESC LIMIT 1
        """,
        (player_id,),
    ).fetchone()
    position = pos_row["pos"] if pos_row else None
    
    # Apply adjustments
    adjustments = {}
    minutes_factor = 1.0
    efficiency_factor = 1.0
    
    # Back-to-back adjustment - affects minutes (fatigue/rotation)
    if is_back_to_back:
        minutes_factor *= config.back_to_back_factor
        adjustments["back_to_back_min"] = config.back_to_back_factor
    
    # Rest advantage - affects minutes (fresher legs = full rotation) but mainly efficiency? 
    # Current logic treats it as a minutes booster/efficiency booster combo.
    # We'll apply it to efficiency for now as "better play".
    if rest_days >= 3:
        efficiency_factor *= config.rest_advantage_factor
        adjustments["rest_advantage_eff"] = config.rest_advantage_factor
    
    # Archetype-based matchup adjustment
    defender_warnings = []
    
    if config.use_archetype_adjustments and opponent_abbrev:
        try:
            from .roster import (
                get_player_profile, 
                should_avoid_betting_over,
                get_archetype_matchup_adjustment,
                get_roster_for_team,
            )
            
            player_profile = get_player_profile(player_name)
            
            if player_profile:
                # Get opponent roster names
                opponent_roster = [p.name for p in get_roster_for_team(opponent_abbrev)]
                
                # Check for elite defenders
                avoid, defenders = should_avoid_betting_over(player_name, opponent_roster)
                if avoid:
                    efficiency_factor *= config.elite_defender_factor
                    defender_warnings = defenders
                    adjustments["elite_defender"] = config.elite_defender_factor
                    adjustments["elite_defender_names"] = defenders
                
                # Additional archetype-specific adjustments
                for defender_name in opponent_roster:
                    defender_profile = get_player_profile(defender_name)
                    if defender_profile and defender_profile.is_elite_defender:
                        matchup_adj = get_archetype_matchup_adjustment(player_profile, defender_profile)
                        if matchup_adj != 1.0:
                            efficiency_factor *= matchup_adj
                            adjustments["archetype_matchup"] = matchup_adj
                            break  # Only apply once
                
                # Store archetype info
                adjustments["archetype"] = {
                    "primary": player_profile.primary_offensive.value,
                    "secondary": player_profile.secondary_offensive.value if player_profile.secondary_offensive else None,
                    "defensive": player_profile.defensive_role.value,
                    "tier": player_profile.tier.name,
                }
        except ImportError:
            pass  # Roster module not available
    
    # Defense vs position adjustment (Weak AND Strong Defenses)
    position_defense_adj = {"pts": 1.0, "reb": 1.0, "ast": 1.0}
    
    if config.use_position_defense and opponent_abbrev and position:
        try:
            from ..ingest.defense_position_parser import calculate_defense_factor
            
            # Map position to defense vs position format (PG, SG, SF, PF, C)
            pos_mapping = {
                "G": "PG",  # Default guard to PG
                "F": "SF",  # Default forward to SF  
                "C": "C",
                "PG": "PG",
                "SG": "SG",
                "SF": "SF",
                "PF": "PF",
            }
            mapped_pos = pos_mapping.get(position, position)
            
            for stat in ["pts", "reb", "ast"]:
                defense_info = calculate_defense_factor(conn, opponent_abbrev, mapped_pos, stat)
                if defense_info:
                    factor = defense_info["factor"]
                    
                    # Apply boost for weak defenses OR penalty for strong defenses
                    # Scale the adjustment to be moderate: 
                    # - factor of 1.10 = defense allows 10% more -> 4.5% boost
                    # - factor of 0.90 = defense allows 10% less -> 4.5% penalty
                    
                    diff = factor - 1.0 
                    # Dampen the effect (0.50 dampening factor)
                    # Example: allow 1.20 (20% more) -> +10% projection
                    adj = 1.0 + (diff * 0.50)
                    
                    # Cap extremes (+/- 15%)
                    adj = max(0.85, min(adj, 1.15))
                    
                    if abs(adj - 1.0) > 0.01: # Signal only if significant
                        position_defense_adj[stat] = adj
                        
                        if f"defense_vs_pos_{stat}" not in adjustments:
                            adjustments[f"defense_vs_pos_{stat}"] = {
                                "factor": defense_info["factor"],
                                "rank": defense_info["rank"],
                                "rating": defense_info["rating"],
                                "boost_applied": adj,
                            }
        except ImportError:
            pass  # Defense position parser not available
    
    # Calculate final projections
    proj_minutes = avg_min * minutes_factor
    proj_pts = avg_pts * minutes_factor * efficiency_factor * position_defense_adj["pts"]
    proj_reb = avg_reb * minutes_factor * efficiency_factor * position_defense_adj["reb"]
    proj_ast = avg_ast * minutes_factor * efficiency_factor * position_defense_adj["ast"]
    
    return PlayerProjection(
        player_id=player_id,
        player_name=player_name,
        team_abbrev=team_abbrev,
        proj_minutes=round(proj_minutes, 1),
        minutes_std=round(std_min, 1),
        proj_pts=round(proj_pts, 1),
        proj_reb=round(proj_reb, 1),
        proj_ast=round(proj_ast, 1),
        pts_std=round(std_pts, 1),
        reb_std=round(std_reb, 1),
        ast_std=round(std_ast, 1),
        pts_per_min=round(pts_per_min, 3),
        reb_per_min=round(reb_per_min, 3),
        ast_per_min=round(ast_per_min, 3),
        games_played=len(logs),
        position=position,
        adjustments=adjustments,
    )


def project_team_players(
    conn: sqlite3.Connection,
    team_abbrev: str,
    config: Optional[ProjectionConfig] = None,
    opponent_abbrev: Optional[str] = None,
    is_back_to_back: bool = False,
    rest_days: int = 1,
) -> list[PlayerProjection]:
    """
    Project stats for top N players on a team.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
        config: Projection configuration
        opponent_abbrev: Opponent team abbreviation
        is_back_to_back: Whether this is a back-to-back game
        rest_days: Days of rest before this game
    
    Returns:
        List of PlayerProjection objects for top N players
    """
    if config is None:
        config = ProjectionConfig()
    
    team_abbrev = normalize_team_abbrev(team_abbrev)
    
    # Find team IDs for this abbreviation
    from ..standings import _team_ids_by_abbrev
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(team_abbrev, [])
    
    if not team_ids:
        return []
    
    # Get players by average minutes
    placeholders = ",".join(["?"] * len(team_ids))
    rows = conn.execute(
        f"""
        SELECT 
            b.player_id,
            AVG(b.minutes) as avg_min,
            COUNT(*) as games
        FROM boxscore_player b
        WHERE b.team_id IN ({placeholders})
          AND b.minutes IS NOT NULL
          AND b.minutes > 0
        GROUP BY b.player_id
        HAVING COUNT(*) >= ?
        ORDER BY avg_min DESC
        LIMIT ?
        """,
        (*team_ids, config.min_games, config.top_n_players * 2),  # Get extra in case some fail
    ).fetchall()
    
    projections = []
    for row in rows:
        if len(projections) >= config.top_n_players:
            break
        
        proj = project_player_stats(
            conn=conn,
            player_id=row["player_id"],
            config=config,
            opponent_abbrev=opponent_abbrev,
            is_back_to_back=is_back_to_back,
            rest_days=rest_days,
        )
        
        if proj:
            rank = len(projections)
            proj.is_top_7 = rank < 7  # Legacy compatibility
            proj.is_top_10 = rank < 10
            projections.append(proj)
    
    return projections


def get_league_average_by_position(
    conn: sqlite3.Connection,
    position: str,
) -> dict[str, float]:
    """Get league average stats for a position."""
    # Normalize position to G/F/C
    pos = position.upper()[:1] if position else ""
    if pos not in ("G", "F", "C"):
        pos = ""
    
    if pos:
        rows = conn.execute(
            """
            SELECT 
                AVG(b.pts) as avg_pts,
                AVG(b.reb) as avg_reb,
                AVG(b.ast) as avg_ast,
                AVG(b.minutes) as avg_min
            FROM boxscore_player b
            WHERE b.pos = ?
              AND b.minutes IS NOT NULL
              AND b.minutes > 15
            """,
            (pos,),
        ).fetchone()
    else:
        rows = conn.execute(
            """
            SELECT 
                AVG(b.pts) as avg_pts,
                AVG(b.reb) as avg_reb,
                AVG(b.ast) as avg_ast,
                AVG(b.minutes) as avg_min
            FROM boxscore_player b
            WHERE b.minutes IS NOT NULL
              AND b.minutes > 15
            """
        ).fetchone()
    
    return {
        "avg_pts": rows["avg_pts"] or 0,
        "avg_reb": rows["avg_reb"] or 0,
        "avg_ast": rows["avg_ast"] or 0,
        "avg_min": rows["avg_min"] or 0,
    }


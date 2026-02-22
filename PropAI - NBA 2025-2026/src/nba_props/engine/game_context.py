"""Matchup analysis and adjustments."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List

from ..team_aliases import normalize_team_abbrev, abbrev_from_team_name


# ============================================================================
# Constants
# ============================================================================

# Data freshness thresholds (in days)
MAX_DEFENSE_DATA_AGE = 14  # Defense data older than this is considered stale
IDEAL_DEFENSE_DATA_AGE = 7  # Ideal freshness for defense data
MIN_GAMES_FOR_DEFENSE = 5  # Minimum games needed for reliable defense rating


# ============================================================================
# Data Freshness Validation
# ============================================================================

@dataclass
class DataFreshnessReport:
    """Report on data freshness for a team."""
    team_abbrev: str
    last_game_date: Optional[str]
    days_since_last_game: int
    games_available: int
    
    # Freshness flags
    is_fresh: bool  # True if data is recent enough
    is_reliable: bool  # True if enough games available
    
    # Warnings
    warnings: List[str] = field(default_factory=list)


def check_defense_data_freshness(
    conn: sqlite3.Connection,
    team_abbrev: str,
    as_of_date: str,
) -> DataFreshnessReport:
    """
    Check if defense data for a team is fresh enough for reliable projections.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
        as_of_date: Reference date for freshness check (YYYY-MM-DD)
    
    Returns:
        DataFreshnessReport with freshness status
    """
    from ..standings import _team_ids_by_abbrev
    
    team_abbrev = normalize_team_abbrev(team_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(team_abbrev, [])
    
    warnings = []
    
    if not team_ids:
        return DataFreshnessReport(
            team_abbrev=team_abbrev,
            last_game_date=None,
            days_since_last_game=999,
            games_available=0,
            is_fresh=False,
            is_reliable=False,
            warnings=["Team not found in database"]
        )
    
    placeholders = ",".join(["?"] * len(team_ids))
    
    # Get most recent game and game count
    row = conn.execute(f"""
        SELECT 
            MAX(g.game_date) as last_game,
            COUNT(*) as games
        FROM games g
        WHERE g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders})
    """, (*team_ids, *team_ids)).fetchone()
    
    last_game_date = row["last_game"] if row else None
    games_available = row["games"] if row else 0
    
    # Calculate days since last game
    days_since = 999
    if last_game_date:
        try:
            ref_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
            last_dt = datetime.strptime(last_game_date, "%Y-%m-%d")
            days_since = (ref_dt - last_dt).days
        except ValueError:
            warnings.append("Could not parse dates for freshness calculation")
    
    # Determine freshness
    is_fresh = days_since <= MAX_DEFENSE_DATA_AGE
    is_reliable = games_available >= MIN_GAMES_FOR_DEFENSE
    
    # Add warnings
    if not is_fresh:
        warnings.append(f"Defense data is {days_since} days old (max recommended: {MAX_DEFENSE_DATA_AGE})")
    elif days_since > IDEAL_DEFENSE_DATA_AGE:
        warnings.append(f"Defense data is {days_since} days old (ideally < {IDEAL_DEFENSE_DATA_AGE})")
    
    if not is_reliable:
        warnings.append(f"Only {games_available} games available (need {MIN_GAMES_FOR_DEFENSE} for reliability)")
    
    return DataFreshnessReport(
        team_abbrev=team_abbrev,
        last_game_date=last_game_date,
        days_since_last_game=days_since,
        games_available=games_available,
        is_fresh=is_fresh,
        is_reliable=is_reliable,
        warnings=warnings
    )


def get_defense_with_fallback(
    conn: sqlite3.Connection,
    team_abbrev: str,
    as_of_date: str,
) -> tuple[Optional["TeamDefenseRating"], DataFreshnessReport]:
    """
    Get team defense rating with freshness check and fallback.
    
    If defense data is stale or unreliable, returns league average as fallback.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
        as_of_date: Reference date
    
    Returns:
        Tuple of (TeamDefenseRating, DataFreshnessReport)
        If data is unreliable, returns league average defense rating
    """
    freshness = check_defense_data_freshness(conn, team_abbrev, as_of_date)
    
    # Try to get actual defense rating
    defense = get_team_defense_rating(conn, team_abbrev)
    
    if defense and freshness.is_fresh and freshness.is_reliable:
        return defense, freshness
    
    # Fallback to league average
    if not defense or not freshness.is_reliable:
        # Create a neutral defense rating (1.0 factors = league average)
        defense = TeamDefenseRating(
            team_abbrev=team_abbrev,
            games_played=freshness.games_available,
            pts_allowed_pg=0,
            pts_allowed_rank=15,  # Middle of league
            reb_allowed_pg=0,
            reb_allowed_rank=15,
            ast_allowed_pg=0,
            ast_allowed_rank=15,
            pts_factor=1.0,
            reb_factor=1.0,
            ast_factor=1.0,
        )
        freshness.warnings.append("Using league average defense due to insufficient data")
    
    return defense, freshness


@dataclass
class BackToBackStatus:
    """Back-to-back game status for a team."""
    is_back_to_back: bool
    rest_days: int
    last_game_date: Optional[str]
    opponent_is_b2b: bool = False
    opponent_rest_days: int = 1


@dataclass
class TeamDefenseRating:
    """Team defense rating against various stat categories."""
    team_abbrev: str
    games_played: int
    
    # Points allowed per game
    pts_allowed_pg: float
    pts_allowed_rank: int  # 1 = best defense
    
    # Rebounds allowed per game
    reb_allowed_pg: float
    reb_allowed_rank: int
    
    # Assists allowed per game
    ast_allowed_pg: float
    ast_allowed_rank: int
    
    # Adjustment factors (1.0 = league average)
    # Values > 1.0 mean this team allows MORE than average (bad defense)
    # Values < 1.0 mean this team allows LESS than average (good defense)
    pts_factor: float = 1.0
    reb_factor: float = 1.0
    ast_factor: float = 1.0


def get_back_to_back_status(
    conn: sqlite3.Connection,
    team_abbrev: str,
    game_date: str,
) -> BackToBackStatus:
    """
    Determine if a team is on a back-to-back for a given game date.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
        game_date: Game date in YYYY-MM-DD format
    
    Returns:
        BackToBackStatus with rest information
    """
    team_abbrev = normalize_team_abbrev(team_abbrev)
    
    # Find team IDs
    from ..standings import _team_ids_by_abbrev
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(team_abbrev, [])
    
    if not team_ids:
        return BackToBackStatus(
            is_back_to_back=False,
            rest_days=1,
            last_game_date=None,
        )
    
    # Find the most recent game before game_date
    placeholders = ",".join(["?"] * len(team_ids))
    row = conn.execute(
        f"""
        SELECT g.game_date
        FROM games g
        WHERE (g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders}))
          AND g.game_date < ?
        ORDER BY g.game_date DESC
        LIMIT 1
        """,
        (*team_ids, *team_ids, game_date),
    ).fetchone()
    
    if not row:
        return BackToBackStatus(
            is_back_to_back=False,
            rest_days=7,  # Assume well-rested if no prior games
            last_game_date=None,
        )
    
    last_game_date = row["game_date"]
    
    # Calculate rest days
    try:
        target_dt = datetime.strptime(game_date, "%Y-%m-%d")
        last_dt = datetime.strptime(last_game_date, "%Y-%m-%d")
        rest_days = (target_dt - last_dt).days - 1  # -1 because same day = 0 rest
    except ValueError:
        rest_days = 1
    
    is_b2b = rest_days == 0
    
    return BackToBackStatus(
        is_back_to_back=is_b2b,
        rest_days=max(rest_days, 0),
        last_game_date=last_game_date,
    )


def get_team_defense_rating(
    conn: sqlite3.Connection,
    team_abbrev: str,
) -> Optional[TeamDefenseRating]:
    """
    Calculate team defense rating based on points/rebounds/assists allowed.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
    
    Returns:
        TeamDefenseRating or None if insufficient data
    """
    team_abbrev = normalize_team_abbrev(team_abbrev)
    
    # Find team IDs
    from ..standings import _team_ids_by_abbrev
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(team_abbrev, [])
    
    if not team_ids:
        return None
    
    # Get stats allowed by this team (opponent stats)
    # When team_abbrev is team1, opponent stats are from team2 (and vice versa)
    placeholders = ",".join(["?"] * len(team_ids))
    
    rows = conn.execute(
        f"""
        SELECT 
            CASE 
                WHEN g.team1_id IN ({placeholders}) THEN tt2.pts
                ELSE tt1.pts
            END as opp_pts,
            CASE 
                WHEN g.team1_id IN ({placeholders}) THEN tt2.reb
                ELSE tt1.reb
            END as opp_reb,
            CASE 
                WHEN g.team1_id IN ({placeholders}) THEN tt2.ast
                ELSE tt1.ast
            END as opp_ast
        FROM games g
        LEFT JOIN boxscore_team_totals tt1 ON tt1.game_id = g.id AND tt1.team_id = g.team1_id
        LEFT JOIN boxscore_team_totals tt2 ON tt2.game_id = g.id AND tt2.team_id = g.team2_id
        WHERE g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders})
        """,
        (*team_ids, *team_ids, *team_ids, *team_ids, *team_ids),
    ).fetchall()
    
    if len(rows) < 3:
        return None
    
    # Calculate averages allowed
    pts_values = [r["opp_pts"] for r in rows if r["opp_pts"] is not None]
    reb_values = [r["opp_reb"] for r in rows if r["opp_reb"] is not None]
    ast_values = [r["opp_ast"] for r in rows if r["opp_ast"] is not None]
    
    if not pts_values:
        return None
    
    pts_allowed_pg = sum(pts_values) / len(pts_values)
    reb_allowed_pg = sum(reb_values) / len(reb_values) if reb_values else 0
    ast_allowed_pg = sum(ast_values) / len(ast_values) if ast_values else 0
    
    # Get league averages for comparison
    league_rows = conn.execute(
        """
        SELECT 
            AVG(tt.pts) as league_pts,
            AVG(tt.reb) as league_reb,
            AVG(tt.ast) as league_ast
        FROM boxscore_team_totals tt
        WHERE tt.pts IS NOT NULL
        """
    ).fetchone()
    
    league_pts = league_rows["league_pts"] or pts_allowed_pg
    league_reb = league_rows["league_reb"] or reb_allowed_pg
    league_ast = league_rows["league_ast"] or ast_allowed_pg
    
    # Calculate adjustment factors
    pts_factor = pts_allowed_pg / league_pts if league_pts > 0 else 1.0
    reb_factor = reb_allowed_pg / league_reb if league_reb > 0 else 1.0
    ast_factor = ast_allowed_pg / league_ast if league_ast > 0 else 1.0
    
    return TeamDefenseRating(
        team_abbrev=team_abbrev,
        games_played=len(rows),
        pts_allowed_pg=round(pts_allowed_pg, 1),
        pts_allowed_rank=0,  # Would need all teams to calculate rank
        reb_allowed_pg=round(reb_allowed_pg, 1),
        reb_allowed_rank=0,
        ast_allowed_pg=round(ast_allowed_pg, 1),
        ast_allowed_rank=0,
        pts_factor=round(pts_factor, 3),
        reb_factor=round(reb_factor, 3),
        ast_factor=round(ast_factor, 3),
    )


def get_all_team_defense_ratings(conn: sqlite3.Connection) -> dict[str, TeamDefenseRating]:
    """Get defense ratings for all teams and calculate rankings."""
    from ..standings import ALL_ABBREVS
    
    ratings = {}
    for abbrev in ALL_ABBREVS:
        rating = get_team_defense_rating(conn, abbrev)
        if rating:
            ratings[abbrev] = rating
    
    # Calculate rankings (1 = best defense = lowest points allowed)
    if ratings:
        sorted_by_pts = sorted(ratings.values(), key=lambda r: r.pts_allowed_pg)
        sorted_by_reb = sorted(ratings.values(), key=lambda r: r.reb_allowed_pg)
        sorted_by_ast = sorted(ratings.values(), key=lambda r: r.ast_allowed_pg)
        
        for i, r in enumerate(sorted_by_pts, 1):
            ratings[r.team_abbrev].pts_allowed_rank = i
        for i, r in enumerate(sorted_by_reb, 1):
            ratings[r.team_abbrev].reb_allowed_rank = i
        for i, r in enumerate(sorted_by_ast, 1):
            ratings[r.team_abbrev].ast_allowed_rank = i
    
    return ratings


def apply_matchup_adjustments(
    proj_pts: float,
    proj_reb: float,
    proj_ast: float,
    opponent_defense: Optional[TeamDefenseRating],
    max_adjustment: float = 0.15,
) -> tuple[float, float, float, dict]:
    """
    Apply opponent defense adjustments to projections.
    
    Args:
        proj_pts: Baseline points projection
        proj_reb: Baseline rebounds projection
        proj_ast: Baseline assists projection
        opponent_defense: Opponent's defense rating
        max_adjustment: Maximum adjustment factor (e.g., 0.15 = +/- 15%)
    
    Returns:
        Tuple of (adj_pts, adj_reb, adj_ast, adjustments_dict)
    """
    if not opponent_defense:
        return proj_pts, proj_reb, proj_ast, {}
    
    def clamp_factor(factor: float, max_adj: float) -> float:
        """Clamp factor to be within (1 - max_adj, 1 + max_adj)."""
        return max(1 - max_adj, min(1 + max_adj, factor))
    
    pts_adj = clamp_factor(opponent_defense.pts_factor, max_adjustment)
    reb_adj = clamp_factor(opponent_defense.reb_factor, max_adjustment)
    ast_adj = clamp_factor(opponent_defense.ast_factor, max_adjustment)
    
    adj_pts = proj_pts * pts_adj
    adj_reb = proj_reb * reb_adj
    adj_ast = proj_ast * ast_adj
    
    adjustments = {
        "opponent": opponent_defense.team_abbrev,
        "pts_factor": pts_adj,
        "reb_factor": reb_adj,
        "ast_factor": ast_adj,
    }
    
    return round(adj_pts, 1), round(adj_reb, 1), round(adj_ast, 1), adjustments


@dataclass
class MatchupRecommendation:
    """A prop recommendation based on matchup analysis."""
    player_name: str
    team_abbrev: str
    opponent_abbrev: str
    
    prop_type: str  # PTS, REB, AST
    direction: str  # OVER, UNDER
    
    # Analysis
    baseline_value: float
    adjusted_value: float
    
    # Factors
    defense_rating: str  # "elite", "good", "average", "poor"
    back_to_back: bool
    rest_advantage: bool
    
    # Confidence
    confidence: str  # HIGH, MEDIUM, LOW
    reasoning: list[str]
    
    # Optional
    line: float = 0.0


def get_position_defense_rating(
    conn: sqlite3.Connection,
    team_abbrev: str,
    position: str,
) -> Optional[dict]:
    """
    Get how well a team defends a specific position.
    
    Analyzes how much players at a given position score against this team
    compared to their average performance.
    """
    from ..standings import _team_ids_by_abbrev
    
    team_abbrev = normalize_team_abbrev(team_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    team_ids = team_ids_map.get(team_abbrev, [])
    
    if not team_ids:
        return None
    
    # Normalize position to G/F/C
    pos = position.upper()[:1] if position else ""
    if pos not in ("G", "F", "C"):
        return None
    
    placeholders = ",".join(["?"] * len(team_ids))
    
    # Get performance of players at this position against this team
    rows = conn.execute(
        f"""
        SELECT 
            p.name,
            b.pts,
            b.reb,
            b.ast,
            b.minutes
        FROM boxscore_player b
        JOIN players p ON p.id = b.player_id
        JOIN games g ON g.id = b.game_id
        WHERE b.pos = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 15
          AND (
            (g.team1_id IN ({placeholders}) AND b.team_id != g.team1_id)
            OR (g.team2_id IN ({placeholders}) AND b.team_id != g.team2_id)
          )
        """,
        (pos, *team_ids, *team_ids),
    ).fetchall()
    
    if len(rows) < 5:
        return None
    
    # Calculate averages
    total_pts = sum(r["pts"] or 0 for r in rows)
    total_reb = sum(r["reb"] or 0 for r in rows)
    total_ast = sum(r["ast"] or 0 for r in rows)
    count = len(rows)
    
    # Compare to league average for this position
    league_rows = conn.execute(
        """
        SELECT 
            AVG(pts) as avg_pts,
            AVG(reb) as avg_reb,
            AVG(ast) as avg_ast
        FROM boxscore_player
        WHERE pos = ?
          AND minutes IS NOT NULL
          AND minutes > 15
        """,
        (pos,),
    ).fetchone()
    
    league_pts = league_rows["avg_pts"] or 1
    league_reb = league_rows["avg_reb"] or 1
    league_ast = league_rows["avg_ast"] or 1
    
    vs_team_pts = total_pts / count
    vs_team_reb = total_reb / count
    vs_team_ast = total_ast / count
    
    return {
        "position": pos,
        "sample_size": count,
        "pts_vs_team": round(vs_team_pts, 1),
        "reb_vs_team": round(vs_team_reb, 1),
        "ast_vs_team": round(vs_team_ast, 1),
        "league_pts": round(league_pts, 1),
        "league_reb": round(league_reb, 1),
        "league_ast": round(league_ast, 1),
        "pts_factor": round(vs_team_pts / league_pts, 3) if league_pts > 0 else 1.0,
        "reb_factor": round(vs_team_reb / league_reb, 3) if league_reb > 0 else 1.0,
        "ast_factor": round(vs_team_ast / league_ast, 3) if league_ast > 0 else 1.0,
    }


def get_player_vs_team_history(
    conn: sqlite3.Connection,
    player_name: str,
    opponent_abbrev: str,
) -> Optional[dict]:
    """
    Get a player's historical performance against a specific team.
    """
    from ..standings import _team_ids_by_abbrev
    
    opponent_abbrev = normalize_team_abbrev(opponent_abbrev)
    team_ids_map = _team_ids_by_abbrev(conn)
    opponent_ids = team_ids_map.get(opponent_abbrev, [])
    
    if not opponent_ids:
        return None
    
    # Find player
    player_row = conn.execute(
        "SELECT id, name FROM players WHERE name LIKE ?",
        (f"%{player_name}%",),
    ).fetchone()
    
    if not player_row:
        return None
    
    player_id = player_row["id"]
    full_name = player_row["name"]
    
    placeholders = ",".join(["?"] * len(opponent_ids))
    
    # Get games against this opponent
    rows = conn.execute(
        f"""
        SELECT 
            g.game_date,
            b.pts,
            b.reb,
            b.ast,
            b.minutes
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.player_id = ?
          AND b.minutes IS NOT NULL
          AND b.minutes > 0
          AND (g.team1_id IN ({placeholders}) OR g.team2_id IN ({placeholders}))
        ORDER BY g.game_date DESC
        """,
        (player_id, *opponent_ids, *opponent_ids),
    ).fetchall()
    
    if not rows:
        return None
    
    # Get player's overall averages
    overall = conn.execute(
        """
        SELECT 
            AVG(pts) as avg_pts,
            AVG(reb) as avg_reb,
            AVG(ast) as avg_ast,
            AVG(minutes) as avg_min
        FROM boxscore_player
        WHERE player_id = ?
          AND minutes IS NOT NULL
          AND minutes > 0
        """,
        (player_id,),
    ).fetchone()
    
    vs_opponent_pts = sum(r["pts"] or 0 for r in rows) / len(rows)
    vs_opponent_reb = sum(r["reb"] or 0 for r in rows) / len(rows)
    vs_opponent_ast = sum(r["ast"] or 0 for r in rows) / len(rows)
    
    return {
        "player": full_name,
        "opponent": opponent_abbrev,
        "games_vs_opponent": len(rows),
        "vs_opponent": {
            "pts": round(vs_opponent_pts, 1),
            "reb": round(vs_opponent_reb, 1),
            "ast": round(vs_opponent_ast, 1),
        },
        "overall": {
            "pts": round(overall["avg_pts"] or 0, 1),
            "reb": round(overall["avg_reb"] or 0, 1),
            "ast": round(overall["avg_ast"] or 0, 1),
        },
        "differential": {
            "pts": round(vs_opponent_pts - (overall["avg_pts"] or 0), 1),
            "reb": round(vs_opponent_reb - (overall["avg_reb"] or 0), 1),
            "ast": round(vs_opponent_ast - (overall["avg_ast"] or 0), 1),
        },
        "recent_games": [
            {
                "date": r["game_date"],
                "pts": r["pts"],
                "reb": r["reb"],
                "ast": r["ast"],
                "min": round(r["minutes"], 1) if r["minutes"] else 0,
            }
            for r in rows[:5]
        ],
    }


def generate_matchup_recommendations(
    conn: sqlite3.Connection,
    away_abbrev: str,
    home_abbrev: str,
    game_date: str,
    min_edge_pct: float = 5.0,
) -> list[MatchupRecommendation]:
    """
    Generate prop recommendations based on matchup analysis.
    
    This combines:
    - Team defense ratings
    - Position-specific defense
    - Player vs team history
    - Back-to-back status
    - Recent form
    """
    from .projector import project_team_players, ProjectionConfig
    
    recommendations = []
    config = ProjectionConfig()
    
    # Get defense ratings
    away_defense = get_team_defense_rating(conn, away_abbrev)
    home_defense = get_team_defense_rating(conn, home_abbrev)
    
    # Get back-to-back status
    away_b2b = get_back_to_back_status(conn, away_abbrev, game_date)
    home_b2b = get_back_to_back_status(conn, home_abbrev, game_date)
    
    # Get projections for both teams
    away_projections = project_team_players(
        conn=conn,
        team_abbrev=away_abbrev,
        config=config,
        opponent_abbrev=home_abbrev,
        is_back_to_back=away_b2b.is_back_to_back,
        rest_days=away_b2b.rest_days,
    )
    
    home_projections = project_team_players(
        conn=conn,
        team_abbrev=home_abbrev,
        config=config,
        opponent_abbrev=away_abbrev,
        is_back_to_back=home_b2b.is_back_to_back,
        rest_days=home_b2b.rest_days,
    )
    
    def defense_tier(factor: float) -> str:
        if factor < 0.95:
            return "elite"
        elif factor < 1.0:
            return "good"
        elif factor < 1.05:
            return "average"
        else:
            return "poor"
    
    def analyze_player(proj, opponent_abbrev, opponent_defense, is_b2b, rest_days):
        """Analyze a single player for matchup recommendations."""
        if not proj.is_top_7:
            return []
        
        player_recs = []
        
        # Get historical performance vs this team
        history = get_player_vs_team_history(conn, proj.player_name, opponent_abbrev)
        
        # Get position-specific defense
        pos_defense = get_position_defense_rating(conn, opponent_abbrev, proj.position or "")
        
        for prop_type in ["PTS", "REB", "AST"]:
            baseline = getattr(proj, f"proj_{prop_type.lower()}")
            std = getattr(proj, f"{prop_type.lower()}_std")
            
            # Get defense factor
            if opponent_defense:
                defense_factor = getattr(opponent_defense, f"{prop_type.lower()}_factor", 1.0)
            else:
                defense_factor = 1.0
            
            # Get position-specific factor
            pos_factor = 1.0
            if pos_defense:
                pos_factor = pos_defense.get(f"{prop_type.lower()}_factor", 1.0)
            
            # Combined factor (average of team defense and position defense)
            combined_factor = (defense_factor + pos_factor) / 2
            
            # Apply adjustments
            adjusted = baseline * combined_factor
            
            # Historical adjustment
            hist_adj = 0
            if history and history["games_vs_opponent"] >= 2:
                hist_diff = history["differential"].get(prop_type.lower(), 0)
                hist_adj = hist_diff * 0.3  # Weight historical performance
                adjusted += hist_adj
            
            # B2B adjustment
            if is_b2b:
                adjusted *= 0.95  # 5% reduction on back-to-backs
            elif rest_days >= 3:
                adjusted *= 1.02  # 2% boost for well-rested
            
            # Calculate direction and confidence
            diff_pct = ((adjusted - baseline) / baseline * 100) if baseline > 0 else 0
            
            if abs(diff_pct) < min_edge_pct:
                continue
            
            direction = "OVER" if adjusted > baseline else "UNDER"
            
            # Build reasoning
            reasoning = []
            
            # Defense rating reason
            def_tier = defense_tier(combined_factor)
            if def_tier in ("elite", "good"):
                reasoning.append(f"{opponent_abbrev} has {def_tier} defense vs {prop_type}")
            elif def_tier == "poor":
                reasoning.append(f"{opponent_abbrev} allows above-average {prop_type}")
            
            # Historical reason
            if history and history["games_vs_opponent"] >= 2:
                if abs(history["differential"].get(prop_type.lower(), 0)) > 2:
                    hist_pts = history["vs_opponent"][prop_type.lower()]
                    reasoning.append(f"Averages {hist_pts} {prop_type} vs {opponent_abbrev} ({history['games_vs_opponent']} games)")
            
            # B2B reason
            if is_b2b:
                reasoning.append("Playing on back-to-back")
            elif rest_days >= 3:
                reasoning.append(f"Well rested ({rest_days} days)")
            
            # Confidence based on factors
            if abs(diff_pct) >= 10 and len(reasoning) >= 2:
                confidence = "HIGH"
            elif abs(diff_pct) >= 7:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"
            
            player_recs.append(MatchupRecommendation(
                player_name=proj.player_name,
                team_abbrev=proj.team_abbrev,
                opponent_abbrev=opponent_abbrev,
                prop_type=prop_type,
                direction=direction,
                baseline_value=round(baseline, 1),
                adjusted_value=round(adjusted, 1),
                defense_rating=def_tier,
                back_to_back=is_b2b,
                rest_advantage=rest_days >= 3,
                confidence=confidence,
                reasoning=reasoning,
            ))
        
        return player_recs
    
    # Analyze away team (vs home defense)
    for proj in away_projections:
        recs = analyze_player(
            proj, home_abbrev, home_defense,
            away_b2b.is_back_to_back, away_b2b.rest_days
        )
        recommendations.extend(recs)
    
    # Analyze home team (vs away defense)
    for proj in home_projections:
        recs = analyze_player(
            proj, away_abbrev, away_defense,
            home_b2b.is_back_to_back, home_b2b.rest_days
        )
        recommendations.extend(recs)
    
    # Sort by confidence and adjusted value difference
    def sort_key(r):
        conf_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        diff = abs(r.adjusted_value - r.baseline_value)
        return (conf_order.get(r.confidence, 3), -diff)
    
    recommendations.sort(key=sort_key)
    
    return recommendations


"""
Enhanced UNDER Model v2.0
=========================

This is a comprehensive UNDER picks model designed for NBA player props betting.
It focuses on identifying situations where players are likely to UNDERPERFORM
their typical averages.

Core Philosophy:
- UNDER picks are more predictable than OVER picks because negative factors 
  compound more reliably than positive ones
- Elite defenses consistently limit player production
- Fatigue, cold streaks, and matchup disadvantages are quantifiable
- Variance/consistency matters - inconsistent players are more likely to hit unders

Key Data Sources Utilized:
1. Defense vs Position (Hashtag Basketball) - CRITICAL
   - Best defenses = target for UNDERS
   - Position-specific analysis (PG, SG, SF, PF, C)
   
2. Box Score History
   - Recent performance trends (L5, L10, L20)
   - Performance variance/consistency
   - Historical vs opponent
   
3. Player Archetypes & Elite Defenders
   - Elite defender matchups
   - Defensive role assignments
   
4. Game Context
   - Back-to-back games
   - Home/Away splits
   - Recent injury returns

Model Target: 70%+ hit rate on HIGH confidence picks
Current Baseline: ~67-68% on HIGH confidence

Author: PropAI Enhanced Model
Version: 2.0
Created: January 2026
"""
from __future__ import annotations

import sqlite3
import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta

from ..team_aliases import normalize_team_abbrev, abbrev_from_team_name
from ..ingest.defense_position_parser import (
    calculate_defense_factor,
    get_defense_vs_position,
    get_defense_vs_position_last_updated,
)


# =============================================================================
# Constants and Thresholds
# =============================================================================

# Defense ranking thresholds (out of 30 teams per position)
ELITE_DEFENSE_THRESHOLD = 5      # Top 5 = elite defense
GOOD_DEFENSE_THRESHOLD = 10      # Top 10 = good defense
AVERAGE_DEFENSE_THRESHOLD = 15   # Top 15 = average
POOR_DEFENSE_THRESHOLD = 25      # 16-25 = below average

# Confidence thresholds (REVISED - calibrated to be more discriminating)
# HIGH (5 stars): Premium picks with elite defense + cold streak (85+)
# MEDIUM (3-4 stars): Good picks with elite defense OR multiple factors (65-84)
# LOW (1-2 stars): Average picks with fewer factors (55-64)
HIGH_CONFIDENCE_THRESHOLD = 85
MEDIUM_CONFIDENCE_THRESHOLD = 65
MIN_CONFIDENCE_THRESHOLD = 55

# Factor weights for scoring
# Based on backtesting analysis:
# - defense_elite + cold_streak = 60.40% hit rate
# - defense_elite alone = 56.81% hit rate
# - cold_streak_severe = 55.94% hit rate
WEIGHTS = {
    "defense_elite": 30,        # Elite defense at position (PRIMARY FACTOR)
    "defense_good": 15,         # Good defense at position
    "defense_average": 5,       # Average defense (minimal weight)
    "cold_streak_severe": 20,   # Very cold (L5 < 80% of season) - HIGH VALUE
    "cold_streak_mild": 12,     # Mild cold (L5 < 90% of season)
    "b2b_second": 8,            # Second game of B2B (lower weight based on backtest)
    "b2b_third_in_four": 5,     # Third game in 4 nights
    "injury_first_back": 18,    # First game back from injury
    "injury_second_back": 12,   # Second game back
    "injury_third_back": 6,     # Third game back
    "high_variance": 6,         # Inconsistent performer (reduced weight)
    "historical_struggle": 10,  # Poor history vs opponent
    "home_disadvantage": 3,     # Away player facing strong home defense (minimal)
    "elite_defender": 10,       # Facing elite defender at position
    "low_minutes_proj": 8,      # Expected low minutes
}

# Factor adjustments (multipliers applied to projections)
# More conservative adjustments based on actual performance data
ADJUSTMENTS = {
    "defense_elite": 0.90,      # 10% reduction
    "defense_good": 0.95,       # 5% reduction
    "defense_average": 0.98,    # 2% reduction
    "cold_streak_severe": 0.88, # 12% reduction (strong signal)
    "cold_streak_mild": 0.94,   # 6% reduction
    "b2b_second": 0.96,         # 4% reduction (less impactful)
    "b2b_third_in_four": 0.98,  # 2% reduction
    "injury_first_back": 0.82,  # 18% reduction
    "injury_second_back": 0.90, # 10% reduction
    "injury_third_back": 0.95,  # 5% reduction
    "high_variance": 0.97,      # 3% reduction
    "historical_struggle": 0.94, # 6% reduction
    "home_disadvantage": 0.99,  # 1% reduction
    "elite_defender": 0.92,     # 8% reduction
    "low_minutes_proj": 0.92,   # 8% reduction
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PlayerStats:
    """Comprehensive player statistics."""
    player_id: int
    player_name: str
    team_abbrev: str
    position: str
    
    # Season averages
    season_pts: float = 0.0
    season_reb: float = 0.0
    season_ast: float = 0.0
    season_min: float = 0.0
    games_played: int = 0
    
    # Recent averages (L5, L10, L20)
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
    
    # Variance (standard deviation)
    pts_variance: float = 0.0
    reb_variance: float = 0.0
    ast_variance: float = 0.0
    
    # Historical vs opponent
    vs_opp_pts: Optional[float] = None
    vs_opp_reb: Optional[float] = None
    vs_opp_ast: Optional[float] = None
    vs_opp_games: int = 0


@dataclass 
class DefenseProfile:
    """Defense vs position profile for a team."""
    team_abbrev: str
    position: str
    overall_rank: int = 15  # 1-150 cross-position
    
    pts_allowed: float = 0.0
    pts_rank: int = 15
    pts_rating: str = "average"
    
    reb_allowed: float = 0.0
    reb_rank: int = 15
    reb_rating: str = "average"
    
    ast_allowed: float = 0.0
    ast_rank: int = 15
    ast_rating: str = "average"
    
    data_available: bool = False
    league_avg_pts: float = 0.0
    league_avg_reb: float = 0.0
    league_avg_ast: float = 0.0


@dataclass
class UnderAnalysis:
    """Detailed analysis for an UNDER pick."""
    player_name: str
    player_id: int
    team_abbrev: str
    opponent_abbrev: str
    position: str
    prop_type: str  # PTS, REB, AST
    
    # Base values
    season_avg: float = 0.0
    recent_avg: float = 0.0  # L5
    l10_avg: float = 0.0
    l20_avg: float = 0.0
    
    # Projection
    projected: float = 0.0
    adjustment_factor: float = 1.0
    
    # Defense analysis
    defense_profile: Optional[DefenseProfile] = None
    defense_factor: float = 1.0
    
    # Factors (name -> weight contribution)
    factors: Dict[str, float] = field(default_factory=dict)
    
    # Factor adjustments (name -> multiplier)
    adjustments: Dict[str, float] = field(default_factory=dict)
    
    # Scoring
    raw_score: float = 0.0
    confidence_score: float = 0.0
    confidence_tier: str = "LOW"
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    is_home: bool = False
    is_b2b: bool = False
    games_since_injury: Optional[int] = None
    variance: float = 0.0
    
    @property
    def factor_count(self) -> int:
        """Count of negative factors."""
        return len(self.factors)
    
    @property
    def total_weight(self) -> float:
        """Sum of all factor weights."""
        return sum(self.factors.values())


@dataclass
class UnderModelResult:
    """Results from the enhanced UNDER model."""
    game_date: str
    status: str = "ACTIVE"
    message: str = ""
    
    picks: List[UnderAnalysis] = field(default_factory=list)
    
    # Stats
    total_players_analyzed: int = 0
    total_props_analyzed: int = 0
    picks_generated: int = 0
    
    # Data status
    defense_data_available: bool = False
    defense_data_freshness: Dict[str, str] = field(default_factory=dict)


# =============================================================================
# Position Mapping
# =============================================================================

def map_position(pos: str) -> str:
    """
    Map various position formats to standard defensive positions.
    Standard: PG, SG, SF, PF, C
    """
    if not pos:
        return "SF"
    
    pos = pos.upper().strip()
    
    if pos in ("PG", "SG", "SF", "PF", "C"):
        return pos
    
    mapping = {
        "G": "PG",
        "F": "SF", 
        "G-F": "SG",
        "F-G": "SG",
        "F-C": "PF",
        "C-F": "PF",
        "GUARD": "PG",
        "FORWARD": "SF",
        "CENTER": "C",
        "PG/SG": "PG",
        "SG/SF": "SG",
        "SF/PF": "SF",
        "PF/C": "PF",
    }
    
    return mapping.get(pos, "SF")


# =============================================================================
# Data Retrieval Functions
# =============================================================================

def get_player_stats(
    conn: sqlite3.Connection,
    player_id: int,
    player_name: str,
    team_abbrev: str,
    opponent_abbrev: str,
    as_of_date: str,
) -> PlayerStats:
    """
    Get comprehensive player statistics including recent games and variance.
    """
    stats = PlayerStats(
        player_id=player_id,
        player_name=player_name,
        team_abbrev=team_abbrev,
        position="SF",  # Default, will be updated
    )
    
    # Get position from most recent game
    pos_row = conn.execute(
        """
        SELECT bp.pos
        FROM boxscore_player bp
        JOIN games g ON g.id = bp.game_id
        WHERE bp.player_id = ? AND g.game_date < ?
        ORDER BY g.game_date DESC
        LIMIT 1
        """,
        (player_id, as_of_date),
    ).fetchone()
    
    if pos_row and pos_row["pos"]:
        stats.position = map_position(pos_row["pos"])
    
    # Get all games before as_of_date
    games = conn.execute(
        """
        SELECT bp.pts, bp.reb, bp.ast, bp.minutes, g.game_date
        FROM boxscore_player bp
        JOIN games g ON g.id = bp.game_id
        WHERE bp.player_id = ? AND g.game_date < ?
          AND bp.minutes IS NOT NULL AND bp.minutes > 0
        ORDER BY g.game_date DESC
        """,
        (player_id, as_of_date),
    ).fetchall()
    
    if not games:
        return stats
    
    stats.games_played = len(games)
    
    # Calculate season averages
    all_pts = [g["pts"] or 0 for g in games]
    all_reb = [g["reb"] or 0 for g in games]
    all_ast = [g["ast"] or 0 for g in games]
    all_min = [g["minutes"] or 0 for g in games]
    
    stats.season_pts = sum(all_pts) / len(all_pts) if all_pts else 0
    stats.season_reb = sum(all_reb) / len(all_reb) if all_reb else 0
    stats.season_ast = sum(all_ast) / len(all_ast) if all_ast else 0
    stats.season_min = sum(all_min) / len(all_min) if all_min else 0
    
    # L5 averages
    l5_games = games[:5]
    if l5_games:
        stats.l5_pts = sum(g["pts"] or 0 for g in l5_games) / len(l5_games)
        stats.l5_reb = sum(g["reb"] or 0 for g in l5_games) / len(l5_games)
        stats.l5_ast = sum(g["ast"] or 0 for g in l5_games) / len(l5_games)
        stats.l5_min = sum(g["minutes"] or 0 for g in l5_games) / len(l5_games)
    
    # L10 averages
    l10_games = games[:10]
    if l10_games:
        stats.l10_pts = sum(g["pts"] or 0 for g in l10_games) / len(l10_games)
        stats.l10_reb = sum(g["reb"] or 0 for g in l10_games) / len(l10_games)
        stats.l10_ast = sum(g["ast"] or 0 for g in l10_games) / len(l10_games)
        stats.l10_min = sum(g["minutes"] or 0 for g in l10_games) / len(l10_games)
    
    # L20 averages
    l20_games = games[:20]
    if l20_games:
        stats.l20_pts = sum(g["pts"] or 0 for g in l20_games) / len(l20_games)
        stats.l20_reb = sum(g["reb"] or 0 for g in l20_games) / len(l20_games)
        stats.l20_ast = sum(g["ast"] or 0 for g in l20_games) / len(l20_games)
        stats.l20_min = sum(g["minutes"] or 0 for g in l20_games) / len(l20_games)
    
    # Calculate variance (standard deviation) from L20 games
    if len(l20_games) >= 5:
        pts_vals = [g["pts"] or 0 for g in l20_games]
        reb_vals = [g["reb"] or 0 for g in l20_games]
        ast_vals = [g["ast"] or 0 for g in l20_games]
        
        stats.pts_variance = _calculate_std(pts_vals)
        stats.reb_variance = _calculate_std(reb_vals)
        stats.ast_variance = _calculate_std(ast_vals)
    
    # Get historical vs opponent
    vs_opp = conn.execute(
        """
        SELECT bp.pts, bp.reb, bp.ast
        FROM boxscore_player bp
        JOIN games g ON g.id = bp.game_id
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        WHERE bp.player_id = ?
          AND g.game_date < ?
          AND (t1.name LIKE ? OR t2.name LIKE ?)
          AND bp.minutes IS NOT NULL AND bp.minutes > 0
        ORDER BY g.game_date DESC
        LIMIT 10
        """,
        (player_id, as_of_date, f"%{opponent_abbrev}%", f"%{opponent_abbrev}%"),
    ).fetchall()
    
    if vs_opp and len(vs_opp) >= 2:
        stats.vs_opp_games = len(vs_opp)
        stats.vs_opp_pts = sum(g["pts"] or 0 for g in vs_opp) / len(vs_opp)
        stats.vs_opp_reb = sum(g["reb"] or 0 for g in vs_opp) / len(vs_opp)
        stats.vs_opp_ast = sum(g["ast"] or 0 for g in vs_opp) / len(vs_opp)
    
    return stats


def _calculate_std(values: List[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def get_defense_profile(
    conn: sqlite3.Connection,
    team_abbrev: str,
    position: str,
) -> DefenseProfile:
    """
    Get comprehensive defense profile for a team at a position.
    """
    profile = DefenseProfile(
        team_abbrev=team_abbrev,
        position=position,
    )
    
    # Get defense vs position data
    defense_data = get_defense_vs_position(conn, team_abbrev, position)
    
    if defense_data:
        profile.data_available = True
        profile.overall_rank = defense_data.overall_rank
        profile.pts_allowed = defense_data.pts_allowed
        profile.pts_rank = defense_data.pts_rank
        profile.reb_allowed = defense_data.reb_allowed
        profile.reb_rank = defense_data.reb_rank
        profile.ast_allowed = defense_data.ast_allowed
        profile.ast_rank = defense_data.ast_rank
        
        # Calculate ratings based on position-specific rank
        # Get all teams' ranks for this position to determine position rank
        all_ranks = conn.execute(
            """
            SELECT team_abbrev, pts_rank, reb_rank, ast_rank
            FROM team_defense_vs_position
            WHERE position = ? AND season = '2025-26'
            ORDER BY overall_rank ASC
            """,
            (position,),
        ).fetchall()
        
        if all_ranks:
            # Find position rank (1-30)
            for i, row in enumerate(all_ranks):
                if row["team_abbrev"] == team_abbrev:
                    pos_rank = i + 1
                    
                    if pos_rank <= ELITE_DEFENSE_THRESHOLD:
                        profile.pts_rating = "elite"
                    elif pos_rank <= GOOD_DEFENSE_THRESHOLD:
                        profile.pts_rating = "good"
                    elif pos_rank <= AVERAGE_DEFENSE_THRESHOLD:
                        profile.pts_rating = "average"
                    elif pos_rank <= POOR_DEFENSE_THRESHOLD:
                        profile.pts_rating = "below_average"
                    else:
                        profile.pts_rating = "poor"
                    
                    # Apply same logic to other stats based on their ranks
                    profile.reb_rating = _get_rating_from_rank(profile.reb_rank, len(all_ranks))
                    profile.ast_rating = _get_rating_from_rank(profile.ast_rank, len(all_ranks))
                    break
        
        # Get league averages
        avg_row = conn.execute(
            """
            SELECT 
                AVG(pts_allowed) as avg_pts,
                AVG(reb_allowed) as avg_reb,
                AVG(ast_allowed) as avg_ast
            FROM team_defense_vs_position
            WHERE position = ? AND season = '2025-26'
            """,
            (position,),
        ).fetchone()
        
        if avg_row:
            profile.league_avg_pts = avg_row["avg_pts"] or 0
            profile.league_avg_reb = avg_row["avg_reb"] or 0
            profile.league_avg_ast = avg_row["avg_ast"] or 0
    
    return profile


def _get_rating_from_rank(rank: int, total: int = 30) -> str:
    """Convert numeric rank to rating string."""
    # Ranks are 1-150, but for position-specific we normalize
    # Lower rank = better defense
    if rank <= total * 0.17:  # Top ~17%
        return "elite"
    elif rank <= total * 0.33:  # Top ~33%
        return "good"
    elif rank <= total * 0.50:  # Top ~50%
        return "average"
    elif rank <= total * 0.83:  # Top ~83%
        return "below_average"
    else:
        return "poor"


def get_back_to_back_info(
    conn: sqlite3.Connection,
    team_abbrev: str,
    game_date: str,
) -> Dict[str, bool]:
    """
    Check if team is on back-to-back or has played 3 in 4 nights.
    """
    from datetime import datetime, timedelta
    
    result = {
        "is_b2b": False,
        "is_third_in_four": False,
    }
    
    try:
        game_dt = datetime.strptime(game_date, "%Y-%m-%d")
        yesterday = (game_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        four_days_ago = (game_dt - timedelta(days=4)).strftime("%Y-%m-%d")
        
        # Check for game yesterday
        yesterday_game = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM games g
            JOIN teams t ON (t.id = g.team1_id OR t.id = g.team2_id)
            WHERE g.game_date = ?
              AND t.name LIKE ?
            """,
            (yesterday, f"%{team_abbrev}%"),
        ).fetchone()
        
        if yesterday_game and yesterday_game["cnt"] > 0:
            result["is_b2b"] = True
        
        # Check for 3 in 4 nights
        recent_games = conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM games g
            JOIN teams t ON (t.id = g.team1_id OR t.id = g.team2_id)
            WHERE g.game_date BETWEEN ? AND ?
              AND g.game_date < ?
              AND t.name LIKE ?
            """,
            (four_days_ago, game_date, game_date, f"%{team_abbrev}%"),
        ).fetchone()
        
        if recent_games and recent_games["cnt"] >= 2:
            result["is_third_in_four"] = True
    except:
        pass
    
    return result


def is_player_out(
    conn: sqlite3.Connection,
    player_name: str,
    game_date: str,
) -> bool:
    """
    Check if a player is marked OUT in the injury report for the given date.
    
    Returns True if the player is OUT and should be excluded from picks.
    """
    # Check injury_report table for OUT status
    row = conn.execute(
        """
        SELECT status 
        FROM injury_report
        WHERE player_name = ?
          AND game_date = ?
          AND status = 'OUT'
        LIMIT 1
        """,
        (player_name, game_date),
    ).fetchone()
    
    return row is not None


def get_injured_players_for_date(
    conn: sqlite3.Connection,
    game_date: str,
) -> set:
    """
    Get a set of player names who are marked OUT for the given date.
    This allows batch checking rather than individual queries.
    """
    rows = conn.execute(
        """
        SELECT player_name 
        FROM injury_report
        WHERE game_date = ?
          AND status = 'OUT'
        """,
        (game_date,),
    ).fetchall()
    
    return {row["player_name"] for row in rows if row["player_name"]}


def _normalize_name_for_matching(name: str) -> str:
    """Normalize a name for matching: lowercase, remove accents, strip."""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_name.lower().strip()


def _is_defender_injured(
    conn: sqlite3.Connection,
    defender_name: str,
    game_date: str,
) -> bool:
    """
    Check if an elite defender is injured (OUT or DOUBTFUL) for the given date.
    Uses fuzzy name matching to handle accent differences.
    """
    if not defender_name or not game_date:
        return False
    
    norm_defender = _normalize_name_for_matching(defender_name)
    
    # Check injury report for this defender
    rows = conn.execute(
        """
        SELECT COALESCE(p.name, ir.player_name) as player_name, ir.status
        FROM injury_report ir
        LEFT JOIN players p ON ir.player_id = p.id
        WHERE ir.game_date = ?
          AND ir.status IN ('OUT', 'DOUBTFUL')
        """,
        (game_date,),
    ).fetchall()
    
    for row in rows:
        if row["player_name"]:
            norm_injured = _normalize_name_for_matching(row["player_name"])
            # Check for exact match or partial match
            if norm_defender == norm_injured or norm_defender in norm_injured or norm_injured in norm_defender:
                return True
    
    return False


def check_elite_defender_matchup(
    conn: sqlite3.Connection,
    opponent_abbrev: str,
    player_position: str,
    game_date: str = None,
) -> Optional[str]:
    """
    Check if there's an elite defender on the opponent for this position.
    Returns the defender name if found and NOT injured, None otherwise.
    
    If game_date is provided, checks if the defender is on the injury report
    and skips them if they are OUT or DOUBTFUL.
    """
    # First check elite_defenders table
    elite = conn.execute(
        """
        SELECT ed.player_name
        FROM elite_defenders ed
        JOIN player_archetypes pa ON pa.player_name = ed.player_name
        WHERE ed.position = ?
          AND pa.team LIKE ?
          AND pa.season = '2025-26'
        LIMIT 1
        """,
        (player_position, f"%{opponent_abbrev}%"),
    ).fetchone()
    
    if elite:
        defender_name = elite["player_name"]
        # Check if this defender is injured
        if game_date and _is_defender_injured(conn, defender_name, game_date):
            # Elite defender is injured - don't count them as a factor
            pass  # Continue to check for other elite defenders
        else:
            return defender_name
    
    # Also check archetypes for is_elite_defender flag
    arch_elite = conn.execute(
        """
        SELECT player_name
        FROM player_archetypes
        WHERE team LIKE ?
          AND position = ?
          AND is_elite_defender = 1
          AND season = '2025-26'
        LIMIT 1
        """,
        (f"%{opponent_abbrev}%", player_position),
    ).fetchone()
    
    if arch_elite:
        defender_name = arch_elite["player_name"]
        # Check if this defender is injured
        if game_date and _is_defender_injured(conn, defender_name, game_date):
            # Elite defender is injured - don't count them
            return None
        return defender_name
    
    return None


# =============================================================================
# Core Analysis Functions
# =============================================================================

def analyze_under_candidate(
    conn: sqlite3.Connection,
    player_stats: PlayerStats,
    opponent_abbrev: str,
    game_date: str,
    prop_type: str,
    is_home: bool = False,
) -> Optional[UnderAnalysis]:
    """
    Perform comprehensive UNDER analysis for a player/prop combination.
    
    This is the core analysis function that evaluates all factors
    and produces a confidence-scored recommendation.
    """
    # Get the right stat averages
    if prop_type == "PTS":
        season_avg = player_stats.season_pts
        recent_avg = player_stats.l5_pts
        l10_avg = player_stats.l10_pts
        l20_avg = player_stats.l20_pts
        variance = player_stats.pts_variance
        vs_opp_avg = player_stats.vs_opp_pts
    elif prop_type == "REB":
        season_avg = player_stats.season_reb
        recent_avg = player_stats.l5_reb
        l10_avg = player_stats.l10_reb
        l20_avg = player_stats.l20_reb
        variance = player_stats.reb_variance
        vs_opp_avg = player_stats.vs_opp_reb
    elif prop_type == "AST":
        season_avg = player_stats.season_ast
        recent_avg = player_stats.l5_ast
        l10_avg = player_stats.l10_ast
        l20_avg = player_stats.l20_ast
        variance = player_stats.ast_variance
        vs_opp_avg = player_stats.vs_opp_ast
    else:
        return None
    
    # Skip very low volume stats
    if season_avg < 5:
        return None
    
    # Create analysis object
    analysis = UnderAnalysis(
        player_name=player_stats.player_name,
        player_id=player_stats.player_id,
        team_abbrev=player_stats.team_abbrev,
        opponent_abbrev=opponent_abbrev,
        position=player_stats.position,
        prop_type=prop_type,
        season_avg=season_avg,
        recent_avg=recent_avg,
        l10_avg=l10_avg,
        l20_avg=l20_avg,
        projected=season_avg,  # Start with season average
        is_home=is_home,
        variance=variance,
    )
    
    # Get defense profile
    defense_profile = get_defense_profile(conn, opponent_abbrev, player_stats.position)
    analysis.defense_profile = defense_profile
    
    # Get B2B info
    b2b_info = get_back_to_back_info(conn, player_stats.team_abbrev, game_date)
    analysis.is_b2b = b2b_info["is_b2b"]
    
    # ==========================================================================
    # Factor Analysis
    # ==========================================================================
    
    # 1. DEFENSE VS POSITION (Primary Factor)
    if defense_profile.data_available:
        if prop_type == "PTS":
            defense_rating = defense_profile.pts_rating
            allowed = defense_profile.pts_allowed
            league_avg = defense_profile.league_avg_pts
        elif prop_type == "REB":
            defense_rating = defense_profile.reb_rating
            allowed = defense_profile.reb_allowed
            league_avg = defense_profile.league_avg_reb
        else:  # AST
            defense_rating = defense_profile.ast_rating
            allowed = defense_profile.ast_allowed
            league_avg = defense_profile.league_avg_ast
        
        # Calculate defense factor
        if league_avg > 0:
            analysis.defense_factor = allowed / league_avg
        
        if defense_rating == "elite":
            analysis.factors["defense_elite"] = WEIGHTS["defense_elite"]
            analysis.adjustments["defense_elite"] = ADJUSTMENTS["defense_elite"]
            analysis.reasons.append(
                f"🛡️ ELITE defense vs {player_stats.position}: {opponent_abbrev} allows only "
                f"{allowed:.1f} {prop_type}/48min (top 5)"
            )
        elif defense_rating == "good":
            analysis.factors["defense_good"] = WEIGHTS["defense_good"]
            analysis.adjustments["defense_good"] = ADJUSTMENTS["defense_good"]
            analysis.reasons.append(
                f"🛡️ Good defense vs {player_stats.position}: {opponent_abbrev} allows "
                f"{allowed:.1f} {prop_type}/48min (top 10)"
            )
        elif defense_rating == "average":
            analysis.factors["defense_average"] = WEIGHTS["defense_average"]
            analysis.adjustments["defense_average"] = ADJUSTMENTS["defense_average"]
            analysis.reasons.append(
                f"Defense vs {player_stats.position}: {opponent_abbrev} allows "
                f"{allowed:.1f} {prop_type}/48min (average)"
            )
        elif defense_rating in ("below_average", "poor"):
            # Bad defense = NOT a good under candidate
            analysis.warnings.append(
                f"⚠️ {opponent_abbrev} has WEAK defense vs {player_stats.position} "
                f"(allows {allowed:.1f} {prop_type}/48min)"
            )
    else:
        analysis.warnings.append("No defense vs position data available")
    
    # 2. COLD STREAK ANALYSIS
    if recent_avg > 0 and season_avg > 0:
        cold_ratio = recent_avg / season_avg
        
        if cold_ratio < 0.80:  # L5 avg is less than 80% of season
            analysis.factors["cold_streak_severe"] = WEIGHTS["cold_streak_severe"]
            analysis.adjustments["cold_streak_severe"] = ADJUSTMENTS["cold_streak_severe"]
            analysis.reasons.append(
                f"❄️ Severe cold streak: L5 avg ({recent_avg:.1f}) is {(1-cold_ratio)*100:.0f}% below "
                f"season avg ({season_avg:.1f})"
            )
        elif cold_ratio < 0.90:  # L5 avg is less than 90% of season
            analysis.factors["cold_streak_mild"] = WEIGHTS["cold_streak_mild"]
            analysis.adjustments["cold_streak_mild"] = ADJUSTMENTS["cold_streak_mild"]
            analysis.reasons.append(
                f"Cooling off: L5 avg ({recent_avg:.1f}) is below season avg ({season_avg:.1f})"
            )
    
    # 3. BACK-TO-BACK FATIGUE
    if b2b_info["is_b2b"]:
        analysis.factors["b2b_second"] = WEIGHTS["b2b_second"]
        analysis.adjustments["b2b_second"] = ADJUSTMENTS["b2b_second"]
        analysis.reasons.append("🔋 Back-to-back game fatigue")
    elif b2b_info["is_third_in_four"]:
        analysis.factors["b2b_third_in_four"] = WEIGHTS["b2b_third_in_four"]
        analysis.adjustments["b2b_third_in_four"] = ADJUSTMENTS["b2b_third_in_four"]
        analysis.reasons.append("🔋 Third game in four nights")
    
    # 4. HIGH VARIANCE (Inconsistent player)
    if variance > 0 and season_avg > 0:
        cv = variance / season_avg  # Coefficient of variation
        if cv > 0.35:  # High variance relative to mean
            analysis.factors["high_variance"] = WEIGHTS["high_variance"]
            analysis.adjustments["high_variance"] = ADJUSTMENTS["high_variance"]
            analysis.reasons.append(
                f"📊 High variance player (CV={cv:.2f}) - inconsistent performer"
            )
    
    # 5. HISTORICAL STRUGGLE VS OPPONENT
    if vs_opp_avg is not None and player_stats.vs_opp_games >= 2:
        if vs_opp_avg < season_avg * 0.85:
            analysis.factors["historical_struggle"] = WEIGHTS["historical_struggle"]
            analysis.adjustments["historical_struggle"] = ADJUSTMENTS["historical_struggle"]
            analysis.reasons.append(
                f"📉 Historical struggle vs {opponent_abbrev}: {vs_opp_avg:.1f} avg "
                f"({player_stats.vs_opp_games} games) vs {season_avg:.1f} season"
            )
    
    # 6. ELITE DEFENDER MATCHUP (only if defender is NOT injured)
    elite_defender = check_elite_defender_matchup(conn, opponent_abbrev, player_stats.position, game_date)
    if elite_defender:
        analysis.factors["elite_defender"] = WEIGHTS["elite_defender"]
        analysis.adjustments["elite_defender"] = ADJUSTMENTS["elite_defender"]
        analysis.reasons.append(
            f"🔒 Facing elite defender: {elite_defender} at {player_stats.position}"
        )
    
    # 7. AWAY PLAYER FACING STRONG HOME DEFENSE
    if not is_home and defense_profile.data_available:
        if defense_profile.pts_rating in ("elite", "good"):
            analysis.factors["home_disadvantage"] = WEIGHTS["home_disadvantage"]
            analysis.adjustments["home_disadvantage"] = ADJUSTMENTS["home_disadvantage"]
            analysis.reasons.append(
                f"🏠 Away player facing strong home defense"
            )
    
    # ==========================================================================
    # Calculate Final Projection and Confidence
    # ==========================================================================
    
    # Apply all adjustments
    total_adjustment = 1.0
    for adj in analysis.adjustments.values():
        total_adjustment *= adj
    
    analysis.adjustment_factor = total_adjustment
    analysis.projected = season_avg * total_adjustment
    
    # Calculate raw score from factor weights
    analysis.raw_score = sum(analysis.factors.values())
    
    # ===========================================================================
    # REVISED CONFIDENCE SCORING (calibrated to be more discriminating)
    # ===========================================================================
    # Max possible raw score from best factors:
    # - defense_elite (30) + cold_streak_severe (20) + b2b (8) + high_variance (6) 
    #   + historical_struggle (10) + elite_defender (10) + home_disadvantage (3) = 87
    # 
    # We want confidence to reflect actual predictive value:
    # - Premium picks (elite defense + cold streak) should be ~90-100
    # - Good picks (elite defense alone OR multiple factors) should be ~70-85
    # - Average picks (good defense + some factors) should be ~55-70
    # - Weak picks (single factor) should be < 55
    #
    # The formula maps raw_score to confidence:
    # - Raw 50+ (premium) -> 85-100
    # - Raw 30-49 (good) -> 65-84
    # - Raw 20-29 (average) -> 55-64
    # - Raw < 20 -> below threshold (filtered out)
    
    if analysis.raw_score >= 50:
        # Premium tier: Elite defense + cold streak + other factors
        # Map 50-100 raw to 85-100 confidence
        analysis.confidence_score = 85 + min(15, (analysis.raw_score - 50) * 0.3)
    elif analysis.raw_score >= 30:
        # Good tier: Elite defense alone OR good defense + cold streak
        # Map 30-49 raw to 65-84 confidence
        analysis.confidence_score = 65 + (analysis.raw_score - 30) * 1.0
    elif analysis.raw_score >= 20:
        # Average tier: Good defense + minor factors
        # Map 20-29 raw to 55-64 confidence
        analysis.confidence_score = 55 + (analysis.raw_score - 20) * 1.0
    else:
        # Weak tier - will be filtered out
        analysis.confidence_score = 40 + analysis.raw_score
    
    # Cap at 100
    analysis.confidence_score = min(100, analysis.confidence_score)
    
    # Determine tier based on REVISED thresholds
    if analysis.confidence_score >= 85:
        analysis.confidence_tier = "HIGH"
    elif analysis.confidence_score >= 65:
        analysis.confidence_tier = "MEDIUM"
    else:
        analysis.confidence_tier = "LOW"
    
    # ==========================================================================
    # ENHANCED FILTERING: Quality over Quantity
    # ==========================================================================
    # Based on backtesting:
    # - Elite defense + cold streak = 60.40% hit rate
    # - Elite defense alone = 56.81%
    # - We want to be MORE SELECTIVE for higher hit rates
    
    # Must have at least one negative factor
    if len(analysis.factors) == 0:
        return None
    
    # Must meet minimum confidence
    if analysis.confidence_score < MIN_CONFIDENCE_THRESHOLD:
        return None
    
    # QUALITY FILTER: Require ELITE defense OR multiple strong factors
    has_elite_defense = "defense_elite" in analysis.factors
    has_good_defense = "defense_good" in analysis.factors
    has_cold_streak = "cold_streak_severe" in analysis.factors or "cold_streak_mild" in analysis.factors
    has_injury_factor = any(k.startswith("injury_") for k in analysis.factors.keys())
    
    # Best combination: Elite defense + cold streak
    is_premium_pick = has_elite_defense and has_cold_streak
    
    # Good combination: Elite defense alone with high confidence
    is_good_pick = has_elite_defense and analysis.confidence_score >= 70
    
    # Acceptable: Good defense with cold streak severe
    is_acceptable_pick = has_good_defense and "cold_streak_severe" in analysis.factors
    
    # Alternative: Injury factor with defense support
    is_injury_pick = has_injury_factor and (has_elite_defense or has_good_defense)
    
    # Require at least one qualifying combination
    if not (is_premium_pick or is_good_pick or is_acceptable_pick or is_injury_pick):
        # For picks without premium factors, require much higher confidence
        if analysis.confidence_score < 80:
            return None
        # And must have at least 3 factors
        if len(analysis.factors) < 3:
            return None
    
    # Tag premium picks
    if is_premium_pick:
        analysis.reasons.insert(0, "⭐ PREMIUM: Elite Defense + Cold Streak")
    elif is_injury_pick:
        analysis.reasons.insert(0, "🩹 INJURY PLAY: Rust factor with defensive support")
    
    return analysis


# =============================================================================
# Main Entry Points
# =============================================================================

def generate_under_picks_v2(
    conn: sqlite3.Connection,
    away_abbrev: str,
    home_abbrev: str,
    game_date: str,
) -> UnderModelResult:
    """
    Generate UNDER picks for a matchup using the enhanced v2 model.
    
    Filters out players who are marked OUT in the injury report.
    """
    from ..standings import compute_player_averages_for_team
    
    result = UnderModelResult(
        game_date=game_date,
        status="ACTIVE",
    )
    
    # Get injured players for this date (batch query for efficiency)
    injured_players = get_injured_players_for_date(conn, game_date)
    
    # Check defense data availability
    defense_status = get_defense_vs_position_last_updated(conn)
    for pos in ["PG", "SG", "SF", "PF", "C"]:
        if pos in defense_status and defense_status[pos]:
            result.defense_data_available = True
            result.defense_data_freshness[pos] = defense_status[pos].get("last_updated", "unknown")
    
    if not result.defense_data_available:
        result.status = "LIMITED"
        result.message = "Defense vs position data not available"
        return result
    
    picks = []
    total_players = 0
    total_props = 0
    skipped_injured = 0
    
    # Analyze away team players (facing home defense)
    away_players = compute_player_averages_for_team(conn, away_abbrev)
    for player in away_players:
        avg_min = player.get("avg_min", 0) or 0
        if avg_min < 20:
            continue
        
        player_name = player.get("player")
        if not player_name:
            continue
        
        # Skip players who are marked OUT
        if player_name in injured_players:
            skipped_injured += 1
            continue
        
        player_row = conn.execute(
            "SELECT id FROM players WHERE name = ?", (player_name,)
        ).fetchone()
        if not player_row:
            continue
        
        player_id = player_row["id"]
        total_players += 1
        
        # Get comprehensive player stats
        player_stats = get_player_stats(
            conn, player_id, player_name, away_abbrev, home_abbrev, game_date
        )
        
        # Analyze each prop type
        for prop_type in ["PTS", "REB", "AST"]:
            total_props += 1
            
            analysis = analyze_under_candidate(
                conn=conn,
                player_stats=player_stats,
                opponent_abbrev=home_abbrev,
                game_date=game_date,
                prop_type=prop_type,
                is_home=False,
            )
            
            if analysis:
                picks.append(analysis)
    
    # Analyze home team players (facing away defense)
    home_players = compute_player_averages_for_team(conn, home_abbrev)
    for player in home_players:
        avg_min = player.get("avg_min", 0) or 0
        if avg_min < 20:
            continue
        
        player_name = player.get("player")
        if not player_name:
            continue
        
        # Skip players who are marked OUT
        if player_name in injured_players:
            skipped_injured += 1
            continue
        
        player_row = conn.execute(
            "SELECT id FROM players WHERE name = ?", (player_name,)
        ).fetchone()
        if not player_row:
            continue
        
        player_id = player_row["id"]
        total_players += 1
        
        # Get comprehensive player stats
        player_stats = get_player_stats(
            conn, player_id, player_name, home_abbrev, away_abbrev, game_date
        )
        
        # Analyze each prop type
        for prop_type in ["PTS", "REB", "AST"]:
            total_props += 1
            
            analysis = analyze_under_candidate(
                conn=conn,
                player_stats=player_stats,
                opponent_abbrev=away_abbrev,
                game_date=game_date,
                prop_type=prop_type,
                is_home=True,
            )
            
            if analysis:
                picks.append(analysis)
    
    # Sort by confidence score (highest first)
    picks.sort(key=lambda x: (x.confidence_score, x.factor_count), reverse=True)
    
    result.picks = picks
    result.total_players_analyzed = total_players
    result.total_props_analyzed = total_props
    result.picks_generated = len(picks)
    
    if picks:
        high_conf = sum(1 for p in picks if p.confidence_tier == "HIGH")
        result.message = f"Found {len(picks)} UNDER candidates ({high_conf} HIGH confidence, {skipped_injured} injured players excluded)"
    else:
        result.message = "No strong UNDER candidates found"
    
    return result


def backtest_under_model_v2(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    min_confidence: float = 60.0,
    confidence_tier: Optional[str] = None,
) -> Dict:
    """
    Comprehensive backtesting for the enhanced UNDER model.
    
    Args:
        conn: Database connection
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        min_confidence: Minimum confidence score to include
        confidence_tier: Filter to specific tier (HIGH, MEDIUM, LOW)
    
    Returns:
        Detailed backtest results
    """
    results = {
        "status": "COMPLETE",
        "start_date": start_date,
        "end_date": end_date,
        "min_confidence": min_confidence,
        "confidence_tier_filter": confidence_tier,
        
        # Overall stats
        "total_picks": 0,
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0,
        
        # By prop type
        "by_prop_type": {
            "PTS": {"picks": 0, "hits": 0, "hit_rate": 0.0, "avg_margin": 0.0},
            "REB": {"picks": 0, "hits": 0, "hit_rate": 0.0, "avg_margin": 0.0},
            "AST": {"picks": 0, "hits": 0, "hit_rate": 0.0, "avg_margin": 0.0},
        },
        
        # By confidence tier
        "by_confidence_tier": {
            "HIGH": {"picks": 0, "hits": 0, "hit_rate": 0.0},
            "MEDIUM": {"picks": 0, "hits": 0, "hit_rate": 0.0},
            "LOW": {"picks": 0, "hits": 0, "hit_rate": 0.0},
        },
        
        # By defense rating
        "by_defense_rating": {
            "elite": {"picks": 0, "hits": 0, "hit_rate": 0.0},
            "good": {"picks": 0, "hits": 0, "hit_rate": 0.0},
            "average": {"picks": 0, "hits": 0, "hit_rate": 0.0},
        },
        
        # Detailed picks
        "picks": [],
        
        # Factor analysis
        "factor_effectiveness": {},
    }
    
    # Get all games in date range
    games = conn.execute(
        """
        SELECT g.id, g.game_date, t1.name AS team1, t2.name AS team2
        FROM games g
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        WHERE g.game_date BETWEEN ? AND ?
        ORDER BY g.game_date ASC
        """,
        (start_date, end_date),
    ).fetchall()
    
    all_margins = {"PTS": [], "REB": [], "AST": []}
    factor_hits = {}
    factor_total = {}
    
    for game in games:
        game_date = game["game_date"]
        team1_abbrev = abbrev_from_team_name(game["team1"])
        team2_abbrev = abbrev_from_team_name(game["team2"])
        
        if not team1_abbrev or not team2_abbrev:
            continue
        
        # Generate under picks for this game
        model_result = generate_under_picks_v2(conn, team1_abbrev, team2_abbrev, game_date)
        
        for analysis in model_result.picks:
            # Apply filters
            if analysis.confidence_score < min_confidence:
                continue
            if confidence_tier and analysis.confidence_tier != confidence_tier:
                continue
            
            # Get actual result from boxscore
            stat_column = analysis.prop_type.lower()
            actual = conn.execute(
                f"""
                SELECT b.{stat_column}
                FROM boxscore_player b
                JOIN games g ON g.id = b.game_id
                WHERE b.player_id = ?
                  AND g.game_date = ?
                """,
                (analysis.player_id, game_date),
            ).fetchone()
            
            if not actual or actual[stat_column] is None:
                continue
            
            actual_value = actual[stat_column]
            
            # Determine if UNDER hit (actual < season average)
            hit = actual_value < analysis.season_avg
            margin = analysis.season_avg - actual_value
            
            # Update overall stats
            results["total_picks"] += 1
            results["by_prop_type"][analysis.prop_type]["picks"] += 1
            results["by_confidence_tier"][analysis.confidence_tier]["picks"] += 1
            
            all_margins[analysis.prop_type].append(margin)
            
            if hit:
                results["hits"] += 1
                results["by_prop_type"][analysis.prop_type]["hits"] += 1
                results["by_confidence_tier"][analysis.confidence_tier]["hits"] += 1
            else:
                results["misses"] += 1
            
            # Track factor effectiveness
            for factor_name in analysis.factors.keys():
                if factor_name not in factor_total:
                    factor_total[factor_name] = 0
                    factor_hits[factor_name] = 0
                factor_total[factor_name] += 1
                if hit:
                    factor_hits[factor_name] += 1
            
            # Track by defense rating
            if analysis.defense_profile and analysis.defense_profile.data_available:
                if analysis.prop_type == "PTS":
                    rating = analysis.defense_profile.pts_rating
                elif analysis.prop_type == "REB":
                    rating = analysis.defense_profile.reb_rating
                else:
                    rating = analysis.defense_profile.ast_rating
                
                if rating in results["by_defense_rating"]:
                    results["by_defense_rating"][rating]["picks"] += 1
                    if hit:
                        results["by_defense_rating"][rating]["hits"] += 1
            
            # Store pick details
            results["picks"].append({
                "game_date": game_date,
                "player": analysis.player_name,
                "team": analysis.team_abbrev,
                "opponent": analysis.opponent_abbrev,
                "position": analysis.position,
                "prop_type": analysis.prop_type,
                "season_avg": round(analysis.season_avg, 1),
                "projected": round(analysis.projected, 1),
                "actual": actual_value,
                "margin": round(margin, 1),
                "hit": hit,
                "confidence": analysis.confidence_score,
                "tier": analysis.confidence_tier,
                "factors": list(analysis.factors.keys()),
                "reasons": analysis.reasons[:3],
            })
    
    # Calculate rates
    if results["total_picks"] > 0:
        results["hit_rate"] = results["hits"] / results["total_picks"]
    
    for prop_type in results["by_prop_type"]:
        data = results["by_prop_type"][prop_type]
        if data["picks"] > 0:
            data["hit_rate"] = data["hits"] / data["picks"]
            if all_margins[prop_type]:
                data["avg_margin"] = sum(all_margins[prop_type]) / len(all_margins[prop_type])
    
    for tier in results["by_confidence_tier"]:
        data = results["by_confidence_tier"][tier]
        if data["picks"] > 0:
            data["hit_rate"] = data["hits"] / data["picks"]
    
    for rating in results["by_defense_rating"]:
        data = results["by_defense_rating"][rating]
        if data["picks"] > 0:
            data["hit_rate"] = data["hits"] / data["picks"]
    
    # Calculate factor effectiveness
    for factor_name in factor_total:
        total = factor_total[factor_name]
        hits = factor_hits[factor_name]
        results["factor_effectiveness"][factor_name] = {
            "picks": total,
            "hits": hits,
            "hit_rate": hits / total if total > 0 else 0.0,
        }
    
    return results


def get_top_under_picks_v2(
    conn: sqlite3.Connection,
    game_date: str,
    max_picks: int = 10,
    min_confidence: float = 60.0,
) -> List[UnderAnalysis]:
    """
    Get the top UNDER picks across all games for a given date.
    Works for both future dates (scheduled_games) and past dates (games).
    """
    all_picks = []
    
    # Try scheduled games first (for future dates)
    games = conn.execute(
        """
        SELECT sg.away_team_id, sg.home_team_id, 
               t1.name AS away_team, t2.name AS home_team
        FROM scheduled_games sg
        JOIN teams t1 ON t1.id = sg.away_team_id
        JOIN teams t2 ON t2.id = sg.home_team_id
        WHERE sg.game_date = ?
        """,
        (game_date,),
    ).fetchall()
    
    # If no scheduled games, try historical games table
    if not games:
        games = conn.execute(
            """
            SELECT t1.name AS away_team, t2.name AS home_team
            FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            WHERE g.game_date = ?
            """,
            (game_date,),
        ).fetchall()
    
    for game in games:
        away_abbrev = abbrev_from_team_name(game["away_team"])
        home_abbrev = abbrev_from_team_name(game["home_team"])
        
        if not away_abbrev or not home_abbrev:
            continue
        
        result = generate_under_picks_v2(conn, away_abbrev, home_abbrev, game_date)
        all_picks.extend(result.picks)
    
    # Filter by minimum confidence
    all_picks = [p for p in all_picks if p.confidence_score >= min_confidence]
    
    # Sort by confidence
    all_picks.sort(key=lambda x: x.confidence_score, reverse=True)
    
    return all_picks[:max_picks]


# =============================================================================
# Utility Functions for Web Integration
# =============================================================================

def format_under_pick_for_display(analysis: UnderAnalysis) -> Dict:
    """Format an UnderAnalysis for web display."""
    return {
        "player_name": analysis.player_name,
        "team": analysis.team_abbrev,
        "opponent": analysis.opponent_abbrev,
        "position": analysis.position,
        "prop_type": analysis.prop_type,
        "direction": "UNDER",
        "season_avg": round(analysis.season_avg, 1),
        "recent_avg": round(analysis.recent_avg, 1),
        "projected": round(analysis.projected, 1),
        "adjustment": f"{(1 - analysis.adjustment_factor) * 100:.0f}% reduction",
        "confidence_score": round(analysis.confidence_score),
        "confidence_tier": analysis.confidence_tier,
        "factor_count": analysis.factor_count,
        "reasons": analysis.reasons,
        "warnings": analysis.warnings,
        "is_home": analysis.is_home,
        "is_b2b": analysis.is_b2b,
    }

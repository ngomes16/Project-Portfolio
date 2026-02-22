"""
UNDER Picks Model - Separate Analysis Module
============================================

This module is SEPARATE from the main pick generation model.
The main model focuses on OVER picks which historically have a ~65-75% pass rate.

This UNDER picks model uses defense vs position data from Hashtag Basketball
to identify strong UNDER candidates based on:
1. Elite defense at opponent's position (primary factor)
2. Player on B2B with fatigue
3. Cold shooting streaks
4. Elite defender assignments
5. Historically poor performance vs opponent
6. Recent injury returns (rust factor)

Key Integration: Defense vs Position Data
=========================================
The defense vs position data provides:
- How each team defends against each position (PG, SG, SF, PF, C)
- Stats allowed: PTS, REB, AST, FG%, 3PM, etc.
- Rankings: 1-30 for each stat (1 = best defense)

For UNDER picks, we target:
- Players facing teams with TOP 10 defense at their position
- Multiple negative factors combining

Module Author: NBA Props Team
Last Updated: January 2026
Status: ACTIVE - Using defense vs position data
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timedelta

from ..team_aliases import normalize_team_abbrev
from ..standings import _team_ids_by_abbrev
from ..ingest.defense_position_parser import (
    calculate_defense_factor,
    get_defense_vs_position,
    get_defense_vs_position_last_updated,
)


@dataclass
class DefenseMatchupAnalysis:
    """Analysis of how a player's position matches up against opponent defense."""
    position: str
    opponent_abbrev: str
    
    # Points analysis
    pts_factor: float = 1.0
    pts_rank: int = 15  # 1-30, lower is better defense
    pts_allowed: float = 0.0
    pts_rating: str = "average"
    
    # Rebounds analysis
    reb_factor: float = 1.0
    reb_rank: int = 15
    reb_allowed: float = 0.0
    reb_rating: str = "average"
    
    # Assists analysis
    ast_factor: float = 1.0
    ast_rank: int = 15
    ast_allowed: float = 0.0
    ast_rating: str = "average"
    
    # Data freshness
    data_available: bool = False
    data_age_days: int = 999


@dataclass
class UnderCandidate:
    """A candidate for an UNDER pick."""
    player_name: str
    player_id: int
    team_abbrev: str
    opponent_abbrev: str
    position: str
    prop_type: str  # PTS, REB, AST
    
    # Values
    season_avg: float
    recent_avg: float  # L5 games
    projected: float
    
    # Defense matchup analysis
    defense_matchup: Optional[DefenseMatchupAnalysis] = None
    
    # Factors that favor UNDER
    factors: dict = field(default_factory=dict)
    
    # Confidence
    confidence_score: float = 50.0
    confidence_tier: str = "LOW"
    
    # Reasoning
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    @property
    def factor_count(self) -> int:
        """Count of negative factors supporting UNDER."""
        return len([f for f in self.factors.values() if f < 1.0])
    
    @property
    def combined_factor(self) -> float:
        """Combined factor from all adjustments."""
        result = 1.0
        for f in self.factors.values():
            result *= f
        return result


@dataclass
class UndersModelResult:
    """Results from the UNDER picks model."""
    game_date: str
    status: str = "ACTIVE"
    message: str = ""
    
    candidates: List[UnderCandidate] = field(default_factory=list)
    
    # Stats for tracking
    total_analyzed: int = 0
    passed_threshold: int = 0
    
    # Data status
    defense_data_available: bool = False
    defense_data_positions: List[str] = field(default_factory=list)


# ============================================================================
# Position Mapping
# ============================================================================

def _map_position(pos: str) -> str:
    """
    Map various position formats to standard positions for defense lookup.
    
    Standard positions: PG, SG, SF, PF, C
    """
    if not pos:
        return "SF"  # Default to SF
    
    pos = pos.upper().strip()
    
    # Direct match
    if pos in ("PG", "SG", "SF", "PF", "C"):
        return pos
    
    # Common mappings
    position_map = {
        "G": "PG",      # Guard -> Point Guard
        "F": "SF",      # Forward -> Small Forward
        "G-F": "SG",    # Guard-Forward -> Shooting Guard
        "F-G": "SF",    # Forward-Guard -> Small Forward
        "F-C": "PF",    # Forward-Center -> Power Forward
        "C-F": "PF",    # Center-Forward -> Power Forward
        "GUARD": "PG",
        "FORWARD": "SF",
        "CENTER": "C",
        "PG/SG": "PG",
        "SG/SF": "SG",
        "SF/PF": "SF",
        "PF/C": "PF",
    }
    
    return position_map.get(pos, "SF")


# ============================================================================
# Defense vs Position Analysis
# ============================================================================

def get_defense_matchup_analysis(
    conn: sqlite3.Connection,
    opponent_abbrev: str,
    player_position: str,
) -> DefenseMatchupAnalysis:
    """
    Analyze how an opponent defends against a specific position.
    
    Args:
        conn: Database connection
        opponent_abbrev: Opponent team abbreviation
        player_position: Player's position (PG, SG, SF, PF, C)
    
    Returns:
        DefenseMatchupAnalysis with factors and ratings
    """
    analysis = DefenseMatchupAnalysis(
        position=player_position,
        opponent_abbrev=opponent_abbrev,
    )
    
    # Get factors for each stat type
    pts_data = calculate_defense_factor(conn, opponent_abbrev, player_position, "pts")
    reb_data = calculate_defense_factor(conn, opponent_abbrev, player_position, "reb")
    ast_data = calculate_defense_factor(conn, opponent_abbrev, player_position, "ast")
    
    if pts_data:
        analysis.data_available = True
        analysis.pts_factor = pts_data["factor"]
        analysis.pts_rank = pts_data["rank"]
        analysis.pts_allowed = pts_data["allowed"]
        analysis.pts_rating = pts_data["rating"]
    
    if reb_data:
        analysis.reb_factor = reb_data["factor"]
        analysis.reb_rank = reb_data["rank"]
        analysis.reb_allowed = reb_data["allowed"]
        analysis.reb_rating = reb_data["rating"]
    
    if ast_data:
        analysis.ast_factor = ast_data["factor"]
        analysis.ast_rank = ast_data["rank"]
        analysis.ast_allowed = ast_data["allowed"]
        analysis.ast_rating = ast_data["rating"]
    
    # Check data freshness
    last_updated = get_defense_vs_position_last_updated(conn)
    if player_position in last_updated and last_updated[player_position]:
        try:
            last_dt = datetime.fromisoformat(last_updated[player_position]["last_updated"].replace("Z", "+00:00"))
            analysis.data_age_days = (datetime.now() - last_dt.replace(tzinfo=None)).days
        except:
            pass
    
    return analysis


def _map_position_to_defense_position(position: str) -> str:
    """
    Map player positions to defense vs position categories.
    
    Some players have positions like "G" (guard) or "F" (forward).
    We need to map these to specific positions for the defense data.
    """
    if not position:
        return "SF"  # Default
    
    pos = position.upper().strip()
    
    # Direct matches
    if pos in ["PG", "SG", "SF", "PF", "C"]:
        return pos
    
    # General positions
    if pos == "G":
        return "PG"  # Default guards to PG
    if pos == "F":
        return "SF"  # Default forwards to SF
    if pos == "F-C" or pos == "C-F":
        return "PF"  # Tweener forwards/centers
    if pos == "G-F" or pos == "F-G":
        return "SG"  # Tweener guards/forwards
    
    # Height-based guesses (fallback)
    return "SF"  # Default


# ============================================================================
# UNDER Pick Analysis
# ============================================================================

def analyze_under_candidate(
    conn: sqlite3.Connection,
    player_id: int,
    player_name: str,
    team_abbrev: str,
    opponent_abbrev: str,
    position: str,
    prop_type: str,
    season_avg: float,
    recent_avg: float,
    is_b2b: bool = False,
    games_since_injury: Optional[int] = None,
) -> Optional[UnderCandidate]:
    """
    Analyze a player for potential UNDER pick.
    
    UNDER factors considered:
    1. Elite defense at opponent's position (from defense vs position data)
    2. Back-to-back fatigue
    3. Cold shooting streak
    4. Historical underperformance vs opponent
    5. Recent injury return (rust factor)
    
    Args:
        conn: Database connection
        player_id: Player ID
        player_name: Player name
        team_abbrev: Player's team abbreviation
        opponent_abbrev: Opponent team abbreviation
        position: Player's position
        prop_type: Prop type (PTS, REB, AST)
        season_avg: Season average for this stat
        recent_avg: Recent (L5) average for this stat
        is_b2b: Whether team is on back-to-back
        games_since_injury: Number of games since returning from injury (None if not applicable)
    
    Returns:
        UnderCandidate if factors support UNDER, None otherwise
    """
    factors = {}
    reasons = []
    warnings = []
    
    # Map position to defense position
    defense_position = _map_position_to_defense_position(position)
    
    # Start with neutral projection
    projected = season_avg
    
    # Get defense matchup analysis
    defense_matchup = get_defense_matchup_analysis(conn, opponent_abbrev, defense_position)
    
    # Factor 1: Defense vs Position Analysis (PRIMARY FACTOR)
    if defense_matchup.data_available:
        if prop_type == "PTS":
            factor = defense_matchup.pts_factor
            rank = defense_matchup.pts_rank
            rating = defense_matchup.pts_rating
            allowed = defense_matchup.pts_allowed
        elif prop_type == "REB":
            factor = defense_matchup.reb_factor
            rank = defense_matchup.reb_rank
            rating = defense_matchup.reb_rating
            allowed = defense_matchup.reb_allowed
        elif prop_type == "AST":
            factor = defense_matchup.ast_factor
            rank = defense_matchup.ast_rank
            rating = defense_matchup.ast_rating
            allowed = defense_matchup.ast_allowed
        else:
            factor = 1.0
            rank = 15
            rating = "average"
            allowed = 0
        
        # Apply defense factor
        if factor < 1.0:  # Team allows LESS than average
            factors["defense_vs_position"] = factor
            projected *= factor
            
            if rating == "elite":
                reasons.append(f"🛡️ ELITE defense vs {defense_position}: {opponent_abbrev} allows only {allowed:.1f} {prop_type} (#{rank})")
            elif rating == "good":
                reasons.append(f"🛡️ Good defense vs {defense_position}: {opponent_abbrev} allows {allowed:.1f} {prop_type} (#{rank})")
            else:
                reasons.append(f"Defense vs {defense_position}: {opponent_abbrev} allows {allowed:.1f} {prop_type} (factor: {factor:.2f})")
        elif factor > 1.05:
            # Defense is BAD - not a good UNDER candidate
            warnings.append(f"⚠️ {opponent_abbrev} is weak vs {defense_position} (allows +{(factor-1)*100:.0f}% more {prop_type})")
    else:
        warnings.append("No defense vs position data available")
    
    # Factor 2: Back-to-Back Fatigue
    if is_b2b:
        b2b_factor = 0.95  # 5% reduction on B2B
        factors["b2b_fatigue"] = b2b_factor
        projected *= b2b_factor
        reasons.append("🔋 Back-to-back game fatigue (-5%)")
    
    # Factor 3: Cold Streak Detection
    if recent_avg < season_avg * 0.85:  # 15% below season average
        cold_factor = 0.93  # 7% reduction for cold streak
        factors["cold_streak"] = cold_factor
        projected *= cold_factor
        reasons.append(f"❄️ Cold streak: L5 avg ({recent_avg:.1f}) well below season ({season_avg:.1f})")
    elif recent_avg < season_avg * 0.92:  # Slight cold
        cold_factor = 0.97
        factors["cold_streak"] = cold_factor
        projected *= cold_factor
        reasons.append(f"Cooling down: L5 avg ({recent_avg:.1f}) below season ({season_avg:.1f})")
    
    # Factor 4: Historical vs Opponent
    history = _get_player_history_vs_opponent(conn, player_id, opponent_abbrev, prop_type)
    if history:
        avg_vs_opp, games_count = history
        if games_count >= 2 and avg_vs_opp < season_avg * 0.90:
            hist_factor = 0.95
            factors["historical_vs_opp"] = hist_factor
            projected *= hist_factor
            reasons.append(f"📉 Historical struggle vs {opponent_abbrev}: {avg_vs_opp:.1f} avg ({games_count} games)")
    
    # Factor 5: Injury Return Rust
    if games_since_injury is not None and games_since_injury <= 3:
        if games_since_injury == 1:
            rust_factor = 0.88  # First game back
            reasons.append("🩹 First game back from injury (rust factor)")
        elif games_since_injury == 2:
            rust_factor = 0.93
            reasons.append("🩹 Second game back from injury")
        else:
            rust_factor = 0.96
            reasons.append("🩹 Third game back from injury")
        factors["injury_rust"] = rust_factor
        projected *= rust_factor
    
    # Calculate negative factor count
    negative_factors = sum(1 for f in factors.values() if f < 1.0)
    
    # Calculate confidence based on factors
    confidence_score = 50.0
    
    # Defense vs position is the most important factor
    if "defense_vs_position" in factors:
        if defense_matchup.data_available:
            # Get the relevant rank
            if prop_type == "PTS":
                rank = defense_matchup.pts_rank
            elif prop_type == "REB":
                rank = defense_matchup.reb_rank
            elif prop_type == "AST":
                rank = defense_matchup.ast_rank
            else:
                rank = 15
            
            # Top 5 defense at position = +20 confidence
            # Top 10 = +15
            # Top 15 = +10
            if rank <= 5:
                confidence_score += 20
            elif rank <= 10:
                confidence_score += 15
            elif rank <= 15:
                confidence_score += 10
    
    # Additional factors add confidence
    if "cold_streak" in factors:
        confidence_score += 10
    if "b2b_fatigue" in factors:
        confidence_score += 8
    if "historical_vs_opp" in factors:
        confidence_score += 7
    if "injury_rust" in factors:
        confidence_score += 12  # Injury rust is a strong signal
    
    # Require at least 60 confidence for UNDER picks
    if confidence_score < 60:
        return None
    
    # Determine tier
    if confidence_score >= 80:
        confidence_tier = "HIGH"
    elif confidence_score >= 70:
        confidence_tier = "MEDIUM"
    else:
        confidence_tier = "LOW"
    
    # Only proceed if we have meaningful negative factors
    if negative_factors < 1:
        return None
    
    return UnderCandidate(
        player_name=player_name,
        player_id=player_id,
        team_abbrev=team_abbrev,
        opponent_abbrev=opponent_abbrev,
        position=position,
        prop_type=prop_type,
        season_avg=season_avg,
        recent_avg=recent_avg,
        projected=projected,
        defense_matchup=defense_matchup,
        factors=factors,
        confidence_score=confidence_score,
        confidence_tier=confidence_tier,
        reasons=reasons,
        warnings=warnings,
    )


def _get_player_history_vs_opponent(
    conn: sqlite3.Connection,
    player_id: int,
    opponent_abbrev: str,
    prop_type: str,
) -> Optional[tuple]:
    """
    Get player's historical performance against a specific opponent.
    
    Returns:
        Tuple of (avg_value, game_count) or None if insufficient data
    """
    stat_column = prop_type.lower()  # pts, reb, ast
    
    try:
        rows = conn.execute(
            f"""
            SELECT b.{stat_column}
            FROM boxscore_player b
            JOIN games g ON g.id = b.game_id
            JOIN teams opp ON (opp.id = g.team1_id OR opp.id = g.team2_id)
            WHERE b.player_id = ?
              AND opp.id != b.team_id
              AND b.{stat_column} IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM teams t WHERE t.name LIKE ? AND t.id = opp.id
              )
            ORDER BY g.game_date DESC
            LIMIT 10
            """,
            (player_id, f"%{opponent_abbrev}%"),
        ).fetchall()
        
        if not rows or len(rows) < 2:
            return None
        
        values = [r[stat_column] for r in rows if r[stat_column] is not None]
        if not values:
            return None
        
        return (sum(values) / len(values), len(values))
    except:
        return None


# ============================================================================
# Generate UNDER Picks for a Matchup
# ============================================================================

def generate_under_picks(
    conn: sqlite3.Connection,
    away_abbrev: str,
    home_abbrev: str,
    game_date: str,
) -> UndersModelResult:
    """
    Generate UNDER pick candidates for a matchup.
    
    Analyzes both teams' players and identifies strong UNDER candidates
    based on defense vs position data and other factors.
    
    Args:
        conn: Database connection
        away_abbrev: Away team abbreviation
        home_abbrev: Home team abbreviation
        game_date: Game date (YYYY-MM-DD)
    
    Returns:
        UndersModelResult with candidates and analysis
    """
    from ..engine.game_context import get_back_to_back_status
    from ..standings import compute_player_averages_for_team
    from ..team_aliases import team_name_from_abbrev
    
    result = UndersModelResult(
        game_date=game_date,
        status="ACTIVE",
        message="",
    )
    
    # Check defense data availability
    defense_status = get_defense_vs_position_last_updated(conn)
    for pos in ["PG", "SG", "SF", "PF", "C"]:
        if pos in defense_status and defense_status[pos]:
            result.defense_data_available = True
            result.defense_data_positions.append(pos)
    
    if not result.defense_data_available:
        result.status = "LIMITED"
        result.message = "Defense vs position data not available. Import data in Data Management."
        return result
    
    candidates = []
    total_analyzed = 0
    
    # Get B2B status for both teams
    try:
        away_b2b = get_back_to_back_status(conn, away_abbrev, game_date).get("is_second_of_b2b", False)
    except:
        away_b2b = False
    
    try:
        home_b2b = get_back_to_back_status(conn, home_abbrev, game_date).get("is_second_of_b2b", False)
    except:
        home_b2b = False
    
    # Analyze away team players (facing home defense)
    away_players = compute_player_averages_for_team(conn, away_abbrev)
    for player in away_players:
        total_analyzed += 1
        
        # Get minutes from the correct key
        avg_min = player.get("avg_min", 0) or 0
        if avg_min < 20:
            continue
        
        # Get player_id by looking up by name
        player_name = player.get("player")
        if not player_name:
            continue
        
        player_row = conn.execute(
            "SELECT id FROM players WHERE name = ?", (player_name,)
        ).fetchone()
        if not player_row:
            continue
        player_id = player_row["id"]
        
        # Map position codes to standard positions
        pos = player.get("pos", "") or ""
        position = _map_position(pos)
        
        # Analyze for each prop type
        for prop_type in ["PTS", "REB", "AST"]:
            stat_key = f"avg_{prop_type.lower()}"
            season_avg = player.get(stat_key, 0) or 0
            
            if season_avg < 5:  # Skip low-volume stats
                continue
            
            # Get recent average (L5)
            recent_avg = _get_recent_avg(conn, player_id, prop_type, 5)
            if recent_avg is None:
                recent_avg = season_avg
            
            candidate = analyze_under_candidate(
                conn=conn,
                player_id=player_id,
                player_name=player_name,
                team_abbrev=away_abbrev,
                opponent_abbrev=home_abbrev,
                position=position,
                prop_type=prop_type,
                season_avg=season_avg,
                recent_avg=recent_avg,
                is_b2b=away_b2b,
            )
            
            if candidate:
                candidates.append(candidate)
    
    # Analyze home team players (facing away defense)
    home_players = compute_player_averages_for_team(conn, home_abbrev)
    for player in home_players:
        total_analyzed += 1
        
        # Get minutes from the correct key
        avg_min = player.get("avg_min", 0) or 0
        if avg_min < 20:
            continue
        
        # Get player_id by looking up by name
        player_name = player.get("player")
        if not player_name:
            continue
        
        player_row = conn.execute(
            "SELECT id FROM players WHERE name = ?", (player_name,)
        ).fetchone()
        if not player_row:
            continue
        player_id = player_row["id"]
        
        # Map position codes to standard positions
        pos = player.get("pos", "") or ""
        position = _map_position(pos)
        
        # Analyze for each prop type
        for prop_type in ["PTS", "REB", "AST"]:
            stat_key = f"avg_{prop_type.lower()}"
            season_avg = player.get(stat_key, 0) or 0
            
            if season_avg < 5:  # Skip low-volume stats
                continue
            
            # Get recent average (L5)
            recent_avg = _get_recent_avg(conn, player_id, prop_type, 5)
            if recent_avg is None:
                recent_avg = season_avg
            
            candidate = analyze_under_candidate(
                conn=conn,
                player_id=player_id,
                player_name=player_name,
                team_abbrev=home_abbrev,
                opponent_abbrev=away_abbrev,
                position=position,
                prop_type=prop_type,
                season_avg=season_avg,
                recent_avg=recent_avg,
                is_b2b=home_b2b,
            )
            
            if candidate:
                candidates.append(candidate)
    
    # Sort by confidence score
    candidates.sort(key=lambda x: x.confidence_score, reverse=True)
    
    result.candidates = candidates
    result.total_analyzed = total_analyzed
    result.passed_threshold = len(candidates)
    
    if candidates:
        result.message = f"Found {len(candidates)} UNDER candidates based on defense matchups"
    else:
        result.message = "No strong UNDER candidates found for this matchup"
    
    return result


def _get_recent_avg(
    conn: sqlite3.Connection,
    player_id: int,
    prop_type: str,
    games: int = 5,
) -> Optional[float]:
    """Get player's recent average for a stat type."""
    stat_column = prop_type.lower()
    
    try:
        rows = conn.execute(
            f"""
            SELECT b.{stat_column}
            FROM boxscore_player b
            JOIN games g ON g.id = b.game_id
            WHERE b.player_id = ?
              AND b.{stat_column} IS NOT NULL
            ORDER BY g.game_date DESC
            LIMIT ?
            """,
            (player_id, games),
        ).fetchall()
        
        if not rows:
            return None
        
        values = [r[stat_column] for r in rows if r[stat_column] is not None]
        if not values:
            return None
        
        return sum(values) / len(values)
    except:
        return None


# ============================================================================
# Backtesting for UNDER Model
# ============================================================================

def backtest_under_model(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    min_confidence: float = 65.0,
) -> dict:
    """
    Backtest the UNDER picks model against historical data.
    
    This runs the model on past games and compares predictions to actual results.
    
    Args:
        conn: Database connection
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        min_confidence: Minimum confidence score to include
    
    Returns:
        Dictionary with backtest results including hit rate, by prop type, etc.
    """
    from datetime import datetime, timedelta
    from ..team_aliases import abbrev_from_team_name
    
    results = {
        "status": "COMPLETE",
        "start_date": start_date,
        "end_date": end_date,
        "min_confidence": min_confidence,
        "total_picks": 0,
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0,
        "by_prop_type": {},
        "by_confidence_tier": {},
        "picks": [],
    }
    
    # Initialize counters
    for prop_type in ["PTS", "REB", "AST"]:
        results["by_prop_type"][prop_type] = {"picks": 0, "hits": 0}
    for tier in ["HIGH", "MEDIUM", "LOW"]:
        results["by_confidence_tier"][tier] = {"picks": 0, "hits": 0}
    
    # Get games in date range
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
    
    for game in games:
        game_date = game["game_date"]
        team1_abbrev = abbrev_from_team_name(game["team1"])
        team2_abbrev = abbrev_from_team_name(game["team2"])
        
        if not team1_abbrev or not team2_abbrev:
            continue
        
        # Generate under picks for this game
        under_result = generate_under_picks(conn, team1_abbrev, team2_abbrev, game_date)
        
        for candidate in under_result.candidates:
            if candidate.confidence_score < min_confidence:
                continue
            
            # Get actual result from boxscore
            stat_column = candidate.prop_type.lower()
            actual = conn.execute(
                f"""
                SELECT b.{stat_column}
                FROM boxscore_player b
                JOIN games g ON g.id = b.game_id
                WHERE b.player_id = ?
                  AND g.game_date = ?
                """,
                (candidate.player_id, game_date),
            ).fetchone()
            
            if not actual or actual[stat_column] is None:
                continue
            
            actual_value = actual[stat_column]
            
            # Determine if UNDER hit
            # For UNDER to hit, actual must be LESS than the season average
            # (This simulates betting the under on their average line)
            hit = actual_value < candidate.season_avg
            
            results["total_picks"] += 1
            results["by_prop_type"][candidate.prop_type]["picks"] += 1
            results["by_confidence_tier"][candidate.confidence_tier]["picks"] += 1
            
            if hit:
                results["hits"] += 1
                results["by_prop_type"][candidate.prop_type]["hits"] += 1
                results["by_confidence_tier"][candidate.confidence_tier]["hits"] += 1
            else:
                results["misses"] += 1
            
            results["picks"].append({
                "game_date": game_date,
                "player": candidate.player_name,
                "team": candidate.team_abbrev,
                "opponent": candidate.opponent_abbrev,
                "prop_type": candidate.prop_type,
                "projected": round(candidate.projected, 1),
                "season_avg": round(candidate.season_avg, 1),
                "actual": actual_value,
                "hit": hit,
                "confidence": candidate.confidence_score,
                "tier": candidate.confidence_tier,
                "reasons": candidate.reasons[:2],  # Top 2 reasons
            })
    
    # Calculate rates
    if results["total_picks"] > 0:
        results["hit_rate"] = results["hits"] / results["total_picks"]
    
    for prop_type in results["by_prop_type"]:
        picks = results["by_prop_type"][prop_type]["picks"]
        if picks > 0:
            results["by_prop_type"][prop_type]["hit_rate"] = (
                results["by_prop_type"][prop_type]["hits"] / picks
            )
        else:
            results["by_prop_type"][prop_type]["hit_rate"] = 0.0
    
    for tier in results["by_confidence_tier"]:
        picks = results["by_confidence_tier"][tier]["picks"]
        if picks > 0:
            results["by_confidence_tier"][tier]["hit_rate"] = (
                results["by_confidence_tier"][tier]["hits"] / picks
            )
        else:
            results["by_confidence_tier"][tier]["hit_rate"] = 0.0
    
    return results


def get_top_under_picks_for_date(
    conn: sqlite3.Connection,
    game_date: str,
    max_picks: int = 10,
) -> List[UnderCandidate]:
    """
    Get the top UNDER picks across all games for a given date.
    
    Args:
        conn: Database connection
        game_date: Game date (YYYY-MM-DD)
        max_picks: Maximum number of picks to return
    
    Returns:
        List of top UnderCandidate objects sorted by confidence
    """
    from ..team_aliases import abbrev_from_team_name
    
    all_candidates = []
    
    # Get scheduled games for this date
    games = conn.execute(
        """
        SELECT sg.away_team_id, sg.home_team_id, t1.name AS away_team, t2.name AS home_team
        FROM scheduled_games sg
        JOIN teams t1 ON t1.id = sg.away_team_id
        JOIN teams t2 ON t2.id = sg.home_team_id
        WHERE sg.game_date = ?
        """,
        (game_date,),
    ).fetchall()
    
    for game in games:
        away_abbrev = abbrev_from_team_name(game["away_team"])
        home_abbrev = abbrev_from_team_name(game["home_team"])
        
        if not away_abbrev or not home_abbrev:
            continue
        
        # Generate under picks for this game
        under_result = generate_under_picks(conn, away_abbrev, home_abbrev, game_date)
        all_candidates.extend(under_result.candidates)
    
    # Sort by confidence and return top picks
    all_candidates.sort(key=lambda x: x.confidence_score, reverse=True)
    
    return all_candidates[:max_picks]

"""
Pick Generation Module - Ensemble Model
========================================

Generates and selects picks using the ensemble projection engine
and multi-factor confidence scoring system.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict

from .config import ModelV7Config, DEFAULT_CONFIG
from .projector import (
    EnsembleProjection, 
    PlayerStats,
    project_all_props, 
    load_player_stats,
    get_player_archetype,
)
from .confidence import ConfidenceBreakdown, calculate_confidence
from ...db import Db
from ...paths import get_paths
from ...team_aliases import abbrev_from_team_name, normalize_team_abbrev


@dataclass
class PropPick:
    """A single prop bet recommendation."""
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
    line: float                 # Line (based on recent average)
    edge_pct: float             # Edge percentage
    
    # Confidence
    confidence_score: int       # 0-100
    confidence_tier: str        # HIGH, MEDIUM, LOW
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    
    # Player context
    player_tier: int = 4
    archetype_group: str = ""
    position: str = ""
    
    # Defense context
    defense_rating: str = ""
    
    # Signal agreement
    signals_agreeing: int = 0
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Result tracking (for backtesting)
    actual_value: Optional[float] = None
    hit: Optional[bool] = None
    margin: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team": self.team_abbrev,
            "opponent": self.opponent_abbrev,
            "date": self.game_date,
            "is_home": self.is_home,
            "prop_type": self.prop_type,
            "direction": self.direction,
            "projection": round(self.projected_value, 1),
            "line": round(self.line, 1),
            "edge_pct": round(self.edge_pct, 1),
            "confidence": self.confidence_score,
            "tier": self.confidence_tier,
            "player_tier": self.player_tier,
            "archetype": self.archetype_group,
            "position": self.position,
            "defense_rating": self.defense_rating,
            "signals_agreeing": self.signals_agreeing,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "actual": self.actual_value,
            "hit": self.hit,
            "margin": self.margin,
        }


@dataclass
class DailyPicks:
    """All picks for a single day."""
    date: str
    games_count: int
    picks: List[PropPick] = field(default_factory=list)
    
    @property
    def high_confidence_picks(self) -> List[PropPick]:
        return [p for p in self.picks if p.confidence_tier == "HIGH"]
    
    @property
    def medium_confidence_picks(self) -> List[PropPick]:
        return [p for p in self.picks if p.confidence_tier == "MEDIUM"]
    
    @property
    def total_picks(self) -> int:
        return len(self.picks)
    
    @property
    def high_count(self) -> int:
        return len(self.high_confidence_picks)
    
    @property
    def medium_count(self) -> int:
        return len(self.medium_confidence_picks)
    
    def by_prop_type(self, prop_type: str) -> List[PropPick]:
        return [p for p in self.picks if p.prop_type == prop_type]
    
    def by_direction(self, direction: str) -> List[PropPick]:
        return [p for p in self.picks if p.direction == direction]
    
    def summary(self) -> str:
        """Generate a summary of the day's picks."""
        lines = [
            f"=" * 60,
            f"ENSEMBLE MODEL PICKS - {self.date}",
            f"=" * 60,
            f"Games: {self.games_count}",
            f"Total Picks: {self.total_picks}",
            f"  HIGH: {self.high_count}",
            f"  MEDIUM: {self.medium_count}",
            "",
            f"By Direction:",
            f"  OVER:  {len(self.by_direction('OVER'))}",
            f"  UNDER: {len(self.by_direction('UNDER'))}",
            "",
        ]
        
        if self.high_confidence_picks:
            lines.append("HIGH CONFIDENCE PICKS:")
            for p in sorted(self.high_confidence_picks, 
                          key=lambda x: x.confidence_score, reverse=True)[:10]:
                lines.append(
                    f"  {p.player_name} {p.prop_type} {p.direction} ({p.line:.1f}) "
                    f"- {p.edge_pct:.1f}% edge, {p.confidence_score} conf"
                )
        
        return "\n".join(lines)


def _projection_to_pick(
    projection: EnsembleProjection,
    config: ModelV7Config,
) -> PropPick:
    """Convert an EnsembleProjection to a PropPick with confidence scoring."""
    # Calculate confidence
    confidence = calculate_confidence(projection, config)
    
    return PropPick(
        player_id=projection.player_id,
        player_name=projection.player_name,
        team_abbrev=projection.team_abbrev,
        opponent_abbrev=projection.opponent_abbrev,
        game_date=projection.game_date,
        is_home=projection.is_home,
        prop_type=projection.prop_type,
        direction=projection.direction,
        projected_value=projection.final_projection,
        line=projection.line,
        edge_pct=projection.edge_pct,
        confidence_score=confidence.total_score,
        confidence_tier=confidence.confidence_tier,
        confidence_breakdown=confidence,
        player_tier=projection.player_tier,
        archetype_group=projection.archetype_group,
        position=projection.player_stats.position if projection.player_stats else "",
        defense_rating=projection.defense_profile.overall_rating if projection.defense_profile else "",
        signals_agreeing=projection.signal_strength.signal_agreement,
        reasons=projection.reasons,
        warnings=projection.warnings,
    )


def generate_game_picks(
    conn: sqlite3.Connection,
    game_id: int,
    game_date: str,
    team1_name: str,
    team2_name: str,
    config: ModelV7Config = DEFAULT_CONFIG,
) -> List[PropPick]:
    """
    Generate picks for a single game.
    
    Args:
        conn: Database connection
        game_id: Game ID
        game_date: Game date (YYYY-MM-DD)
        team1_name: Away team name
        team2_name: Home team name
        config: Model configuration
    
    Returns:
        List of PropPick objects for this game
    """
    all_picks = []
    
    team1_abbrev = abbrev_from_team_name(team1_name) or normalize_team_abbrev(team1_name)
    team2_abbrev = abbrev_from_team_name(team2_name) or normalize_team_abbrev(team2_name)
    
    if not team1_abbrev or not team2_abbrev:
        return []
    
    # Get players who played for these teams recently
    # Team 1 (away) players
    team1_players = _get_team_players(conn, team1_name, game_date, config)
    # Team 2 (home) players
    team2_players = _get_team_players(conn, team2_name, game_date, config)
    
    # Generate projections for team 1 (playing vs team 2, away)
    for player_id in team1_players:
        projections = project_all_props(
            conn, player_id, team2_abbrev, game_date, is_home=False, config=config
        )
        for proj in projections:
            pick = _projection_to_pick(proj, config)
            all_picks.append(pick)
    
    # Generate projections for team 2 (playing vs team 1, home)
    for player_id in team2_players:
        projections = project_all_props(
            conn, player_id, team1_abbrev, game_date, is_home=True, config=config
        )
        for proj in projections:
            pick = _projection_to_pick(proj, config)
            all_picks.append(pick)
    
    # Filter and select best picks
    return _select_best_picks(all_picks, config)


def _get_team_players(
    conn: sqlite3.Connection,
    team_name: str,
    game_date: str,
    config: ModelV7Config,
) -> List[int]:
    """Get player IDs for a team who meet minutes threshold."""
    team_abbrev = abbrev_from_team_name(team_name) or normalize_team_abbrev(team_name)
    
    # Get team ID(s) - search by name pattern
    teams = conn.execute(
        "SELECT id FROM teams WHERE name LIKE ? OR name LIKE ?",
        (f"%{team_abbrev}%", f"%{team_name}%"),
    ).fetchall()
    
    if not teams:
        return []
    
    team_ids = [t["id"] for t in teams]
    ph = ",".join(["?"] * len(team_ids))
    
    # Get players with sufficient minutes
    rows = conn.execute(
        f"""
        SELECT DISTINCT b.player_id, AVG(b.minutes) as avg_min, COUNT(*) as games
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        WHERE b.team_id IN ({ph})
          AND g.game_date < ?
          AND b.minutes IS NOT NULL
        GROUP BY b.player_id
        HAVING AVG(b.minutes) >= ? AND COUNT(*) >= ?
        ORDER BY AVG(b.minutes) DESC
        LIMIT 15
        """,
        (*team_ids, game_date, config.min_minutes_threshold, config.min_games_required),
    ).fetchall()
    
    return [r["player_id"] for r in rows]


def _select_best_picks(
    picks: List[PropPick],
    config: ModelV7Config,
) -> List[PropPick]:
    """
    Select the best picks from all candidates.
    
    Selection criteria:
    1. Minimum edge threshold
    2. Maximum picks per player
    3. Balance direction (slight UNDER preference)
    4. Filter problematic archetypes if configured
    5. Filter by defense quality if configured
    """
    # Filter by minimum edge
    valid_picks = [p for p in picks if p.edge_pct >= config.min_edge_threshold]
    
    # Filter scoring guards if configured
    if config.filter_scoring_guards:
        valid_picks = [
            p for p in valid_picks 
            if p.archetype_group.lower() != "scoring_guards" or p.confidence_score >= 75
        ]
    
    # Filter hub_bigs if configured (14.3% hit rate!)
    if hasattr(config, 'exclude_hub_bigs') and config.exclude_hub_bigs:
        valid_picks = [
            p for p in valid_picks
            if p.archetype_group.lower() != "hub_bigs"
        ]
    
    # Filter slashers if configured (41.7% hit rate)
    if hasattr(config, 'exclude_slashers') and config.exclude_slashers:
        valid_picks = [
            p for p in valid_picks
            if p.archetype_group.lower() != "slashers"
        ]
    
    # Filter by defense quality if configured
    if hasattr(config, 'exclude_terrible_defense') and config.exclude_terrible_defense:
        valid_picks = [
            p for p in valid_picks
            if p.defense_rating.lower() != "terrible"
        ]
    
    # Filter to mid-tier defense if configured (71.4% hit rate)
    if hasattr(config, 'prefer_mid_tier_defense') and config.prefer_mid_tier_defense:
        valid_picks = [
            p for p in valid_picks
            if p.defense_rating.lower() in ["good", "average", "elite", "poor", ""]
        ]
    
    # Sort by confidence score (primary) and edge (secondary)
    valid_picks.sort(key=lambda p: (p.confidence_score, p.edge_pct), reverse=True)
    
    # Apply max picks per player
    player_pick_count = {}
    selected = []
    
    for pick in valid_picks:
        count = player_pick_count.get(pick.player_id, 0)
        if count < config.max_picks_per_player:
            selected.append(pick)
            player_pick_count[pick.player_id] = count + 1
    
    # Limit to target picks per game (approximately)
    # This will be refined at the daily level
    return selected


def generate_daily_picks(
    conn: sqlite3.Connection,
    date: str,
    config: ModelV7Config = DEFAULT_CONFIG,
) -> DailyPicks:
    """Generate picks for all games on a given date."""
    # Get all games for the date
    games = conn.execute(
        """
        SELECT g.id, g.game_date, t1.name as team1_name, t2.name as team2_name
        FROM games g
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        WHERE g.game_date = ?
        """,
        (date,),
    ).fetchall()
    
    all_picks = []
    games_count = len(games)
    
    for game in games:
        game_picks = generate_game_picks(
            conn=conn,
            game_id=game["id"],
            game_date=date,
            team1_name=game["team1_name"],
            team2_name=game["team2_name"],
            config=config,
        )
        all_picks.extend(game_picks)
    
    # Final selection across all games
    final_picks = _final_selection(all_picks, games_count, config)
    
    return DailyPicks(
        date=date,
        games_count=games_count,
        picks=final_picks,
    )


def _final_selection(
    picks: List[PropPick],
    games_count: int,
    config: ModelV7Config,
) -> List[PropPick]:
    """
    Final pick selection across all games.
    
    Ensures:
    1. Target picks per game
    2. Balanced prop types
    3. HIGH confidence prioritized
    4. Direction balance (slight UNDER preference)
    """
    if not picks:
        return []
    
    target_picks = games_count * config.picks_per_game
    
    # Sort by confidence
    picks.sort(key=lambda p: (p.confidence_score, p.edge_pct), reverse=True)
    
    # First, take all HIGH confidence picks
    high_picks = [p for p in picks if p.confidence_tier == "HIGH"]
    
    # Then fill with MEDIUM
    medium_picks = [p for p in picks if p.confidence_tier == "MEDIUM"]
    
    # Combine with preference for variety
    selected = []
    player_counts = {}
    prop_type_counts = {"PTS": 0, "REB": 0, "AST": 0}
    
    # Add HIGH picks first
    for pick in high_picks:
        pid = pick.player_id
        if player_counts.get(pid, 0) < config.max_picks_per_player:
            selected.append(pick)
            player_counts[pid] = player_counts.get(pid, 0) + 1
            prop_type_counts[pick.prop_type] += 1
    
    # Add MEDIUM picks to reach target
    for pick in medium_picks:
        if len(selected) >= target_picks:
            break
        pid = pick.player_id
        if player_counts.get(pid, 0) < config.max_picks_per_player:
            selected.append(pick)
            player_counts[pid] = player_counts.get(pid, 0) + 1
            prop_type_counts[pick.prop_type] += 1
    
    return selected


def get_daily_picks(
    date: str,
    config: ModelV7Config = DEFAULT_CONFIG,
) -> DailyPicks:
    """
    Public interface to get daily picks.
    
    Args:
        date: Date string (YYYY-MM-DD)
        config: Model configuration
    
    Returns:
        DailyPicks object with all picks for the day
    """
    paths = get_paths()
    db = Db(paths.db_path)
    with db.connect() as conn:
        return generate_daily_picks(conn, date, config)


def grade_picks(
    conn: sqlite3.Connection,
    picks: List[PropPick],
) -> List[PropPick]:
    """
    Grade picks against actual results.
    
    Updates each pick's actual_value, hit, and margin fields.
    """
    for pick in picks:
        # Get actual stats for this player on this date
        row = conn.execute(
            """
            SELECT b.pts, b.reb, b.ast, b.minutes
            FROM boxscore_player b
            JOIN games g ON g.id = b.game_id
            WHERE b.player_id = ?
              AND g.game_date = ?
              AND b.minutes > 0
            LIMIT 1
            """,
            (pick.player_id, pick.game_date),
        ).fetchone()
        
        if row:
            pt = pick.prop_type.lower()
            actual = row[pt] or 0
            pick.actual_value = actual
            
            if pick.direction == "OVER":
                pick.hit = actual > pick.line
            else:
                pick.hit = actual < pick.line
            
            pick.margin = actual - pick.line
    
    return picks

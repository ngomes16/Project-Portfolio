"""
Pick Generation Module
======================

Generates and selects picks for games using the projection engine
and confidence scoring system.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict

from .config import ModelV6Config, DEFAULT_CONFIG
from .projector import Projection, load_player_stats, calculate_projection, project_all_props
from .player_groups import PlayerGroup, get_player_group, classify_player
from .confidence import ConfidenceBreakdown, calculate_confidence


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
    defense_rating: str = ""    # elite, good, average, poor, terrible
    defense_adjustment: float = 1.0
    
    # Adjustments applied
    trend_adjustment: float = 1.0
    rest_adjustment: float = 1.0
    
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
            "prop_type": self.prop_type,
            "direction": self.direction,
            "projection": self.projected_value,
            "line": self.line,
            "edge": f"{self.edge_pct:.1f}%",
            "confidence": self.confidence_score,
            "tier": self.confidence_tier,
            "player_tier": self.player_tier,
            "archetype": self.archetype_group,
            "position": self.position,
            "defense_rating": self.defense_rating,
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
    
    def get_picks_by_type(self, prop_type: str) -> List[PropPick]:
        return [p for p in self.picks if p.prop_type == prop_type]
    
    def get_picks_by_archetype(self, archetype_group: str) -> List[PropPick]:
        return [p for p in self.picks if p.archetype_group == archetype_group]
    
    def summary(self) -> str:
        """Generate a summary of the day's picks."""
        lines = [
            f"Daily Picks for {self.date}",
            f"Games: {self.games_count}",
            f"Total Picks: {self.total_picks}",
            f"  HIGH: {self.high_count}",
            f"  MEDIUM: {self.medium_count}",
            "",
        ]
        
        if self.high_confidence_picks:
            lines.append("HIGH CONFIDENCE PICKS:")
            for p in self.high_confidence_picks[:5]:
                lines.append(f"  {p.player_name} {p.prop_type} {p.direction} ({p.line}) - {p.edge_pct:.1f}%")
        
        return "\n".join(lines)


def _projection_to_pick(
    projection: Projection,
    config: ModelV6Config,
) -> PropPick:
    """Convert a Projection to a PropPick with confidence scoring."""
    # Calculate confidence
    confidence = calculate_confidence(projection, config)
    
    # Get player group info
    player_group = projection.player_group
    defense_matchup = projection.defense_matchup
    
    return PropPick(
        player_id=projection.player_id,
        player_name=projection.player_name,
        team_abbrev=projection.team_abbrev,
        opponent_abbrev=projection.opponent_abbrev,
        game_date=projection.game_date,
        prop_type=projection.prop_type,
        direction=projection.direction,
        projected_value=projection.final_projection,
        line=projection.line,
        edge_pct=projection.edge_pct,
        confidence_score=confidence.total_score,
        confidence_tier=confidence.confidence_tier,
        confidence_breakdown=confidence,
        player_tier=player_group.tier_value if player_group else 4,
        archetype_group=player_group.archetype_group if player_group else "",
        position=player_group.position if player_group else "",
        defense_rating=defense_matchup.defense_rating if defense_matchup else "",
        defense_adjustment=projection.defense_adjustment,
        trend_adjustment=projection.trend_adjustment,
        rest_adjustment=projection.rest_adjustment,
        reasons=projection.reasons,
        warnings=projection.warnings,
    )


def generate_game_picks(
    conn: sqlite3.Connection,
    game_id: int,
    game_date: str,
    team1_name: str,
    team2_name: str,
    config: ModelV6Config = DEFAULT_CONFIG,
) -> List[PropPick]:
    """
    Generate picks for a single game.
    
    Args:
        conn: Database connection
        game_id: Game ID
        game_date: Game date (YYYY-MM-DD)
        team1_name: First team name
        team2_name: Second team name
        config: Model configuration
    
    Returns:
        List of PropPicks for the game
    """
    from ...team_aliases import abbrev_from_team_name
    
    t1_abbrev = abbrev_from_team_name(team1_name) or ""
    t2_abbrev = abbrev_from_team_name(team2_name) or ""
    
    all_picks = []
    
    # Process both teams
    for team_name, team_abbrev, opp_abbrev in [
        (team1_name, t1_abbrev, t2_abbrev),
        (team2_name, t2_abbrev, t1_abbrev),
    ]:
        # Get team ID
        team = conn.execute(
            "SELECT id FROM teams WHERE name = ?", (team_name,)
        ).fetchone()
        
        if not team:
            continue
        
        # Get eligible players
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
            (team["id"], game_date, config.min_minutes_threshold - 5, config.min_games_required),
        ).fetchall()
        
        for p in players:
            # Get all projections for this player
            projections = project_all_props(
                conn=conn,
                player_id=p["player_id"],
                opponent_abbrev=opp_abbrev,
                game_date=game_date,
                config=config,
            )
            
            # Convert to picks
            for proj in projections:
                if proj.direction == "PASS":
                    continue
                
                pick = _projection_to_pick(proj, config)
                all_picks.append(pick)
    
    # Sort by confidence score
    all_picks.sort(key=lambda p: (p.confidence_score, p.edge_pct), reverse=True)
    
    # Select picks with variety
    selected = _select_diverse_picks(all_picks, config)
    
    return selected


def _select_diverse_picks(
    all_picks: List[PropPick],
    config: ModelV6Config,
) -> List[PropPick]:
    """
    Select a diverse set of picks from all candidates.
    
    Ensures:
    - Max picks per player
    - Mix of prop types
    - Mix of teams
    - Target total per game
    """
    selected = []
    player_counts = {}
    
    # First pass: HIGH and MEDIUM confidence only
    for pick in all_picks:
        if pick.confidence_tier not in ("HIGH", "MEDIUM"):
            continue
        
        player_id = pick.player_id
        if player_counts.get(player_id, 0) >= config.max_picks_per_player:
            continue
        
        selected.append(pick)
        player_counts[player_id] = player_counts.get(player_id, 0) + 1
        
        if len(selected) >= config.picks_per_game:
            break
    
    # Second pass: Relax if needed
    if len(selected) < config.picks_per_game:
        for pick in all_picks:
            if pick in selected:
                continue
            
            player_id = pick.player_id
            if player_counts.get(player_id, 0) >= config.max_picks_per_player:
                continue
            
            # Allow LOW confidence picks if needed
            selected.append(pick)
            player_counts[player_id] = player_counts.get(player_id, 0) + 1
            
            if len(selected) >= config.picks_per_game:
                break
    
    return selected


def get_daily_picks(
    date: str,
    config: ModelV6Config = DEFAULT_CONFIG,
) -> DailyPicks:
    """
    Generate picks for all games on a specific date.
    
    Args:
        date: Date string (YYYY-MM-DD)
        config: Model configuration
    
    Returns:
        DailyPicks with all recommendations
    """
    from ...db import Db
    from ...paths import get_paths
    
    paths = get_paths()
    db = Db(paths.db_path)
    
    with db.connect() as conn:
        # Get all games on this date
        games = conn.execute(
            """
            SELECT g.id, g.game_date, t1.name as team1, t2.name as team2
            FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            WHERE g.game_date = ?
            """,
            (date,),
        ).fetchall()
        
        all_picks = []
        
        for game in games:
            game_picks = generate_game_picks(
                conn=conn,
                game_id=game["id"],
                game_date=game["game_date"],
                team1_name=game["team1"],
                team2_name=game["team2"],
                config=config,
            )
            all_picks.extend(game_picks)
        
        # Sort all picks by confidence
        all_picks.sort(key=lambda p: (p.confidence_score, p.edge_pct), reverse=True)
        
        return DailyPicks(
            date=date,
            games_count=len(games),
            picks=all_picks,
        )


def get_picks_for_matchup(
    away_team: str,
    home_team: str,
    game_date: str,
    config: ModelV6Config = DEFAULT_CONFIG,
) -> List[PropPick]:
    """
    Generate picks for a specific matchup.
    
    Args:
        away_team: Away team name or abbreviation
        home_team: Home team name or abbreviation
        game_date: Game date (YYYY-MM-DD)
        config: Model configuration
    
    Returns:
        List of PropPicks for the matchup
    """
    from ...db import Db
    from ...paths import get_paths
    from ...team_aliases import team_name_from_abbrev, normalize_team_abbrev
    
    paths = get_paths()
    db = Db(paths.db_path)
    
    # Normalize team names
    away_name = team_name_from_abbrev(normalize_team_abbrev(away_team)) or away_team
    home_name = team_name_from_abbrev(normalize_team_abbrev(home_team)) or home_team
    
    with db.connect() as conn:
        # Find or create placeholder game ID
        game = conn.execute(
            """
            SELECT g.id FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            WHERE g.game_date = ?
              AND (t1.name = ? OR t1.name = ?)
              AND (t2.name = ? OR t2.name = ?)
            """,
            (game_date, away_name, home_name, away_name, home_name),
        ).fetchone()
        
        game_id = game["id"] if game else 0
        
        return generate_game_picks(
            conn=conn,
            game_id=game_id,
            game_date=game_date,
            team1_name=away_name,
            team2_name=home_name,
            config=config,
        )


def grade_picks(
    picks: List[PropPick],
    conn: sqlite3.Connection,
) -> List[PropPick]:
    """
    Grade picks against actual results.
    
    Args:
        picks: List of picks to grade
        conn: Database connection
    
    Returns:
        Same picks with actual values and hit status filled in
    """
    for pick in picks:
        # Get actual value from boxscore
        actual = conn.execute(
            """
            SELECT b.pts, b.reb, b.ast
            FROM boxscore_player b
            JOIN games g ON g.id = b.game_id
            WHERE b.player_id = ?
              AND g.game_date = ?
            """,
            (pick.player_id, pick.game_date),
        ).fetchone()
        
        if actual:
            prop_type = pick.prop_type.lower()
            pick.actual_value = actual[prop_type]
            
            if pick.actual_value is not None:
                pick.margin = pick.actual_value - pick.line
                
                if pick.direction == "OVER":
                    pick.hit = pick.actual_value > pick.line
                else:
                    pick.hit = pick.actual_value < pick.line
    
    return picks

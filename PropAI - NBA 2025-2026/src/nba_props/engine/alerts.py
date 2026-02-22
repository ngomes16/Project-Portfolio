"""Automated edge alert system for finding prop betting opportunities.

This module scans all available lines against projections and identifies
props where the projection differs significantly from the sportsbook line.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..team_aliases import normalize_team_abbrev, abbrev_from_team_name, team_name_from_abbrev


@dataclass
class EdgeAlert:
    """An alert for a potential edge in a prop bet."""
    player_id: int
    player_name: str
    team_abbrev: str
    
    # Prop details
    prop_type: str  # PTS, REB, AST
    line: float
    odds_american: Optional[int]
    book: Optional[str]
    
    # Projection
    projected_value: float
    projected_std: float
    
    # Edge
    direction: str  # OVER or UNDER
    edge_pct: float  # Percentage edge
    edge_value: float  # Absolute difference
    
    # Probability
    over_probability: float
    under_probability: float
    
    # Context
    games_played: int
    is_top_7: bool
    
    # Rating
    confidence: str  # HIGH, MEDIUM, LOW
    reasons: list[str] = field(default_factory=list)


@dataclass
class AlertScanResult:
    """Results from scanning for edge alerts."""
    scan_date: str
    lines_scanned: int
    alerts_found: int
    
    # Alerts by confidence
    high_confidence: list[EdgeAlert] = field(default_factory=list)
    medium_confidence: list[EdgeAlert] = field(default_factory=list)
    low_confidence: list[EdgeAlert] = field(default_factory=list)
    
    @property
    def all_alerts(self) -> list[EdgeAlert]:
        return self.high_confidence + self.medium_confidence + self.low_confidence


def scan_for_edge_alerts(
    conn: sqlite3.Connection,
    lines_date: str,
    min_edge_pct: float = 5.0,
    min_games: int = 3,
) -> AlertScanResult:
    """
    Scan all lines for a given date and find edges.
    
    Args:
        conn: Database connection
        lines_date: Date to scan lines for
        min_edge_pct: Minimum edge percentage to trigger alert
        min_games: Minimum games for projection to be valid
    
    Returns:
        AlertScanResult with categorized alerts
    """
    from .projector import project_player_stats, ProjectionConfig
    from .edge_calculator import calculate_prop_edge
    
    result = AlertScanResult(
        scan_date=lines_date,
        lines_scanned=0,
        alerts_found=0,
    )
    
    # Get all lines for this date
    lines = conn.execute(
        """
        SELECT sl.id, sl.player_id, p.name as player_name, 
               sl.prop_type, sl.line, sl.odds_american, sl.book
        FROM sportsbook_lines sl
        JOIN players p ON p.id = sl.player_id
        WHERE sl.as_of_date = ?
        """,
        (lines_date,),
    ).fetchall()
    
    if not lines:
        return result
    
    config = ProjectionConfig(min_games=min_games)
    
    # Group by player to avoid duplicate projections
    player_projections = {}
    
    for line_row in lines:
        result.lines_scanned += 1
        
        player_id = line_row["player_id"]
        prop_type = line_row["prop_type"]
        line = line_row["line"]
        odds = line_row["odds_american"]
        book = line_row["book"]
        player_name = line_row["player_name"]
        
        # Get projection (cached)
        if player_id not in player_projections:
            proj = project_player_stats(conn, player_id, config)
            player_projections[player_id] = proj
        else:
            proj = player_projections[player_id]
        
        if not proj:
            continue
        
        # Calculate edge
        edge = calculate_prop_edge(
            projection=proj,
            prop_type=prop_type,
            line=line,
            odds_american=odds,
            book=book,
        )
        
        # Check if meets threshold
        if edge.edge_pct < min_edge_pct:
            continue
        
        # Determine reasons for edge
        reasons = []
        
        # Volume reason
        if proj.games_played >= 10:
            reasons.append(f"Based on {proj.games_played} games of data")
        elif proj.games_played >= 5:
            reasons.append(f"Based on {proj.games_played} games (moderate sample)")
        
        # Edge magnitude reason
        if edge.edge_pct >= 15:
            reasons.append(f"Large edge ({edge.edge_pct:.1f}%)")
        elif edge.edge_pct >= 10:
            reasons.append(f"Solid edge ({edge.edge_pct:.1f}%)")
        
        # Projection vs line reason
        diff = edge.projected_value - line
        if abs(diff) >= 5:
            reasons.append(f"Projection {edge.projected_value:.1f} vs line {line}")
        
        # Standard deviation reason
        if abs(diff) > edge.projected_std:
            reasons.append("Line outside 1 standard deviation")
        
        # Create alert
        alert = EdgeAlert(
            player_id=player_id,
            player_name=player_name,
            team_abbrev=proj.team_abbrev,
            prop_type=prop_type,
            line=line,
            odds_american=odds,
            book=book,
            projected_value=edge.projected_value,
            projected_std=edge.projected_std,
            direction=edge.recommendation,
            edge_pct=edge.edge_pct,
            edge_value=abs(edge.projected_value - line),
            over_probability=edge.over_probability,
            under_probability=edge.under_probability,
            games_played=proj.games_played,
            is_top_7=edge.is_top_7,
            confidence=edge.confidence,
            reasons=reasons,
        )
        
        result.alerts_found += 1
        
        if edge.confidence == "HIGH":
            result.high_confidence.append(alert)
        elif edge.confidence == "MEDIUM":
            result.medium_confidence.append(alert)
        else:
            result.low_confidence.append(alert)
    
    # Sort alerts by edge
    for alerts in [result.high_confidence, result.medium_confidence, result.low_confidence]:
        alerts.sort(key=lambda a: -a.edge_pct)
    
    return result


def find_best_props_today(
    conn: sqlite3.Connection,
    game_date: Optional[str] = None,
    min_edge_pct: float = 5.0,
    top_n: int = 10,
) -> list[EdgeAlert]:
    """
    Find the best prop opportunities for today's games.
    
    Args:
        conn: Database connection
        game_date: Date to look for lines (defaults to today)
        min_edge_pct: Minimum edge percentage
        top_n: Number of top props to return
    
    Returns:
        List of top EdgeAlert objects
    """
    if not game_date:
        game_date = datetime.now().strftime("%Y-%m-%d")
    
    scan_result = scan_for_edge_alerts(conn, game_date, min_edge_pct)
    
    # Return top N from all alerts
    all_alerts = scan_result.all_alerts
    return all_alerts[:top_n]


def find_value_plays_by_team(
    conn: sqlite3.Connection,
    team_abbrev: str,
    lines_date: str,
    min_edge_pct: float = 3.0,
) -> list[EdgeAlert]:
    """
    Find value plays for a specific team.
    
    Args:
        conn: Database connection
        team_abbrev: Team abbreviation
        lines_date: Date to check lines for
        min_edge_pct: Minimum edge percentage
    
    Returns:
        List of EdgeAlert objects for the team
    """
    from .projector import project_team_players, ProjectionConfig
    from .edge_calculator import calculate_prop_edge
    
    team_abbrev = normalize_team_abbrev(team_abbrev)
    team_name = team_name_from_abbrev(team_abbrev)
    
    alerts = []
    config = ProjectionConfig()
    
    # Get projections for team
    projections = project_team_players(conn, team_abbrev, config)
    
    if not projections:
        return alerts
    
    # Get lines for players on this team
    for proj in projections:
        lines = conn.execute(
            """
            SELECT sl.prop_type, sl.line, sl.odds_american, sl.book
            FROM sportsbook_lines sl
            WHERE sl.player_id = ?
              AND sl.as_of_date = ?
            """,
            (proj.player_id, lines_date),
        ).fetchall()
        
        for line_row in lines:
            edge = calculate_prop_edge(
                projection=proj,
                prop_type=line_row["prop_type"],
                line=line_row["line"],
                odds_american=line_row["odds_american"],
                book=line_row["book"],
            )
            
            if edge.edge_pct < min_edge_pct:
                continue
            
            alert = EdgeAlert(
                player_id=proj.player_id,
                player_name=proj.player_name,
                team_abbrev=team_abbrev,
                prop_type=line_row["prop_type"],
                line=line_row["line"],
                odds_american=line_row["odds_american"],
                book=line_row["book"],
                projected_value=edge.projected_value,
                projected_std=edge.projected_std,
                direction=edge.recommendation,
                edge_pct=edge.edge_pct,
                edge_value=abs(edge.projected_value - line_row["line"]),
                over_probability=edge.over_probability,
                under_probability=edge.under_probability,
                games_played=proj.games_played,
                is_top_7=proj.is_top_7,
                confidence=edge.confidence,
            )
            
            alerts.append(alert)
    
    alerts.sort(key=lambda a: -a.edge_pct)
    return alerts


def daily_edge_report(
    conn: sqlite3.Connection,
    game_date: Optional[str] = None,
    min_edge_pct: float = 5.0,
) -> dict:
    """
    Generate a daily report of all edge opportunities.
    
    Returns:
        Dictionary with report data for display/export
    """
    if not game_date:
        game_date = datetime.now().strftime("%Y-%m-%d")
    
    scan_result = scan_for_edge_alerts(conn, game_date, min_edge_pct)
    
    report = {
        "date": game_date,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "lines_scanned": scan_result.lines_scanned,
            "alerts_found": scan_result.alerts_found,
            "high_confidence": len(scan_result.high_confidence),
            "medium_confidence": len(scan_result.medium_confidence),
            "low_confidence": len(scan_result.low_confidence),
        },
        "high_confidence_plays": [
            {
                "player": a.player_name,
                "team": a.team_abbrev,
                "prop": a.prop_type,
                "direction": a.direction,
                "line": a.line,
                "projection": a.projected_value,
                "edge_pct": a.edge_pct,
                "confidence": a.confidence,
                "reasons": a.reasons,
            }
            for a in scan_result.high_confidence
        ],
        "medium_confidence_plays": [
            {
                "player": a.player_name,
                "team": a.team_abbrev,
                "prop": a.prop_type,
                "direction": a.direction,
                "line": a.line,
                "projection": a.projected_value,
                "edge_pct": a.edge_pct,
            }
            for a in scan_result.medium_confidence[:10]  # Limit to top 10
        ],
        "all_over_plays": [
            {
                "player": a.player_name,
                "prop": a.prop_type,
                "line": a.line,
                "projection": a.projected_value,
                "edge_pct": a.edge_pct,
            }
            for a in scan_result.all_alerts if a.direction == "OVER"
        ][:10],
        "all_under_plays": [
            {
                "player": a.player_name,
                "prop": a.prop_type,
                "line": a.line,
                "projection": a.projected_value,
                "edge_pct": a.edge_pct,
            }
            for a in scan_result.all_alerts if a.direction == "UNDER"
        ][:10],
    }
    
    return report


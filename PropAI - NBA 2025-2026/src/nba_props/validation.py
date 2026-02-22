"""Data validation and integrity checks for NBA props database."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .team_aliases import abbrev_from_team_name, team_name_from_abbrev
from .standings import ALL_ABBREVS


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    passed: bool
    message: str
    details: list[dict] = field(default_factory=list)
    severity: str = "WARNING"  # INFO, WARNING, ERROR


@dataclass
class ValidationReport:
    """Complete validation report."""
    results: list[ValidationResult] = field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0
    warnings: int = 0
    errors: int = 0
    
    def add_result(self, result: ValidationResult) -> None:
        self.results.append(result)
        self.total_checks += 1
        if result.passed:
            self.passed_checks += 1
        elif result.severity == "WARNING":
            self.warnings += 1
        elif result.severity == "ERROR":
            self.errors += 1
    
    def is_valid(self) -> bool:
        """Returns True if no errors (warnings are OK)."""
        return self.errors == 0


def check_duplicate_games(conn: sqlite3.Connection) -> ValidationResult:
    """Check for duplicate games (same teams on same date)."""
    rows = conn.execute(
        """
        WITH normalized AS (
          SELECT
            id,
            game_date,
            CASE WHEN team1_id < team2_id THEN team1_id ELSE team2_id END AS a_id,
            CASE WHEN team1_id < team2_id THEN team2_id ELSE team1_id END AS b_id
          FROM games
        )
        SELECT
          n.game_date,
          ta.name AS team_a,
          tb.name AS team_b,
          COUNT(*) AS cnt,
          GROUP_CONCAT(n.id) AS game_ids
        FROM normalized n
        JOIN teams ta ON ta.id = n.a_id
        JOIN teams tb ON tb.id = n.b_id
        GROUP BY n.game_date, n.a_id, n.b_id
        HAVING COUNT(*) > 1
        ORDER BY n.game_date DESC, cnt DESC
        """
    ).fetchall()
    
    if not rows:
        return ValidationResult(
            check_name="duplicate_games",
            passed=True,
            message="No duplicate games found",
        )
    
    return ValidationResult(
        check_name="duplicate_games",
        passed=False,
        message=f"Found {len(rows)} duplicate game(s) by date + matchup",
        details=[
            {
                "date": r["game_date"],
                "team_a": r["team_a"],
                "team_b": r["team_b"],
                "count": r["cnt"],
                "game_ids": r["game_ids"],
            }
            for r in rows
        ],
        severity="ERROR",
    )


def check_team_played_twice_same_day(conn: sqlite3.Connection) -> ValidationResult:
    """Check for teams that appear in multiple games on the same day."""
    rows = conn.execute(
        """
        WITH team_dates AS (
            SELECT game_date, team1_id as team_id FROM games
            UNION ALL
            SELECT game_date, team2_id as team_id FROM games
        )
        SELECT td.game_date, t.name as team, COUNT(*) as cnt
        FROM team_dates td
        JOIN teams t ON t.id = td.team_id
        GROUP BY td.game_date, td.team_id
        HAVING COUNT(*) > 1
        ORDER BY td.game_date DESC, cnt DESC
        """
    ).fetchall()
    
    if not rows:
        return ValidationResult(
            check_name="team_played_twice_same_day",
            passed=True,
            message="No teams played multiple games on the same day",
        )
    
    return ValidationResult(
        check_name="team_played_twice_same_day",
        passed=False,
        message=f"Found {len(rows)} instance(s) of teams playing multiple games on same day",
        details=[
            {
                "date": r["game_date"],
                "team": r["team"],
                "games": r["cnt"],
            }
            for r in rows
        ],
        severity="ERROR",
    )


def check_invalid_team_names(conn: sqlite3.Connection) -> ValidationResult:
    """Check for team names that don't match known NBA teams."""
    rows = conn.execute("SELECT id, name FROM teams ORDER BY name").fetchall()
    
    # Build list of valid team names from abbreviations
    valid_team_names = set()
    for abbrev in ALL_ABBREVS:
        name = team_name_from_abbrev(abbrev)
        if name:
            valid_team_names.add(name)
    
    invalid_teams = []
    for r in rows:
        name = r["name"]
        # Check if it's a valid team name
        if name not in valid_team_names and abbrev_from_team_name(name) is None:
            invalid_teams.append({"id": r["id"], "name": name})
    
    if not invalid_teams:
        return ValidationResult(
            check_name="invalid_team_names",
            passed=True,
            message="All team names are valid NBA teams",
        )
    
    return ValidationResult(
        check_name="invalid_team_names",
        passed=False,
        message=f"Found {len(invalid_teams)} invalid team name(s)",
        details=invalid_teams,
        severity="WARNING",
    )


def check_orphaned_teams(conn: sqlite3.Connection) -> ValidationResult:
    """Check for teams with no associated games."""
    rows = conn.execute(
        """
        SELECT t.id, t.name
        FROM teams t
        LEFT JOIN games g ON g.team1_id = t.id OR g.team2_id = t.id
        WHERE g.id IS NULL
        ORDER BY t.name
        """
    ).fetchall()
    
    if not rows:
        return ValidationResult(
            check_name="orphaned_teams",
            passed=True,
            message="No orphaned teams found",
        )
    
    return ValidationResult(
        check_name="orphaned_teams",
        passed=False,
        message=f"Found {len(rows)} team(s) with no games",
        details=[{"id": r["id"], "name": r["name"]} for r in rows],
        severity="INFO",
    )


def check_extreme_player_stats(conn: sqlite3.Connection) -> ValidationResult:
    """Check for player stats that seem unreasonable."""
    rows = conn.execute(
        """
        SELECT p.name, g.game_date, t.name as team, 
               b.pts, b.reb, b.ast, b.minutes
        FROM boxscore_player b
        JOIN players p ON p.id = b.player_id
        JOIN games g ON g.id = b.game_id
        JOIN teams t ON t.id = b.team_id
        WHERE b.pts > 70 
           OR b.reb > 35 
           OR b.ast > 25 
           OR b.minutes > 60
           OR (b.pts < 0 AND b.pts IS NOT NULL)
           OR (b.reb < 0 AND b.reb IS NOT NULL)
           OR (b.ast < 0 AND b.ast IS NOT NULL)
        ORDER BY g.game_date DESC
        """
    ).fetchall()
    
    if not rows:
        return ValidationResult(
            check_name="extreme_player_stats",
            passed=True,
            message="No extreme player stats found",
        )
    
    return ValidationResult(
        check_name="extreme_player_stats",
        passed=False,
        message=f"Found {len(rows)} player performance(s) with extreme stats",
        details=[
            {
                "player": r["name"],
                "date": r["game_date"],
                "team": r["team"],
                "pts": r["pts"],
                "reb": r["reb"],
                "ast": r["ast"],
                "minutes": r["minutes"],
            }
            for r in rows
        ],
        severity="WARNING",
    )


def check_game_date_range(conn: sqlite3.Connection) -> ValidationResult:
    """Check that game dates are within reasonable range for current season."""
    rows = conn.execute(
        """
        SELECT game_date, COUNT(*) as cnt
        FROM games
        WHERE game_date < '2025-10-01' OR game_date > '2026-06-30'
        GROUP BY game_date
        ORDER BY game_date
        """
    ).fetchall()
    
    if not rows:
        return ValidationResult(
            check_name="game_date_range",
            passed=True,
            message="All game dates are within 2025-26 season range",
        )
    
    return ValidationResult(
        check_name="game_date_range",
        passed=False,
        message=f"Found {len(rows)} game date(s) outside expected season range",
        details=[{"date": r["game_date"], "count": r["cnt"]} for r in rows],
        severity="WARNING",
    )


def check_team_totals_consistency(conn: sqlite3.Connection) -> ValidationResult:
    """Check that team totals match sum of player stats (when totals exist)."""
    rows = conn.execute(
        """
        SELECT g.game_date, t.name as team,
               tt.pts as team_pts,
               (SELECT SUM(b.pts) FROM boxscore_player b 
                WHERE b.game_id = g.id AND b.team_id = t.id AND b.pts IS NOT NULL) as sum_pts,
               tt.reb as team_reb,
               (SELECT SUM(b.reb) FROM boxscore_player b 
                WHERE b.game_id = g.id AND b.team_id = t.id AND b.reb IS NOT NULL) as sum_reb,
               tt.ast as team_ast,
               (SELECT SUM(b.ast) FROM boxscore_player b 
                WHERE b.game_id = g.id AND b.team_id = t.id AND b.ast IS NOT NULL) as sum_ast
        FROM boxscore_team_totals tt
        JOIN games g ON g.id = tt.game_id
        JOIN teams t ON t.id = tt.team_id
        WHERE tt.pts IS NOT NULL
        """
    ).fetchall()
    
    mismatches = []
    for r in rows:
        if r["team_pts"] != r["sum_pts"]:
            mismatches.append({
                "date": r["game_date"],
                "team": r["team"],
                "stat": "PTS",
                "team_total": r["team_pts"],
                "sum_players": r["sum_pts"],
            })
        if r["team_reb"] and r["sum_reb"] and r["team_reb"] != r["sum_reb"]:
            mismatches.append({
                "date": r["game_date"],
                "team": r["team"],
                "stat": "REB",
                "team_total": r["team_reb"],
                "sum_players": r["sum_reb"],
            })
    
    if not mismatches:
        return ValidationResult(
            check_name="team_totals_consistency",
            passed=True,
            message="Team totals match sum of player stats",
        )
    
    return ValidationResult(
        check_name="team_totals_consistency",
        passed=False,
        message=f"Found {len(mismatches)} mismatch(es) between team totals and player sums",
        details=mismatches[:10],  # Limit to first 10
        severity="WARNING",
    )


def check_player_name_duplicates(conn: sqlite3.Connection) -> ValidationResult:
    """Check for potential duplicate player entries (similar names)."""
    # This is a simple check - could be improved with fuzzy matching
    rows = conn.execute(
        """
        SELECT p1.id as id1, p1.name as name1, p2.id as id2, p2.name as name2
        FROM players p1
        JOIN players p2 ON p1.id < p2.id
        WHERE (
            LOWER(REPLACE(p1.name, ' ', '')) = LOWER(REPLACE(p2.name, ' ', ''))
            OR LOWER(REPLACE(REPLACE(p1.name, '.', ''), ' ', '')) = LOWER(REPLACE(REPLACE(p2.name, '.', ''), ' ', ''))
        )
        ORDER BY p1.name
        """
    ).fetchall()
    
    if not rows:
        return ValidationResult(
            check_name="player_name_duplicates",
            passed=True,
            message="No potential duplicate player names found",
        )
    
    return ValidationResult(
        check_name="player_name_duplicates",
        passed=False,
        message=f"Found {len(rows)} potential duplicate player name(s)",
        details=[
            {
                "player1": {"id": r["id1"], "name": r["name1"]},
                "player2": {"id": r["id2"], "name": r["name2"]},
            }
            for r in rows
        ],
        severity="WARNING",
    )


def check_games_with_too_few_players(conn: sqlite3.Connection) -> ValidationResult:
    """Check for games where a team has fewer than 5 players with stats."""
    rows = conn.execute(
        """
        SELECT g.id, g.game_date, t.name as team, COUNT(*) as player_count
        FROM boxscore_player b
        JOIN games g ON g.id = b.game_id
        JOIN teams t ON t.id = b.team_id
        WHERE b.minutes IS NOT NULL AND b.minutes > 0
        GROUP BY g.id, b.team_id
        HAVING COUNT(*) < 5
        ORDER BY g.game_date DESC
        """
    ).fetchall()
    
    if not rows:
        return ValidationResult(
            check_name="games_with_too_few_players",
            passed=True,
            message="All games have at least 5 players per team with stats",
        )
    
    return ValidationResult(
        check_name="games_with_too_few_players",
        passed=False,
        message=f"Found {len(rows)} team-game(s) with fewer than 5 players",
        details=[
            {
                "game_id": r["id"],
                "date": r["game_date"],
                "team": r["team"],
                "players_with_stats": r["player_count"],
            }
            for r in rows
        ],
        severity="WARNING",
    )


def check_missing_team_totals(conn: sqlite3.Connection) -> ValidationResult:
    """Check for games missing team totals."""
    rows = conn.execute(
        """
        SELECT g.id, g.game_date, t1.name as team1, t2.name as team2
        FROM games g
        JOIN teams t1 ON t1.id = g.team1_id
        JOIN teams t2 ON t2.id = g.team2_id
        LEFT JOIN boxscore_team_totals tt1 ON tt1.game_id = g.id AND tt1.team_id = g.team1_id
        LEFT JOIN boxscore_team_totals tt2 ON tt2.game_id = g.id AND tt2.team_id = g.team2_id
        WHERE tt1.id IS NULL OR tt2.id IS NULL
        ORDER BY g.game_date DESC
        """
    ).fetchall()
    
    if not rows:
        return ValidationResult(
            check_name="missing_team_totals",
            passed=True,
            message="All games have team totals for both teams",
        )
    
    return ValidationResult(
        check_name="missing_team_totals",
        passed=False,
        message=f"Found {len(rows)} game(s) missing team totals",
        details=[
            {
                "game_id": r["id"],
                "date": r["game_date"],
                "team1": r["team1"],
                "team2": r["team2"],
            }
            for r in rows[:10]
        ],
        severity="INFO",
    )


def run_all_validations(conn: sqlite3.Connection) -> ValidationReport:
    """Run all validation checks and return a comprehensive report."""
    report = ValidationReport()
    
    # Critical checks
    report.add_result(check_duplicate_games(conn))
    report.add_result(check_team_played_twice_same_day(conn))
    
    # Data quality checks
    report.add_result(check_invalid_team_names(conn))
    report.add_result(check_extreme_player_stats(conn))
    report.add_result(check_game_date_range(conn))
    report.add_result(check_team_totals_consistency(conn))
    report.add_result(check_player_name_duplicates(conn))
    report.add_result(check_games_with_too_few_players(conn))
    
    # Informational checks
    report.add_result(check_orphaned_teams(conn))
    report.add_result(check_missing_team_totals(conn))
    
    return report


def cleanup_orphaned_teams(conn: sqlite3.Connection) -> int:
    """Remove teams that have no games. Returns count of removed teams."""
    cur = conn.execute(
        """
        DELETE FROM teams
        WHERE id NOT IN (
            SELECT team1_id FROM games
            UNION
            SELECT team2_id FROM games
        )
        """
    )
    conn.commit()
    return cur.rowcount


def merge_duplicate_players(conn: sqlite3.Connection, keep_id: int, remove_id: int) -> int:
    """Merge a duplicate player into another player record."""
    # Update all references from remove_id to keep_id
    updates = 0
    
    # Update boxscore_player
    cur = conn.execute(
        """
        UPDATE boxscore_player SET player_id = ?
        WHERE player_id = ? AND game_id NOT IN (
            SELECT game_id FROM boxscore_player WHERE player_id = ?
        )
        """,
        (keep_id, remove_id, keep_id),
    )
    updates += cur.rowcount
    
    # Delete duplicate entries (if same player in same game)
    conn.execute(
        "DELETE FROM boxscore_player WHERE player_id = ?",
        (remove_id,),
    )
    
    # Update sportsbook_lines
    cur = conn.execute(
        "UPDATE sportsbook_lines SET player_id = ? WHERE player_id = ?",
        (keep_id, remove_id),
    )
    updates += cur.rowcount
    
    # Update injury_report
    cur = conn.execute(
        "UPDATE injury_report SET player_id = ? WHERE player_id = ?",
        (keep_id, remove_id),
    )
    updates += cur.rowcount
    
    # Delete the duplicate player record
    conn.execute("DELETE FROM players WHERE id = ?", (remove_id,))
    
    conn.commit()
    return updates


# ============================================================================
# Data Freshness Validations
# ============================================================================

def check_data_freshness(conn: sqlite3.Connection, max_days_stale: int = 3) -> ValidationResult:
    """
    Check if game data is recent enough.
    
    Args:
        conn: Database connection
        max_days_stale: Maximum days since last game data
    
    Returns:
        ValidationResult with freshness status
    """
    row = conn.execute(
        "SELECT MAX(game_date) as last_date FROM games"
    ).fetchone()
    
    if not row or not row["last_date"]:
        return ValidationResult(
            check_name="data_freshness",
            passed=False,
            message="No game data found in database",
            severity="ERROR"
        )
    
    last_date = row["last_date"]
    try:
        last_dt = datetime.strptime(last_date, "%Y-%m-%d")
        days_old = (datetime.now() - last_dt).days
    except ValueError:
        return ValidationResult(
            check_name="data_freshness",
            passed=False,
            message=f"Invalid date format in database: {last_date}",
            severity="ERROR"
        )
    
    if days_old <= max_days_stale:
        return ValidationResult(
            check_name="data_freshness",
            passed=True,
            message=f"Data is fresh (last game: {last_date}, {days_old} days ago)"
        )
    
    return ValidationResult(
        check_name="data_freshness",
        passed=False,
        message=f"Data is stale: last game was {days_old} days ago ({last_date})",
        details=[{"last_game_date": last_date, "days_stale": days_old}],
        severity="WARNING"
    )


def check_team_game_coverage(conn: sqlite3.Connection, min_games: int = 5) -> ValidationResult:
    """
    Check that all teams have enough games for reliable projections.
    
    Args:
        conn: Database connection
        min_games: Minimum games required per team
    
    Returns:
        ValidationResult with team coverage
    """
    rows = conn.execute(
        """
        SELECT t.name, COUNT(DISTINCT g.id) as games
        FROM teams t
        LEFT JOIN games g ON g.team1_id = t.id OR g.team2_id = t.id
        GROUP BY t.id
        HAVING COUNT(DISTINCT g.id) < ?
        ORDER BY COUNT(DISTINCT g.id)
        """,
        (min_games,)
    ).fetchall()
    
    if not rows:
        return ValidationResult(
            check_name="team_game_coverage",
            passed=True,
            message=f"All teams have at least {min_games} games"
        )
    
    return ValidationResult(
        check_name="team_game_coverage",
        passed=False,
        message=f"Found {len(rows)} team(s) with fewer than {min_games} games",
        details=[{"team": r["name"], "games": r["games"]} for r in rows],
        severity="WARNING"
    )


def check_player_sample_sizes(conn: sqlite3.Connection, min_games: int = 5) -> ValidationResult:
    """
    Check how many players have sufficient games for reliable projections.
    
    Args:
        conn: Database connection
        min_games: Minimum games for reliable projection
    
    Returns:
        ValidationResult with player sample coverage
    """
    # Count players by game count bucket
    row = conn.execute(
        """
        SELECT 
            SUM(CASE WHEN games >= 20 THEN 1 ELSE 0 END) as good_sample,
            SUM(CASE WHEN games >= 10 AND games < 20 THEN 1 ELSE 0 END) as ok_sample,
            SUM(CASE WHEN games >= 5 AND games < 10 THEN 1 ELSE 0 END) as marginal_sample,
            SUM(CASE WHEN games < 5 THEN 1 ELSE 0 END) as insufficient_sample
        FROM (
            SELECT player_id, COUNT(*) as games
            FROM boxscore_player
            WHERE minutes > 0
            GROUP BY player_id
        )
        """
    ).fetchone()
    
    good = row["good_sample"] or 0
    ok = row["ok_sample"] or 0
    marginal = row["marginal_sample"] or 0
    insufficient = row["insufficient_sample"] or 0
    total = good + ok + marginal + insufficient
    
    details = {
        "good_sample_20+_games": good,
        "ok_sample_10-19_games": ok,
        "marginal_sample_5-9_games": marginal,
        "insufficient_under_5_games": insufficient,
        "total_players": total,
        "pct_reliable": round((good + ok) / total * 100, 1) if total > 0 else 0
    }
    
    if insufficient > total * 0.5:  # More than 50% have insufficient data
        return ValidationResult(
            check_name="player_sample_sizes",
            passed=False,
            message=f"Many players lack sufficient games ({insufficient} of {total})",
            details=[details],
            severity="WARNING"
        )
    
    return ValidationResult(
        check_name="player_sample_sizes",
        passed=True,
        message=f"{good + ok} players have reliable sample sizes (10+ games)",
        details=[details]
    )


def check_defense_data_availability(conn: sqlite3.Connection) -> ValidationResult:
    """
    Check if defense vs position data is available and recent.
    """
    # Check team_defense_vs_position table
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) as count, MAX(as_of_date) as last_date
            FROM team_defense_vs_position
            """
        ).fetchone()
        
        count = row["count"] or 0
        last_date = row["last_date"]
        
        if count == 0:
            return ValidationResult(
                check_name="defense_data_availability",
                passed=False,
                message="No defense vs position data available - projections will use league average",
                severity="WARNING"
            )
        
        # Check freshness
        if last_date:
            try:
                last_dt = datetime.strptime(last_date, "%Y-%m-%d")
                days_old = (datetime.now() - last_dt).days
                
                if days_old > 14:
                    return ValidationResult(
                        check_name="defense_data_availability",
                        passed=False,
                        message=f"Defense data is {days_old} days old (max recommended: 14)",
                        details=[{"last_update": last_date, "records": count}],
                        severity="WARNING"
                    )
            except ValueError:
                pass
        
        return ValidationResult(
            check_name="defense_data_availability",
            passed=True,
            message=f"Defense data available: {count} records",
            details=[{"last_update": last_date, "records": count}]
        )
        
    except Exception:
        # Table might not exist
        return ValidationResult(
            check_name="defense_data_availability",
            passed=False,
            message="Defense vs position table not found - using fallback calculations",
            severity="INFO"
        )


def get_projection_readiness_report(conn: sqlite3.Connection) -> dict:
    """
    Get a comprehensive report on whether the database is ready for projections.
    
    Returns:
        Dictionary with readiness status and any issues
    """
    issues = []
    warnings = []
    
    # Check data freshness
    freshness = check_data_freshness(conn)
    if not freshness.passed:
        if freshness.severity == "ERROR":
            issues.append(freshness.message)
        else:
            warnings.append(freshness.message)
    
    # Check team coverage
    team_coverage = check_team_game_coverage(conn)
    if not team_coverage.passed:
        warnings.append(team_coverage.message)
    
    # Check player samples
    player_samples = check_player_sample_sizes(conn)
    if not player_samples.passed:
        warnings.append(player_samples.message)
    
    # Check defense data
    defense_data = check_defense_data_availability(conn)
    if not defense_data.passed:
        if defense_data.severity == "WARNING":
            warnings.append(defense_data.message)
    
    # Determine overall readiness
    is_ready = len(issues) == 0
    
    return {
        "is_ready": is_ready,
        "critical_issues": issues,
        "warnings": warnings,
        "checks": {
            "data_freshness": freshness.passed,
            "team_coverage": team_coverage.passed,
            "player_samples": player_samples.passed,
            "defense_data": defense_data.passed
        },
        "details": {
            "freshness": freshness.details,
            "team_coverage": team_coverage.details,
            "player_samples": player_samples.details,
            "defense_data": defense_data.details
        }
    }


def run_all_validations_with_freshness(conn: sqlite3.Connection) -> ValidationReport:
    """Run all validation checks including freshness checks."""
    report = run_all_validations(conn)
    
    # Add freshness checks
    report.add_result(check_data_freshness(conn))
    report.add_result(check_team_game_coverage(conn))
    report.add_result(check_player_sample_sizes(conn))
    report.add_result(check_defense_data_availability(conn))
    
    return report

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .db import Db, init_db
from .ingest import ingest_boxscore_file
from .ingest.paste import save_pasted_boxscore_text
from .ingest.lines_parser import parse_lines_text
from .ingest.team_stats_ingest import ingest_team_stats_file
from .paths import get_paths
from .team_aliases import team_name_from_abbrev
from .util import normalize_team_name

# Flask is optional - only import when needed
FLASK_AVAILABLE = False
try:
    from flask import Flask
    FLASK_AVAILABLE = True
except ImportError:
    pass


def _run_web_app_if_available(host: str, port: int) -> int:
    """Run web app if Flask is available, otherwise show instructions."""
    if not FLASK_AVAILABLE:
        print("\n❌ Flask is not installed. The web GUI requires Flask.")
        print("\nTo install Flask, run:")
        print("    pip install flask")
        print("\nOr install with all optional dependencies:")
        print("    pip install -e '.[web]'")
        print("\n✅ All other CLI commands work without Flask!")
        print("   Try: python run_cli.py summary")
        print("   Try: python run_cli.py list-games")
        print("   Try: python run_cli.py seed-archetypes")
        return 1
    
    # Import and run web app only when Flask is available
    from .web.app import run_web_app
    run_web_app(host=host, port=port)
    return 0


def _cmd_init_db(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    init_db(db_path)
    print(f"Initialized DB: {db_path}")
    return 0


def _cmd_ingest_boxscore(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    init_db(db_path)  # safe to call repeatedly

    db = Db(path=db_path)
    source_file = Path(args.file).resolve()
    try:
        with db.connect() as conn:
            game_id = ingest_boxscore_file(conn, source_file=source_file)
            conn.commit()
        print(f"Ingested game_id={game_id} from {source_file}")
        return 0
    except ValueError as e:
        print(str(e))
        return 1


def _cmd_list_games(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    db = Db(path=db_path)
    limit = int(args.limit)
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT g.id, g.game_date, t1.name AS team1, t2.name AS team2, g.source_file
            FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            ORDER BY g.game_date DESC, g.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    for r in rows:
        print(f"{r['id']:>5}  {r['game_date']}  {r['team1']} vs {r['team2']}")
        if args.verbose:
            print(f"       {r['source_file']}")
    return 0


def _cmd_show_game(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    db = Db(path=db_path)
    game_id = int(args.game_id)
    with db.connect() as conn:
        g = conn.execute(
            """
            SELECT g.id, g.game_date, t1.name AS team1, t2.name AS team2
            FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            WHERE g.id = ?
            """,
            (game_id,),
        ).fetchone()
        if not g:
            print(f"Game id not found: {game_id}")
            return 1

        print(f"Game {g['id']} — {g['game_date']} — {g['team1']} vs {g['team2']}")
        rows = conn.execute(
            """
            SELECT t.name AS team, p.name AS player, b.pos, b.status, b.minutes, b.pts, b.reb, b.ast
            FROM boxscore_player b
            JOIN teams t ON t.id = b.team_id
            JOIN players p ON p.id = b.player_id
            WHERE b.game_id = ?
            ORDER BY t.name, (b.minutes IS NULL) ASC, b.minutes DESC, p.name
            """,
            (game_id,),
        ).fetchall()
    for r in rows:
        print(
            f"{r['team']:<22} {r['player']:<24} "
            f"{(r['pos'] or ''):<2} {(r['status'] or ''):<24} "
            f"MIN={r['minutes']!s:<5} PTS={r['pts']!s:<3} REB={r['reb']!s:<3} AST={r['ast']!s:<3}"
        )
    return 0


def _cmd_show_inactives(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    db = Db(path=db_path)
    game_id = int(args.game_id)
    with db.connect() as conn:
        g = conn.execute(
            """
            SELECT g.id, g.game_date, t1.name AS team1, t2.name AS team2
            FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            WHERE g.id = ?
            """,
            (game_id,),
        ).fetchone()
        if not g:
            print(f"Game id not found: {game_id}")
            return 1
        print(f"Inactive Players — Game {g['id']} — {g['game_date']} — {g['team1']} vs {g['team2']}")
        rows = conn.execute(
            """
            SELECT t.name AS team, ip.player_name, ip.reason
            FROM inactive_players ip
            JOIN teams t ON t.id = ip.team_id
            WHERE ip.game_id = ?
            ORDER BY t.name, ip.player_name
            """,
            (game_id,),
        ).fetchall()

    if not rows:
        print("(none)")
        return 0
    for r in rows:
        reason = "" if not r["reason"] else f" ({r['reason']})"
        print(f"{r['team']:<22} {r['player_name']}{reason}")
    return 0


def _cmd_summary(args: argparse.Namespace) -> int:
    from .engine.archetype_db import get_archetype_count_db
    from .engine.roster import PLAYER_DATABASE
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    with db.connect() as conn:
        counts = {
            "teams": conn.execute("SELECT COUNT(*) AS n FROM teams").fetchone()["n"],
            "players": conn.execute("SELECT COUNT(*) AS n FROM players").fetchone()["n"],
            "games": conn.execute("SELECT COUNT(*) AS n FROM games").fetchone()["n"],
            "boxscore_player_rows": conn.execute("SELECT COUNT(*) AS n FROM boxscore_player").fetchone()[
                "n"
            ],
            "sportsbook_lines": conn.execute("SELECT COUNT(*) AS n FROM sportsbook_lines").fetchone()["n"],
            "archetypes_in_db": get_archetype_count_db(conn, "2025-26"),
            "archetypes_defaults": len(PLAYER_DATABASE),
        }
    for k, v in counts.items():
        print(f"{k}: {v}")
    return 0


def _cmd_audit_duplicates(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    with db.connect() as conn:
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
            ORDER BY n.game_date DESC, cnt DESC;
            """
        ).fetchall()
    if not rows:
        print("No duplicate games found (by date + matchup).")
        return 0
    print("Duplicate games found (by date + matchup):")
    for r in rows:
        print(
            f"{r['game_date']}  {r['team_a']} vs {r['team_b']}  "
            f"count={r['cnt']}  game_ids={r['game_ids']}"
        )
    return 1


def _cmd_ingest_boxscore_stdin(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)

    text = sys.stdin.read()
    if not text.strip():
        print("No input read from stdin. Paste the box score text and then press Ctrl-D.", file=sys.stderr)
        return 2

    paths = get_paths()
    saved = save_pasted_boxscore_text(
        text=text,
        game_date=args.date,
        paths=paths,
        label=args.label,
    )

    with db.connect() as conn:
        game_id = ingest_boxscore_file(conn, source_file=saved.path)
        conn.commit()
    print(f"Ingested game_id={game_id} from pasted stdin (saved to {saved.path})")
    return 0


def _cmd_ingest_lines_stdin(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)

    text = sys.stdin.read()
    if not text.strip():
        print("No input read from stdin. Paste the lines text and then press Ctrl-D.", file=sys.stderr)
        return 2

    items = parse_lines_text(text)
    if not items:
        print("No lines were parsed. Make sure your paste includes section headers like 'Points line:'", file=sys.stderr)
        return 2

    as_of_date = args.date.strip()
    book = (args.book or "").strip() or None

    with db.connect() as conn:
        for it in items:
            # Create player if needed. Team/game may be unknown pre-game; keep NULL for now.
            player_id = conn.execute("SELECT id FROM players WHERE name = ?", (it.player,)).fetchone()
            if player_id:
                pid = int(player_id["id"])
            else:
                cur = conn.execute("INSERT INTO players(name) VALUES (?)", (it.player,))
                pid = int(cur.lastrowid)

            conn.execute(
                """
                INSERT INTO sportsbook_lines(as_of_date, game_id, team_id, player_id, prop_type, line, odds_american, book)
                VALUES (?, NULL, NULL, ?, ?, ?, ?, ?)
                """,
                (as_of_date, pid, it.prop_type, it.line, it.odds_american, book),
            )
        conn.commit()

    print(f"Inserted {len(items)} line(s) for as_of_date={as_of_date}")
    return 0


def _cmd_list_lines(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    date = (args.date or "").strip()
    with db.connect() as conn:
        if date:
            rows = conn.execute(
                """
                SELECT sl.as_of_date, p.name AS player, sl.prop_type, sl.line, sl.odds_american, sl.book
                FROM sportsbook_lines sl
                JOIN players p ON p.id = sl.player_id
                WHERE sl.as_of_date = ?
                ORDER BY p.name, sl.prop_type
                """,
                (date,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT sl.as_of_date, p.name AS player, sl.prop_type, sl.line, sl.odds_american, sl.book
                FROM sportsbook_lines sl
                JOIN players p ON p.id = sl.player_id
                ORDER BY sl.as_of_date DESC, p.name, sl.prop_type
                LIMIT 200
                """
            ).fetchall()
    for r in rows:
        odds = "" if r["odds_american"] is None else f"{int(r['odds_american']):+d}"
        book = "" if not r["book"] else f" ({r['book']})"
        print(f"{r['as_of_date']}  {r['player']}  {r['prop_type']} {r['line']}  {odds}{book}")
    return 0


def _cmd_ingest_team_stats(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)

    source_file = Path(args.file).resolve()
    team_raw = (args.team or "").strip()
    team_name: str | None
    if not team_raw:
        team_name = None
    elif 2 <= len(team_raw) <= 4 and team_raw.isalpha():
        team_name = team_name_from_abbrev(team_raw.upper())
        if not team_name:
            team_name = team_raw
    else:
        team_name = normalize_team_name(team_raw)

    as_of = (args.as_of or "").strip() or None

    with db.connect() as conn:
        snapshot_id = ingest_team_stats_file(conn, source_file=source_file, team_name=team_name, as_of_date=as_of)
        conn.commit()

    print(f"Ingested team stats snapshot_id={snapshot_id} from {source_file}")
    return 0


def _cmd_show_team_stats(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)

    team_raw = (args.team or "").strip()
    if not team_raw:
        print("Please provide --team (e.g. PHX or 'Phoenix Suns')", file=sys.stderr)
        return 2

    if 2 <= len(team_raw) <= 4 and team_raw.isalpha():
        team_name = team_name_from_abbrev(team_raw.upper()) or team_raw
    else:
        team_name = normalize_team_name(team_raw)

    limit = int(args.limit)
    with db.connect() as conn:
        snap = conn.execute(
            """
            SELECT s.id, s.season, s.as_of_date, s.source_file
            FROM team_stats_snapshot s
            JOIN teams t ON t.id = s.team_id
            WHERE t.name = ?
            ORDER BY COALESCE(s.as_of_date, '') DESC, s.id DESC
            LIMIT 1
            """,
            (team_name,),
        ).fetchone()

        if not snap:
            print(f"No team stats snapshots found for team: {team_name}")
            return 1

        print(f"Team Stats Snapshot {snap['id']} — {team_name} — season={snap['season']} as_of={snap['as_of_date']}")
        print(f"Source: {snap['source_file']}")
        print()

        rows = conn.execute(
            """
            SELECT p.name AS player, tsp.pos, tsp.min, tsp.pts, tsp.reb, tsp.ast, tsp.gp, tsp.gs
            FROM team_stats_player tsp
            JOIN players p ON p.id = tsp.player_id
            WHERE tsp.snapshot_id = ?
            ORDER BY (tsp.min IS NULL) ASC, tsp.min DESC, p.name
            LIMIT ?
            """,
            (int(snap["id"]), limit),
        ).fetchall()

    for r in rows:
        print(
            f"{r['player']:<24} {(r['pos'] or ''):<2} "
            f"GP={r['gp']!s:<3} GS={r['gs']!s:<3} "
            f"MIN={r['min']!s:<5} PTS={r['pts']!s:<5} REB={r['reb']!s:<5} AST={r['ast']!s:<5}"
        )
    return 0


def _cmd_seed_archetypes(args: argparse.Namespace) -> int:
    """Seed the database with default archetypes from the hard-coded PLAYER_DATABASE."""
    from .engine.archetype_db import seed_archetypes_from_defaults, get_archetype_count_db
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    season = (args.season or "2025-26").strip()
    overwrite = args.overwrite
    
    with db.connect() as conn:
        before_count = get_archetype_count_db(conn, season)
        count = seed_archetypes_from_defaults(conn, season, overwrite)
        after_count = get_archetype_count_db(conn, season)
    
    print(f"Seeded {count} player archetypes for season {season}")
    print(f"Database now has {after_count} archetypes (was {before_count})")
    if not overwrite:
        print("(Use --overwrite to update existing entries)")
    return 0


def _cmd_list_archetypes(args: argparse.Namespace) -> int:
    """List player archetypes in the database."""
    from .engine.archetype_db import get_all_archetypes_db, get_archetype_count_db
    from .engine.roster import PLAYER_DATABASE
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    season = (args.season or "2025-26").strip()
    tier = int(args.tier) if args.tier else None
    team = (args.team or "").strip() or None
    
    with db.connect() as conn:
        archetypes = get_all_archetypes_db(conn, season=season, tier=tier, team=team)
        db_count = get_archetype_count_db(conn, season)
    
    if not archetypes:
        print(f"No archetypes found in database for season {season}")
        print(f"(Defaults available: {len(PLAYER_DATABASE)} players)")
        print("Run 'seed-archetypes' to populate the database from defaults")
        return 0
    
    print(f"Player Archetypes (season={season}, db_count={db_count})")
    if tier:
        print(f"  Filtered to tier: {tier}")
    if team:
        print(f"  Filtered to team: {team}")
    print()
    
    for a in archetypes:
        elite = "*" if a.is_elite_defender else " "
        print(
            f"T{a.tier}{elite} {a.player_name:<24} {(a.team or 'Unknown'):<24} "
            f"{a.primary_offensive:<20} src={a.source}"
        )
    
    print()
    print(f"Total: {len(archetypes)} archetypes shown")
    return 0


def _cmd_show_archetype(args: argparse.Namespace) -> int:
    """Show detailed archetype info for a specific player."""
    from .engine.archetype_db import get_player_archetype_db, get_similar_players_db
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    player_name = args.player.strip()
    season = (args.season or "2025-26").strip()
    
    with db.connect() as conn:
        archetype = get_player_archetype_db(conn, player_name, season)
        similar = get_similar_players_db(conn, player_name, season) if archetype else []
    
    if not archetype:
        print(f"No archetype found for player: {player_name}")
        return 1
    
    print(f"Player Archetype: {archetype.player_name}")
    print(f"  Team:           {archetype.team or 'Unknown'}")
    print(f"  Position:       {archetype.position or 'Unknown'}")
    print(f"  Height:         {archetype.height or 'Unknown'}")
    print(f"  Tier:           {archetype.tier}")
    print()
    print(f"  Primary Off:    {archetype.primary_offensive}")
    print(f"  Secondary Off:  {archetype.secondary_offensive or 'None'}")
    print(f"  Defensive Role: {archetype.defensive_role}")
    print(f"  Elite Defender: {'Yes' if archetype.is_elite_defender else 'No'}")
    print()
    
    if archetype.strengths:
        print(f"  Strengths:      {', '.join(archetype.strengths[:3])}")
    if archetype.weaknesses:
        print(f"  Weaknesses:     {', '.join(archetype.weaknesses[:3])}")
    if archetype.notes:
        print(f"  Notes:          {archetype.notes[:80]}...")
    if archetype.guards_positions:
        print(f"  Guards Pos:     {', '.join(archetype.guards_positions)}")
    
    print()
    print(f"  Source:         {archetype.source}")
    print(f"  Confidence:     {archetype.confidence}")
    
    if similar:
        print()
        print(f"  Similar Players: {', '.join(similar[:5])}")
    
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """Run data validation checks on the database."""
    from .validation import run_all_validations, cleanup_orphaned_teams
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    with db.connect() as conn:
        report = run_all_validations(conn)
        
        print(f"\n{'='*60}")
        print("NBA Props Database Validation Report")
        print(f"{'='*60}\n")
        
        for result in report.results:
            status = "✅ PASS" if result.passed else ("❌ ERROR" if result.severity == "ERROR" else "⚠️  WARN" if result.severity == "WARNING" else "ℹ️  INFO")
            print(f"{status}: {result.check_name}")
            print(f"       {result.message}")
            
            if not result.passed and (args.verbose or result.severity == "ERROR"):
                for detail in result.details[:5]:  # Show first 5 details
                    print(f"         → {detail}")
                if len(result.details) > 5:
                    print(f"         ... and {len(result.details) - 5} more")
            print()
        
        print(f"{'='*60}")
        print(f"Summary: {report.passed_checks}/{report.total_checks} checks passed")
        print(f"         Errors: {report.errors}, Warnings: {report.warnings}")
        print(f"{'='*60}\n")
        
        # Attempt fixes if requested
        if args.fix and (report.errors > 0 or report.warnings > 0):
            print("Attempting automatic fixes...")
            
            # Clean up orphaned teams
            count = cleanup_orphaned_teams(conn)
            if count > 0:
                print(f"  - Removed {count} orphaned team(s)")
            else:
                print("  - No orphaned teams to remove")
            
            print("\nRe-running validation...")
            report = run_all_validations(conn)
            print(f"After fixes: {report.passed_checks}/{report.total_checks} checks passed")
    
    return 1 if report.errors > 0 else 0


def _cmd_cleanup(args: argparse.Namespace) -> int:
    """Clean up orphaned data from the database."""
    from .validation import cleanup_orphaned_teams
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    with db.connect() as conn:
        # Check what would be cleaned
        orphaned_teams = conn.execute(
            """
            SELECT t.id, t.name
            FROM teams t
            LEFT JOIN games g ON g.team1_id = t.id OR g.team2_id = t.id
            WHERE g.id IS NULL
            ORDER BY t.name
            """
        ).fetchall()
        
        if not orphaned_teams:
            print("No orphaned data found to clean up.")
            return 0
        
        print(f"Found {len(orphaned_teams)} orphaned team(s):")
        for t in orphaned_teams:
            print(f"  - {t['name']} (id={t['id']})")
        
        if args.dry_run:
            print("\nDry run - no changes made.")
            return 0
        
        print("\nCleaning up...")
        count = cleanup_orphaned_teams(conn)
        print(f"Removed {count} orphaned team(s).")
    
    return 0


def _cmd_purge_test_data(args: argparse.Namespace) -> int:
    """Purge scheduled matchup + generated picks for a specific date.

    Intended for removing test data that was accidentally created.
    """
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)

    target_date = str(args.date).strip()
    away = (args.away or "").strip().upper()
    home = (args.home or "").strip().upper()
    dry_run = bool(args.dry_run)

    if not target_date:
        print("--date is required")
        return 2

    def _team_id_by_name(conn, team_name: str) -> int | None:
        row = conn.execute("SELECT id FROM teams WHERE name = ?", (team_name,)).fetchone()
        return int(row["id"]) if row else None

    summary: list[str] = []
    with db.connect() as conn:
        # ------------------------------------------------------------------
        # Backtesting picks/history
        # ------------------------------------------------------------------
        picks_cnt = conn.execute(
            "SELECT COUNT(*) AS n FROM model_picks WHERE pick_date = ?",
            (target_date,),
        ).fetchone()["n"]
        perf_cnt = conn.execute(
            "SELECT COUNT(*) AS n FROM model_performance_daily WHERE performance_date = ?",
            (target_date,),
        ).fetchone()["n"]

        if not dry_run:
            conn.execute("DELETE FROM model_picks WHERE pick_date = ?", (target_date,))
            conn.execute(
                "DELETE FROM model_performance_daily WHERE performance_date = ?",
                (target_date,),
            )

        summary.append(f"model_picks deleted: {picks_cnt}")
        summary.append(f"model_performance_daily deleted: {perf_cnt}")

        # ------------------------------------------------------------------
        # Scheduled matchup + any related game/lines
        # ------------------------------------------------------------------
        if away and home:
            away_name = team_name_from_abbrev(away)
            home_name = team_name_from_abbrev(home)
            if not away_name or not home_name:
                print(f"Invalid team abbrev(s): away={away!r} home={home!r}")
                return 2

            away_id = _team_id_by_name(conn, away_name)
            home_id = _team_id_by_name(conn, home_name)
            if away_id is None or home_id is None:
                # If the matchup was inserted via UI, these should exist.
                summary.append(
                    f"scheduled_games deleted: 0 (teams missing in DB for {away}@{home})"
                )
                summary.append("game_lines deleted: 0")
                summary.append("games deleted: 0")
            else:
                sched_cnt = conn.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM scheduled_games
                    WHERE game_date = ?
                      AND ((away_team_id = ? AND home_team_id = ?)
                           OR (away_team_id = ? AND home_team_id = ?))
                    """,
                    (target_date, away_id, home_id, home_id, away_id),
                ).fetchone()["n"]

                game_lines_cnt = conn.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM game_lines
                    WHERE game_date = ?
                      AND ((away_team_id = ? AND home_team_id = ?)
                           OR (away_team_id = ? AND home_team_id = ?))
                    """,
                    (target_date, away_id, home_id, home_id, away_id),
                ).fetchone()["n"]

                game_ids = conn.execute(
                    """
                    SELECT id
                    FROM games
                    WHERE game_date = ?
                      AND ((team1_id = ? AND team2_id = ?)
                           OR (team1_id = ? AND team2_id = ?))
                    """,
                    (target_date, away_id, home_id, home_id, away_id),
                ).fetchall()

                sportsbook_lines_deleted = 0
                games_deleted = 0

                if not dry_run:
                    conn.execute(
                        """
                        DELETE FROM scheduled_games
                        WHERE game_date = ?
                          AND ((away_team_id = ? AND home_team_id = ?)
                               OR (away_team_id = ? AND home_team_id = ?))
                        """,
                        (target_date, away_id, home_id, home_id, away_id),
                    )
                    conn.execute(
                        """
                        DELETE FROM game_lines
                        WHERE game_date = ?
                          AND ((away_team_id = ? AND home_team_id = ?)
                               OR (away_team_id = ? AND home_team_id = ?))
                        """,
                        (target_date, away_id, home_id, home_id, away_id),
                    )

                    # sportsbook_lines doesn't cascade on game delete; clean it explicitly.
                    for r in game_ids:
                        gid = int(r["id"])
                        sportsbook_lines_deleted += conn.execute(
                            "DELETE FROM sportsbook_lines WHERE game_id = ?",
                            (gid,),
                        ).rowcount
                        games_deleted += conn.execute("DELETE FROM games WHERE id = ?", (gid,)).rowcount

                summary.append(f"scheduled_games deleted: {sched_cnt}")
                summary.append(f"game_lines deleted: {game_lines_cnt}")
                summary.append(f"sportsbook_lines deleted: {sportsbook_lines_deleted}")
                summary.append(f"games deleted: {len(game_ids) if dry_run else games_deleted}")

        if not dry_run:
            conn.commit()

    print(f"Purge complete for {target_date}{' (dry-run)' if dry_run else ''}:")
    for line in summary:
        print(f"- {line}")
    return 0


def _cmd_backtest(args: argparse.Namespace) -> int:
    """Run backtest comparing projections to actual outcomes."""
    from datetime import datetime, timedelta
    from .engine.backtesting import run_backtest
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    # Default to last 30 days if not specified
    end_date = (args.end or "").strip() or datetime.now().strftime("%Y-%m-%d")
    start_date = (args.start or "").strip()
    if not start_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        start_dt = end_dt - timedelta(days=30)
        start_date = start_dt.strftime("%Y-%m-%d")
    
    min_edge = args.min_edge
    
    with db.connect() as conn:
        result = run_backtest(conn, start_date, end_date, min_edge)
        
        print(f"\n{'='*70}")
        print(f"Backtest Results: {start_date} to {end_date}")
        print(f"{'='*70}\n")
        
        if result.total_props == 0:
            print("No props found for backtesting in this date range.")
            print("Make sure you have both sportsbook lines AND game results.")
            return 0
        
        print(f"Total Props Evaluated: {result.total_props}")
        print(f"Minimum Edge: {min_edge}%\n")
        
        print(f"Overall Results:")
        print(f"  Hits:    {result.hits}")
        print(f"  Misses:  {result.misses}")
        print(f"  Hit Rate: {result.hit_rate*100:.1f}%\n")
        
        print(f"By Prop Type:")
        if result.pts_total > 0:
            print(f"  PTS: {result.pts_hits}/{result.pts_total} ({result.pts_hits/result.pts_total*100:.1f}%)")
        if result.reb_total > 0:
            print(f"  REB: {result.reb_hits}/{result.reb_total} ({result.reb_hits/result.reb_total*100:.1f}%)")
        if result.ast_total > 0:
            print(f"  AST: {result.ast_hits}/{result.ast_total} ({result.ast_hits/result.ast_total*100:.1f}%)")
        
        print(f"\nBy Confidence:")
        if result.high_conf_total > 0:
            print(f"  HIGH:   {result.high_conf_hits}/{result.high_conf_total} ({result.high_conf_hits/result.high_conf_total*100:.1f}%)")
        if result.med_conf_total > 0:
            print(f"  MEDIUM: {result.med_conf_hits}/{result.med_conf_total} ({result.med_conf_hits/result.med_conf_total*100:.1f}%)")
        if result.low_conf_total > 0:
            print(f"  LOW:    {result.low_conf_hits}/{result.low_conf_total} ({result.low_conf_hits/result.low_conf_total*100:.1f}%)")
        
        print(f"\nBy Direction:")
        if result.over_total > 0:
            print(f"  OVER:  {result.over_hits}/{result.over_total} ({result.over_hits/result.over_total*100:.1f}%)")
        if result.under_total > 0:
            print(f"  UNDER: {result.under_hits}/{result.under_total} ({result.under_hits/result.under_total*100:.1f}%)")
        
        print(f"\nTheoretical Performance:")
        print(f"  Total Wagers: ${result.theoretical_wagers:,.0f}")
        print(f"  Profit/Loss:  ${result.theoretical_profit:+,.2f}")
        print(f"  ROI: {result.theoretical_roi:+.2f}%")
        
        # Calibration
        print(f"\nCalibration (predicted probability vs actual hit rate):")
        for bin_name, bin_data in result.calibration_bins.items():
            if bin_data["predicted"] > 0:
                actual_rate = bin_data["actual"] / bin_data["predicted"] * 100
                print(f"  {bin_name}%: {bin_data['actual']}/{bin_data['predicted']} ({actual_rate:.0f}%)")
    
    return 0


def _cmd_model_picks(args: argparse.Namespace) -> int:
    """Generate picks using the optimized Model Final."""
    from datetime import datetime, timedelta
    from .engine.model_final import get_daily_picks, run_full_backtest, ModelFinalConfig
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    
    game_date = (args.date or "").strip()
    if not game_date:
        game_date = datetime.now().strftime("%Y-%m-%d")
    
    backtest_mode = args.backtest
    
    if backtest_mode:
        # Run backtest mode
        days = int(args.days or 21)
        end_date = game_date
        start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
        
        result = run_full_backtest(start_date, end_date, db_path=str(db_path), verbose=True)
        return 0
    
    # Generate picks for a specific date
    picks = get_daily_picks(game_date, db_path=str(db_path))
    
    if picks.picks_count == 0:
        print(f"No picks generated for {game_date}")
        print("Make sure there are games on this date with sufficient player history.")
        return 1
    
    print(f"\n{'='*70}")
    print(f"MODEL FINAL PICKS FOR {game_date}")
    print(f"{'='*70}")
    print(f"Games: {picks.games} | Total Picks: {picks.picks_count} | HIGH Confidence: {picks.high_count}")
    print()
    
    # Group by confidence tier
    high_picks = [p for p in picks.picks if p.confidence_tier == "HIGH"]
    medium_picks = [p for p in picks.picks if p.confidence_tier == "MEDIUM"]
    
    if high_picks:
        print("=" * 70)
        print("HIGH CONFIDENCE PICKS (Expected ~70% hit rate)")
        print("=" * 70)
        for i, pick in enumerate(high_picks, 1):
            print(f"\n#{i}: {pick.player_name} ({pick.team_abbrev} vs {pick.opponent_abbrev})")
            print(f"    {pick.prop_type} {pick.direction}")
            print(f"    Projection: {pick.projected_value} | Line: {pick.line} | Edge: {pick.edge_pct}%")
            print(f"    Confidence: {pick.confidence_score}/100")
            if pick.reasons:
                print(f"    Reasons: {'; '.join(pick.reasons[:3])}")
            if pick.warnings:
                print(f"    ⚠️  Warnings: {'; '.join(pick.warnings)}")
    
    if medium_picks:
        print("\n" + "=" * 70)
        print("MEDIUM CONFIDENCE PICKS (Expected ~60% hit rate)")
        print("=" * 70)
        for i, pick in enumerate(medium_picks, 1):
            print(f"\n#{i}: {pick.player_name} ({pick.team_abbrev} vs {pick.opponent_abbrev})")
            print(f"    {pick.prop_type} {pick.direction}")
            print(f"    Projection: {pick.projected_value} | Line: {pick.line} | Edge: {pick.edge_pct}%")
            print(f"    Confidence: {pick.confidence_score}/100")
    
    print("\n" + "=" * 70)
    print("Note: Lines are calculated as L10/L7/L5 averages per specification.")
    print("HIGH confidence picks have historically hit at ~70%, MEDIUM at ~60%.")
    print("=" * 70)
    
    return 0


def _cmd_model_backtest(args: argparse.Namespace) -> int:
    """Run comprehensive backtest of Model Final."""
    from datetime import datetime, timedelta
    from .engine.model_final import run_full_backtest
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    
    weeks = int(args.weeks or 4)
    days = weeks * 7
    end_date = (args.end or "").strip() or datetime.now().strftime("%Y-%m-%d")
    start_date = (args.start or "").strip()
    
    if not start_date:
        start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
    
    result = run_full_backtest(start_date, end_date, db_path=str(db_path), verbose=True)
    return 0


def _cmd_accuracy(args: argparse.Namespace) -> int:
    """Analyze projection accuracy for a player."""
    from .engine.backtesting import compare_projection_accuracy
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    player_name = (args.player or "").strip()
    stat = (args.stat or "PTS").strip().upper()
    games = args.games
    
    with db.connect() as conn:
        result = compare_projection_accuracy(conn, player_name, stat, games)
        
        if not result:
            print(f"Not enough data for player: {player_name}")
            return 1
        
        print(f"\n{'='*60}")
        print(f"Projection Accuracy: {result['player']}")
        print(f"Stat: {result['prop_type']}")
        print(f"{'='*60}\n")
        
        print(f"Games Analyzed: {result['games_analyzed']}")
        print(f"Average Error: {result['avg_error']:+.1f} ({result['bias']})")
        print(f"Average Absolute Error: {result['avg_abs_error']:.1f}")
        print(f"Within 1 Std Dev: {result['within_std_pct']:.0f}%")
        
        print(f"\nRecent Games:")
        print(f"{'Date':<12} {'Actual':>8} {'Proj':>8} {'Error':>8} {'Std':>8} {'InStd'}")
        print("-" * 55)
        for c in result["recent_comparisons"]:
            in_std = "✓" if c["within_std"] else ""
            print(f"{c['date']:<12} {c['actual']:>8} {c['projected']:>8.1f} {c['error']:>+8.1f} {c['std']:>8.1f} {in_std:>5}")
    
    return 0


def _cmd_bias_analysis(args: argparse.Namespace) -> int:
    """Analyze systematic projection biases across all players."""
    from .engine.backtesting import analyze_projection_bias
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    min_games = args.min_games
    
    with db.connect() as conn:
        result = analyze_projection_bias(conn, min_games)
        
        print(f"\n{'='*60}")
        print(f"Projection Bias Analysis")
        print(f"{'='*60}\n")
        
        print(f"Players Analyzed: {result['players_analyzed']}")
        print(f"Total Comparisons: {result['total_comparisons']}")
        print(f"Minimum Games per Player: {min_games}\n")
        
        print(f"Bias by Stat Type:")
        print(f"{'Stat':<6} {'Count':>8} {'Mean Err':>10} {'Abs Err':>10} {'Std Dev':>10} {'Interpretation'}")
        print("-" * 60)
        
        for stat in ["pts", "reb", "ast"]:
            data = result[stat]
            if data["count"] > 0:
                mean = data["mean"]
                if mean > 0.5:
                    interp = "Underprojects"
                elif mean < -0.5:
                    interp = "Overprojects"
                else:
                    interp = "Neutral"
                print(f"{stat.upper():<6} {data['count']:>8} {mean:>+10.2f} {data['abs_mean']:>10.2f} {data['std']:>10.2f} {interp}")
        
        print(f"\nInterpretation:")
        print("  - Positive mean error = projections are too low (underproject)")
        print("  - Negative mean error = projections are too high (overproject)")
        print("  - Lower std dev = more consistent projections")
    
    return 0


def _cmd_alerts(args: argparse.Namespace) -> int:
    """Find prop edges where projection differs from line."""
    from datetime import datetime
    from .engine.alerts import scan_for_edge_alerts, find_value_plays_by_team
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    scan_date = (args.date or "").strip() or datetime.now().strftime("%Y-%m-%d")
    min_edge = args.min_edge
    team_filter = (args.team or "").strip().upper()
    
    with db.connect() as conn:
        if team_filter:
            # Filter to specific team
            alerts = find_value_plays_by_team(conn, team_filter, scan_date, min_edge)
            
            print(f"\n{'='*70}")
            print(f"Edge Alerts for {team_filter} - {scan_date}")
            print(f"{'='*70}\n")
            
            if not alerts:
                print(f"No edges found with >= {min_edge}% edge for {team_filter}")
                return 0
            
            print(f"Found {len(alerts)} edge(s):\n")
        else:
            # Scan all lines
            result = scan_for_edge_alerts(conn, scan_date, min_edge)
            
            print(f"\n{'='*70}")
            print(f"Edge Alert Scan - {scan_date}")
            print(f"{'='*70}\n")
            
            print(f"Lines Scanned: {result.lines_scanned}")
            print(f"Alerts Found: {result.alerts_found}")
            print(f"Minimum Edge: {min_edge}%\n")
            
            if result.alerts_found == 0:
                print(f"No edges found with >= {min_edge}% edge")
                print("Make sure you have lines imported for this date.")
                return 0
            
            alerts = result.all_alerts
        
        # Display alerts
        print(f"{'Player':<24} {'Team':<5} {'Prop':<4} {'Dir':<6} {'Line':>6} {'Proj':>6} {'Edge':>6} {'Conf'}")
        print("-" * 75)
        
        for alert in alerts:
            conf_marker = "🔥" if alert.confidence == "HIGH" else "⚡" if alert.confidence == "MEDIUM" else "•"
            print(f"{alert.player_name:<24} {alert.team_abbrev:<5} {alert.prop_type:<4} {alert.direction:<6} "
                  f"{alert.line:>6.1f} {alert.projected_value:>6.1f} {alert.edge_pct:>5.1f}% {conf_marker}")
            
            if alert.reasons and alert.confidence in ("HIGH", "MEDIUM"):
                for reason in alert.reasons[:2]:
                    print(f"    → {reason}")
        
        if not team_filter:
            # Summary
            high = len(result.high_confidence)
            med = len(result.medium_confidence)
            
            print(f"\nSummary:")
            print(f"  🔥 High confidence: {high}")
            print(f"  ⚡ Medium confidence: {med}")
            
            # Best plays
            if result.high_confidence:
                print(f"\n🔥 Top High-Confidence Plays:")
                for a in result.high_confidence[:3]:
                    diff = a.projected_value - a.line
                    print(f"   {a.player_name} {a.prop_type} {a.direction}: proj {a.projected_value:.1f} vs line {a.line} ({diff:+.1f})")
    
    return 0


def _cmd_matchup(args: argparse.Namespace) -> int:
    """Generate matchup-specific prop recommendations."""
    from datetime import datetime
    from .engine.game_context import (
        generate_matchup_recommendations,
        get_back_to_back_status,
        get_team_defense_rating,
    )
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    away = (args.away or "").strip().upper()
    home = (args.home or "").strip().upper()
    game_date = (args.date or "").strip() or datetime.now().strftime("%Y-%m-%d")
    min_edge = args.min_edge
    
    with db.connect() as conn:
        # Get context info
        away_b2b = get_back_to_back_status(conn, away, game_date)
        home_b2b = get_back_to_back_status(conn, home, game_date)
        away_def = get_team_defense_rating(conn, away)
        home_def = get_team_defense_rating(conn, home)
        
        # Get recommendations
        recommendations = generate_matchup_recommendations(
            conn, away, home, game_date, min_edge
        )
        
        print(f"\n{'='*80}")
        print(f"Matchup Analysis: {away} @ {home}")
        print(f"Date: {game_date}")
        print(f"{'='*80}")
        
        print(f"\nContext:")
        print(f"  {away}: B2B={'Yes' if away_b2b.is_back_to_back else 'No'}, Rest={away_b2b.rest_days} days")
        print(f"  {home}: B2B={'Yes' if home_b2b.is_back_to_back else 'No'}, Rest={home_b2b.rest_days} days")
        
        print(f"\nDefense Ratings:")
        if away_def:
            print(f"  {away}: PTS factor={away_def.pts_factor:.2f}, REB={away_def.reb_factor:.2f}, AST={away_def.ast_factor:.2f}")
        if home_def:
            print(f"  {home}: PTS factor={home_def.pts_factor:.2f}, REB={home_def.reb_factor:.2f}, AST={home_def.ast_factor:.2f}")
        
        if not recommendations:
            print(f"\nNo recommendations with edge >= {min_edge}%")
            return 0
        
        print(f"\n{'='*80}")
        print(f"Prop Recommendations (edge >= {min_edge}%)")
        print(f"{'='*80}\n")
        
        for r in recommendations:
            conf_marker = "🔥" if r.confidence == "HIGH" else "⚡" if r.confidence == "MEDIUM" else "•"
            print(f"{conf_marker} {r.player_name} ({r.team_abbrev}) - {r.prop_type} {r.direction}")
            print(f"    Baseline: {r.baseline_value:.1f} → Adjusted: {r.adjusted_value:.1f}")
            print(f"    vs {r.opponent_abbrev} defense: {r.defense_rating}")
            if r.reasoning:
                for reason in r.reasoning:
                    print(f"    • {reason}")
            print()
        
        # Summary
        high_conf = len([r for r in recommendations if r.confidence == "HIGH"])
        med_conf = len([r for r in recommendations if r.confidence == "MEDIUM"])
        
        print(f"Summary: {len(recommendations)} total recommendations")
        print(f"  🔥 High confidence: {high_conf}")
        print(f"  ⚡ Medium confidence: {med_conf}")
    
    return 0


def _cmd_usage_impact(args: argparse.Namespace) -> int:
    """Show how a player's absence impacts teammates."""
    from .engine.usage_redistribution import (
        calculate_usage_redistribution,
        get_team_usage_profiles,
        get_historical_impact,
    )
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    team = (args.team or "").strip().upper()
    absent_player = (args.out or "").strip()
    show_historical = args.historical
    
    with db.connect() as conn:
        # Get team usage profiles
        profiles = get_team_usage_profiles(conn, team)
        
        if not profiles:
            print(f"No data available for team: {team}")
            return 1
        
        print(f"\n{'='*70}")
        print(f"Team Usage Profiles: {team}")
        print(f"{'='*70}\n")
        
        print(f"{'Player':<24} {'Pos':<4} {'MIN':>6} {'PTS':>6} {'REB':>5} {'AST':>5} {'Usage':>7} {'Tier'}")
        print("-" * 70)
        
        for p in profiles[:10]:
            print(f"{p.player_name:<24} {(p.position or ''):<4} {p.avg_minutes:>6.1f} {p.avg_pts:>6.1f} "
                  f"{p.avg_reb:>5.1f} {p.avg_ast:>5.1f} {p.usage_rate*100:>6.1f}% T{p.tier}")
        
        # Calculate redistribution
        result = calculate_usage_redistribution(conn, team, absent_player)
        
        if not result:
            print(f"\nPlayer not found: {absent_player}")
            return 1
        
        print(f"\n{'='*70}")
        print(f"Usage Redistribution: {result.absent_player} is OUT")
        print(f"{'='*70}")
        print(f"\nAbsent player's typical contribution:")
        print(f"  PTS: {result.absent_stats['avg_pts']:.1f}")
        print(f"  REB: {result.absent_stats['avg_reb']:.1f}")
        print(f"  AST: {result.absent_stats['avg_ast']:.1f}")
        print(f"  MIN: {result.absent_stats['avg_min']:.1f}")
        print(f"  Usage Rate: {result.absent_stats['usage_rate']*100:.1f}%")
        
        print(f"\nProjected boosts for teammates:")
        print(f"{'Player':<24} {'Baseline':>18} {'Boost':>18} {'Projected':>18}")
        print(f"{'':24} {'PTS REB AST':>18} {'PTS REB AST':>18} {'PTS REB AST':>18}")
        print("-" * 84)
        
        for r in result.redistributions:
            baseline = f"{r['baseline_pts']:>5.1f} {r['baseline_reb']:>4.1f} {r['baseline_ast']:>4.1f}"
            boost = f"+{r['pts_boost']:>4.1f} +{r['reb_boost']:>3.1f} +{r['ast_boost']:>3.1f}"
            projected = f"{r['projected_pts']:>5.1f} {r['projected_reb']:>4.1f} {r['projected_ast']:>4.1f}"
            print(f"{r['player']:<24} {baseline:>18} {boost:>18} {projected:>18}")
        
        print(f"\nTotal redistributed: PTS={result.total_pts_redistributed:.1f}, "
              f"REB={result.total_reb_redistributed:.1f}, AST={result.total_ast_redistributed:.1f}")
        
        # Show historical impact if requested
        if show_historical:
            historical = get_historical_impact(conn, team, absent_player)
            
            if historical and historical["teammate_impacts"]:
                print(f"\n{'='*70}")
                print(f"Historical Impact Analysis")
                print(f"{'='*70}")
                print(f"Based on {historical['games_with_player']} games with {historical['absent_player']} "
                      f"vs {historical['games_without_player']} games without")
                print()
                
                print(f"{'Teammate':<24} {'With (PTS/REB/AST)':<20} {'Without':<20} {'Difference':<20}")
                print("-" * 84)
                
                for impact in historical["teammate_impacts"][:8]:
                    with_stats = impact["with_absent_player"]
                    without_stats = impact["without_absent_player"]
                    diff = impact["difference"]
                    
                    with_str = f"{with_stats['pts']:>5.1f}/{with_stats['reb']:>4.1f}/{with_stats['ast']:>4.1f}"
                    without_str = f"{without_stats['pts']:>5.1f}/{without_stats['reb']:>4.1f}/{without_stats['ast']:>4.1f}"
                    diff_str = f"{diff['pts']:>+5.1f}/{diff['reb']:>+4.1f}/{diff['ast']:>+4.1f}"
                    
                    print(f"{impact['player']:<24} {with_str:<20} {without_str:<20} {diff_str:<20}")
            else:
                print("\nNo historical data available (need games without this player)")
    
    return 0


def _cmd_project(args: argparse.Namespace) -> int:
    """Generate projections for a player or team."""
    from datetime import datetime
    from .engine.projector import project_team_players, project_player_stats, ProjectionConfig
    from .engine.game_context import get_back_to_back_status, get_team_defense_rating, apply_matchup_adjustments
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    team = (args.team or "").strip().upper()
    player_name = (args.player or "").strip()
    opponent = (args.opponent or "").strip().upper()
    game_date = (args.date or "").strip() or datetime.now().strftime("%Y-%m-%d")
    
    if not team and not player_name:
        print("Please provide --team or --player", file=sys.stderr)
        return 2
    
    with db.connect() as conn:
        if team:
            # Get back-to-back status
            b2b = get_back_to_back_status(conn, team, game_date)
            
            # Get opponent defense rating if specified
            opp_defense = None
            if opponent:
                opp_defense = get_team_defense_rating(conn, opponent)
            
            # Generate projections
            projections = project_team_players(
                conn=conn,
                team_abbrev=team,
                opponent_abbrev=opponent or None,
                is_back_to_back=b2b.is_back_to_back,
                rest_days=b2b.rest_days,
            )
            
            if not projections:
                print(f"No projections available for team: {team}")
                print("(Need at least 3 games of data)")
                return 1
            
            print(f"\n{'='*70}")
            print(f"Projections for {team}" + (f" vs {opponent}" if opponent else ""))
            print(f"Date: {game_date}")
            print(f"Back-to-back: {'Yes' if b2b.is_back_to_back else 'No'}, Rest days: {b2b.rest_days}")
            if opp_defense:
                print(f"Opponent defense factors: PTS={opp_defense.pts_factor:.2f}, REB={opp_defense.reb_factor:.2f}, AST={opp_defense.ast_factor:.2f}")
            print(f"{'='*70}\n")
            
            print(f"{'Player':<24} {'Pos':<4} {'MIN':>6} {'PTS':>6} {'REB':>6} {'AST':>6} {'Games':>6} {'Top7'}")
            print("-" * 70)
            
            for proj in projections:
                # Apply opponent adjustments
                if opp_defense:
                    adj_pts, adj_reb, adj_ast, _ = apply_matchup_adjustments(
                        proj.proj_pts, proj.proj_reb, proj.proj_ast, opp_defense
                    )
                else:
                    adj_pts, adj_reb, adj_ast = proj.proj_pts, proj.proj_reb, proj.proj_ast
                
                top7 = "✓" if proj.is_top_7 else ""
                print(f"{proj.player_name:<24} {(proj.position or ''):<4} {proj.proj_minutes:>6.1f} {adj_pts:>6.1f} {adj_reb:>6.1f} {adj_ast:>6.1f} {proj.games_played:>6} {top7:>4}")
        
        else:
            # Single player projection
            player_row = conn.execute(
                "SELECT id, name FROM players WHERE name LIKE ?", (f"%{player_name}%",)
            ).fetchone()
            
            if not player_row:
                print(f"Player not found: {player_name}")
                return 1
            
            proj = project_player_stats(
                conn=conn,
                player_id=player_row["id"],
                opponent_abbrev=opponent or None,
                is_back_to_back=False,
                rest_days=1,
            )
            
            if not proj:
                print(f"No projections available for player: {player_row['name']}")
                print("(Need at least 3 games of data)")
                return 1
            
            print(f"\nProjection for {proj.player_name}")
            print(f"Team: {proj.team_abbrev}")
            print(f"Position: {proj.position or 'Unknown'}")
            print(f"Games sampled: {proj.games_played}")
            print()
            print(f"  Minutes: {proj.proj_minutes:.1f} (±{proj.minutes_std:.1f})")
            print(f"  Points:  {proj.proj_pts:.1f} (±{proj.pts_std:.1f})")
            print(f"  Rebounds: {proj.proj_reb:.1f} (±{proj.reb_std:.1f})")
            print(f"  Assists: {proj.proj_ast:.1f} (±{proj.ast_std:.1f})")
            print()
            print("Per-minute rates:")
            print(f"  PTS/min: {proj.pts_per_min:.3f}")
            print(f"  REB/min: {proj.reb_per_min:.3f}")
            print(f"  AST/min: {proj.ast_per_min:.3f}")
            
            if proj.adjustments:
                print()
                print("Adjustments applied:")
                for k, v in proj.adjustments.items():
                    print(f"  {k}: {v}")
    
    return 0


def _cmd_ingest_drtg_stdin(args: argparse.Namespace) -> int:
    """Ingest player DRTG data from stdin (paste from StatMuse)."""
    from .ingest.player_drtg_parser import parse_player_drtg_text, save_player_drtg_to_db
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    text = sys.stdin.read()
    if not text.strip():
        print("No input read from stdin. Paste the DRTG data and then press Ctrl-D.", file=sys.stderr)
        return 2
    
    team = (args.team or "").strip().upper() or None
    season = (args.season or "2025-26").strip()
    
    result = parse_player_drtg_text(text, expected_team=team, expected_season=season)
    
    if not result.rows:
        print("No DRTG data could be parsed from input.", file=sys.stderr)
        for err in result.errors:
            print(f"  Error: {err}", file=sys.stderr)
        return 2
    
    with db.connect() as conn:
        save_result = save_player_drtg_to_db(conn, result)
    
    print(f"DRTG data ingested for team: {result.team_abbrev}")
    print(f"  Inserted: {save_result['inserted']}")
    print(f"  Updated: {save_result['updated']}")
    print(f"  Total: {save_result['total']}")
    
    # Show preview
    print(f"\nPreview of parsed data:")
    for row in result.rows[:5]:
        print(f"  {row.rank}. {row.name}: DRTG={row.drtg:.1f}, GP={row.games_played}, MPG={row.minutes_per_game:.1f}")
    if len(result.rows) > 5:
        print(f"  ... and {len(result.rows) - 5} more")
    
    return 0


def _cmd_list_drtg(args: argparse.Namespace) -> int:
    """List player DRTG data from the database."""
    from .ingest.player_drtg_parser import (
        get_team_drtg_rankings, 
        get_league_drtg_rankings,
        get_drtg_data_freshness,
    )
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    team = (args.team or "").strip().upper() or None
    limit = int(args.limit)
    season = (args.season or "2025-26").strip()
    
    with db.connect() as conn:
        if team:
            # Get DRTG for specific team
            rankings = get_team_drtg_rankings(conn, team, season)
            
            if not rankings:
                print(f"No DRTG data found for team: {team}")
                return 1
            
            freshness = get_drtg_data_freshness(conn, team)
            
            print(f"\n{'='*70}")
            print(f"Player Defensive Ratings: {team}")
            print(f"Season: {season}")
            if freshness.get("last_updated"):
                print(f"Last Updated: {freshness['last_updated']}")
            print(f"{'='*70}\n")
            
            print(f"{'Rank':<6} {'Player':<24} {'DRTG':>7} {'GP':>5} {'MPG':>6} {'PPG':>6} {'RPG':>5}")
            print("-" * 70)
            
            for i, row in enumerate(rankings[:limit]):
                print(f"{i+1:<6} {row.name:<24} {row.drtg:>7.1f} {row.games_played:>5} "
                      f"{row.minutes_per_game:>6.1f} {(row.ppg or 0):>6.1f} {(row.rpg or 0):>5.1f}")
        else:
            # Get league-wide rankings
            rankings = get_league_drtg_rankings(conn, season, limit)
            
            if not rankings:
                print("No DRTG data found in database.")
                return 1
            
            print(f"\n{'='*70}")
            print(f"League-Wide Best Defensive Ratings")
            print(f"Season: {season} (min 15 MPG)")
            print(f"{'='*70}\n")
            
            print(f"{'Rank':<6} {'Player':<24} {'Team':<5} {'DRTG':>7} {'GP':>5} {'MPG':>6}")
            print("-" * 70)
            
            for row in rankings:
                print(f"{row.rank:<6} {row.name:<24} {row.team_abbrev:<5} {row.drtg:>7.1f} "
                      f"{row.games_played:>5} {row.minutes_per_game:>6.1f}")
    
    return 0


def _cmd_drtg_freshness(args: argparse.Namespace) -> int:
    """Show DRTG data freshness and teams needing updates."""
    from .ingest.player_drtg_parser import (
        get_drtg_data_freshness,
        get_teams_needing_drtg_update,
    )
    
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)
    
    max_age = int(args.max_age)
    
    with db.connect() as conn:
        freshness = get_drtg_data_freshness(conn)
        needs_update = get_teams_needing_drtg_update(conn, max_age)
    
    print(f"\n{'='*70}")
    print(f"DRTG Data Freshness Report")
    print(f"{'='*70}\n")
    
    # Teams with data
    if freshness:
        print(f"Teams with DRTG data ({len(freshness)}/30):\n")
        print(f"{'Team':<6} {'Last Updated':<22} {'Records':>8}")
        print("-" * 40)
        
        for team, info in sorted(freshness.items(), key=lambda x: x[1]["last_updated"] or "0", reverse=True):
            print(f"{team:<6} {info['last_updated'] or 'Never':<22} {info['records_count']:>8}")
    else:
        print("No DRTG data has been ingested yet.\n")
    
    # Teams needing updates
    if needs_update:
        print(f"\n{'='*70}")
        print(f"Teams Needing DRTG Updates (>{max_age} days old or missing)")
        print(f"{'='*70}\n")
        
        high_priority = [t for t in needs_update if t["priority"] == "HIGH"]
        medium_priority = [t for t in needs_update if t["priority"] == "MEDIUM"]
        
        if high_priority:
            print(f"🔴 HIGH PRIORITY ({len(high_priority)} teams) - No data:")
            for t in high_priority[:10]:
                print(f"   • {t['team']}: {t['reason']}")
            if len(high_priority) > 10:
                print(f"   ... and {len(high_priority) - 10} more")
            print()
        
        if medium_priority:
            print(f"🟡 MEDIUM PRIORITY ({len(medium_priority)} teams) - Stale data:")
            for t in medium_priority[:10]:
                last = t['last_updated'].split(' ')[0] if t['last_updated'] else 'Never'
                print(f"   • {t['team']}: last updated {last}")
    else:
        print(f"\n✅ All teams have DRTG data updated within {max_age} days!")
    
    return 0


def _cmd_top_players(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    init_db(db_path)
    db = Db(path=db_path)

    team_raw = (args.team or "").strip()
    if not team_raw:
        print("Please provide --team (e.g. PHX or 'Phoenix Suns')", file=sys.stderr)
        return 2

    if 2 <= len(team_raw) <= 4 and team_raw.isalpha():
        team_name = team_name_from_abbrev(team_raw.upper()) or team_raw
    else:
        team_name = normalize_team_name(team_raw)

    limit = int(args.limit)
    source = (args.source or "auto").strip().lower()
    if source not in {"auto", "team-stats", "boxscores"}:
        print("--source must be one of: auto, team-stats, boxscores", file=sys.stderr)
        return 2

    with db.connect() as conn:
        team_row = conn.execute("SELECT id, name FROM teams WHERE name = ?", (team_name,)).fetchone()
        if not team_row:
            print(f"Unknown team (not in DB yet): {team_name}")
            return 1
        team_id = int(team_row["id"])

        snap = conn.execute(
            """
            SELECT id, season, as_of_date
            FROM team_stats_snapshot
            WHERE team_id = ?
            ORDER BY COALESCE(as_of_date, '') DESC, id DESC
            LIMIT 1
            """,
            (team_id,),
        ).fetchone()

        use_team_stats = (source == "team-stats") or (source == "auto" and snap is not None)

        if use_team_stats and snap:
            print(
                f"Top {limit} players by MIN (team-stats snapshot {snap['id']}, season={snap['season']} as_of={snap['as_of_date']})"
            )
            rows = conn.execute(
                """
                SELECT p.name AS player, tsp.pos, tsp.min, tsp.pts, tsp.reb, tsp.ast
                FROM team_stats_player tsp
                JOIN players p ON p.id = tsp.player_id
                WHERE tsp.snapshot_id = ?
                ORDER BY (tsp.min IS NULL) ASC, tsp.min DESC, p.name
                LIMIT ?
                """,
                (int(snap["id"]), limit),
            ).fetchall()
            for r in rows:
                print(
                    f"{r['player']:<24} {(r['pos'] or ''):<2} "
                    f"MIN={r['min']!s:<5} PTS={r['pts']!s:<5} REB={r['reb']!s:<5} AST={r['ast']!s:<5}"
                )
            return 0

        # Fallback: boxscore-derived minutes
        print(f"Top {limit} players by avg MIN (boxscores; all ingested games so far)")
        rows = conn.execute(
            """
            SELECT p.name AS player, b.pos, AVG(b.minutes) AS avg_min, COUNT(*) AS games
            FROM boxscore_player b
            JOIN players p ON p.id = b.player_id
            WHERE b.team_id = ? AND b.minutes IS NOT NULL
            GROUP BY b.player_id, b.pos
            ORDER BY avg_min DESC, games DESC, p.name
            LIMIT ?
            """,
            (team_id, limit),
        ).fetchall()
    for r in rows:
        print(f"{r['player']:<24} {(r['pos'] or ''):<2} AVG_MIN={r['avg_min']:.1f} games={r['games']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    paths = get_paths()
    default_db = str(paths.db_path)

    p = argparse.ArgumentParser(prog="nba-props", description="Local NBA prop ingestion + projections")
    p.add_argument("--db", default=default_db, help=f"Path to SQLite DB (default: {default_db})")

    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init-db", help="Create/initialize the SQLite database")
    s.set_defaults(func=_cmd_init_db)

    s = sub.add_parser("ingest-boxscore", help="Ingest a single boxscore .txt file")
    s.add_argument("file", help="Path to boxscore .txt file")
    s.set_defaults(func=_cmd_ingest_boxscore)

    s = sub.add_parser(
        "ingest-boxscore-stdin",
        help="Paste a boxscore into stdin, save to data/raw, and ingest",
    )
    s.add_argument("--date", required=True, help="Game date YYYY-MM-DD (example: 2026-01-01)")
    s.add_argument("--label", default="PASTE", help="Optional label for the saved raw file")
    s.set_defaults(func=_cmd_ingest_boxscore_stdin)

    s = sub.add_parser(
        "ingest-lines-stdin",
        help="Paste sportsbook lines into stdin and store them (PTS/REB/AST sections)",
    )
    s.add_argument("--date", required=True, help="As-of date YYYY-MM-DD (example: 2026-01-02)")
    s.add_argument("--book", default="", help="Optional book name (e.g. DK, FD, Caesars)")
    s.set_defaults(func=_cmd_ingest_lines_stdin)

    s = sub.add_parser("list-games", help="List ingested games")
    s.add_argument("--limit", default="20")
    s.add_argument("--verbose", action="store_true")
    s.set_defaults(func=_cmd_list_games)

    s = sub.add_parser("show-game", help="Show ingested player lines for a game")
    s.add_argument("game_id")
    s.set_defaults(func=_cmd_show_game)

    s = sub.add_parser("show-inactives", help="Show inactive player list ingested for a game (Inactive Players section)")
    s.add_argument("game_id")
    s.set_defaults(func=_cmd_show_inactives)

    s = sub.add_parser("summary", help="Show counts of data ingested into the SQLite DB")
    s.set_defaults(func=_cmd_summary)

    s = sub.add_parser(
        "audit-duplicates",
        help="Check for duplicate games (same date + matchup) to ensure no overlap",
    )
    s.set_defaults(func=_cmd_audit_duplicates)

    s = sub.add_parser("gui", help="Launch the web-based GUI (requires Flask)")
    s.add_argument("--port", type=int, default=5050, help="Port to run on (default: 5050)")
    s.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    s.set_defaults(func=lambda args: _run_web_app_if_available(host=args.host, port=args.port))

    s = sub.add_parser("list-lines", help="List ingested sportsbook lines")
    s.add_argument("--date", default="", help="Filter by as-of date (YYYY-MM-DD)")
    s.set_defaults(func=_cmd_list_lines)

    s = sub.add_parser(
        "ingest-team-stats",
        help="Ingest a team stats markdown file (e.g. team_stats__PHX__2026-01-01.txt) into SQLite",
    )
    s.add_argument("file", help="Path to team stats .txt file")
    s.add_argument(
        "--team",
        default="",
        help="Team abbreviation (e.g. PHX) or full name (e.g. 'Phoenix Suns'). Optional if filename is canonical.",
    )
    s.add_argument(
        "--as-of",
        default="",
        help="Optional as-of date YYYY-MM-DD (overrides filename inference when present)",
    )
    s.set_defaults(func=_cmd_ingest_team_stats)

    s = sub.add_parser("show-team-stats", help="Show latest ingested team stats snapshot for a team")
    s.add_argument("--team", required=True, help="Team abbreviation (e.g. PHX) or full name")
    s.add_argument("--limit", default="25", help="Max player rows to show (default: 25)")
    s.set_defaults(func=_cmd_show_team_stats)

    s = sub.add_parser(
        "top-players",
        help="Show top-N players (for the 'top 7 only' rule) using team-stats snapshot or boxscores",
    )
    s.add_argument("--team", required=True, help="Team abbreviation (e.g. PHX) or full name")
    s.add_argument("--limit", default="7", help="How many players to show (default: 7)")
    s.add_argument(
        "--source",
        default="auto",
        help="auto|team-stats|boxscores (default: auto). auto uses team-stats if available, else boxscores.",
    )
    s.set_defaults(func=_cmd_top_players)

    # Archetype management commands
    s = sub.add_parser(
        "seed-archetypes",
        help="Seed the database with default player archetypes from the built-in roster",
    )
    s.add_argument("--season", default="2025-26", help="Season to seed (default: 2025-26)")
    s.add_argument("--overwrite", action="store_true", help="Overwrite existing entries")
    s.set_defaults(func=_cmd_seed_archetypes)

    s = sub.add_parser("list-archetypes", help="List player archetypes in the database")
    s.add_argument("--season", default="2025-26", help="Season to list (default: 2025-26)")
    s.add_argument("--tier", default="", help="Filter by tier (1-6)")
    s.add_argument("--team", default="", help="Filter by team name")
    s.set_defaults(func=_cmd_list_archetypes)

    s = sub.add_parser("show-archetype", help="Show detailed archetype info for a player")
    s.add_argument("player", help="Player name")
    s.add_argument("--season", default="2025-26", help="Season (default: 2025-26)")
    s.set_defaults(func=_cmd_show_archetype)

    # Data validation commands
    s = sub.add_parser(
        "validate",
        help="Run data validation checks on the database",
    )
    s.add_argument("--fix", action="store_true", help="Attempt to fix issues (cleanup orphaned data)")
    s.add_argument("--verbose", action="store_true", help="Show all details for each check")
    s.set_defaults(func=_cmd_validate)

    s = sub.add_parser(
        "cleanup",
        help="Clean up orphaned data (teams with no games, etc.)",
    )
    s.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without doing it")
    s.set_defaults(func=_cmd_cleanup)

    s = sub.add_parser(
        "purge-test-data",
        help="Delete a scheduled matchup (optional) and remove generated backtesting picks/history for a date",
    )
    s.add_argument("--date", required=True, help="Date to purge (YYYY-MM-DD)")
    s.add_argument("--away", default="", help="Optional away team abbreviation (e.g. LAL)")
    s.add_argument("--home", default="", help="Optional home team abbreviation (e.g. BOS)")
    s.add_argument("--dry-run", action="store_true", help="Show what would be deleted without modifying the DB")
    s.set_defaults(func=_cmd_purge_test_data)

    # Projection command
    s = sub.add_parser(
        "project",
        help="Generate projections for a player or team",
    )
    s.add_argument("--team", help="Team abbreviation (e.g. PHX)")
    s.add_argument("--player", help="Player name")
    s.add_argument("--opponent", default="", help="Opponent abbreviation for matchup adjustments")
    s.add_argument("--date", default="", help="Game date (YYYY-MM-DD) for back-to-back detection")
    s.set_defaults(func=_cmd_project)

    # Usage redistribution command
    s = sub.add_parser(
        "usage-impact",
        help="Show how a player's absence impacts teammates",
    )
    s.add_argument("--team", required=True, help="Team abbreviation (e.g. PHX)")
    s.add_argument("--out", required=True, help="Player who is out/absent")
    s.add_argument("--historical", action="store_true", help="Show historical impact if available")
    s.set_defaults(func=_cmd_usage_impact)

    # Matchup recommendations command
    s = sub.add_parser(
        "matchup",
        help="Generate matchup-specific prop recommendations",
    )
    s.add_argument("--away", required=True, help="Away team abbreviation")
    s.add_argument("--home", required=True, help="Home team abbreviation")
    s.add_argument("--date", default="", help="Game date (YYYY-MM-DD)")
    s.add_argument("--min-edge", type=float, default=5.0, help="Minimum edge percentage to show")
    s.set_defaults(func=_cmd_matchup)

    # Backtesting commands
    s = sub.add_parser(
        "backtest",
        help="Run backtest comparing projections to actual outcomes",
    )
    s.add_argument("--start", default="", help="Start date (YYYY-MM-DD)")
    s.add_argument("--end", default="", help="End date (YYYY-MM-DD)")
    s.add_argument("--min-edge", type=float, default=3.0, help="Minimum edge percentage")
    s.set_defaults(func=_cmd_backtest)

    s = sub.add_parser(
        "accuracy",
        help="Analyze projection accuracy for a player",
    )
    s.add_argument("--player", required=True, help="Player name")
    s.add_argument("--stat", default="PTS", help="Stat to analyze (PTS, REB, AST)")
    s.add_argument("--games", type=int, default=10, help="Number of games to analyze")
    s.set_defaults(func=_cmd_accuracy)

    s = sub.add_parser(
        "bias-analysis",
        help="Analyze systematic projection biases across all players",
    )
    s.add_argument("--min-games", type=int, default=5, help="Minimum games per player")
    s.set_defaults(func=_cmd_bias_analysis)

    # Edge alerts command
    s = sub.add_parser(
        "alerts",
        help="Find prop edges where projection differs from line",
    )
    s.add_argument("--date", default="", help="Date to scan lines for (YYYY-MM-DD)")
    s.add_argument("--min-edge", type=float, default=5.0, help="Minimum edge percentage")
    s.add_argument("--team", default="", help="Filter to specific team")
    s.set_defaults(func=_cmd_alerts)

    # Player DRTG (Defensive Rating) commands
    s = sub.add_parser(
        "ingest-drtg-stdin",
        help="Paste player DRTG data from StatMuse and ingest into the database",
    )
    s.add_argument("--team", default="", help="Team abbreviation to filter (optional)")
    s.add_argument("--season", default="2025-26", help="Season (default: 2025-26)")
    s.set_defaults(func=_cmd_ingest_drtg_stdin)

    s = sub.add_parser(
        "list-drtg",
        help="List player defensive ratings from the database",
    )
    s.add_argument("--team", default="", help="Team abbreviation to filter (e.g. PHX)")
    s.add_argument("--limit", default="30", help="Maximum results (default: 30)")
    s.add_argument("--season", default="2025-26", help="Season (default: 2025-26)")
    s.set_defaults(func=_cmd_list_drtg)

    s = sub.add_parser(
        "drtg-freshness",
        help="Show DRTG data freshness and teams needing updates",
    )
    s.add_argument("--max-age", default="14", help="Max age in days before data is considered stale (default: 14)")
    s.set_defaults(func=_cmd_drtg_freshness)

    # Model picks command (new high-accuracy model)
    s = sub.add_parser(
        "model-picks",
        help="Generate picks using the optimized L15 model (70%+ accuracy on HIGH confidence)",
    )
    s.add_argument("--date", default="", help="Date to generate picks for (YYYY-MM-DD, default: today)")
    s.add_argument("--backtest", action="store_true", help="Run backtest instead of generating picks")
    s.add_argument("--tier", default="", help="Filter by confidence tier (HIGH, MED, LOW)")
    s.add_argument("--stat", default="", help="Filter by stat type (PTS, REB, AST)")
    s.add_argument("--weeks", type=int, default=2, help="Number of weeks to backtest (default: 2)")
    s.set_defaults(func=_cmd_model_picks)

    # Model backtest command  
    s = sub.add_parser(
        "model-backtest",
        help="Run full backtest on the optimized model with detailed breakdown",
    )
    s.add_argument("--weeks", type=int, default=4, help="Number of weeks to backtest (default: 4)")
    s.add_argument("--start", default="", help="Start date (YYYY-MM-DD, overrides --weeks)")
    s.add_argument("--end", default="", help="End date (YYYY-MM-DD)")
    s.set_defaults(func=_cmd_model_backtest)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))



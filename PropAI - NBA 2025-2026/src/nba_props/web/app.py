"""Flask web application for NBA Props Predictor."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from ..db import Db, init_db
from ..ingest import ingest_boxscore_file
from ..ingest.paste import save_pasted_boxscore_text
from ..ingest.lines_parser import parse_lines_text
from ..ingest.matchups_parser import parse_matchups_text, parse_simple_matchup
from ..ingest.web_scraper import (
    fetch_injuries, fetch_matchups, fetch_box_scores,
    injuries_to_text, matchups_to_text, box_scores_to_text,
    HAS_SCRAPING_DEPS,
)
from ..paths import get_paths
from ..standings import compute_conference_standings, compute_player_averages_for_team
from ..team_aliases import abbrev_from_team_name, team_name_from_abbrev
from ..engine.projector import project_team_players, ProjectionConfig
from ..engine.game_context import get_back_to_back_status, get_team_defense_rating, apply_matchup_adjustments
from ..engine.edge_calculator import generate_prop_report, calculate_prop_edge
from ..engine.archetypes import get_player_archetype, classify_player_by_stats, KNOWN_ARCHETYPES
from ..engine.archetype_db import (
    get_player_archetype_db,
    get_all_archetypes_db,
    update_player_archetype,
    delete_player_archetype,
    seed_archetypes_from_defaults,
    get_similarity_groups_db,
    get_elite_defenders_db,
    get_similar_players_db,
    should_avoid_betting_over_db,
    get_roster_for_team_db,
    get_archetype_count_db,
    toggle_star_status,
    get_star_players_for_team,
    get_all_star_players,
    is_star_player,
    set_bet_status,
    get_bet_status,
    BET_STATUS_AVOID,
    BET_STATUS_NEUTRAL,
    BET_STATUS_STAR,
)
from ..engine.optimization import run_optimization_grid


def _calculate_confidence_stars(score: float) -> int:
    """
    Calculate star rating (1-5) from confidence score.
    
    Calibrated for Under Model V2 scoring:
    - 5 stars (★★★★★): Score >= 90 - Premium picks (elite defense + cold streak + bonus)
    - 4 stars (★★★★☆): Score >= 80 - HIGH tier (elite defense + something)
    - 3 stars (★★★☆☆): Score >= 70 - MEDIUM tier high end
    - 2 stars (★★☆☆☆): Score >= 60 - MEDIUM tier low end  
    - 1 star  (★☆☆☆☆): Score < 60 - LOW tier
    """
    if score >= 90:
        return 5
    elif score >= 80:
        return 4
    elif score >= 70:
        return 3
    elif score >= 60:
        return 2
    else:
        return 1


def create_app() -> Flask:
    """Create and configure the Flask application."""
    paths = get_paths()
    
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )
    app.config["SECRET_KEY"] = "nba-props-local-dev"
    
    # Initialize database
    init_db(paths.db_path)
    
    def get_db() -> Db:
        return Db(path=paths.db_path)
    
    # -------------------------------------------------------------------------
    # Pages
    # -------------------------------------------------------------------------
    
    @app.route("/")
    def index():
        """Main dashboard page."""
        return render_template("index.html")
    
    @app.route("/games")
    def games_page():
        """Games list page."""
        return render_template("games.html")
    
    @app.route("/paste")
    def paste_page():
        """Paste box score page."""
        return render_template("paste.html")
    
    @app.route("/projections")
    def projections_page():
        """Projections and props page."""
        return render_template("projections.html")
    
    @app.route("/teams")
    def teams_page():
        """Teams overview page."""
        return render_template("teams.html")
    
    @app.route("/team/<abbrev>")
    def team_detail_page(abbrev: str):
        """Team detail page."""
        return render_template("team_detail.html", team_abbrev=abbrev.upper())
    
    @app.route("/data")
    def data_page():
        """Data management page - redirects to paste page."""
        from flask import redirect, url_for
        return redirect(url_for('paste_page'))
    
    @app.route("/players")
    def players_page():
        """Unified players page with roster, archetypes, and matchup analysis."""
        return render_template("players.html")
    
    @app.route("/matchups")
    def matchups_page():
        """Today's matchups and predictions page."""
        return render_template("matchups.html")
    
    @app.route("/modellab")
    def modellab():
        """Model Lab page - new revamped version with learning dashboard."""
        return render_template("modellab_new.html")
    
    # Legacy routes - redirect to unified players page
    @app.route("/archetypes")
    def archetypes_page():
        """Player archetypes page - redirects to players."""
        return render_template("players.html")
    
    @app.route("/roster")
    def roster_page():
        """Player roster with detailed archetypes - redirects to players."""
        return render_template("players.html")
    
    @app.route("/backtesting")
    def backtesting_page():
        """Model testing and backtesting dashboard."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Find a good default date: last date with picks or scheduled games
        db = get_db()
        default_date = today
        with db.connect() as conn:
            # Try to get the most recent date with picks first
            last_pick = conn.execute(
                "SELECT pick_date FROM model_picks ORDER BY pick_date DESC LIMIT 1"
            ).fetchone()
            if last_pick:
                default_date = last_pick["pick_date"]
            else:
                # Fall back to most recent scheduled game date
                last_game = conn.execute(
                    "SELECT game_date FROM scheduled_games ORDER BY game_date DESC LIMIT 1"
                ).fetchone()
                if last_game:
                    default_date = last_game["game_date"]
        
        return render_template("backtesting.html", today=today, default_date=default_date)
    
    @app.route("/matchup")
    def matchup_page():
        """Matchup analysis with defender tracking - redirects to players."""
        return render_template("players.html")
    
    # -------------------------------------------------------------------------
    # API Endpoints
    # -------------------------------------------------------------------------
    
    @app.route("/api/stats")
    def api_stats():
        """Get database statistics."""
        db = get_db()
        with db.connect() as conn:
            games = conn.execute("SELECT COUNT(*) AS n FROM games").fetchone()["n"]
            players = conn.execute("SELECT COUNT(*) AS n FROM players").fetchone()["n"]
            teams = conn.execute("SELECT COUNT(*) AS n FROM teams").fetchone()["n"]
            lines = conn.execute("SELECT COUNT(*) AS n FROM sportsbook_lines").fetchone()["n"]
            
            # Get archetype count from DB
            archetypes_db = get_archetype_count_db(conn)
            
            # Get latest game date
            latest = conn.execute(
                "SELECT game_date FROM games ORDER BY game_date DESC LIMIT 1"
            ).fetchone()
            latest_date = latest["game_date"] if latest else None
            
        # Get default archetype count
        from ..engine.roster import PLAYER_DATABASE
        archetypes_default = len(PLAYER_DATABASE)
            
        return jsonify({
            "games": games,
            "players": players,
            "teams": teams,
            "lines": lines,
            "archetypes_db": archetypes_db,
            "archetypes_default": archetypes_default,
            "latest_game_date": latest_date,
        })
    
    @app.route("/api/games")
    def api_games():
        """Get list of games."""
        limit = request.args.get("limit", 50, type=int)
        db = get_db()
        with db.connect() as conn:
            rows = conn.execute(
                """
                SELECT g.id, g.game_date, g.season,
                       t1.name AS team1, t2.name AS team2,
                       tt1.pts AS team1_pts, tt2.pts AS team2_pts
                FROM games g
                JOIN teams t1 ON t1.id = g.team1_id
                JOIN teams t2 ON t2.id = g.team2_id
                LEFT JOIN boxscore_team_totals tt1 ON tt1.game_id = g.id AND tt1.team_id = g.team1_id
                LEFT JOIN boxscore_team_totals tt2 ON tt2.game_id = g.id AND tt2.team_id = g.team2_id
                ORDER BY g.game_date DESC, g.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        
        games = []
        for r in rows:
            games.append({
                "id": r["id"],
                "date": r["game_date"],
                "season": r["season"],
                "team1": r["team1"],
                "team2": r["team2"],
                "team1_abbrev": abbrev_from_team_name(r["team1"]) or "",
                "team2_abbrev": abbrev_from_team_name(r["team2"]) or "",
                "team1_pts": r["team1_pts"],
                "team2_pts": r["team2_pts"],
            })
        return jsonify({"games": games})
    
    @app.route("/api/game/<int:game_id>")
    def api_game_detail(game_id: int):
        """Get detailed game information."""
        db = get_db()
        with db.connect() as conn:
            game = conn.execute(
                """
                SELECT g.id, g.game_date, g.season,
                       t1.name AS team1, t2.name AS team2
                FROM games g
                JOIN teams t1 ON t1.id = g.team1_id
                JOIN teams t2 ON t2.id = g.team2_id
                WHERE g.id = ?
                """,
                (game_id,),
            ).fetchone()
            
            if not game:
                return jsonify({"error": "Game not found"}), 404
            
            players = conn.execute(
                """
                SELECT t.name AS team, p.name AS player, 
                       b.pos, b.status, b.minutes, b.pts, b.reb, b.ast,
                       b.fgm, b.fga, b.tpm, b.tpa, b.ftm, b.fta,
                       b.stl, b.blk, b.tov, b.plus_minus
                FROM boxscore_player b
                JOIN teams t ON t.id = b.team_id
                JOIN players p ON p.id = b.player_id
                WHERE b.game_id = ?
                ORDER BY t.name, (b.minutes IS NULL) ASC, b.minutes DESC
                """,
                (game_id,),
            ).fetchall()
            
            totals = conn.execute(
                """
                SELECT t.name AS team, tt.pts, tt.reb, tt.ast
                FROM boxscore_team_totals tt
                JOIN teams t ON t.id = tt.team_id
                WHERE tt.game_id = ?
                """,
                (game_id,),
            ).fetchall()
        
        return jsonify({
            "game": {
                "id": game["id"],
                "date": game["game_date"],
                "season": game["season"],
                "team1": game["team1"],
                "team2": game["team2"],
            },
            "players": [dict(p) for p in players],
            "totals": {t["team"]: {"pts": t["pts"], "reb": t["reb"], "ast": t["ast"]} for t in totals},
        })
    
    @app.route("/api/standings")
    def api_standings():
        """Get conference standings."""
        db = get_db()
        with db.connect() as conn:
            standings = compute_conference_standings(conn)
        
        result = {"East": [], "West": []}
        for conf in ["East", "West"]:
            for row in standings.get(conf, []):
                result[conf].append({
                    "seed": row.seed,
                    "abbrev": row.abbr,
                    "team": row.team_name,
                    "wins": row.wins,
                    "losses": row.losses,
                    "win_pct": round(row.win_pct, 3) if row.win_pct else 0,
                })
        return jsonify(result)
    
    @app.route("/api/scheduled-games")
    def api_scheduled_games():
        """Get scheduled games for a date."""
        game_date = request.args.get('date')
        if not game_date:
            return jsonify({"error": "Date parameter required"}), 400
        
        db = get_db()
        with db.connect() as conn:
            # Get standings for team records
            standings = compute_conference_standings(conn)
            team_records = {}
            for conf in ["East", "West"]:
                for row in standings.get(conf, []):
                    team_records[row.abbr] = f"{row.wins}-{row.losses}"
            
            # Get scheduled games with team names
            rows = conn.execute("""
                SELECT 
                    sg.id,
                    sg.game_date,
                    sg.game_time,
                    sg.spread,
                    sg.over_under,
                    sg.tv_channel,
                    sg.status,
                    away.name as away_team,
                    home.name as home_team
                FROM scheduled_games sg
                JOIN teams away ON sg.away_team_id = away.id
                JOIN teams home ON sg.home_team_id = home.id
                WHERE sg.game_date = ?
                ORDER BY sg.game_time
            """, (game_date,)).fetchall()
            
            games = []
            for row in rows:
                away_abbrev = abbrev_from_team_name(row["away_team"]) or row["away_team"][:3].upper()
                home_abbrev = abbrev_from_team_name(row["home_team"]) or row["home_team"][:3].upper()
                
                games.append({
                    "id": row["id"],
                    "game_date": row["game_date"],
                    "game_time": row["game_time"],
                    "away_team": row["away_team"],
                    "home_team": row["home_team"],
                    "away_abbrev": away_abbrev,
                    "home_abbrev": home_abbrev,
                    "spread": row["spread"],
                    "over_under": row["over_under"],
                    "tv_channel": row["tv_channel"],
                    "status": row["status"],
                    "away_record": team_records.get(away_abbrev, ""),
                    "home_record": team_records.get(home_abbrev, ""),
                })
        
        return jsonify({"games": games, "date": game_date})
    
    @app.route("/api/scheduled-games/parse", methods=["POST"])
    def api_scheduled_games_parse():
        """Parse matchup text and save to scheduled_games table."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "No matchup text provided"}), 400
        
        try:
            matchups = parse_matchups_text(text)
            
            if not matchups:
                return jsonify({"error": "No matchups could be parsed from text. Make sure the format includes team names, @ symbol, and optionally Line/O/U values."}), 400
            
            detected_date = matchups[0].game_date if matchups else None
            
            db = get_db()
            saved_count = 0
            updated_count = 0
            saved_matchups = []
            
            with db.connect() as conn:
                for m in matchups:
                    # Get or create team IDs
                    away_team_id = conn.execute(
                        "SELECT id FROM teams WHERE name = ?", (m.away_team,)
                    ).fetchone()
                    home_team_id = conn.execute(
                        "SELECT id FROM teams WHERE name = ?", (m.home_team,)
                    ).fetchone()
                    
                    if not away_team_id:
                        conn.execute("INSERT INTO teams (name) VALUES (?)", (m.away_team,))
                        away_team_id = conn.execute(
                            "SELECT id FROM teams WHERE name = ?", (m.away_team,)
                        ).fetchone()
                    if not home_team_id:
                        conn.execute("INSERT INTO teams (name) VALUES (?)", (m.home_team,))
                        home_team_id = conn.execute(
                            "SELECT id FROM teams WHERE name = ?", (m.home_team,)
                        ).fetchone()
                    
                    away_id = away_team_id["id"]
                    home_id = home_team_id["id"]
                    
                    # Check if game already exists for this date and teams
                    existing = conn.execute("""
                        SELECT id FROM scheduled_games 
                        WHERE game_date = ? AND away_team_id = ? AND home_team_id = ?
                    """, (m.game_date, away_id, home_id)).fetchone()
                    
                    was_updated = False
                    if existing:
                        # Update existing game with new line info
                        conn.execute("""
                            UPDATE scheduled_games 
                            SET spread = ?, over_under = ?, game_time = ?, tv_channel = ?, updated_at = datetime('now')
                            WHERE id = ?
                        """, (m.spread, m.over_under, m.game_time, m.tv_channel, existing["id"]))
                        updated_count += 1
                        was_updated = True
                    else:
                        # Insert new scheduled game
                        conn.execute("""
                            INSERT INTO scheduled_games (game_date, away_team_id, home_team_id, spread, over_under, game_time, tv_channel, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled')
                        """, (m.game_date, away_id, home_id, m.spread, m.over_under, m.game_time, m.tv_channel))
                        saved_count += 1
                    
                    # Add to response matchups list
                    saved_matchups.append({
                        "away": m.away_abbrev,
                        "home": m.home_abbrev,
                        "away_team": m.away_team,
                        "home_team": m.home_team,
                        "spread": m.spread,
                        "ou": m.over_under,
                        "game_time": m.game_time,
                        "date": m.game_date,
                        "status": "updated" if was_updated else "new",
                    })
                
                conn.commit()
            
            total_processed = saved_count + updated_count
            return jsonify({
                "success": True,
                "count": saved_count,
                "updated": updated_count,
                "total": total_processed,
                "date": detected_date,
                "matchups": saved_matchups,
                "message": f"Added {saved_count} new matchups" + (f", updated {updated_count} existing" if updated_count else "")
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/scheduled-games", methods=["POST"])
    def api_scheduled_games_add():
        """Add a single scheduled game (manual entry)."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        away = data.get("away", "").strip().upper()
        home = data.get("home", "").strip().upper()
        date = data.get("date", "").strip()
        time = data.get("time")
        spread = data.get("spread")
        over_under = data.get("over_under")
        
        if not away or not home or not date:
            return jsonify({"error": "Missing required fields: away, home, date"}), 400
        
        # Resolve team names
        away_team = team_name_from_abbrev(away)
        home_team = team_name_from_abbrev(home)
        
        if not away_team:
            return jsonify({"error": f"Unknown away team: {away}"}), 400
        if not home_team:
            return jsonify({"error": f"Unknown home team: {home}"}), 400
        
        try:
            db = get_db()
            with db.connect() as conn:
                # Get team IDs
                away_row = conn.execute("SELECT id FROM teams WHERE name = ?", (away_team,)).fetchone()
                home_row = conn.execute("SELECT id FROM teams WHERE name = ?", (home_team,)).fetchone()
                
                if not away_row:
                    conn.execute("INSERT INTO teams (name) VALUES (?)", (away_team,))
                    away_row = conn.execute("SELECT id FROM teams WHERE name = ?", (away_team,)).fetchone()
                if not home_row:
                    conn.execute("INSERT INTO teams (name) VALUES (?)", (home_team,))
                    home_row = conn.execute("SELECT id FROM teams WHERE name = ?", (home_team,)).fetchone()
                
                # Check if already exists
                existing = conn.execute("""
                    SELECT id FROM scheduled_games 
                    WHERE game_date = ? AND away_team_id = ? AND home_team_id = ?
                """, (date, away_row["id"], home_row["id"])).fetchone()
                
                if existing:
                    # Update
                    conn.execute("""
                        UPDATE scheduled_games 
                        SET spread = ?, over_under = ?, game_time = ?
                        WHERE id = ?
                    """, (spread, over_under, time, existing["id"]))
                else:
                    # Insert
                    conn.execute("""
                        INSERT INTO scheduled_games (game_date, away_team_id, home_team_id, spread, over_under, game_time, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'scheduled')
                    """, (date, away_row["id"], home_row["id"], spread, over_under, time))
                
                conn.commit()
            
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/data-freshness")
    def api_data_freshness():
        """Get data freshness info for the matchups page."""
        db = get_db()
        with db.connect() as conn:
            # Get latest game date
            latest_game = conn.execute(
                "SELECT game_date FROM games ORDER BY game_date DESC LIMIT 1"
            ).fetchone()
            
            # Get latest scheduled game date
            latest_scheduled = conn.execute(
                "SELECT game_date FROM scheduled_games ORDER BY game_date DESC LIMIT 1"
            ).fetchone()
            
            # Get latest lines date (using as_of_date column)
            latest_lines = conn.execute(
                "SELECT as_of_date FROM sportsbook_lines ORDER BY as_of_date DESC LIMIT 1"
            ).fetchone()
        
        return jsonify({
            "latest_boxscore_date": latest_game["game_date"] if latest_game else None,
            "latest_scheduled_date": latest_scheduled["game_date"] if latest_scheduled else None,
            "latest_lines_date": latest_lines["as_of_date"] if latest_lines else None,
        })
    
    @app.route("/api/team/<abbrev>")
    def api_team_detail(abbrev: str):
        """Get team details and player averages."""
        abbrev = abbrev.upper()
        team_name = team_name_from_abbrev(abbrev)
        if not team_name:
            return jsonify({"error": "Unknown team"}), 404
        
        db = get_db()
        with db.connect() as conn:
            standings = compute_conference_standings(conn)
            players = compute_player_averages_for_team(conn, abbrev)
            
            # Find team record
            team_record = None
            for conf in ["East", "West"]:
                for row in standings.get(conf, []):
                    if row.abbr == abbrev:
                        team_record = {
                            "conference": conf,
                            "seed": row.seed,
                            "wins": row.wins,
                            "losses": row.losses,
                            "win_pct": round(row.win_pct, 3) if row.win_pct else 0,
                        }
                        break
        
        return jsonify({
            "abbrev": abbrev,
            "name": team_name,
            "record": team_record,
            "players": players,
        })
    
    @app.route("/api/team/<abbrev>/dashboard")
    def api_team_dashboard(abbrev: str):
        """Get comprehensive team dashboard data including roster archetypes."""
        from ..engine.roster import get_roster_for_team, PLAYER_DATABASE, PlayerTier
        from ..engine.game_context import get_team_defense_rating
        
        # Check if we should use DB-backed archetypes
        use_db_archetypes = request.args.get("use_db", "true").lower() == "true"
        
        abbrev = abbrev.upper()
        team_name = team_name_from_abbrev(abbrev)
        if not team_name:
            return jsonify({"error": "Unknown team"}), 404
        
        db = get_db()
        with db.connect() as conn:
            standings = compute_conference_standings(conn)
            player_stats = compute_player_averages_for_team(conn, abbrev)
            
            # Find team record
            team_record = None
            for conf in ["East", "West"]:
                for row in standings.get(conf, []):
                    if row.abbr == abbrev:
                        team_record = {
                            "conference": conf,
                            "seed": row.seed,
                            "wins": row.wins,
                            "losses": row.losses,
                            "win_pct": round(row.win_pct, 3) if row.win_pct else 0,
                        }
                        break
            
            # Get recent games for this team
            recent_games = conn.execute(
                """
                SELECT g.id, g.game_date, 
                       t1.name AS team1, t2.name AS team2,
                       tt1.pts AS team1_pts, tt2.pts AS team2_pts
                FROM games g
                JOIN teams t1 ON t1.id = g.team1_id
                JOIN teams t2 ON t2.id = g.team2_id
                LEFT JOIN boxscore_team_totals tt1 ON tt1.game_id = g.id AND tt1.team_id = g.team1_id
                LEFT JOIN boxscore_team_totals tt2 ON tt2.game_id = g.id AND tt2.team_id = g.team2_id
                WHERE t1.name = ? OR t2.name = ?
                ORDER BY g.game_date DESC
                LIMIT 10
                """,
                (team_name, team_name),
            ).fetchall()
            
            # Get recent player performances (last 5 games)
            recent_performances = conn.execute(
                """
                SELECT p.name, g.game_date,
                       b.pts, b.reb, b.ast, b.minutes
                FROM boxscore_player b
                JOIN players p ON p.id = b.player_id
                JOIN games g ON g.id = b.game_id
                JOIN teams t ON t.id = b.team_id
                WHERE t.name = ?
                ORDER BY g.game_date DESC, b.pts DESC
                LIMIT 50
                """,
                (team_name,),
            ).fetchall()
            
            # Get team defense rating
            try:
                defense_rating = get_team_defense_rating(conn, abbrev)
            except Exception:
                defense_rating = None
        
        # Get roster archetypes - prefer DB, fallback to static PLAYER_DATABASE
        roster_profiles = []
        elite_defenders = []
        star_players = []
        
        if use_db_archetypes:
            # Try to get from database first
            db_roster = get_roster_for_team_db(conn, team_name)
            if db_roster:
                for profile in db_roster:
                    player_data = {
                        "name": profile.player_name,
                        "position": profile.position,
                        "height": profile.height,
                        "primary_offensive": profile.primary_offensive,
                        "secondary_offensive": profile.secondary_offensive,
                        "defensive_role": profile.defensive_role,
                        "tier": f"TIER_{profile.tier}",
                        "tier_value": profile.tier,
                        "is_elite_defender": profile.is_elite_defender,
                        "is_star": profile.is_star,
                        "bet_status": profile.bet_status,
                        "strengths": profile.strengths,
                        "weaknesses": profile.weaknesses,
                        "notes": profile.notes,
                        "guards_positions": profile.guards_positions,
                        "source": profile.source,
                    }
                    roster_profiles.append(player_data)
        
        # Fallback to static PLAYER_DATABASE if no DB data
        if not roster_profiles:
            team_roster = get_roster_for_team(team_name)
            for profile in team_roster:
                player_data = {
                    "name": profile.name,
                    "position": profile.position,
                    "height": profile.height,
                    "primary_offensive": profile.primary_offensive.value,
                    "secondary_offensive": profile.secondary_offensive.value if profile.secondary_offensive else None,
                    "defensive_role": profile.defensive_role.value,
                    "tier": profile.tier.name,
                    "tier_value": profile.tier.value,
                    "is_elite_defender": profile.is_elite_defender,
                    "is_star": False,  # Static players default to not star
                    "bet_status": BET_STATUS_NEUTRAL,  # Default to neutral
                    "strengths": profile.strengths,
                    "weaknesses": profile.weaknesses,
                    "notes": profile.notes,
                    "guards_positions": profile.guards_positions,
                    "source": "default",
                }
                roster_profiles.append(player_data)
        
        # Build elite defenders and star players from roster_profiles
        for player_data in roster_profiles:
            if player_data.get("is_elite_defender"):
                elite_defenders.append(player_data)
            
            # Use bet_status to determine star status
            bet_status = player_data.get("bet_status", BET_STATUS_NEUTRAL)
            if bet_status == BET_STATUS_STAR:
                star_players.append(player_data)
            elif bet_status == BET_STATUS_NEUTRAL and player_data.get("tier_value", 6) <= 2:
                # Fallback: consider tier 1-2 (MVP, Two-Way Star) as star if neutral
                star_players.append(player_data)
        
        # Sort roster by tier, then by bet_status (stars first)
        roster_profiles.sort(key=lambda x: (-(x.get("bet_status", 1)), x["tier_value"], x["name"]))
        
        # Merge player stats with roster profiles
        stats_by_name = {p["player"]: p for p in player_stats}
        for profile in roster_profiles:
            if profile["name"] in stats_by_name:
                profile["stats"] = stats_by_name[profile["name"]]
        
        # Calculate hot players (best recent performers)
        hot_players = []
        player_recent_games = {}
        for perf in recent_performances:
            name = perf["name"]
            if name not in player_recent_games:
                player_recent_games[name] = []
            if len(player_recent_games[name]) < 5:
                player_recent_games[name].append({
                    "date": perf["game_date"],
                    "pts": perf["pts"],
                    "reb": perf["reb"],
                    "ast": perf["ast"],
                    "minutes": perf["minutes"],
                })
        
        for name, games in player_recent_games.items():
            if len(games) >= 2:
                avg_pts = sum(g["pts"] or 0 for g in games) / len(games)
                avg_reb = sum(g["reb"] or 0 for g in games) / len(games)
                avg_ast = sum(g["ast"] or 0 for g in games) / len(games)
                hot_players.append({
                    "name": name,
                    "games": len(games),
                    "avg_pts": round(avg_pts, 1),
                    "avg_reb": round(avg_reb, 1),
                    "avg_ast": round(avg_ast, 1),
                    "recent_games": games[:3],
                })
        
        # Sort by average points
        hot_players.sort(key=lambda x: x["avg_pts"], reverse=True)
        
        # Format recent games
        formatted_games = []
        for game in recent_games:
            is_team1 = game["team1"] == team_name
            opponent = game["team2"] if is_team1 else game["team1"]
            team_pts = game["team1_pts"] if is_team1 else game["team2_pts"]
            opp_pts = game["team2_pts"] if is_team1 else game["team1_pts"]
            
            if team_pts and opp_pts:
                result = "W" if team_pts > opp_pts else "L"
            else:
                result = None
            
            formatted_games.append({
                "id": game["id"],  # Include game ID for navigation
                "date": game["game_date"],
                "opponent": opponent,
                "opponent_abbrev": abbrev_from_team_name(opponent),
                "team_pts": team_pts,
                "opp_pts": opp_pts,
                "result": result,
                "home": not is_team1,
            })
        
        # Team descriptions (static data for now)
        team_descriptions = {
            "BOS": "The defending champions feature elite two-way players and a deep roster. Known for ball movement and versatile defenders.",
            "MIL": "Built around Giannis Antetokounmpo's dominance at the rim. High-powered offense with improving perimeter defense.",
            "PHI": "Joel Embiid anchors both ends. Physical, half-court oriented team with strong interior defense.",
            "NYK": "Defensive-minded team under Thibodeau. Physical play style with strong rebounding.",
            "CLE": "Young, athletic core with elite guard play. Aggressive defense and transition offense.",
            "MIA": "The Heat Culture emphasizes toughness and defense. Zone defense specialists with 3-point shooting.",
            "ATL": "Trae Young's playmaking drives the offense. High-volume shooting team building toward contention.",
            "CHI": "Dynamic backcourt with solid veterans. Balanced scoring with room for growth.",
            "IND": "Tyrese Haliburton runs a fast-paced offense. Elite pace and transition scoring.",
            "ORL": "Young defensive core led by Paolo Banchero. Long, athletic team still developing.",
            "DET": "Rebuilding around Cade Cunningham. Young roster gaining experience.",
            "TOR": "Versatile, switchable defenders. Unconventional roster construction with length.",
            "BKN": "Retooling roster with young talent. High-upside players developing together.",
            "CHA": "LaMelo Ball's creativity leads the offense. Athletic team working toward consistency.",
            "WAS": "Young roster in development phase. Focus on player growth and future assets.",
            "DEN": "Jokic orchestrates elite offense from the post. Back-to-back champions with deep playoff experience.",
            "OKC": "Young, athletic core with elite defense. Shai Gilgeous-Alexander leads a rising contender.",
            "MIN": "Elite defensive team with Anthony Edwards leading. Physical, playoff-tested roster.",
            "LAC": "Kawhi Leonard and Paul George lead a championship-caliber roster when healthy. Elite wing defenders.",
            "PHX": "Kevin Durant and Devin Booker form elite scoring duo. Superstar-driven offense.",
            "LAL": "LeBron James and Anthony Davis anchor a veteran contender. Size and experience.",
            "SAC": "De'Aaron Fox's speed drives fast-paced offense. Light the Beam! Exciting, up-tempo style.",
            "GSW": "Dynasty core with Steph Curry's gravity. Elite shooting and playoff pedigree.",
            "DAL": "Luka Doncic's brilliance powers everything. Elite offensive rating with improving defense.",
            "NOP": "Zion Williamson's power and versatile roster. Injury-plagued but talented when healthy.",
            "MEM": "Ja Morant's athleticism leads young core. Physical, defensive-minded team.",
            "HOU": "Young rebuilding roster with high picks developing. Fast-paced with room to grow.",
            "SAS": "Victor Wembanyama anchors the rebuild. Historic franchise developing next generation.",
            "UTA": "Rebuilding with young talent. Focus on development and draft assets.",
            "POR": "Building around young guards. Transitioning to next competitive window.",
        }
        
        # Defensive weaknesses analysis
        defensive_analysis = {
            "rating": None,
            "pts_allowed_pg": None,
            "weaknesses": [],
            "strengths": [],
        }
        
        if defense_rating:
            defensive_analysis["rating"] = "elite" if defense_rating.pts_factor < 0.95 else "good" if defense_rating.pts_factor < 1.0 else "average" if defense_rating.pts_factor < 1.05 else "poor"
            defensive_analysis["pts_allowed_pg"] = defense_rating.pts_allowed_pg
            defensive_analysis["reb_allowed_pg"] = defense_rating.reb_allowed_pg
            defensive_analysis["ast_allowed_pg"] = defense_rating.ast_allowed_pg
            
            # Determine strengths/weaknesses
            if defense_rating.pts_factor < 0.98:
                defensive_analysis["strengths"].append("Limiting opponent scoring")
            if defense_rating.reb_factor < 0.98:
                defensive_analysis["strengths"].append("Defensive rebounding")
            if defense_rating.ast_factor < 0.98:
                defensive_analysis["strengths"].append("Disrupting ball movement")
                
            if defense_rating.pts_factor > 1.02:
                defensive_analysis["weaknesses"].append("Allowing easy baskets")
            if defense_rating.reb_factor > 1.02:
                defensive_analysis["weaknesses"].append("Giving up offensive rebounds")
            if defense_rating.ast_factor > 1.02:
                defensive_analysis["weaknesses"].append("Susceptible to ball movement")
        
        return jsonify({
            "abbrev": abbrev,
            "name": team_name,
            "description": team_descriptions.get(abbrev, ""),
            "record": team_record,
            "roster": roster_profiles,
            "star_players": star_players,
            "elite_defenders": elite_defenders,
            "player_stats": player_stats,
            "hot_players": hot_players[:5],
            "recent_games": formatted_games,
            "defensive_analysis": defensive_analysis,
        })
    
    @app.route("/api/team/<abbrev>/all-games")
    def api_team_all_games(abbrev: str):
        """Get ALL games for a specific team with pagination support."""
        abbrev = abbrev.upper()
        team_name = team_name_from_abbrev(abbrev)
        if not team_name:
            return jsonify({"error": "Unknown team"}), 404
        
        # Pagination parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        offset = (page - 1) * per_page
        
        db = get_db()
        with db.connect() as conn:
            # Get total count
            count_row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM games g
                JOIN teams t1 ON t1.id = g.team1_id
                JOIN teams t2 ON t2.id = g.team2_id
                WHERE t1.name = ? OR t2.name = ?
                """,
                (team_name, team_name),
            ).fetchone()
            total = count_row["total"] if count_row else 0
            
            # Get games with pagination
            rows = conn.execute(
                """
                SELECT g.id, g.game_date, g.season, g.source_file,
                       t1.name AS team1, t2.name AS team2,
                       tt1.pts AS team1_pts, tt2.pts AS team2_pts
                FROM games g
                JOIN teams t1 ON t1.id = g.team1_id
                JOIN teams t2 ON t2.id = g.team2_id
                LEFT JOIN boxscore_team_totals tt1 ON tt1.game_id = g.id AND tt1.team_id = g.team1_id
                LEFT JOIN boxscore_team_totals tt2 ON tt2.game_id = g.id AND tt2.team_id = g.team2_id
                WHERE t1.name = ? OR t2.name = ?
                ORDER BY g.game_date DESC, g.id DESC
                LIMIT ? OFFSET ?
                """,
                (team_name, team_name, per_page, offset),
            ).fetchall()
        
        games = []
        for r in rows:
            is_team1 = r["team1"] == team_name
            opponent = r["team2"] if is_team1 else r["team1"]
            team_pts = r["team1_pts"] if is_team1 else r["team2_pts"]
            opp_pts = r["team2_pts"] if is_team1 else r["team1_pts"]
            
            if team_pts and opp_pts:
                result = "W" if team_pts > opp_pts else "L"
            else:
                result = None
            
            games.append({
                "id": r["id"],
                "date": r["game_date"],
                "season": r["season"],
                "source_file": r["source_file"],
                "team1": r["team1"],
                "team2": r["team2"],
                "team1_abbrev": abbrev_from_team_name(r["team1"]) or "",
                "team2_abbrev": abbrev_from_team_name(r["team2"]) or "",
                "team1_pts": r["team1_pts"],
                "team2_pts": r["team2_pts"],
                "opponent": opponent,
                "opponent_abbrev": abbrev_from_team_name(opponent) or "",
                "team_pts": team_pts,
                "opp_pts": opp_pts,
                "result": result,
                "home": not is_team1,
            })
        
        return jsonify({
            "games": games,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        })
    
    @app.route("/api/game/<int:game_id>", methods=["DELETE"])
    def api_delete_game(game_id: int):
        """Delete a game and all associated data (cascading delete)."""
        db = get_db()
        with db.connect() as conn:
            # First check if game exists
            game = conn.execute(
                "SELECT id, game_date FROM games WHERE id = ?", (game_id,)
            ).fetchone()
            
            if not game:
                return jsonify({"error": "Game not found"}), 404
            
            # Get game info for response
            game_info = conn.execute(
                """
                SELECT g.game_date, t1.name AS team1, t2.name AS team2
                FROM games g
                JOIN teams t1 ON t1.id = g.team1_id
                JOIN teams t2 ON t2.id = g.team2_id
                WHERE g.id = ?
                """,
                (game_id,),
            ).fetchone()
            
            # Delete the game (cascading will handle related records)
            conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": f"Game {game_id} deleted successfully",
                "deleted_game": {
                    "id": game_id,
                    "date": game_info["game_date"] if game_info else None,
                    "team1": game_info["team1"] if game_info else None,
                    "team2": game_info["team2"] if game_info else None,
                }
            })
    
    @app.route("/api/game/<int:game_id>/score", methods=["PUT"])
    def api_update_game_score(game_id: int):
        """Update the score of a game (modifies boxscore_team_totals)."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        team1_pts = data.get("team1_pts")
        team2_pts = data.get("team2_pts")
        
        if team1_pts is None or team2_pts is None:
            return jsonify({"error": "Both team1_pts and team2_pts are required"}), 400
        
        db = get_db()
        with db.connect() as conn:
            # Get game info
            game = conn.execute(
                """
                SELECT g.id, g.team1_id, g.team2_id, t1.name AS team1, t2.name AS team2
                FROM games g
                JOIN teams t1 ON t1.id = g.team1_id
                JOIN teams t2 ON t2.id = g.team2_id
                WHERE g.id = ?
                """,
                (game_id,),
            ).fetchone()
            
            if not game:
                return jsonify({"error": "Game not found"}), 404
            
            # Update team1 score
            conn.execute(
                """
                UPDATE boxscore_team_totals 
                SET pts = ? 
                WHERE game_id = ? AND team_id = ?
                """,
                (team1_pts, game_id, game["team1_id"]),
            )
            
            # Update team2 score
            conn.execute(
                """
                UPDATE boxscore_team_totals 
                SET pts = ? 
                WHERE game_id = ? AND team_id = ?
                """,
                (team2_pts, game_id, game["team2_id"]),
            )
            
            conn.commit()
            
            return jsonify({
                "success": True,
                "message": "Score updated successfully",
                "game": {
                    "id": game_id,
                    "team1": game["team1"],
                    "team2": game["team2"],
                    "team1_pts": team1_pts,
                    "team2_pts": team2_pts,
                }
            })
    
    @app.route("/api/recent-dates")
    def api_recent_dates():
        """Get recent game dates for quick selection."""
        db = get_db()
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT game_date FROM games ORDER BY game_date DESC LIMIT 30"
            ).fetchall()
        return jsonify({"dates": [r["game_date"] for r in rows]})
    
    @app.route("/api/ingest/boxscore", methods=["POST"])
    def api_ingest_boxscore():
        """Ingest a pasted box score."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get("text", "").strip()
        game_date = data.get("date", "").strip()
        label = data.get("label", "PASTE").strip()
        
        if not text:
            return jsonify({"error": "No box score text provided"}), 400
        if not game_date:
            return jsonify({"error": "No game date provided"}), 400
        
        try:
            saved = save_pasted_boxscore_text(
                text=text,
                game_date=game_date,
                paths=paths,
                label=label,
            )
            
            db = get_db()
            with db.connect() as conn:
                game_id = ingest_boxscore_file(conn, source_file=saved.path)
                conn.commit()
            
            return jsonify({
                "success": True,
                "game_id": game_id,
                "saved_path": str(saved.path),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/ingest/lines", methods=["POST"])
    def api_ingest_lines():
        """Ingest sportsbook lines."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get("text", "").strip()
        as_of_date = data.get("date", "").strip()
        book = data.get("book", "").strip() or None
        
        if not text:
            return jsonify({"error": "No lines text provided"}), 400
        if not as_of_date:
            return jsonify({"error": "No as-of date provided"}), 400
        
        try:
            items = parse_lines_text(text)
            if not items:
                return jsonify({"error": "No lines parsed from text"}), 400
            
            db = get_db()
            with db.connect() as conn:
                for item in items:
                    player_row = conn.execute(
                        "SELECT id FROM players WHERE name = ?", (item.player,)
                    ).fetchone()
                    if player_row:
                        pid = int(player_row["id"])
                    else:
                        cur = conn.execute(
                            "INSERT INTO players(name) VALUES (?)", (item.player,)
                        )
                        pid = int(cur.lastrowid)
                    
                    conn.execute(
                        """
                        INSERT INTO sportsbook_lines(as_of_date, game_id, team_id, player_id, prop_type, line, odds_american, book)
                        VALUES (?, NULL, NULL, ?, ?, ?, ?, ?)
                        """,
                        (as_of_date, pid, item.prop_type, item.line, item.odds_american, book),
                    )
                conn.commit()
            
            return jsonify({
                "success": True,
                "count": len(items),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/detect-teams", methods=["POST"])
    def api_detect_teams():
        """Detect team names from pasted text."""
        data = request.get_json()
        text = data.get("text", "") if data else ""
        
        # Look for team names in the text
        detected = []
        for team_name in [
            "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
            "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
            "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
            "Los Angeles Clippers", "LA Clippers", "Los Angeles Lakers", "LA Lakers",
            "Memphis Grizzlies", "Miami Heat", "Milwaukee Bucks", "Minnesota Timberwolves",
            "New Orleans Pelicans", "New York Knicks", "Oklahoma City Thunder", "Orlando Magic",
            "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers", "Sacramento Kings",
            "San Antonio Spurs", "Toronto Raptors", "Utah Jazz", "Washington Wizards",
        ]:
            if team_name in text:
                abbrev = abbrev_from_team_name(team_name)
                if abbrev and abbrev not in [d.get("abbrev") for d in detected]:
                    detected.append({"name": team_name, "abbrev": abbrev})
        
        return jsonify({"teams": detected[:2]})  # Return at most 2 teams
    
    @app.route("/api/suggest-date", methods=["POST"])
    def api_suggest_date():
        """Suggest a game date based on detected teams and recent games."""
        data = request.get_json()
        teams = data.get("teams", []) if data else []
        
        if len(teams) < 2:
            # Return today's date as default
            return jsonify({"date": datetime.now().strftime("%Y-%m-%d"), "source": "default"})
        
        # Look for recent games between these teams
        db = get_db()
        with db.connect() as conn:
            # Get the most recent game date in the database
            latest = conn.execute(
                "SELECT game_date FROM games ORDER BY game_date DESC LIMIT 1"
            ).fetchone()
            
            if latest:
                # Suggest the day after the latest game (common pattern for adding new games)
                from datetime import timedelta
                latest_date = datetime.strptime(latest["game_date"], "%Y-%m-%d")
                next_date = latest_date + timedelta(days=1)
                return jsonify({
                    "date": next_date.strftime("%Y-%m-%d"),
                    "source": "next_day",
                    "latest_game": latest["game_date"]
                })
        
        # Default to today
        return jsonify({"date": datetime.now().strftime("%Y-%m-%d"), "source": "default"})
    
    @app.route("/api/projections", methods=["POST"])
    def api_projections():
        """Generate projections for a matchup."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        away = data.get("away", "").strip().upper()
        home = data.get("home", "").strip().upper()
        game_date = data.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
        lines_date = data.get("lines_date", "").strip() or game_date
        
        if not away or not home:
            return jsonify({"error": "Please provide both away and home teams"}), 400
        
        if away == home:
            return jsonify({"error": "Teams must be different"}), 400
        
        db = get_db()
        try:
            with db.connect() as conn:
                report = generate_prop_report(
                    conn=conn,
                    away_abbrev=away,
                    home_abbrev=home,
                    game_date=game_date,
                    lines_date=lines_date,
                )
            return jsonify(report)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/matchup-analysis", methods=["POST"])
    def api_matchup_analysis():
        """
        Generate comprehensive matchup analysis with all advanced metrics.
        
        This endpoint uses the Advisor layer from matchup_advisor module
        to provide actionable betting recommendations.
        
        Request Body (JSON):
            - away: Away team abbreviation (e.g., "LAL")
            - home: Home team abbreviation (e.g., "BOS")
            - date: Game date (YYYY-MM-DD)
            - spread: Optional point spread
            - over_under: Optional total points line
        
        Returns:
            ComprehensiveMatchupReport as JSON with:
            - best_over_plays: List of recommended OVER bets
            - best_under_plays: List of recommended UNDER bets
            - avoid_players: Players to avoid betting on
            - key_matchups: Important storylines
            - Defense profiles for both teams
        """
        from ..engine.matchup_advisor import generate_comprehensive_matchup_report
        from dataclasses import asdict
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        away = data.get("away", "").strip().upper()
        home = data.get("home", "").strip().upper()
        game_date = data.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
        spread = data.get("spread")
        over_under = data.get("over_under")
        
        if not away or not home:
            return jsonify({"error": "Please provide both away and home teams"}), 400
        
        if away == home:
            return jsonify({"error": "Teams must be different"}), 400
        
        db = get_db()
        try:
            with db.connect() as conn:
                report = generate_comprehensive_matchup_report(
                    conn=conn,
                    away_abbrev=away,
                    home_abbrev=home,
                    game_date=game_date,
                    spread=float(spread) if spread is not None else None,
                    over_under=float(over_under) if over_under is not None else None,
                )
                
                # Also generate under_v2 picks for this matchup
                under_v2_plays = []
                try:
                    from ..engine.under_model_v2 import generate_under_picks_v2
                    under_result = generate_under_picks_v2(conn, away, home, game_date)
                    if under_result.picks:
                        for analysis in under_result.picks:
                            under_v2_plays.append({
                                "player": analysis.player_name,
                                "team": analysis.team_abbrev,
                                "opponent": analysis.opponent_abbrev,
                                "prop": analysis.prop_type,
                                "baseline": analysis.season_avg,
                                "adjusted": analysis.projected,
                                "adjustment_pct": round((1 - analysis.adjustment_factor) * -100, 1),
                                "confidence": analysis.confidence_tier,
                                "confidence_score": analysis.confidence_score,
                                "reasons": analysis.reasons[:5],
                                "warnings": analysis.warnings[:3] if analysis.warnings else [],
                                "source": "under_v2",
                            })
                except Exception as e:
                    import traceback
                    print(f"Note: under_model_v2 not available for matchup: {e}")
                    traceback.print_exc()
            
            # Transform the dataclass to the format expected by the frontend
            def transform_defense_profile(profile):
                if profile is None:
                    return None
                return {
                    "pts_factor": profile.pts_factor,
                    "reb_factor": profile.reb_factor,
                    "ast_factor": profile.ast_factor,
                    "rating": profile.pts_rating,
                    "pts_rating": profile.pts_rating,
                    "reb_rating": profile.reb_rating,
                    "ast_rating": profile.ast_rating,
                }
            
            def transform_player_projection(proj_dict):
                return {
                    "player_id": proj_dict.get("player_id"),
                    "player": proj_dict.get("player_name"),
                    "team": proj_dict.get("team_abbrev"),
                    "position": proj_dict.get("position", ""),
                    "minutes": proj_dict.get("proj_minutes", 0),
                    "pts": proj_dict.get("proj_pts", 0),
                    "reb": proj_dict.get("proj_reb", 0),
                    "ast": proj_dict.get("proj_ast", 0),
                    "games": proj_dict.get("games_played", 0),
                    "is_top_7": proj_dict.get("is_top_7", True),
                    "is_top_10": proj_dict.get("is_top_10", True),
                    "trend": {
                        "pts": proj_dict.get("pts_trend", "stable"),
                        "reb": proj_dict.get("reb_trend", "stable"),
                        "ast": proj_dict.get("ast_trend", "stable"),
                        "pts_change": proj_dict.get("pts_trend_pct", 0),
                        "reb_change": proj_dict.get("reb_trend_pct", 0),
                        "ast_change": proj_dict.get("ast_trend_pct", 0),
                    },
                    "archetype": proj_dict.get("adjustments", {}).get("archetype"),
                    "edges": proj_dict.get("matchup_edges", {}),
                    "game_log": [],
                }
            
            def transform_matchup_edge(edge):
                return {
                    "player": edge.player_name,
                    "team": edge.team_abbrev,
                    "opponent": edge.opponent_abbrev,
                    "prop": edge.prop_type,
                    "baseline": edge.baseline_projection,
                    "adjusted": edge.adjusted_projection,
                    "adjustment_pct": edge.adjustment_pct,
                    "confidence": edge.confidence_tier,
                    "confidence_score": edge.confidence_score,
                    "reasons": edge.reasons,
                    "warnings": edge.warnings,
                }
            
            result = {
                "matchup": {
                    "away": report.away_abbrev,
                    "home": report.home_abbrev,
                    "date": report.game_date,
                    "spread": report.spread,
                    "over_under": report.over_under,
                    "is_close_game": report.is_close_game,
                },
                "context": {
                    "away_b2b": report.away_b2b,
                    "away_rest_days": report.away_rest_days,
                    "home_b2b": report.home_b2b,
                    "home_rest_days": report.home_rest_days,
                },
                "defense": {
                    "away": {
                        "overall_rating": "Average Defense",
                        "guard_defense": transform_defense_profile(report.away_defense_vs_guards),
                        "forward_defense": transform_defense_profile(report.away_defense_vs_forwards),
                        "center_defense": transform_defense_profile(report.away_defense_vs_centers),
                    },
                    "home": {
                        "overall_rating": "Average Defense",
                        "guard_defense": transform_defense_profile(report.home_defense_vs_guards),
                        "forward_defense": transform_defense_profile(report.home_defense_vs_forwards),
                        "center_defense": transform_defense_profile(report.home_defense_vs_centers),
                    },
                },
                "away_projections": [
                    transform_player_projection(p) for p in report.away_player_projections
                ],
                "home_projections": [
                    transform_player_projection(p) for p in report.home_player_projections
                ],
                "best_over_plays": [
                    transform_matchup_edge(e) for e in report.best_over_plays
                ],
                "best_under_plays": (
                    # Combine traditional under plays with under_v2 plays
                    [transform_matchup_edge(e) for e in report.best_under_plays] + 
                    under_v2_plays
                ),
                "avoid_players": report.avoid_players,
                "key_matchups": report.key_matchups,
            }
            
            # Sort under plays by confidence score
            result["best_under_plays"] = sorted(
                result["best_under_plays"],
                key=lambda x: x.get("confidence_score", 0),
                reverse=True
            )
            
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/team/<abbrev>/defense-profile")
    def api_team_defense_profile(abbrev: str):
        """Get detailed defensive profile for a team by position."""
        from ..engine.matchup_advisor import (
            get_team_defense_summary,
            get_all_position_defense_profiles,
        )
        
        abbrev = abbrev.upper()
        
        db = get_db()
        try:
            with db.connect() as conn:
                summary = get_team_defense_summary(conn, abbrev)
                position_profiles = get_all_position_defense_profiles(conn, abbrev)
                
                profiles_dict = {}
                for pos, profile in position_profiles.items():
                    profiles_dict[pos] = {
                        "pts_allowed_avg": profile.pts_allowed_avg,
                        "reb_allowed_avg": profile.reb_allowed_avg,
                        "ast_allowed_avg": profile.ast_allowed_avg,
                        "pts_factor": profile.pts_factor,
                        "reb_factor": profile.reb_factor,
                        "ast_factor": profile.ast_factor,
                        "pts_rating": profile.pts_rating,
                        "reb_rating": profile.reb_rating,
                        "ast_rating": profile.ast_rating,
                        "sample_size": profile.sample_size,
                    }
                
                return jsonify({
                    "team": abbrev,
                    "summary": summary,
                    "position_profiles": profiles_dict,
                })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/player/<int:player_id>/trend")
    def api_player_trend(player_id: int):
        """Get trend analysis for a player."""
        from ..engine.matchup_advisor import get_player_trend
        
        db = get_db()
        try:
            with db.connect() as conn:
                trend = get_player_trend(conn, player_id)
                
                if not trend:
                    return jsonify({"error": "Insufficient data for trend analysis"}), 404
                
                return jsonify({
                    "player_name": trend.player_name,
                    "player_id": trend.player_id,
                    "team": trend.team_abbrev,
                    "recent": {
                        "pts": trend.recent_pts,
                        "reb": trend.recent_reb,
                        "ast": trend.recent_ast,
                        "min": trend.recent_min,
                        "games": trend.recent_games,
                    },
                    "season": {
                        "pts": trend.season_pts,
                        "reb": trend.season_reb,
                        "ast": trend.season_ast,
                        "games": trend.season_games,
                    },
                    "trends": {
                        "pts": trend.pts_trend,
                        "reb": trend.reb_trend,
                        "ast": trend.ast_trend,
                    },
                    "changes": {
                        "pts": trend.pts_change_pct,
                        "reb": trend.reb_change_pct,
                        "ast": trend.ast_change_pct,
                    },
                    "consistency": {
                        "pts": trend.pts_consistency,
                        "reb": trend.reb_consistency,
                        "ast": trend.ast_consistency,
                    },
                    "game_log": trend.game_log,
                })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/player/<player_name>/vs-team/<opponent>")
    def api_player_vs_team(player_name: str, opponent: str):
        """Get player's historical performance against a specific team."""
        from ..engine.matchup_advisor import get_player_vs_team_profile
        
        db = get_db()
        try:
            with db.connect() as conn:
                profile = get_player_vs_team_profile(conn, player_name, opponent.upper())
                
                if not profile:
                    return jsonify({"error": "No data found"}), 404
                
                return jsonify({
                    "player": profile.player_name,
                    "opponent": profile.opponent_abbrev,
                    "games_played": profile.games_played,
                    "has_history": profile.has_history,
                    "vs_opponent": {
                        "pts": profile.pts_avg,
                        "reb": profile.reb_avg,
                        "ast": profile.ast_avg,
                        "min": profile.min_avg,
                    },
                    "overall": {
                        "pts": profile.overall_pts_avg,
                        "reb": profile.overall_reb_avg,
                        "ast": profile.overall_ast_avg,
                    },
                    "differential": {
                        "pts": profile.pts_diff,
                        "reb": profile.reb_diff,
                        "ast": profile.ast_diff,
                    },
                    "recent_games": profile.recent_games,
                })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/position-defense-rankings/<position>")
    def api_position_defense_rankings(position: str):
        """Get defense rankings for all teams against a specific position."""
        from ..engine.matchup_advisor import rank_position_defense_profiles
        
        position = position.upper()[:1]
        if position not in ("G", "F", "C"):
            return jsonify({"error": "Position must be G, F, or C"}), 400
        
        db = get_db()
        try:
            with db.connect() as conn:
                rankings = rank_position_defense_profiles(conn, position)
                
                return jsonify({
                    "position": position,
                    "rankings": [
                        {
                            "rank": i + 1,
                            "team": r.team_abbrev,
                            "pts_allowed_avg": r.pts_allowed_avg,
                            "pts_factor": r.pts_factor,
                            "pts_rating": r.pts_rating,
                            "reb_factor": r.reb_factor,
                            "reb_rating": r.reb_rating,
                            "ast_factor": r.ast_factor,
                            "ast_rating": r.ast_rating,
                            "sample_size": r.sample_size,
                        }
                        for i, r in enumerate(rankings)
                    ]
                })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/team/<abbrev>/projections")
    def api_team_projections(abbrev: str):
        """Get projections for a team's players."""
        abbrev = abbrev.upper()
        opponent = request.args.get("opponent", "").upper()
        game_date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        db = get_db()
        try:
            with db.connect() as conn:
                # Get back-to-back status
                b2b = get_back_to_back_status(conn, abbrev, game_date)
                
                # Get opponent defense if specified
                opp_defense = None
                if opponent:
                    opp_defense = get_team_defense_rating(conn, opponent)
                
                # Generate projections
                projections = project_team_players(
                    conn=conn,
                    team_abbrev=abbrev,
                    opponent_abbrev=opponent or None,
                    is_back_to_back=b2b.is_back_to_back,
                    rest_days=b2b.rest_days,
                )
                
                # Apply opponent adjustments
                results = []
                for proj in projections:
                    adj_pts, adj_reb, adj_ast, adj_info = apply_matchup_adjustments(
                        proj.proj_pts, proj.proj_reb, proj.proj_ast, opp_defense
                    )
                    
                    results.append({
                        "player_id": proj.player_id,
                        "player": proj.player_name,
                        "position": proj.position,
                        "minutes": proj.proj_minutes,
                        "pts": adj_pts,
                        "reb": adj_reb,
                        "ast": adj_ast,
                        "pts_std": proj.pts_std,
                        "reb_std": proj.reb_std,
                        "ast_std": proj.ast_std,
                        "games": proj.games_played,
                        "is_top_7": proj.is_top_7,
                        "adjustments": {**proj.adjustments, **adj_info},
                    })
                
                return jsonify({
                    "team": abbrev,
                    "game_date": game_date,
                    "opponent": opponent or None,
                    "is_back_to_back": b2b.is_back_to_back,
                    "rest_days": b2b.rest_days,
                    "projections": results,
                })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/defense-ratings")
    def api_defense_ratings():
        """Get defense ratings for all teams."""
        from ..engine.game_context import get_all_team_defense_ratings
        
        db = get_db()
        try:
            with db.connect() as conn:
                ratings = get_all_team_defense_ratings(conn)
            
            return jsonify({
                "ratings": [
                    {
                        "team": r.team_abbrev,
                        "games": r.games_played,
                        "pts_allowed": r.pts_allowed_pg,
                        "reb_allowed": r.reb_allowed_pg,
                        "ast_allowed": r.ast_allowed_pg,
                        "pts_factor": r.pts_factor,
                        "reb_factor": r.reb_factor,
                        "ast_factor": r.ast_factor,
                    }
                    for r in ratings.values()
                ]
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/lines")
    def api_lines():
        """Get sportsbook lines."""
        date = request.args.get("date", "")
        limit = request.args.get("limit", 100, type=int)
        
        db = get_db()
        with db.connect() as conn:
            if date:
                rows = conn.execute(
                    """
                    SELECT sl.id, sl.as_of_date, p.name AS player, sl.prop_type, 
                           sl.line, sl.odds_american, sl.book
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
                    SELECT sl.id, sl.as_of_date, p.name AS player, sl.prop_type, 
                           sl.line, sl.odds_american, sl.book
                    FROM sportsbook_lines sl
                    JOIN players p ON p.id = sl.player_id
                    ORDER BY sl.as_of_date DESC, p.name, sl.prop_type
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        
        return jsonify({
            "lines": [dict(r) for r in rows]
        })
    
    @app.route("/api/player/<player_name>/archetype")
    def api_player_archetype(player_name: str):
        """Get archetype classification for a player."""
        archetype = get_player_archetype(player_name)
        
        if not archetype:
            # Try to classify from database stats
            db = get_db()
            with db.connect() as conn:
                player_row = conn.execute(
                    "SELECT id FROM players WHERE name LIKE ?", (f"%{player_name}%",)
                ).fetchone()
                if player_row:
                    archetype = classify_player_by_stats(conn, player_row["id"])
        
        if not archetype:
            return jsonify({"error": "Player not found or unclassified"}), 404
        
        return jsonify({
            "player": archetype.player_name,
            "tier": archetype.tier,
            "primary_offensive": archetype.primary_offensive,
            "secondary_offensive": archetype.secondary_offensive,
            "defensive_role": archetype.defensive_role,
            "notes": archetype.notes,
        })
    
    @app.route("/api/archetypes")
    def api_archetypes():
        """Get all known player archetypes."""
        archetypes = []
        for name, data in KNOWN_ARCHETYPES.items():
            primary, secondary, defensive, tier, notes = data
            archetypes.append({
                "player": name,
                "tier": tier,
                "primary_offensive": primary,
                "secondary_offensive": secondary,
                "defensive_role": defensive,
                "notes": notes,
            })
        
        # Sort by tier, then by player name
        archetypes.sort(key=lambda x: (x["tier"], x["player"]))
        return jsonify({"archetypes": archetypes})
    
    # -------------------------------------------------------------------------
    # Roster System API Endpoints
    # -------------------------------------------------------------------------
    
    @app.route("/api/roster")
    def api_roster():
        """Get complete player roster with archetypes."""
        from ..engine.roster import PLAYER_DATABASE, PlayerTier
        
        tier = request.args.get("tier", "")
        team = request.args.get("team", "")
        elite_defenders_only = request.args.get("elite_defenders", "false").lower() == "true"
        
        players = []
        for name, profile in PLAYER_DATABASE.items():
            # Apply filters
            if tier and profile.tier.name.lower() != tier.lower():
                continue
            if team and profile.team.lower() != team.lower():
                continue
            if elite_defenders_only and not profile.is_elite_defender:
                continue
            
            players.append({
                "name": name,
                "team": profile.team,
                "position": profile.position,
                "height": profile.height,
                "primary_offensive": profile.primary_offensive.value,
                "secondary_offensive": profile.secondary_offensive.value if profile.secondary_offensive else None,
                "defensive_role": profile.defensive_role.value,
                "tier": profile.tier.name,
                "tier_value": profile.tier.value,
                "is_elite_defender": profile.is_elite_defender,
                "strengths": profile.strengths,
                "weaknesses": profile.weaknesses,
                "notes": profile.notes,
                "guards_positions": profile.guards_positions,
                "avoid_betting_against": profile.avoid_betting_against,
            })
        
        # Sort by tier, then name
        players.sort(key=lambda x: (x["tier_value"], x["name"]))
        
        return jsonify({
            "players": players,
            "count": len(players),
        })
    
    @app.route("/api/roster/player/<player_name>")
    def api_roster_player(player_name: str):
        """Get detailed profile for a specific player."""
        from ..engine.roster import get_player_profile, get_similar_players
        
        profile = get_player_profile(player_name)
        if not profile:
            return jsonify({"error": "Player not found in roster"}), 404
        
        similar = get_similar_players(player_name)
        
        return jsonify({
            "name": profile.name,
            "team": profile.team,
            "position": profile.position,
            "height": profile.height,
            "primary_offensive": profile.primary_offensive.value,
            "secondary_offensive": profile.secondary_offensive.value if profile.secondary_offensive else None,
            "defensive_role": profile.defensive_role.value,
            "tier": profile.tier.name,
            "is_elite_defender": profile.is_elite_defender,
            "strengths": profile.strengths,
            "weaknesses": profile.weaknesses,
            "notes": profile.notes,
            "guards_positions": profile.guards_positions,
            "avoid_betting_against": profile.avoid_betting_against,
            "similar_players": similar,
        })
    
    @app.route("/api/roster/similarity-groups")
    def api_similarity_groups():
        """Get all player similarity groups."""
        from ..engine.roster import PLAYER_SIMILARITY_GROUPS
        
        return jsonify({
            "groups": {
                name: players for name, players in PLAYER_SIMILARITY_GROUPS.items()
            }
        })
    
    @app.route("/api/roster/elite-defenders")
    def api_elite_defenders():
        """Get all elite defenders grouped by position."""
        from ..engine.roster import ELITE_DEFENDERS_BY_POSITION, get_player_profile
        
        result = {}
        for position, defenders in ELITE_DEFENDERS_BY_POSITION.items():
            result[position] = []
            for name in defenders:
                profile = get_player_profile(name)
                if profile:
                    result[position].append({
                        "name": name,
                        "team": profile.team,
                        "defensive_role": profile.defensive_role.value,
                    })
                else:
                    result[position].append({
                        "name": name,
                        "team": "Unknown",
                        "defensive_role": "Unknown",
                    })
        
        return jsonify({"defenders_by_position": result})
    
    @app.route("/api/roster/matchup-check", methods=["POST"])
    def api_matchup_check():
        """Check if we should avoid betting on a player based on opponent's defenders."""
        from ..engine.roster import should_avoid_betting_over, get_player_profile, get_roster_for_team
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        player_name = data.get("player", "").strip()
        opponent_team = data.get("opponent", "").strip()
        
        if not player_name or not opponent_team:
            return jsonify({"error": "Player and opponent team required"}), 400
        
        profile = get_player_profile(player_name)
        if not profile:
            return jsonify({
                "player": player_name,
                "opponent": opponent_team,
                "avoid": False,
                "reason": "Player not in database",
                "defenders": [],
            })
        
        # Get opponent roster
        opponent_roster = [p.name for p in get_roster_for_team(opponent_team)]
        
        avoid, defenders = should_avoid_betting_over(player_name, opponent_roster)
        
        return jsonify({
            "player": player_name,
            "player_position": profile.position,
            "player_archetype": profile.primary_offensive.value,
            "opponent": opponent_team,
            "avoid": avoid,
            "elite_defenders": defenders,
            "recommendation": "Consider UNDER or avoid" if avoid else "Standard projection",
        })
    
    @app.route("/api/roster/tiers")
    def api_roster_tiers():
        """Get players grouped by tier."""
        from ..engine.roster import PLAYER_DATABASE, get_players_by_tier, PlayerTier
        
        result = {}
        for tier in PlayerTier:
            players = get_players_by_tier(tier)
            result[tier.name] = {
                "tier_value": tier.value,
                "description": {
                    PlayerTier.MVP_CANDIDATE: "Heliocentric stars, high usage",
                    PlayerTier.TWO_WAY_STAR: "Elite two-way players",
                    PlayerTier.ELITE_BIG: "Top tier big men",
                    PlayerTier.ELITE_ROLE: "Championship-level role players",
                    PlayerTier.SPECIALIST: "Scoring and other specialists",
                    PlayerTier.ROTATION: "Key rotation pieces",
                }.get(tier, ""),
                "count": len(players),
                "players": players,
            }
        
        return jsonify({"tiers": result})
    
    # -------------------------------------------------------------------------
    # Database-Backed Archetype API Endpoints
    # -------------------------------------------------------------------------
    
    @app.route("/api/archetypes-db")
    def api_archetypes_db():
        """Get all player archetypes from database (with fallback to defaults)."""
        season = request.args.get("season", "2025-26")
        tier = request.args.get("tier", type=int)
        team = request.args.get("team", "")
        elite_only = request.args.get("elite_defenders", "false").lower() == "true"
        stars_only = request.args.get("stars_only", "false").lower() == "true"
        
        db = get_db()
        with db.connect() as conn:
            archetypes = get_all_archetypes_db(
                conn, 
                season=season,
                tier=tier,
                team=team if team else None,
                elite_defenders_only=elite_only,
                stars_only=stars_only,
            )
            
            # Get count
            count = get_archetype_count_db(conn, season)
        
        return jsonify({
            "archetypes": [
                {
                    "id": a.id,
                    "player": a.player_name,
                    "team": a.team,
                    "position": a.position,
                    "height": a.height,
                    "primary_offensive": a.primary_offensive,
                    "secondary_offensive": a.secondary_offensive,
                    "defensive_role": a.defensive_role,
                    "tier": a.tier,
                    "is_elite_defender": a.is_elite_defender,
                    "is_star": a.is_star,
                    "strengths": a.strengths,
                    "weaknesses": a.weaknesses,
                    "notes": a.notes,
                    "guards_positions": a.guards_positions,
                    "avoid_betting_against": a.avoid_betting_against,
                    "source": a.source,
                    "confidence": a.confidence,
                }
                for a in archetypes
            ],
            "count": len(archetypes),
            "db_count": count,
            "season": season,
        })
    
    @app.route("/api/archetypes-db/player/<player_name>")
    def api_archetype_db_player(player_name: str):
        """Get archetype for a specific player from database."""
        season = request.args.get("season", "2025-26")
        
        db = get_db()
        with db.connect() as conn:
            archetype = get_player_archetype_db(conn, player_name, season)
            similar = get_similar_players_db(conn, player_name, season) if archetype else []
        
        if not archetype:
            return jsonify({"error": "Player not found"}), 404
        
        return jsonify({
            "player": archetype.player_name,
            "team": archetype.team,
            "position": archetype.position,
            "height": archetype.height,
            "primary_offensive": archetype.primary_offensive,
            "secondary_offensive": archetype.secondary_offensive,
            "defensive_role": archetype.defensive_role,
            "tier": archetype.tier,
            "is_elite_defender": archetype.is_elite_defender,
            "is_star": archetype.is_star,
            "strengths": archetype.strengths,
            "weaknesses": archetype.weaknesses,
            "notes": archetype.notes,
            "guards_positions": archetype.guards_positions,
            "avoid_betting_against": archetype.avoid_betting_against,
            "source": archetype.source,
            "confidence": archetype.confidence,
            "similar_players": similar,
        })
    
    @app.route("/api/archetypes-db/player/<player_name>", methods=["PUT", "POST"])
    def api_archetype_db_update(player_name: str):
        """Update or create an archetype for a player."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        season = data.get("season", "2025-26")
        
        # Extract updatable fields
        update_fields = {}
        allowed_fields = [
            "team", "position", "height", "primary_offensive", "secondary_offensive",
            "defensive_role", "tier", "is_elite_defender", "is_star", "strengths", "weaknesses",
            "notes", "guards_positions", "avoid_betting_against"
        ]
        
        for field in allowed_fields:
            if field in data:
                update_fields[field] = data[field]
        
        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400
        
        db = get_db()
        try:
            with db.connect() as conn:
                success = update_player_archetype(conn, player_name, season, **update_fields)
            
            return jsonify({
                "success": success,
                "player": player_name,
                "updated_fields": list(update_fields.keys()),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/archetypes-db/player/<player_name>", methods=["DELETE"])
    def api_archetype_db_delete(player_name: str):
        """Delete a player's archetype from database (will fall back to defaults)."""
        season = request.args.get("season", "2025-26")
        
        db = get_db()
        try:
            with db.connect() as conn:
                success = delete_player_archetype(conn, player_name, season)
            
            return jsonify({
                "success": success,
                "player": player_name,
                "note": "Player will now use default archetype if available",
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/archetypes-db/seed", methods=["POST"])
    def api_archetypes_seed():
        """Seed database with default archetypes from PLAYER_DATABASE."""
        data = request.get_json() or {}
        season = data.get("season", "2025-26")
        overwrite = data.get("overwrite", False)
        
        db = get_db()
        try:
            with db.connect() as conn:
                count = seed_archetypes_from_defaults(conn, season, overwrite)
            
            return jsonify({
                "success": True,
                "seeded_count": count,
                "season": season,
                "overwrite": overwrite,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/archetypes-db/similarity-groups")
    def api_similarity_groups_db():
        """Get player similarity groups from database."""
        season = request.args.get("season", "2025-26")
        
        db = get_db()
        with db.connect() as conn:
            groups = get_similarity_groups_db(conn, season)
        
        return jsonify({"groups": groups, "season": season})
    
    @app.route("/api/archetypes-db/elite-defenders")
    def api_elite_defenders_db():
        """Get elite defenders by position from database."""
        season = request.args.get("season", "2025-26")
        
        db = get_db()
        with db.connect() as conn:
            defenders = get_elite_defenders_db(conn, season)
        
        return jsonify({"defenders_by_position": defenders, "season": season})
    
    @app.route("/api/archetypes-db/matchup-check", methods=["POST"])
    def api_matchup_check_db():
        """Check if we should avoid betting on a player using DB-backed data."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        player_name = data.get("player", "").strip()
        opponent_team = data.get("opponent", "").strip()
        season = data.get("season", "2025-26")
        
        if not player_name or not opponent_team:
            return jsonify({"error": "Player and opponent team required"}), 400
        
        db = get_db()
        with db.connect() as conn:
            archetype = get_player_archetype_db(conn, player_name, season)
            if not archetype:
                return jsonify({
                    "player": player_name,
                    "opponent": opponent_team,
                    "avoid": False,
                    "reason": "Player not in database or defaults",
                    "defenders": [],
                })
            
            avoid, defenders = should_avoid_betting_over_db(conn, player_name, opponent_team, season)
        
        return jsonify({
            "player": player_name,
            "player_position": archetype.position,
            "player_archetype": archetype.primary_offensive,
            "opponent": opponent_team,
            "avoid": avoid,
            "elite_defenders": defenders,
            "recommendation": "Consider UNDER or avoid" if avoid else "Standard projection",
            "source": archetype.source,
        })
    
    @app.route("/api/archetypes-db/team/<team_name>")
    def api_team_roster_db(team_name: str):
        """Get roster archetypes for a team from database."""
        season = request.args.get("season", "2025-26")
        
        # Convert abbreviation to full name if needed
        full_name = team_name_from_abbrev(team_name.upper()) or team_name
        
        db = get_db()
        with db.connect() as conn:
            roster = get_roster_for_team_db(conn, full_name, season)
        
        return jsonify({
            "team": full_name,
            "abbrev": abbrev_from_team_name(full_name),
            "roster": [
                {
                    "player": p.player_name,
                    "position": p.position,
                    "height": p.height,
                    "primary_offensive": p.primary_offensive,
                    "secondary_offensive": p.secondary_offensive,
                    "defensive_role": p.defensive_role,
                    "tier": p.tier,
                    "is_elite_defender": p.is_elite_defender,
                    "is_star": p.is_star,
                    "source": p.source,
                }
                for p in roster
            ],
            "count": len(roster),
            "season": season,
        })
    
    @app.route("/api/archetypes-db/stats")
    def api_archetypes_stats():
        """Get statistics about archetypes in database."""
        season = request.args.get("season", "2025-26")
        
        db = get_db()
        with db.connect() as conn:
            total = get_archetype_count_db(conn, season)
            
            # Get counts by tier
            tier_counts = conn.execute(
                """
                SELECT tier, COUNT(*) as count
                FROM player_archetypes
                WHERE season = ?
                GROUP BY tier
                ORDER BY tier
                """,
                (season,),
            ).fetchall()
            
            # Get counts by source
            source_counts = conn.execute(
                """
                SELECT source, COUNT(*) as count
                FROM player_archetypes
                WHERE season = ?
                GROUP BY source
                """,
                (season,),
            ).fetchall()
            
            # Get count of elite defenders
            elite_count = conn.execute(
                """
                SELECT COUNT(*) as count
                FROM player_archetypes
                WHERE season = ? AND is_elite_defender = 1
                """,
                (season,),
            ).fetchone()
        
        # Count from defaults (hard-coded)
        from ..engine.roster import PLAYER_DATABASE
        defaults_count = len(PLAYER_DATABASE)
        
        return jsonify({
            "season": season,
            "total_in_db": total,
            "defaults_available": defaults_count,
            "by_tier": {str(r["tier"]): r["count"] for r in tier_counts},
            "by_source": {r["source"]: r["count"] for r in source_counts},
            "elite_defenders": elite_count["count"] if elite_count else 0,
        })
    
    # -------------------------------------------------------------------------
    # Star Player Management API Endpoints
    # -------------------------------------------------------------------------
    
    @app.route("/api/archetypes-db/player/<player_name>/star", methods=["POST", "PUT"])
    def api_toggle_star_status(player_name: str):
        """Toggle or set star status for a player."""
        data = request.get_json() or {}
        is_star = data.get("is_star", True)
        season = data.get("season", "2025-26")
        
        db = get_db()
        try:
            with db.connect() as conn:
                success = toggle_star_status(conn, player_name, is_star, season)
            
            return jsonify({
                "success": success,
                "player": player_name,
                "is_star": is_star,
                "season": season,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/archetypes-db/stars")
    def api_all_star_players():
        """Get all star players across all teams."""
        season = request.args.get("season", "2025-26")
        team = request.args.get("team", "")
        
        db = get_db()
        with db.connect() as conn:
            if team:
                full_name = team_name_from_abbrev(team.upper()) or team
                stars = get_star_players_for_team(conn, full_name, season)
            else:
                stars = get_all_star_players(conn, season)
        
        return jsonify({
            "stars": [
                {
                    "player": s.player_name,
                    "team": s.team,
                    "position": s.position,
                    "tier": s.tier,
                    "primary_offensive": s.primary_offensive,
                    "is_elite_defender": s.is_elite_defender,
                }
                for s in stars
            ],
            "count": len(stars),
            "season": season,
        })
    
    @app.route("/api/archetypes-db/team/<team_name>/stars")
    def api_team_stars(team_name: str):
        """Get star players for a specific team."""
        season = request.args.get("season", "2025-26")
        full_name = team_name_from_abbrev(team_name.upper()) or team_name
        
        db = get_db()
        with db.connect() as conn:
            stars = get_star_players_for_team(conn, full_name, season)
        
        return jsonify({
            "team": full_name,
            "abbrev": abbrev_from_team_name(full_name),
            "stars": [
                {
                    "player": s.player_name,
                    "position": s.position,
                    "tier": s.tier,
                    "primary_offensive": s.primary_offensive,
                    "is_elite_defender": s.is_elite_defender,
                }
                for s in stars
            ],
            "count": len(stars),
            "season": season,
        })

    @app.route("/api/star-players/toggle", methods=["POST"])
    def api_star_players_toggle():
        """Toggle star status for a player (used by team detail page)."""
        data = request.get_json() or {}
        player_name = data.get("player_name")
        season = data.get("season", "2025-26")
        
        if not player_name:
            return jsonify({"success": False, "error": "player_name is required"}), 400
        
        db = get_db()
        try:
            with db.connect() as conn:
                # First check current star status
                current_status = is_star_player(conn, player_name, season)
                new_status = not current_status
                
                # Toggle the status
                success = toggle_star_status(conn, player_name, new_status, season)
                
                return jsonify({
                    "success": success,
                    "player_name": player_name,
                    "is_star": new_status,
                    "season": season,
                })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/player/bet-status", methods=["POST"])
    def api_player_bet_status():
        """Set bet status for a player (0=avoid, 1=neutral, 2=star)."""
        data = request.get_json() or {}
        player_name = data.get("player_name")
        new_status = data.get("bet_status")
        team = data.get("team")  # Team is important for new entries
        season = data.get("season", "2025-26")
        
        if not player_name:
            return jsonify({"success": False, "error": "player_name is required"}), 400
        
        if new_status is None:
            return jsonify({"success": False, "error": "bet_status is required"}), 400
        
        if new_status not in [0, 1, 2]:
            return jsonify({"success": False, "error": "bet_status must be 0, 1, or 2"}), 400
        
        db = get_db()
        try:
            with db.connect() as conn:
                # Set the new bet status
                success = set_bet_status(conn, player_name, new_status, team=team, season=season)
                
                return jsonify({
                    "success": success,
                    "player_name": player_name,
                    "bet_status": new_status,
                    "is_star": new_status == BET_STATUS_STAR,
                    "team": team,
                    "season": season,
                })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/player/bet-status/<player_name>")
    def api_get_player_bet_status(player_name: str):
        """Get bet status for a player."""
        season = request.args.get("season", "2025-26")
        
        db = get_db()
        try:
            with db.connect() as conn:
                status = get_bet_status(conn, player_name, season)
                
                return jsonify({
                    "success": True,
                    "player_name": player_name,
                    "bet_status": status,
                    "is_star": status == BET_STATUS_STAR,
                    "season": season,
                })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/salaries")
    def api_salaries():
        """Get player salaries."""
        limit = request.args.get("limit", 100, type=int)
        team = request.args.get("team", "")
        
        db = get_db()
        with db.connect() as conn:
            # Check if salary table exists and has data
            try:
                if team:
                    rows = conn.execute(
                        """
                        SELECT salary_rank, player_name, position, team, salary
                        FROM player_salaries
                        WHERE team LIKE ?
                        ORDER BY salary DESC
                        LIMIT ?
                        """,
                        (f"%{team}%", limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT salary_rank, player_name, position, team, salary
                        FROM player_salaries
                        ORDER BY salary DESC
                        LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()
                
                return jsonify({
                    "salaries": [
                        {
                            "rank": r["salary_rank"],
                            "player": r["player_name"],
                            "position": r["position"],
                            "team": r["team"],
                            "salary": r["salary"],
                            "salary_formatted": f"${r['salary']:,}",
                        }
                        for r in rows
                    ]
                })
            except Exception:
                return jsonify({"salaries": [], "note": "Salary data not yet imported"})
    
    @app.route("/api/ingest/salaries", methods=["POST"])
    def api_ingest_salaries():
        """Ingest salary data from pasted text."""
        from ..ingest.salary_parser import parse_salary_text, ingest_salaries
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "No salary text provided"}), 400
        
        try:
            salaries = parse_salary_text(text)
            if not salaries:
                return jsonify({"error": "No salaries parsed from text"}), 400
            
            db = get_db()
            with db.connect() as conn:
                count = ingest_salaries(conn, salaries)
            
            return jsonify({
                "success": True,
                "count": count,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/ingest/game-line", methods=["POST"])
    def api_ingest_game_line():
        """Ingest a game spread/line."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        game_date = data.get("date", "").strip()
        away_team = data.get("away", "").strip().upper()
        home_team = data.get("home", "").strip().upper()
        spread = data.get("spread")  # Home team spread (negative = home favored)
        over_under = data.get("over_under")
        book = data.get("book", "consensus").strip()
        
        if not game_date or not away_team or not home_team:
            return jsonify({"error": "Date, away team, and home team are required"}), 400
        
        db = get_db()
        try:
            with db.connect() as conn:
                from ..db import get_or_create_team
                away_team_name = team_name_from_abbrev(away_team) or away_team
                home_team_name = team_name_from_abbrev(home_team) or home_team
                
                away_id = get_or_create_team(conn, away_team_name)
                home_id = get_or_create_team(conn, home_team_name)
                
                conn.execute(
                    """
                    INSERT OR REPLACE INTO game_lines 
                    (game_date, away_team_id, home_team_id, spread, over_under, book)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (game_date, away_id, home_id, spread, over_under, book),
                )
                conn.commit()
            
            return jsonify({
                "success": True,
                "game_date": game_date,
                "matchup": f"{away_team} @ {home_team}",
                "spread": spread,
                "over_under": over_under,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/game-lines")
    def api_game_lines():
        """Get game lines/spreads."""
        date = request.args.get("date", "")
        close_only = request.args.get("close_only", "false").lower() == "true"
        
        db = get_db()
        with db.connect() as conn:
            try:
                if date:
                    sql = """
                        SELECT gl.game_date, t1.name AS away_team, t2.name AS home_team,
                               gl.spread, gl.over_under, gl.book
                        FROM game_lines gl
                        JOIN teams t1 ON t1.id = gl.away_team_id
                        JOIN teams t2 ON t2.id = gl.home_team_id
                        WHERE gl.game_date = ?
                    """
                    params = [date]
                else:
                    sql = """
                        SELECT gl.game_date, t1.name AS away_team, t2.name AS home_team,
                               gl.spread, gl.over_under, gl.book
                        FROM game_lines gl
                        JOIN teams t1 ON t1.id = gl.away_team_id
                        JOIN teams t2 ON t2.id = gl.home_team_id
                        ORDER BY gl.game_date DESC
                        LIMIT 50
                    """
                    params = []
                
                if close_only:
                    # Filter to games with spread <= 6 points
                    if date:
                        sql = sql.replace("WHERE", "WHERE ABS(gl.spread) <= 6 AND")
                    else:
                        sql = sql.replace("ORDER BY", "WHERE ABS(gl.spread) <= 6 ORDER BY")
                
                rows = conn.execute(sql, params).fetchall()
                
                return jsonify({
                    "game_lines": [
                        {
                            "date": r["game_date"],
                            "away": r["away_team"],
                            "away_abbrev": abbrev_from_team_name(r["away_team"]),
                            "home": r["home_team"],
                            "home_abbrev": abbrev_from_team_name(r["home_team"]),
                            "spread": r["spread"],
                            "over_under": r["over_under"],
                            "book": r["book"],
                            "is_close": abs(r["spread"] or 0) <= 6,
                        }
                        for r in rows
                    ]
                })
            except Exception:
                return jsonify({"game_lines": [], "note": "No game lines data yet"})
    
    @app.route("/api/injuries")
    def api_injuries():
        """Get injury report."""
        date = request.args.get("date", "")
        team = request.args.get("team", "")
        
        db = get_db()
        with db.connect() as conn:
            try:
                sql = """
                    SELECT ir.game_date, t.name AS team, 
                           COALESCE(p.name, ir.player_name) AS player,
                           ir.status, ir.minutes_limit, ir.notes
                    FROM injury_report ir
                    JOIN teams t ON t.id = ir.team_id
                    LEFT JOIN players p ON p.id = ir.player_id
                """
                params = []
                conditions = []
                
                if date:
                    conditions.append("ir.game_date = ?")
                    params.append(date)
                if team:
                    conditions.append("t.name LIKE ?")
                    params.append(f"%{team}%")
                
                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)
                
                sql += " ORDER BY ir.game_date DESC, t.name, ir.status"
                
                rows = conn.execute(sql, params).fetchall()
                
                return jsonify({
                    "injuries": [
                        {
                            "date": r["game_date"],
                            "team": r["team"],
                            "team_abbrev": abbrev_from_team_name(r["team"]),
                            "player": r["player"],
                            "status": r["status"],
                            "minutes_limit": r["minutes_limit"],
                            "notes": r["notes"],
                        }
                        for r in rows
                    ]
                })
            except Exception:
                return jsonify({"injuries": []})
    
    @app.route("/api/injuries")
    def api_get_injuries():
        """Get injuries for specified teams on a given date."""
        away = request.args.get("away", "").strip().upper()
        home = request.args.get("home", "").strip().upper()
        game_date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        db = get_db()
        try:
            with db.connect() as conn:
                # Get away team injuries
                away_injuries = {}
                if away:
                    away_team_id = conn.execute(
                        "SELECT id FROM teams WHERE abbrev = ?", (away,)
                    ).fetchone()
                    if away_team_id:
                        rows = conn.execute(
                            """
                            SELECT player_name, status
                            FROM injury_report
                            WHERE team_id = ? AND game_date = ?
                            """,
                            (away_team_id["id"], game_date)
                        ).fetchall()
                        for row in rows:
                            away_injuries[row["player_name"]] = row["status"]
                
                # Get home team injuries
                home_injuries = {}
                if home:
                    home_team_id = conn.execute(
                        "SELECT id FROM teams WHERE abbrev = ?", (home,)
                    ).fetchone()
                    if home_team_id:
                        rows = conn.execute(
                            """
                            SELECT player_name, status
                            FROM injury_report
                            WHERE team_id = ? AND game_date = ?
                            """,
                            (home_team_id["id"], game_date)
                        ).fetchall()
                        for row in rows:
                            home_injuries[row["player_name"]] = row["status"]
                
                return jsonify({
                    "away_injuries": away_injuries,
                    "home_injuries": home_injuries,
                    "date": game_date,
                })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/projections/with-injuries", methods=["POST"])
    def api_projections_with_injuries():
        """Generate projections with custom injury adjustments."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        away = data.get("away", "").strip().upper()
        home = data.get("home", "").strip().upper()
        game_date = data.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
        injuries = data.get("injuries", {"away": {}, "home": {}})
        
        if not away or not home:
            return jsonify({"error": "Please provide both away and home teams"}), 400
        
        db = get_db()
        try:
            with db.connect() as conn:
                # Get base projections
                report = generate_prop_report(
                    conn=conn,
                    away_abbrev=away,
                    home_abbrev=home,
                    game_date=game_date,
                    lines_date=game_date,
                )
                
                # Apply injury adjustments
                away_injuries = injuries.get("away", {})
                home_injuries = injuries.get("home", {})
                
                # Get OUT players' stats for redistribution
                def get_out_players_stats(projections, injury_dict):
                    out_stats = {"pts": 0, "reb": 0, "ast": 0, "minutes": 0}
                    out_count = 0
                    for p in projections:
                        if injury_dict.get(p["player"]) == "OUT":
                            out_stats["pts"] += p.get("pts", 0)
                            out_stats["reb"] += p.get("reb", 0)
                            out_stats["ast"] += p.get("ast", 0)
                            out_stats["minutes"] += p.get("minutes", 0)
                            out_count += 1
                    return out_stats, out_count
                
                def redistribute_stats(projections, injury_dict, out_stats, out_count):
                    """Redistribute stats from OUT players to remaining players."""
                    if out_count == 0:
                        return projections
                    
                    # Count active players
                    active_players = [p for p in projections if injury_dict.get(p["player"]) != "OUT"]
                    if not active_players:
                        return projections
                    
                    # Only redistribute to top players (by minutes)
                    top_active = sorted(active_players, key=lambda x: x.get("minutes", 0), reverse=True)[:7]
                    
                    # Calculate boost per player
                    boost_factor = 1.0 / len(top_active)
                    
                    adjusted = []
                    for p in projections:
                        p_copy = dict(p)
                        if p in top_active:
                            # Boost stats proportionally
                            p_copy["pts"] = p["pts"] + (out_stats["pts"] * boost_factor * 0.6)
                            p_copy["reb"] = p["reb"] + (out_stats["reb"] * boost_factor * 0.4)
                            p_copy["ast"] = p["ast"] + (out_stats["ast"] * boost_factor * 0.5)
                            p_copy["minutes"] = min(p["minutes"] + (out_stats["minutes"] * boost_factor * 0.3), 42)
                            p_copy["injury_boosted"] = True
                        adjusted.append(p_copy)
                    
                    return adjusted
                
                # Process away team
                away_out_stats, away_out_count = get_out_players_stats(report.get("away_projections", []), away_injuries)
                adjusted_away = redistribute_stats(report.get("away_projections", []), away_injuries, away_out_stats, away_out_count)
                
                # Process home team
                home_out_stats, home_out_count = get_out_players_stats(report.get("home_projections", []), home_injuries)
                adjusted_home = redistribute_stats(report.get("home_projections", []), home_injuries, home_out_stats, home_out_count)
                
                # Update report with adjusted projections
                report["away_projections"] = adjusted_away
                report["home_projections"] = adjusted_home
                report["injury_adjustments"] = {
                    "away_out_count": away_out_count,
                    "home_out_count": home_out_count,
                    "away_redistributed": away_out_stats,
                    "home_redistributed": home_out_stats,
                }
                
                return jsonify(report)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/ingest/injury", methods=["POST"])
    def api_ingest_injury():
        """Add an injury report entry."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        game_date = data.get("date", "").strip()
        team = data.get("team", "").strip().upper()
        player = data.get("player", "").strip()
        status = data.get("status", "OUT").strip().upper()
        minutes_limit = data.get("minutes_limit")
        notes = data.get("notes", "").strip() or None
        
        if not game_date or not team or not player:
            return jsonify({"error": "Date, team, and player are required"}), 400
        
        db = get_db()
        try:
            with db.connect() as conn:
                from ..db import get_or_create_team, get_or_create_player
                
                team_name = team_name_from_abbrev(team) or team
                team_id = get_or_create_team(conn, team_name)
                
                # Try to find existing player
                player_row = conn.execute(
                    "SELECT id FROM players WHERE name LIKE ?", (f"%{player}%",)
                ).fetchone()
                player_id = player_row["id"] if player_row else None
                
                conn.execute(
                    """
                    INSERT INTO injury_report 
                    (game_date, team_id, player_id, player_name, status, minutes_limit, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (game_date, team_id, player_id, player, status, minutes_limit, notes),
                )
                conn.commit()
            
            return jsonify({
                "success": True,
                "player": player,
                "team": team,
                "status": status,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/ingest/injury-report", methods=["POST"])
    def api_ingest_injury_report():
        """Parse and ingest a full injury report from raw text."""
        from ..ingest.injury_parser import parse_injury_report_text, summarize_injury_report
        from ..db import get_or_create_team
        import unicodedata
        
        def normalize_name_for_match(name: str) -> str:
            """Normalize a name for matching by removing accents and lowercasing."""
            # Normalize unicode characters to their decomposed form, then remove combining marks
            nfkd = unicodedata.normalize('NFKD', name)
            ascii_name = ''.join(c for c in nfkd if not unicodedata.combining(c))
            return ascii_name.lower().strip()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "No injury report text provided"}), 400
        
        # Optional: filter to specific date
        filter_date = data.get("date", "").strip() or None
        # Whether to include G-League assignments
        include_g_league = data.get("include_g_league", False)
        
        try:
            report = parse_injury_report_text(text)
            
            db = get_db()
            ingested_count = 0
            skipped_count = 0
            
            with db.connect() as conn:
                # Pre-fetch all players for efficient matching
                all_players = conn.execute("SELECT id, name FROM players").fetchall()
                player_lookup = {}
                for p in all_players:
                    normalized = normalize_name_for_match(p["name"])
                    player_lookup[normalized] = p["id"]
                    # Also add last name for partial matching
                    parts = p["name"].split()
                    if len(parts) >= 2:
                        last_name = normalize_name_for_match(parts[-1])
                        first_name = normalize_name_for_match(parts[0])
                        # Store "lastname firstname" combo for "LastName, FirstName" format matching
                        player_lookup[f"{last_name} {first_name}"] = p["id"]
                
                for entry in report.entries:
                    # Filter by date if specified
                    if filter_date and entry.game_date != filter_date:
                        skipped_count += 1
                        continue
                    
                    # Skip G-League unless requested
                    if entry.is_g_league and not include_g_league:
                        skipped_count += 1
                        continue
                    
                    team_id = get_or_create_team(conn, entry.team_name)
                    
                    # Try to find existing player using normalized name matching
                    normalized_entry_name = normalize_name_for_match(entry.player_name)
                    player_id = player_lookup.get(normalized_entry_name)
                    
                    # If not found, try partial matching
                    if not player_id:
                        for normalized_db_name, pid in player_lookup.items():
                            # Check if entry name is contained in db name or vice versa
                            if (normalized_entry_name in normalized_db_name or 
                                normalized_db_name in normalized_entry_name):
                                player_id = pid
                                break
                    
                    # Check if entry already exists - match by player name regardless of team_id
                    # This prevents duplicates when team name variations cause different team_ids
                    existing = conn.execute(
                        """
                        SELECT id FROM injury_report 
                        WHERE game_date = ? AND player_name = ?
                        """,
                        (entry.game_date, entry.player_name),
                    ).fetchone()
                    
                    if existing:
                        # Update existing entry (also update team_id to the most recent)
                        conn.execute(
                            """
                            UPDATE injury_report 
                            SET status = ?, notes = ?, player_id = ?, team_id = ?
                            WHERE id = ?
                            """,
                            (entry.status, entry.reason, player_id, team_id, existing["id"]),
                        )
                    else:
                        # Insert new entry
                        conn.execute(
                            """
                            INSERT INTO injury_report 
                            (game_date, team_id, player_id, player_name, status, notes)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (entry.game_date, team_id, player_id, entry.player_name, 
                             entry.status, entry.reason),
                        )
                    
                    ingested_count += 1
                
                conn.commit()
            
            summary = summarize_injury_report(report)
            
            return jsonify({
                "success": True,
                "report_date": report.report_date,
                "total_entries": len(report.entries),
                "ingested": ingested_count,
                "skipped": skipped_count,
                "teams_not_submitted": report.teams_not_submitted,
                "summary": summary,
                "warnings": report.warnings,  # Include any parsing warnings
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/injuries/clear", methods=["POST"])
    def api_clear_injuries():
        """Clear injury report entries for a specific date or all."""
        data = request.get_json() or {}
        date = data.get("date", "").strip()
        
        db = get_db()
        try:
            with db.connect() as conn:
                if date:
                    conn.execute("DELETE FROM injury_report WHERE game_date = ?", (date,))
                else:
                    conn.execute("DELETE FROM injury_report")
                conn.commit()
            
            return jsonify({
                "success": True,
                "cleared_date": date or "all",
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    # -------------------------------------------------------------------------
    # Defense vs Position Data API
    # -------------------------------------------------------------------------
    
    @app.route("/api/ingest/defense-vs-position", methods=["POST"])
    def api_ingest_defense_vs_position():
        """
        Parse and ingest defense vs position data from Hashtag Basketball.
        
        Expected JSON: { "text": "raw page content", "position": "PG" }
        Position can be: PG, SG, SF, PF, C
        """
        from ..ingest.defense_position_parser import (
            parse_defense_vs_position_text,
            save_defense_vs_position_to_db,
        )
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get("text", "").strip()
        position = data.get("position", "").strip().upper()
        
        if not text:
            return jsonify({"error": "No defense data text provided"}), 400
        
        if position and position not in ["PG", "SG", "SF", "PF", "C"]:
            return jsonify({"error": f"Invalid position: {position}. Must be PG, SG, SF, PF, or C"}), 400
        
        try:
            # Parse the text
            result = parse_defense_vs_position_text(text, expected_position=position if position else None)
            
            if not result.rows:
                error_msg = "No valid data rows parsed. "
                if result.errors:
                    error_msg += ". ".join(result.errors)
                return jsonify({"error": error_msg}), 400
            
            # Save to database
            db = get_db()
            with db.connect() as conn:
                save_result = save_defense_vs_position_to_db(conn, result)
            
            return jsonify({
                "success": True,
                "position": save_result.get("position", result.position),
                "as_of_date": save_result.get("as_of_date"),
                "inserted": save_result.get("inserted", 0),
                "updated": save_result.get("updated", 0),
                "total": save_result.get("total", len(result.rows)),
                "source_date": result.last_updated,
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/defense-vs-position/status")
    def api_defense_vs_position_status():
        """
        Get the last updated status for all defense vs position data.
        Returns when each position's data was last imported.
        """
        from ..ingest.defense_position_parser import get_defense_vs_position_last_updated
        
        db = get_db()
        with db.connect() as conn:
            try:
                status = get_defense_vs_position_last_updated(conn)
                return jsonify({
                    "positions": status,
                })
            except Exception as e:
                return jsonify({"positions": {}, "error": str(e)})
    
    @app.route("/api/defense-vs-position/<team_abbrev>")
    def api_defense_vs_position_team(team_abbrev: str):
        """
        Get defense vs position data for a specific team.
        Returns how the team defends each position.
        """
        from ..ingest.defense_position_parser import get_all_defense_vs_position_for_team
        
        team_abbrev = team_abbrev.upper()
        
        db = get_db()
        with db.connect() as conn:
            try:
                rows = get_all_defense_vs_position_for_team(conn, team_abbrev)
                
                if not rows:
                    return jsonify({
                        "team": team_abbrev,
                        "positions": [],
                        "note": "No defense vs position data available for this team",
                    })
                
                return jsonify({
                    "team": team_abbrev,
                    "positions": [
                        {
                            "position": row.position,
                            "overall_rank": row.overall_rank,
                            "pts_allowed": row.pts_allowed,
                            "pts_rank": row.pts_rank,
                            "reb_allowed": row.reb_allowed,
                            "reb_rank": row.reb_rank,
                            "ast_allowed": row.ast_allowed,
                            "ast_rank": row.ast_rank,
                            "fg_pct_allowed": row.fg_pct_allowed,
                            "fg_pct_rank": row.fg_pct_rank,
                            "tpm_allowed": row.tpm_allowed,
                            "tpm_rank": row.tpm_rank,
                        }
                        for row in rows
                    ]
                })
            except Exception as e:
                return jsonify({"team": team_abbrev, "positions": [], "error": str(e)})
    
    @app.route("/api/defense-vs-position/analysis/<player_position>/<opponent_abbrev>")
    def api_defense_analysis_for_matchup(player_position: str, opponent_abbrev: str):
        """
        Get matchup analysis for a player position against a specific opponent.
        Returns factors for PTS, REB, AST predictions.
        """
        from ..ingest.defense_position_parser import calculate_defense_factor
        
        player_position = player_position.upper()
        opponent_abbrev = opponent_abbrev.upper()
        
        if player_position not in ["PG", "SG", "SF", "PF", "C"]:
            return jsonify({"error": f"Invalid position: {player_position}"}), 400
        
        db = get_db()
        with db.connect() as conn:
            try:
                pts_factor = calculate_defense_factor(conn, opponent_abbrev, player_position, "pts")
                reb_factor = calculate_defense_factor(conn, opponent_abbrev, player_position, "reb")
                ast_factor = calculate_defense_factor(conn, opponent_abbrev, player_position, "ast")
                
                if not pts_factor:
                    return jsonify({
                        "position": player_position,
                        "opponent": opponent_abbrev,
                        "note": "No defense vs position data available",
                        "factors": None,
                    })
                
                return jsonify({
                    "position": player_position,
                    "opponent": opponent_abbrev,
                    "factors": {
                        "pts": pts_factor,
                        "reb": reb_factor,
                        "ast": ast_factor,
                    },
                    "recommendation": {
                        "pts": "OVER" if pts_factor["factor"] > 1.05 else ("UNDER" if pts_factor["factor"] < 0.95 else "NEUTRAL"),
                        "reb": "OVER" if reb_factor["factor"] > 1.05 else ("UNDER" if reb_factor["factor"] < 0.95 else "NEUTRAL"),
                        "ast": "OVER" if ast_factor["factor"] > 1.05 else ("UNDER" if ast_factor["factor"] < 0.95 else "NEUTRAL"),
                    }
                })
            except Exception as e:
                return jsonify({
                    "position": player_position,
                    "opponent": opponent_abbrev,
                    "error": str(e),
                })

    # -------------------------------------------------------------------------
    # Player DRTG (Defensive Rating) API Endpoints
    # -------------------------------------------------------------------------
    
    @app.route("/api/ingest/player-drtg", methods=["POST"])
    def api_ingest_player_drtg():
        """
        Parse and ingest player DRTG data from StatMuse or similar sources.
        
        Expected JSON: { "text": "raw page content", "team": "PHX", "season": "2025-26" }
        Team is optional - will be auto-detected from data.
        """
        from ..ingest.player_drtg_parser import parse_player_drtg_text, save_player_drtg_to_db
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get("text", "").strip()
        team = data.get("team", "").strip().upper() or None
        season = data.get("season", "2025-26").strip()
        
        if not text:
            return jsonify({"error": "No DRTG data text provided"}), 400
        
        try:
            # Parse the text (team will be auto-detected if not provided)
            result = parse_player_drtg_text(text, expected_team=team, expected_season=season)
            
            if not result.rows:
                error_msg = "No valid DRTG data rows parsed. "
                if result.errors:
                    error_msg += ". ".join(result.errors)
                return jsonify({"error": error_msg}), 400
            
            # Save to database
            db = get_db()
            with db.connect() as conn:
                save_result = save_player_drtg_to_db(conn, result)
            
            detected_team = save_result.get("team", result.team_abbrev)
            was_auto_detected = team is None and detected_team is not None
            
            return jsonify({
                "success": True,
                "team": detected_team,
                "team_auto_detected": was_auto_detected,
                "season": season,
                "inserted": save_result.get("inserted", 0),
                "updated": save_result.get("updated", 0),
                "total": save_result.get("total", len(result.rows)),
                "players": [
                    {"name": r.name, "drtg": r.drtg, "rank": r.rank}
                    for r in result.rows[:10]
                ],
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/player-drtg/<team_abbrev>")
    def api_player_drtg_team(team_abbrev: str):
        """Get player DRTG data for a specific team."""
        from ..ingest.player_drtg_parser import get_team_drtg_rankings, get_drtg_data_freshness
        
        team_abbrev = team_abbrev.upper()
        season = request.args.get("season", "2025-26")
        
        db = get_db()
        with db.connect() as conn:
            rankings = get_team_drtg_rankings(conn, team_abbrev, season)
            freshness = get_drtg_data_freshness(conn, team_abbrev)
        
        if not rankings:
            return jsonify({
                "team": team_abbrev,
                "players": [],
                "note": "No DRTG data available for this team",
            })
        
        return jsonify({
            "team": team_abbrev,
            "season": season,
            "last_updated": freshness.get("last_updated"),
            "players": [
                {
                    "rank": r.rank,
                    "name": r.name,
                    "drtg": r.drtg,
                    "games_played": r.games_played,
                    "minutes_per_game": r.minutes_per_game,
                    "ppg": r.ppg,
                    "rpg": r.rpg,
                    "apg": r.apg,
                    "spg": r.spg,
                    "bpg": r.bpg,
                    "plus_minus": r.plus_minus,
                }
                for r in rankings
            ],
        })
    
    @app.route("/api/player-drtg/league")
    def api_player_drtg_league():
        """Get league-wide DRTG rankings (best defenders)."""
        from ..ingest.player_drtg_parser import get_league_drtg_rankings
        
        season = request.args.get("season", "2025-26")
        limit = request.args.get("limit", 50, type=int)
        min_minutes = request.args.get("min_minutes", 15.0, type=float)
        
        db = get_db()
        with db.connect() as conn:
            rankings = get_league_drtg_rankings(conn, season, limit, min_minutes)
        
        return jsonify({
            "season": season,
            "min_minutes": min_minutes,
            "players": [
                {
                    "rank": r.rank,
                    "name": r.name,
                    "team": r.team_abbrev,
                    "drtg": r.drtg,
                    "games_played": r.games_played,
                    "minutes_per_game": r.minutes_per_game,
                    "ppg": r.ppg,
                    "rpg": r.rpg,
                    "spg": r.spg,
                    "bpg": r.bpg,
                }
                for r in rankings
            ],
        })
    
    @app.route("/api/player-drtg/status")
    def api_player_drtg_status():
        """Get DRTG data freshness status for all teams."""
        from ..ingest.player_drtg_parser import (
            get_drtg_data_freshness,
            get_teams_needing_drtg_update,
        )
        
        max_age = request.args.get("max_age", 14, type=int)
        
        db = get_db()
        with db.connect() as conn:
            freshness = get_drtg_data_freshness(conn)
            needs_update = get_teams_needing_drtg_update(conn, max_age)
        
        return jsonify({
            "teams_with_data": freshness,
            "teams_count": len(freshness),
            "needs_update": needs_update,
            "needs_update_count": len(needs_update),
            "max_age_days": max_age,
        })
    
    @app.route("/api/player-drtg/<player_name>/drtg")
    def api_player_drtg_individual(player_name: str):
        """Get DRTG data for an individual player."""
        from ..ingest.player_drtg_parser import get_player_drtg
        
        season = request.args.get("season", "2025-26")
        
        db = get_db()
        with db.connect() as conn:
            drtg = get_player_drtg(conn, player_name, season)
        
        if not drtg:
            return jsonify({"error": "Player DRTG data not found"}), 404
        
        return jsonify({
            "player": drtg.name,
            "team": drtg.team_abbrev,
            "season": drtg.season,
            "drtg": drtg.drtg,
            "rank": drtg.rank,
            "games_played": drtg.games_played,
            "minutes_per_game": drtg.minutes_per_game,
            "ppg": drtg.ppg,
            "rpg": drtg.rpg,
            "apg": drtg.apg,
            "spg": drtg.spg,
            "bpg": drtg.bpg,
            "plus_minus": drtg.plus_minus,
        })

    @app.route("/api/ingest/matchups", methods=["POST"])
    def api_ingest_matchups():
        """Parse matchup text and store for today's games."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "No matchup text provided"}), 400
        
        try:
            matchups = parse_matchups_text(text)
            
            if not matchups:
                return jsonify({"error": "No matchups could be parsed from text. Make sure the format includes team names and @ symbol. Completed games (with scores) are automatically skipped."}), 400
            
            # Determine if date was auto-extracted (check if all matchups have same date)
            detected_date = matchups[0].game_date if matchups else None
            
            # Store matchups in session/memory for analysis
            # We'll return them for client-side usage
            result_matchups = []
            for m in matchups:
                result_matchups.append({
                    "game_date": m.game_date,
                    "away_team": m.away_team,
                    "home_team": m.home_team,
                    "away_abbrev": m.away_abbrev,
                    "home_abbrev": m.home_abbrev,
                    "game_time": m.game_time,
                    "spread": m.spread,
                    "favorite_abbrev": m.favorite_abbrev,
                    "over_under": m.over_under,
                    "tv_channel": m.tv_channel,
                    "status": m.status,
                })
            
            return jsonify({
                "success": True,
                "count": len(result_matchups),
                "detected_date": detected_date,
                "matchups": result_matchups,
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to parse matchups: {str(e)}"}), 400
    
    @app.route("/api/recalculate", methods=["POST"])
    def api_recalculate():
        """
        Trigger recalculation of all projections and model updates.
        This should be called after adding all box scores for a day.
        """
        from ..engine.matchup_advisor import generate_comprehensive_matchup_report
        
        data = request.get_json() or {}
        target_date = data.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
        
        db = get_db()
        try:
            with db.connect() as conn:
                # 1. Get count of games added recently
                games_today = conn.execute(
                    "SELECT COUNT(*) as n FROM games WHERE game_date = ?",
                    (target_date,),
                ).fetchone()["n"]
                
                # 2. Get count of all games
                total_games = conn.execute(
                    "SELECT COUNT(*) as n FROM games"
                ).fetchone()["n"]
                
                # 3. Get latest game date
                latest = conn.execute(
                    "SELECT game_date FROM games ORDER BY game_date DESC LIMIT 1"
                ).fetchone()
                latest_date = latest["game_date"] if latest else None
                
                # 4. Calculate updated team defense ratings
                from ..engine.game_context import get_all_team_defense_ratings
                defense_ratings = get_all_team_defense_ratings(conn)
                
                # 5. Get summary stats
                players = conn.execute("SELECT COUNT(*) as n FROM players").fetchone()["n"]
                
            return jsonify({
                "success": True,
                "message": "Model recalculated with latest data",
                "stats": {
                    "games_for_date": games_today,
                    "total_games": total_games,
                    "total_players": players,
                    "latest_game_date": latest_date,
                    "teams_with_defense_data": len(defense_ratings),
                },
                "date": target_date,
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 400
    
    @app.route("/api/modellab/run", methods=["POST"])
    def run_model_optimization():
        """Run the model optimization for the given date range."""
        data = request.json or {}
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        if not start_date or not end_date:
            return jsonify({"error": "Missing dates"}), 400
            
        try:
            results = run_optimization_grid(start_date, end_date)
            return jsonify({
                "results": [r.to_dict() for r in results]
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/modellab/backtest", methods=["POST"])
    def api_modellab_backtest():
        """
        Run a backtest over a date range using the selected model.
        
        Request body:
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)
            - model: "v8" (default), "production", "v4", or "v5"
        
        Returns aggregate statistics and daily breakdown.
        """
        from datetime import timedelta
        
        data = request.json or {}
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        model_version = data.get("model", "v8")
        
        if not start_date or not end_date:
            return jsonify({"error": "Missing start_date or end_date"}), 400
        
        try:
            # Import the appropriate model
            if model_version == "v5":
                from ..engine.model_v5 import get_daily_picks, ModelV5Config as ModelConfig
                config = ModelConfig()
            elif model_version == "v4":
                from ..engine.model_v4 import get_daily_picks, ModelV4Config as ModelConfig
                config = ModelConfig()
            elif model_version == "production":
                from ..engine.model_production import get_daily_picks, ModelConfig
                config = ModelConfig()
            else:
                # Default: use V8 model
                from ..engine.model_v8 import get_daily_picks, ModelV8Config as ModelConfig
                config = ModelConfig()
            
            db = get_db()
            
            # Aggregate stats
            total_picks = 0
            total_hits = 0
            over_picks = 0
            over_hits = 0
            under_picks = 0
            under_hits = 0
            high_conf_picks = 0
            high_conf_hits = 0
            daily_results = []
            
            current = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                
                try:
                    daily = get_daily_picks(date_str, config=config)
                    
                    if not daily.picks:
                        current += timedelta(days=1)
                        continue
                    
                    with db.connect() as conn:
                        # Get actual results for this date
                        actuals = {}
                        box_data = conn.execute("""
                            SELECT p.name as player_name, bp.pts, bp.reb, bp.ast
                            FROM boxscore_player bp
                            JOIN games g ON bp.game_id = g.id
                            JOIN players p ON bp.player_id = p.id
                            WHERE g.game_date = ?
                        """, (date_str,)).fetchall()
                        
                        for row in box_data:
                            actuals[row["player_name"]] = {
                                "PTS": row["pts"],
                                "REB": row["reb"],
                                "AST": row["ast"],
                            }
                    
                    # Grade picks
                    day_picks = 0
                    day_hits = 0
                    
                    for pick in daily.picks:
                        actual = actuals.get(pick.player_name, {}).get(pick.prop_type)
                        if actual is not None:
                            day_picks += 1
                            total_picks += 1
                            
                            if pick.direction == "OVER":
                                over_picks += 1
                                hit = actual > pick.line
                                if hit:
                                    over_hits += 1
                            else:
                                under_picks += 1
                                hit = actual < pick.line
                                if hit:
                                    under_hits += 1
                            
                            if hit:
                                day_hits += 1
                                total_hits += 1
                            
                            # Track HIGH confidence picks
                            if hasattr(pick, 'confidence') and pick.confidence == "HIGH":
                                high_conf_picks += 1
                                if hit:
                                    high_conf_hits += 1
                    
                    if day_picks > 0:
                        # Get game count for this day
                        with db.connect() as conn:
                            games_row = conn.execute(
                                "SELECT COUNT(*) as n FROM games WHERE game_date = ?",
                                (date_str,)
                            ).fetchone()
                            games = games_row["n"] if games_row else 0
                        
                        daily_results.append({
                            "date": date_str,
                            "games": games,
                            "picks": day_picks,
                            "hits": day_hits,
                            "rate": (day_hits / day_picks * 100) if day_picks > 0 else 0,
                        })
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    # Skip this day if there's an error
                    pass
                
                current += timedelta(days=1)
            
            return jsonify({
                "hit_rate": total_hits / total_picks if total_picks > 0 else 0,
                "total_picks": total_picks,
                "total_hits": total_hits,
                "over_rate": over_hits / over_picks if over_picks > 0 else 0,
                "under_rate": under_hits / under_picks if under_picks > 0 else 0,
                "high_rate": high_conf_hits / high_conf_picks if high_conf_picks > 0 else 0,
                "days_tested": len(daily_results),
                "daily_results": daily_results,
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route("/api/modellab/learn", methods=["POST"])
    def api_modellab_learn():
        """
        Run learning algorithm on historical data to find optimal adjustments.
        Returns adjustments that can be applied to improve predictions.
        """
        data = request.json or {}
        start_date = data.get("start_date", "2025-10-25")
        end_date = data.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        
        try:
            db = get_db()
            
            # Analyze historical performance to find patterns
            with db.connect() as conn:
                # Get picks from model_picks table
                picks = conn.execute("""
                    SELECT * FROM model_picks 
                    WHERE pick_date BETWEEN ? AND ?
                    AND actual_value IS NOT NULL
                """, (start_date, end_date)).fetchall()
                
                if not picks:
                    return jsonify({
                        "adjustments": {},
                        "insights": [{
                            "icon": "📊",
                            "type": "info",
                            "title": "No Historical Data",
                            "text": "No graded picks found in the selected date range. Run backtests to generate data."
                        }]
                    })
                
                # Analyze by prop type
                prop_adjustments = {}
                for prop in ["PTS", "REB", "AST"]:
                    prop_picks = [p for p in picks if p["prop_type"] == prop]
                    if prop_picks:
                        total = len(prop_picks)
                        hits = sum(1 for p in prop_picks if p["result"] == "HIT")
                        rate = hits / total if total > 0 else 0
                        
                        # If below 50%, suggest negative adjustment
                        # If above 55%, suggest positive adjustment
                        if rate < 0.50 and total >= 10:
                            prop_adjustments[f"{prop.lower()}_bias"] = -2.5
                        elif rate > 0.55 and total >= 10:
                            prop_adjustments[f"{prop.lower()}_bias"] = 1.5
                
                # Analyze by direction
                over_picks = [p for p in picks if p["direction"] == "OVER"]
                under_picks = [p for p in picks if p["direction"] == "UNDER"]
                
                over_rate = sum(1 for p in over_picks if p["result"] == "HIT") / len(over_picks) if over_picks else 0
                under_rate = sum(1 for p in under_picks if p["result"] == "HIT") / len(under_picks) if under_picks else 0
                
                if len(over_picks) >= 20 and over_rate < 0.48:
                    prop_adjustments["over_caution"] = -3.0
                if len(under_picks) >= 20 and under_rate < 0.48:
                    prop_adjustments["under_caution"] = -3.0
                
                # Generate insights
                insights = []
                total_picks = len(picks)
                total_hits = sum(1 for p in picks if p["result"] == "HIT")
                overall_rate = total_hits / total_picks if total_picks > 0 else 0
                
                if overall_rate >= 0.55:
                    insights.append({
                        "icon": "🎯",
                        "type": "positive",
                        "title": f"Strong Performance: {overall_rate*100:.1f}%",
                        "text": f"Model is performing well with {total_hits}/{total_picks} hits."
                    })
                elif overall_rate >= 0.48:
                    insights.append({
                        "icon": "📈",
                        "type": "neutral",
                        "title": f"Moderate Performance: {overall_rate*100:.1f}%",
                        "text": "Model is around breakeven. Adjustments may help."
                    })
                else:
                    insights.append({
                        "icon": "⚠️",
                        "type": "warning",
                        "title": f"Below Target: {overall_rate*100:.1f}%",
                        "text": "Model needs calibration. Applying conservative adjustments."
                    })
                
                return jsonify({
                    "adjustments": prop_adjustments,
                    "insights": insights,
                    "overall_rate": overall_rate,
                    "total_picks": total_picks,
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route("/api/modellab/patterns")
    def api_modellab_patterns():
        """
        Get pattern analysis from historical picks.
        Shows which patterns (prop type, direction, confidence) perform best.
        """
        try:
            db = get_db()
            
            with db.connect() as conn:
                # Get all graded picks
                picks = conn.execute("""
                    SELECT prop_type, direction, confidence, result
                    FROM model_picks 
                    WHERE actual_value IS NOT NULL
                """).fetchall()
                
                if not picks:
                    return jsonify({
                        "patterns": [],
                        "prop_stats": {},
                        "message": "No graded picks available. Run backtests first."
                    })
                
                # Analyze by prop type
                prop_stats = {}
                for prop in ["PTS", "REB", "AST"]:
                    prop_picks = [p for p in picks if p["prop_type"] == prop]
                    over_picks = [p for p in prop_picks if p["direction"] == "OVER"]
                    under_picks = [p for p in prop_picks if p["direction"] == "UNDER"]
                    
                    prop_stats[prop.lower()] = {
                        "total": len(prop_picks),
                        "hits": sum(1 for p in prop_picks if p["result"] == "HIT"),
                        "over_total": len(over_picks),
                        "over_hits": sum(1 for p in over_picks if p["result"] == "HIT"),
                        "under_total": len(under_picks),
                        "under_hits": sum(1 for p in under_picks if p["result"] == "HIT"),
                    }
                
                # Build patterns list
                patterns = []
                
                # By confidence level
                for conf in ["HIGH", "MEDIUM", "LOW"]:
                    conf_picks = [p for p in picks if p.get("confidence") == conf]
                    if conf_picks:
                        hits = sum(1 for p in conf_picks if p["result"] == "HIT")
                        patterns.append({
                            "name": f"{conf} Confidence",
                            "icon": "🎯" if conf == "HIGH" else "📊" if conf == "MEDIUM" else "📉",
                            "description": f"Picks with {conf.lower()} confidence",
                            "hits": hits,
                            "misses": len(conf_picks) - hits,
                            "total": len(conf_picks),
                            "rate": (hits / len(conf_picks) * 100) if conf_picks else 0,
                        })
                
                # By direction
                for direction in ["OVER", "UNDER"]:
                    dir_picks = [p for p in picks if p["direction"] == direction]
                    if dir_picks:
                        hits = sum(1 for p in dir_picks if p["result"] == "HIT")
                        patterns.append({
                            "name": f"{direction} Picks",
                            "icon": "⬆️" if direction == "OVER" else "⬇️",
                            "description": f"All {direction.lower()} selections",
                            "hits": hits,
                            "misses": len(dir_picks) - hits,
                            "total": len(dir_picks),
                            "rate": (hits / len(dir_picks) * 100) if dir_picks else 0,
                        })
                
                # By prop type
                for prop in ["PTS", "REB", "AST"]:
                    prop_picks = [p for p in picks if p["prop_type"] == prop]
                    if prop_picks:
                        hits = sum(1 for p in prop_picks if p["result"] == "HIT")
                        icon = "🏀" if prop == "PTS" else "🔄" if prop == "REB" else "👐"
                        patterns.append({
                            "name": f"{prop} Props",
                            "icon": icon,
                            "description": f"{prop.lower().capitalize()} prop bets",
                            "hits": hits,
                            "misses": len(prop_picks) - hits,
                            "total": len(prop_picks),
                            "rate": (hits / len(prop_picks) * 100) if prop_picks else 0,
                        })
                
                return jsonify({
                    "patterns": patterns,
                    "prop_stats": prop_stats,
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    # =========================================================================
    # Model Final - Backtesting API Endpoints
    # =========================================================================
    
    def _generate_under_v2_picks(target_date: str, force: bool = False):
        """
        Helper function to generate UNDER picks using the enhanced v2 model.
        This is a standalone function because under_model_v2 has a different interface.
        
        The under_v2 model focuses exclusively on UNDER picks with:
        - Elite defense vs position analysis (Hashtag Basketball data)
        - Cold streak detection (L5 < 80% of season avg)
        - Back-to-back fatigue factor
        - Comprehensive factor weighting system
        
        Target: 66%+ hit rate on HIGH confidence picks (backtested)
        """
        import json
        from ..engine.under_model_v2 import get_top_under_picks_v2, format_under_pick_for_display
        
        db = get_db()
        
        try:
            with db.connect() as conn:
                # Check for cached under_v2 picks first
                # We use a special marker in reasons to identify under_v2 picks
                if not force:
                    cached = conn.execute(
                        """
                        SELECT p.*, r.actual_value, r.hit, r.margin
                        FROM model_picks p
                        LEFT JOIN model_pick_results r ON r.pick_id = p.id
                        WHERE p.pick_date = ?
                          AND p.direction = 'UNDER'
                          AND p.reasons LIKE '%under_model_v2%'
                        ORDER BY p.confidence_score DESC, p.rank
                        """,
                        (target_date,),
                    ).fetchall()
                    
                    if cached:
                        picks = []
                        for row in cached:
                            reasons = json.loads(row["reasons"]) if row["reasons"] else []
                            score = row["confidence_score"] or 50
                            stars = _calculate_confidence_stars(score)
                            picks.append({
                                "id": row["id"],
                                "player": row["player_name"],
                                "team": row["team_abbrev"],
                                "opponent": row["opponent_abbrev"],
                                "prop": row["prop_type"],
                                "direction": row["direction"],
                                "projection": row["projection"],
                                "line": row["line"],
                                "confidence": row["confidence"],
                                "confidence_score": row["confidence_score"],
                                "confidence_stars": stars,
                                "reasons": [r for r in reasons if r != "[under_model_v2]"],
                                "rank": row["rank"],
                                "actual": row["actual_value"],
                                "hit": row["hit"],
                                "result": row["hit"] is not None,
                            })
                        return jsonify({
                            "picks": picks,
                            "cached": True,
                            "date": target_date,
                            "model": "under_v2",
                        })
                
                # Generate fresh picks using under_model_v2
                under_picks = get_top_under_picks_v2(
                    conn, 
                    target_date, 
                    max_picks=15,  # Get top 15 under picks
                    min_confidence=55.0  # Include MEDIUM confidence and above
                )
                
                if not under_picks:
                    return jsonify({
                        "picks": [],
                        "cached": False,
                        "date": target_date,
                        "model": "under_v2",
                        "message": "No UNDER picks found - no games or insufficient data for this date",
                    })
                
                # Clear old under_v2 picks if force
                if force:
                    old_ids = [r["id"] for r in conn.execute(
                        """
                        SELECT id FROM model_picks 
                        WHERE pick_date = ? 
                          AND direction = 'UNDER'
                          AND reasons LIKE '%under_model_v2%'
                        """, 
                        (target_date,)
                    ).fetchall()]
                    if old_ids:
                        conn.execute(
                            f"DELETE FROM model_pick_results WHERE pick_id IN ({','.join('?' * len(old_ids))})",
                            old_ids
                        )
                        conn.execute(
                            f"DELETE FROM model_picks WHERE id IN ({','.join('?' * len(old_ids))})",
                            old_ids
                        )
                        conn.commit()
                
                # Store new picks and prepare response
                picks_response = []
                for rank, analysis in enumerate(under_picks, 1):
                    # Build reasons list with model marker
                    reasons_list = analysis.reasons[:5] + ["[under_model_v2]"]
                    
                    # Insert into model_picks table
                    conn.execute(
                        """
                        INSERT INTO model_picks 
                        (pick_date, player_id, player_name, team_abbrev, opponent_abbrev, 
                         prop_type, direction, projection, line, confidence, confidence_score, 
                         reasons, rank)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            target_date,
                            analysis.player_id,
                            analysis.player_name,
                            analysis.team_abbrev,
                            analysis.opponent_abbrev,
                            analysis.prop_type,
                            "UNDER",
                            analysis.projected,
                            analysis.season_avg,  # Use season avg as "line" for under picks
                            analysis.confidence_tier,
                            analysis.confidence_score,
                            json.dumps(reasons_list),
                            rank,
                        ),
                    )
                    
                    # Calculate stars from confidence score
                    score = analysis.confidence_score or 50
                    stars = _calculate_confidence_stars(score)
                    
                    picks_response.append({
                        "player": analysis.player_name,
                        "team": analysis.team_abbrev,
                        "opponent": analysis.opponent_abbrev,
                        "prop": analysis.prop_type,
                        "direction": "UNDER",
                        "projection": round(analysis.projected, 1),
                        "line": round(analysis.season_avg, 1),
                        "confidence": analysis.confidence_tier,
                        "confidence_score": round(analysis.confidence_score, 1),
                        "confidence_stars": stars,
                        "is_star_player": False,
                        "has_h2h": analysis.vs_opp_games > 0 if hasattr(analysis, 'vs_opp_games') else False,
                        "is_b2b": analysis.is_b2b,
                        "reasons": analysis.reasons[:5],
                        "rank": rank,
                        "actual": None,
                        "hit": None,
                        "result": False,
                        # Extra under_v2 specific info
                        "factor_count": analysis.factor_count,
                        "defense_rating": (
                            analysis.defense_profile.pts_rating 
                            if analysis.defense_profile and analysis.prop_type == "PTS"
                            else analysis.defense_profile.reb_rating 
                            if analysis.defense_profile and analysis.prop_type == "REB"
                            else analysis.defense_profile.ast_rating 
                            if analysis.defense_profile 
                            else "unknown"
                        ) if analysis.defense_profile else "N/A",
                    })
                
                conn.commit()
                
                return jsonify({
                    "picks": picks_response,
                    "cached": False,
                    "date": target_date,
                    "model": "under_v2",
                    "total_picks": len(picks_response),
                    "high_confidence": sum(1 for p in picks_response if p["confidence"] == "HIGH"),
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route("/api/backtesting/generate-picks", methods=["POST"])
    def api_backtesting_generate_picks():
        """
        Generate or load cached picks for a given date using the optimized model.
        
        Request body:
            - date: Target date (YYYY-MM-DD)
            - force: If true, regenerate even if cached picks exist
            - model: "v8" (default), "under_v2" (enhanced under model), "production", "v4", or "v5"
        
        Returns picks with results if already graded.
        """
        import json
        
        data = request.json or {}
        target_date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        force = data.get("force", False)
        model_version = data.get("model", "v8")
        
        # Handle under_v2 model separately (different interface)
        if model_version == "under_v2":
            return _generate_under_v2_picks(target_date, force)
        
        # Import the appropriate model
        if model_version == "v5":
            from ..engine.model_v5 import get_daily_picks, ModelV5Config as ModelConfig
            config = ModelConfig()
        elif model_version == "v4":
            from ..engine.model_v4 import get_daily_picks, ModelV4Config as ModelConfig
            config = ModelConfig()
        elif model_version == "production":
            from ..engine.model_production import get_daily_picks, ModelConfig
            config = ModelConfig()
        else:
            # Default: use V8 model with OVER and UNDER support + proper confidence
            from ..engine.model_v8 import get_daily_picks, ModelV8Config as ModelConfig
            config = ModelConfig()
        
        db = get_db()
        
        try:
            with db.connect() as conn:
                # Check for cached picks
                if not force:
                    cached = conn.execute(
                        """
                        SELECT p.*, r.actual_value, r.hit, r.margin
                        FROM model_picks p
                        LEFT JOIN model_pick_results r ON r.pick_id = p.id
                        WHERE p.pick_date = ?
                        ORDER BY p.confidence_score DESC, p.rank
                        """,
                        (target_date,),
                    ).fetchall()
                    
                    if cached:
                        picks = []
                        for row in cached:
                            reasons = json.loads(row["reasons"]) if row["reasons"] else []
                            # Extract star rating from confidence_score (properly calibrated)
                            score = row["confidence_score"] or 50
                            stars = _calculate_confidence_stars(score)
                            picks.append({
                                "id": row["id"],
                                "player": row["player_name"],
                                "team": row["team_abbrev"],
                                "opponent": row["opponent_abbrev"],
                                "prop": row["prop_type"],
                                "direction": row["direction"],
                                "projection": row["projection"],
                                "line": row["line"],
                                "confidence": row["confidence"],
                                "confidence_score": row["confidence_score"],
                                "confidence_stars": stars,
                                "reasons": reasons,
                                "rank": row["rank"],
                                "actual": row["actual_value"],
                                "hit": row["hit"],
                                "result": row["hit"] is not None,
                            })
                        return jsonify({
                            "picks": picks,
                            "cached": True,
                            "date": target_date,
                            "model": model_version,
                        })
                
                # Generate new picks
                daily = get_daily_picks(target_date, config=config)
                
                # For v8 model, also generate UNDER picks using under_model_v2
                # This provides specialized UNDER analysis while v8 handles OVER picks
                under_v2_picks = []
                if model_version == "v8":
                    try:
                        from ..engine.under_model_v2 import get_top_under_picks_v2
                        under_v2_picks = get_top_under_picks_v2(
                            conn, 
                            target_date, 
                            max_picks=10,  # Get top 10 under picks
                            min_confidence=60.0  # MEDIUM and HIGH confidence
                        )
                    except Exception as e:
                        import traceback
                        print(f"Note: under_model_v2 picks not available: {e}")
                        traceback.print_exc()
                
                if daily.picks_count == 0 and not under_v2_picks:
                    return jsonify({
                        "picks": [],
                        "cached": False,
                        "date": target_date,
                        "model": model_version,
                        "message": "No picks generated - no games or insufficient data for this date",
                    })
                
                # Clear old picks if force
                if force:
                    old_ids = [r["id"] for r in conn.execute(
                        "SELECT id FROM model_picks WHERE pick_date = ?", (target_date,)
                    ).fetchall()]
                    if old_ids:
                        conn.execute(
                            f"DELETE FROM model_pick_results WHERE pick_id IN ({','.join('?' * len(old_ids))})",
                            old_ids
                        )
                        conn.execute("DELETE FROM model_picks WHERE pick_date = ?", (target_date,))
                        conn.commit()
                
                # Store new picks
                picks_response = []
                for rank, pick in enumerate(daily.picks, 1):
                    conn.execute(
                        """
                        INSERT INTO model_picks 
                        (pick_date, player_name, team_abbrev, opponent_abbrev, prop_type,
                         direction, projection, line, confidence, confidence_score, reasons, rank)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            target_date,
                            pick.player_name,
                            pick.team_abbrev,
                            pick.opponent_abbrev,
                            pick.prop_type,
                            pick.direction,
                            pick.projected_value,
                            pick.line,
                            pick.confidence_tier,
                            pick.confidence_score,
                            json.dumps(pick.reasons + [f"⚠️ {w}" for w in getattr(pick, 'warnings', [])]),
                            rank,
                        ),
                    )
                    
                    # Get star rating from pick (V8 model includes it) or calculate from score
                    stars = getattr(pick, 'confidence_stars', None)
                    if stars is None:
                        score = pick.confidence_score or 50
                        stars = _calculate_confidence_stars(score)
                    
                    picks_response.append({
                        "player": pick.player_name,
                        "team": pick.team_abbrev,
                        "opponent": pick.opponent_abbrev,
                        "prop": pick.prop_type,
                        "direction": pick.direction,
                        "projection": pick.projected_value,
                        "line": pick.line,
                        "confidence": pick.confidence_tier,
                        "confidence_score": pick.confidence_score,
                        "confidence_stars": stars,
                        "is_star_player": getattr(pick, 'is_star_player', False),
                        "has_h2h": getattr(pick, 'has_h2h_data', False),
                        "is_b2b": getattr(pick, 'is_back_to_back', False),
                        "reasons": pick.reasons + [f"⚠️ {w}" for w in getattr(pick, 'warnings', [])],
                        "rank": rank,
                        "actual": None,
                        "hit": None,
                        "result": False,
                    })
                
                # Add under_v2 picks to the response
                if under_v2_picks:
                    under_start_rank = len(picks_response) + 1
                    for i, analysis in enumerate(under_v2_picks):
                        # Store under_v2 pick in database
                        reasons_list = analysis.reasons[:5] + ["[under_model_v2]"]
                        conn.execute(
                            """
                            INSERT INTO model_picks 
                            (pick_date, player_id, player_name, team_abbrev, opponent_abbrev, 
                             prop_type, direction, projection, line, confidence, confidence_score, 
                             reasons, rank)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                target_date,
                                analysis.player_id,
                                analysis.player_name,
                                analysis.team_abbrev,
                                analysis.opponent_abbrev,
                                analysis.prop_type,
                                "UNDER",
                                analysis.projected,
                                analysis.season_avg,
                                analysis.confidence_tier,
                                analysis.confidence_score,
                                json.dumps(reasons_list),
                                under_start_rank + i,
                            ),
                        )
                        
                        # Calculate stars
                        score = analysis.confidence_score or 50
                        stars = _calculate_confidence_stars(score)
                        
                        picks_response.append({
                            "player": analysis.player_name,
                            "team": analysis.team_abbrev,
                            "opponent": analysis.opponent_abbrev,
                            "prop": analysis.prop_type,
                            "direction": "UNDER",
                            "projection": round(analysis.projected, 1),
                            "line": round(analysis.season_avg, 1),
                            "confidence": analysis.confidence_tier,
                            "confidence_score": round(analysis.confidence_score, 1),
                            "confidence_stars": stars,
                            "is_star_player": False,
                            "has_h2h": False,
                            "is_b2b": analysis.is_b2b,
                            "reasons": analysis.reasons[:5],
                            "rank": under_start_rank + i,
                            "actual": None,
                            "hit": None,
                            "result": False,
                        })
                
                conn.commit()
                
                # Sort all picks by confidence_score (highest first)
                picks_response.sort(key=lambda x: (x.get("confidence_score", 0), -x.get("rank", 999)), reverse=True)
                
                return jsonify({
                    "picks": picks_response,
                    "cached": False,
                    "date": target_date,
                    "model": model_version,
                    "games": daily.games if daily else 0,
                    "under_v2_count": len(under_v2_picks) if under_v2_picks else 0,
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/backtesting/compare-results", methods=["POST"])
    def api_backtesting_compare_results():
        """
        Grade picks against actual box score results.
        
        Request body:
            - date: Date to grade (YYYY-MM-DD)
        
        Returns picks with results and calculates grade.
        """
        import json
        
        data = request.json or {}
        target_date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        db = get_db()
        
        try:
            with db.connect() as conn:
                # Get picks for the date
                picks = conn.execute(
                    """
                    SELECT p.*, r.actual_value, r.hit
                    FROM model_picks p
                    LEFT JOIN model_pick_results r ON r.pick_id = p.id
                    WHERE p.pick_date = ?
                    ORDER BY p.confidence_score DESC, p.rank
                    """,
                    (target_date,),
                ).fetchall()
                
                if not picks:
                    return jsonify({"error": "No picks found for this date. Generate picks first."}), 404
                
                results = []
                total_graded = 0
                total_hits = 0
                pts_picks, pts_hits = 0, 0
                reb_picks, reb_hits = 0, 0
                ast_picks, ast_hits = 0, 0
                high_picks, high_hits = 0, 0
                over_picks, over_hits = 0, 0
                under_picks, under_hits = 0, 0
                
                for pick in picks:
                    pick_dict = dict(pick)
                    reasons = json.loads(pick["reasons"]) if pick["reasons"] else []
                    
                    # Try to get actual value from boxscores
                    stat_col = pick["prop_type"].lower()
                    actual_row = conn.execute(
                        f"""
                        SELECT b.{stat_col} as stat_value
                        FROM boxscore_player b
                        JOIN games g ON g.id = b.game_id
                        JOIN players pl ON pl.id = b.player_id
                        WHERE LOWER(pl.name) = LOWER(?)
                          AND g.game_date = ?
                          AND b.minutes > 0
                        """,
                        (pick["player_name"], target_date),
                    ).fetchone()
                    
                    actual_value = actual_row["stat_value"] if actual_row else None
                    hit = None
                    
                    if actual_value is not None:
                        line = pick["line"] or pick["projection"]
                        if pick["direction"] == "OVER":
                            hit = 1 if actual_value > line else 0
                        else:  # UNDER
                            hit = 1 if actual_value < line else 0
                        
                        margin = actual_value - line
                        
                        # Update or insert result
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO model_pick_results 
                            (pick_id, actual_value, hit, margin, graded_at)
                            VALUES (?, ?, ?, ?, datetime('now'))
                            """,
                            (pick["id"], actual_value, hit, margin),
                        )
                        
                        total_graded += 1
                        if hit:
                            total_hits += 1
                        
                        # Track by type
                        if pick["prop_type"] == "PTS":
                            pts_picks += 1
                            if hit: pts_hits += 1
                        elif pick["prop_type"] == "REB":
                            reb_picks += 1
                            if hit: reb_hits += 1
                        elif pick["prop_type"] == "AST":
                            ast_picks += 1
                            if hit: ast_hits += 1
                        
                        # Track by confidence
                        if pick["confidence"] == "HIGH":
                            high_picks += 1
                            if hit: high_hits += 1
                        
                        # Track by direction
                        if pick["direction"] == "OVER":
                            over_picks += 1
                            if hit: over_hits += 1
                        else:
                            under_picks += 1
                            if hit: under_hits += 1
                    
                    results.append({
                        "id": pick["id"],
                        "player": pick["player_name"],
                        "team": pick["team_abbrev"],
                        "opponent": pick["opponent_abbrev"],
                        "prop": pick["prop_type"],
                        "direction": pick["direction"],
                        "projection": pick["projection"],
                        "line": pick["line"],
                        "confidence": pick["confidence"],
                        "confidence_score": pick["confidence_score"],
                        "reasons": reasons,
                        "rank": pick["rank"],
                        "actual": actual_value,
                        "hit": hit,
                        "result": hit is not None,
                    })
                
                # Calculate grade
                hit_rate = (total_hits / total_graded * 100) if total_graded > 0 else 0
                if total_graded == 0:
                    grade = "PENDING"  # No games graded yet
                elif hit_rate >= 70:
                    grade = "A"
                elif hit_rate >= 60:
                    grade = "B"
                elif hit_rate >= 50:
                    grade = "C"
                elif hit_rate >= 40:
                    grade = "D"
                else:
                    grade = "F"
                
                # Update daily performance (only if some games graded)
                if total_graded > 0:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO model_performance_daily
                        (performance_date, total_picks, hits, misses, pending, hit_rate,
                         pts_picks, pts_hits, reb_picks, reb_hits, ast_picks, ast_hits,
                         high_conf_picks, high_conf_hits, over_picks, over_hits,
                         under_picks, under_hits, grade, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        """,
                        (
                            target_date,
                            len(picks),
                            total_hits,
                            total_graded - total_hits,
                            len(picks) - total_graded,
                            hit_rate,
                            pts_picks, pts_hits,
                            reb_picks, reb_hits,
                            ast_picks, ast_hits,
                            high_picks, high_hits,
                            over_picks, over_hits,
                            under_picks, under_hits,
                            grade,
                        ),
                    )
                    conn.commit()
                
                return jsonify({
                    "results": results,
                    "grade": {
                        "letter": grade,
                        "hit_rate": hit_rate,
                        "hits": total_hits,
                        "misses": total_graded - total_hits,
                        "pending": len(picks) - total_graded,
                        "total": total_graded,
                        "pts_accuracy": (pts_hits / pts_picks * 100) if pts_picks > 0 else None,
                        "reb_accuracy": (reb_hits / reb_picks * 100) if reb_picks > 0 else None,
                        "ast_accuracy": (ast_hits / ast_picks * 100) if ast_picks > 0 else None,
                        "high_conf_accuracy": (high_hits / high_picks * 100) if high_picks > 0 else None,
                        "over_accuracy": (over_hits / over_picks * 100) if over_picks > 0 else None,
                        "under_accuracy": (under_hits / under_picks * 100) if under_picks > 0 else None,
                    },
                    "date": target_date,
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/backtesting/performance")
    def api_backtesting_performance():
        """
        Get overall model performance statistics.
        
        Returns aggregated stats across all tracked days.
        """
        db = get_db()
        
        try:
            with db.connect() as conn:
                # Get daily performance records
                daily = conn.execute(
                    """
                    SELECT * FROM model_performance_daily
                    ORDER BY performance_date DESC
                    """
                ).fetchall()
                
                if not daily:
                    return jsonify({
                        "overall": {
                            "days_tracked": 0,
                            "total_picks": 0,
                            "total_hits": 0,
                            "total_misses": 0,
                            "overall_hit_rate": 0,
                        },
                        "daily": [],
                    })
                
                # Aggregate overall stats
                total_picks = sum(d["total_picks"] or 0 for d in daily)
                total_hits = sum(d["hits"] or 0 for d in daily)
                total_misses = sum(d["misses"] or 0 for d in daily)
                
                overall_hit_rate = (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0
                
                # Format daily records
                daily_list = []
                for d in daily:
                    daily_list.append({
                        "date": d["performance_date"],
                        "total_picks": d["total_picks"],
                        "hits": d["hits"],
                        "misses": d["misses"],
                        "pending": d["pending"],
                        "hit_rate": d["hit_rate"],
                        "grade": d["grade"],
                        "pts_accuracy": (d["pts_hits"] / d["pts_picks"] * 100) if d["pts_picks"] else None,
                        "reb_accuracy": (d["reb_hits"] / d["reb_picks"] * 100) if d["reb_picks"] else None,
                        "ast_accuracy": (d["ast_hits"] / d["ast_picks"] * 100) if d["ast_picks"] else None,
                    })
                
                return jsonify({
                    "overall": {
                        "days_tracked": len(daily),
                        "total_picks": total_picks,
                        "total_hits": total_hits,
                        "total_misses": total_misses,
                        "overall_hit_rate": overall_hit_rate,
                    },
                    "daily": daily_list,
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/backtesting/picks-history")
    def api_backtesting_picks_history():
        """
        Get historical picks with optional date filtering.
        
        Query params:
            - start_date: Filter from date (YYYY-MM-DD)
            - end_date: Filter to date (YYYY-MM-DD)
            - limit: Max records to return
        """
        import json
        
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")
        limit = request.args.get("limit", "100")
        
        try:
            limit = int(limit)
        except ValueError:
            limit = 100
        
        db = get_db()
        
        try:
            with db.connect() as conn:
                # Build query
                query = """
                    SELECT p.*, r.actual_value, r.hit, r.margin
                    FROM model_picks p
                    LEFT JOIN model_pick_results r ON r.pick_id = p.id
                    WHERE 1=1
                """
                params = []
                
                if start_date:
                    query += " AND p.pick_date >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND p.pick_date <= ?"
                    params.append(end_date)
                
                query += " ORDER BY p.pick_date DESC, p.confidence_score DESC, p.rank LIMIT ?"
                params.append(limit)
                
                picks = conn.execute(query, params).fetchall()
                
                # Calculate stats
                total = len(picks)
                graded = [p for p in picks if p["hit"] is not None]
                hits = len([p for p in graded if p["hit"] == 1])
                misses = len(graded) - hits
                
                picks_list = []
                for pick in picks:
                    reasons = json.loads(pick["reasons"]) if pick["reasons"] else []
                    picks_list.append({
                        "id": pick["id"],
                        "date": pick["pick_date"],
                        "player": pick["player_name"],
                        "team": pick["team_abbrev"],
                        "opponent": pick["opponent_abbrev"],
                        "prop": pick["prop_type"],
                        "direction": pick["direction"],
                        "projection": pick["projection"],
                        "line": pick["line"],
                        "confidence": pick["confidence"],
                        "confidence_score": pick["confidence_score"],
                        "reasons": reasons,
                        "rank": pick["rank"],
                        "actual": pick["actual_value"],
                        "hit": pick["hit"],
                        "result": pick["hit"] is not None,
                    })
                
                return jsonify({
                    "picks": picks_list,
                    "stats": {
                        "total": total,
                        "graded": len(graded),
                        "hits": hits,
                        "misses": misses,
                        "hit_rate": (hits / len(graded) * 100) if graded else None,
                    },
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/backtesting/calendar-data")
    def api_backtesting_calendar_data():
        """
        Get calendar data for the backtesting UI.
        Returns dates with picks and their performance status.
        """
        db = get_db()
        
        try:
            with db.connect() as conn:
                # Get all dates with picks or games
                data = conn.execute(
                    """
                    SELECT 
                        COALESCE(p.pick_date, g.game_date) as date,
                        COUNT(DISTINCT p.id) as picks_count,
                        SUM(CASE WHEN r.hit = 1 THEN 1 ELSE 0 END) as hits,
                        SUM(CASE WHEN r.hit = 0 THEN 1 ELSE 0 END) as misses,
                        COUNT(DISTINCT g.id) as games_count
                    FROM games g
                    LEFT JOIN model_picks p ON p.pick_date = g.game_date
                    LEFT JOIN model_pick_results r ON r.pick_id = p.id
                    GROUP BY COALESCE(p.pick_date, g.game_date)
                    ORDER BY date DESC
                    """
                ).fetchall()
                
                calendar = {}
                for row in data:
                    date = row["date"]
                    picks = row["picks_count"] or 0
                    hits = row["hits"] or 0
                    misses = row["misses"] or 0
                    games = row["games_count"] or 0
                    
                    hit_rate = None
                    status = "no-picks"
                    
                    if picks > 0:
                        if hits + misses > 0:
                            hit_rate = hits / (hits + misses) * 100
                            if hit_rate >= 60:
                                status = "good"
                            elif hit_rate >= 45:
                                status = "neutral"
                            else:
                                status = "bad"
                        else:
                            status = "pending"
                    elif games > 0:
                        status = "has-games"
                    
                    calendar[date] = {
                        "picks": picks,
                        "hits": hits,
                        "misses": misses,
                        "games": games,
                        "hit_rate": hit_rate,
                        "status": status,
                    }
                
                return jsonify({"calendar": calendar})
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    # =========================================================================
    # Under Model V2 - Enhanced UNDER Picks API Endpoints
    # =========================================================================
    
    @app.route("/api/under-v2/backtest", methods=["POST"])
    def api_under_v2_backtest():
        """
        Run a comprehensive backtest on the enhanced UNDER model v2.
        
        This endpoint provides detailed analysis of under_model_v2 performance
        including factor effectiveness, confidence tier breakdown, and defense
        rating analysis.
        
        Request body:
            - start_date: Start date (YYYY-MM-DD)
            - end_date: End date (YYYY-MM-DD)
            - min_confidence: Minimum confidence score (default: 60)
            - confidence_tier: Filter to specific tier (HIGH, MEDIUM, LOW)
        
        Returns:
            - Overall hit rate and pick counts
            - Breakdown by prop type (PTS, REB, AST)
            - Breakdown by confidence tier
            - Breakdown by defense rating (elite, good, average)
            - Factor effectiveness analysis
            - Detailed pick history
        """
        from ..engine.under_model_v2 import backtest_under_model_v2
        
        data = request.json or {}
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        min_confidence = data.get("min_confidence", 60.0)
        confidence_tier = data.get("confidence_tier", None)
        
        if not start_date or not end_date:
            return jsonify({"error": "Missing start_date or end_date"}), 400
        
        db = get_db()
        
        try:
            with db.connect() as conn:
                results = backtest_under_model_v2(
                    conn,
                    start_date=start_date,
                    end_date=end_date,
                    min_confidence=min_confidence,
                    confidence_tier=confidence_tier,
                )
                
                # Format the response
                return jsonify({
                    "status": results["status"],
                    "date_range": {
                        "start": start_date,
                        "end": end_date,
                    },
                    "filters": {
                        "min_confidence": min_confidence,
                        "confidence_tier": confidence_tier,
                    },
                    "summary": {
                        "total_picks": results["total_picks"],
                        "hits": results["hits"],
                        "misses": results["misses"],
                        "hit_rate": round(results["hit_rate"] * 100, 2) if results["hit_rate"] else 0,
                    },
                    "by_prop_type": {
                        prop: {
                            "picks": data["picks"],
                            "hits": data["hits"],
                            "hit_rate": round(data["hit_rate"] * 100, 2) if data["hit_rate"] else 0,
                            "avg_margin": round(data["avg_margin"], 2) if data.get("avg_margin") else 0,
                        }
                        for prop, data in results["by_prop_type"].items()
                    },
                    "by_confidence_tier": {
                        tier: {
                            "picks": data["picks"],
                            "hits": data["hits"],
                            "hit_rate": round(data["hit_rate"] * 100, 2) if data["hit_rate"] else 0,
                        }
                        for tier, data in results["by_confidence_tier"].items()
                    },
                    "by_defense_rating": {
                        rating: {
                            "picks": data["picks"],
                            "hits": data["hits"],
                            "hit_rate": round(data["hit_rate"] * 100, 2) if data["hit_rate"] else 0,
                        }
                        for rating, data in results["by_defense_rating"].items()
                    },
                    "factor_effectiveness": {
                        factor: {
                            "picks": data["picks"],
                            "hits": data["hits"],
                            "hit_rate": round(data["hit_rate"] * 100, 2) if data["hit_rate"] else 0,
                        }
                        for factor, data in results.get("factor_effectiveness", {}).items()
                    },
                    "picks": results.get("picks", [])[:100],  # Limit detailed picks to 100
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/under-v2/analyze-matchup", methods=["POST"])
    def api_under_v2_analyze_matchup():
        """
        Analyze a specific matchup for UNDER opportunities.
        
        Request body:
            - away_team: Away team abbreviation (e.g., "LAL")
            - home_team: Home team abbreviation (e.g., "BOS")
            - game_date: Date of the game (YYYY-MM-DD)
        
        Returns detailed UNDER analysis for all players in the matchup.
        """
        from ..engine.under_model_v2 import generate_under_picks_v2, format_under_pick_for_display
        
        data = request.json or {}
        away_team = data.get("away_team")
        home_team = data.get("home_team")
        game_date = data.get("game_date")
        
        if not away_team or not home_team or not game_date:
            return jsonify({"error": "Missing away_team, home_team, or game_date"}), 400
        
        db = get_db()
        
        try:
            with db.connect() as conn:
                result = generate_under_picks_v2(conn, away_team, home_team, game_date)
                
                # Format picks for display
                picks = []
                for analysis in result.picks:
                    picks.append(format_under_pick_for_display(analysis))
                
                return jsonify({
                    "status": result.status,
                    "message": result.message,
                    "game": {
                        "away_team": away_team,
                        "home_team": home_team,
                        "date": game_date,
                    },
                    "defense_data_status": result.defense_data_freshness,
                    "picks": picks,
                    "summary": {
                        "total_analyzed": result.total_players_analyzed,
                        "props_analyzed": result.total_props_analyzed,
                        "picks_generated": result.picks_generated,
                        "high_confidence": sum(1 for p in result.picks if p.confidence_tier == "HIGH"),
                        "medium_confidence": sum(1 for p in result.picks if p.confidence_tier == "MEDIUM"),
                    },
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/under-v2/defense-data")
    def api_under_v2_defense_data():
        """
        Get current defense vs position data from the database.
        Shows what defensive data is available for the UNDER model.
        """
        from ..ingest.defense_position_parser import get_defense_vs_position_last_updated
        
        db = get_db()
        
        try:
            with db.connect() as conn:
                # Get freshness data
                freshness = get_defense_vs_position_last_updated(conn)
                
                # Get all defense data
                defense_data = conn.execute(
                    """
                    SELECT * FROM team_defense_vs_position
                    ORDER BY position, overall_rank
                    """
                ).fetchall()
                
                # Format by position
                by_position = {}
                for row in defense_data:
                    pos = row["position"]
                    if pos not in by_position:
                        by_position[pos] = []
                    by_position[pos].append({
                        "team": row["team_abbrev"],
                        "overall_rank": row["overall_rank"],
                        "pts_allowed": row["pts_allowed"],
                        "pts_rank": row["pts_rank"],
                        "reb_allowed": row["reb_allowed"],
                        "reb_rank": row["reb_rank"],
                        "ast_allowed": row["ast_allowed"],
                        "ast_rank": row["ast_rank"],
                    })
                
                # Get elite defenses summary (top 5 at each position)
                elite_summary = {}
                for pos in ["PG", "SG", "SF", "PF", "C"]:
                    if pos in by_position:
                        elite_summary[pos] = {
                            "top_5_pts": [t["team"] for t in by_position[pos] if t["pts_rank"] <= 5][:5],
                            "top_5_reb": [t["team"] for t in sorted(by_position[pos], key=lambda t: t["reb_rank"]) if t["reb_rank"] <= 5][:5],
                            "top_5_ast": [t["team"] for t in sorted(by_position[pos], key=lambda t: t["ast_rank"]) if t["ast_rank"] <= 5][:5],
                        }
                
                return jsonify({
                    "freshness": {
                        pos: info.get("last_updated", "unknown") if info else "unavailable"
                        for pos, info in freshness.items()
                    },
                    "total_records": len(defense_data),
                    "positions": list(by_position.keys()),
                    "elite_defenses": elite_summary,
                    "data": by_position,
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    # =========================================================================
    # Model Lab - Learning & Experimentation API Endpoints
    # =========================================================================
    
    @app.route("/api/modellab/learning-stats")
    def api_modellab_learning_stats():
        """
        Get learning statistics - historical accuracy by pattern, prop type, and confidence level.
        This powers the Learning Dashboard in the Model Lab UI.
        """
        db = get_db()
        
        try:
            with db.connect() as conn:
                # Overall performance summary
                overall = conn.execute("""
                    SELECT 
                        COUNT(*) as total_picks,
                        SUM(CASE WHEN r.hit = 1 THEN 1 ELSE 0 END) as hits,
                        SUM(CASE WHEN r.hit = 0 THEN 1 ELSE 0 END) as misses,
                        AVG(CASE WHEN r.hit IS NOT NULL THEN r.hit * 100.0 ELSE NULL END) as hit_rate
                    FROM model_picks p
                    JOIN model_pick_results r ON r.pick_id = p.id
                """).fetchone()
                
                # Performance by prop type
                by_prop = conn.execute("""
                    SELECT 
                        p.prop_type,
                        COUNT(*) as picks,
                        SUM(CASE WHEN r.hit = 1 THEN 1 ELSE 0 END) as hits,
                        AVG(r.hit * 100.0) as hit_rate
                    FROM model_picks p
                    JOIN model_pick_results r ON r.pick_id = p.id
                    GROUP BY p.prop_type
                    ORDER BY picks DESC
                """).fetchall()
                
                # Performance by direction (OVER vs UNDER)
                by_direction = conn.execute("""
                    SELECT 
                        p.direction,
                        COUNT(*) as picks,
                        SUM(CASE WHEN r.hit = 1 THEN 1 ELSE 0 END) as hits,
                        AVG(r.hit * 100.0) as hit_rate
                    FROM model_picks p
                    JOIN model_pick_results r ON r.pick_id = p.id
                    GROUP BY p.direction
                """).fetchall()
                
                # Performance by confidence stars (calculated from score)
                by_stars = conn.execute("""
                    SELECT 
                        CASE 
                            WHEN p.confidence_score >= 85 THEN 5
                            WHEN p.confidence_score >= 70 THEN 4
                            WHEN p.confidence_score >= 55 THEN 3
                            WHEN p.confidence_score >= 40 THEN 2
                            ELSE 1
                        END as stars,
                        COUNT(*) as picks,
                        SUM(CASE WHEN r.hit = 1 THEN 1 ELSE 0 END) as hits,
                        AVG(r.hit * 100.0) as hit_rate
                    FROM model_picks p
                    JOIN model_pick_results r ON r.pick_id = p.id
                    GROUP BY stars
                    ORDER BY stars DESC
                """).fetchall()
                
                # Recent trends (last 7 days)
                recent_trend = conn.execute("""
                    SELECT 
                        p.pick_date,
                        COUNT(*) as picks,
                        SUM(CASE WHEN r.hit = 1 THEN 1 ELSE 0 END) as hits,
                        AVG(r.hit * 100.0) as hit_rate
                    FROM model_picks p
                    JOIN model_pick_results r ON r.pick_id = p.id
                    WHERE p.pick_date >= date('now', '-7 days')
                    GROUP BY p.pick_date
                    ORDER BY p.pick_date DESC
                """).fetchall()
                
                # Pattern analysis from reasons (look for patterns in the reasons JSON)
                patterns_data = conn.execute("""
                    SELECT 
                        p.reasons,
                        r.hit
                    FROM model_picks p
                    JOIN model_pick_results r ON r.pick_id = p.id
                    WHERE p.reasons IS NOT NULL
                """).fetchall()
                
                # Analyze patterns from reasons
                import json
                pattern_stats = {}
                for row in patterns_data:
                    try:
                        reasons = json.loads(row["reasons"]) if row["reasons"] else []
                        hit = row["hit"]
                        for reason in reasons:
                            if reason.startswith("⚠️"):
                                continue  # Skip warnings
                            # Extract pattern keywords
                            for keyword in ["Cold Bounce", "Hot Sustained", "UNDER", "OVER", "defense", "pace", "B2B"]:
                                if keyword.lower() in reason.lower():
                                    if keyword not in pattern_stats:
                                        pattern_stats[keyword] = {"picks": 0, "hits": 0}
                                    pattern_stats[keyword]["picks"] += 1
                                    if hit:
                                        pattern_stats[keyword]["hits"] += 1
                    except:
                        pass
                
                # Calculate hit rates for patterns
                patterns = []
                for pattern, stats in pattern_stats.items():
                    if stats["picks"] >= 5:  # Only include patterns with enough data
                        patterns.append({
                            "pattern": pattern,
                            "picks": stats["picks"],
                            "hits": stats["hits"],
                            "hit_rate": stats["hits"] / stats["picks"] * 100 if stats["picks"] > 0 else 0
                        })
                patterns.sort(key=lambda x: x["picks"], reverse=True)
                
                return jsonify({
                    "overall": {
                        "total_picks": overall["total_picks"] or 0,
                        "hits": overall["hits"] or 0,
                        "misses": overall["misses"] or 0,
                        "hit_rate": round(overall["hit_rate"], 1) if overall["hit_rate"] else 0,
                    },
                    "by_prop": [dict(row) for row in by_prop],
                    "by_direction": [dict(row) for row in by_direction],
                    "by_stars": [dict(row) for row in by_stars],
                    "recent_trend": [dict(row) for row in recent_trend],
                    "patterns": patterns,
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/modellab/experiment", methods=["POST"])
    def api_modellab_experiment():
        """
        Run a model experiment with custom parameters over a date range.
        Returns detailed results for analysis.
        """
        data = request.json or {}
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        params = data.get("params", {})
        
        if not start_date or not end_date:
            return jsonify({"error": "Missing start_date or end_date"}), 400
        
        try:
            from ..engine.model_v8 import get_daily_picks, ModelV8Config
            
            # Create config with custom parameters
            config = ModelV8Config(
                min_games=params.get("min_games", 5),
                min_edge=params.get("min_edge", 0.02),
                max_picks=params.get("max_picks", 20),
                enable_learning=params.get("enable_learning", True),
                enable_under_picks=params.get("enable_under_picks", True),
            )
            
            db = get_db()
            
            results = []
            from datetime import datetime, timedelta
            current = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                
                try:
                    daily = get_daily_picks(date_str, config=config)
                    
                    with db.connect() as conn:
                        # Get actual results for this date
                        actuals = {}
                        box_data = conn.execute("""
                            SELECT player_name, pts, reb, ast, stl, blk, fg3m, 
                                   pts + reb + ast as pra,
                                   pts + reb as pr,
                                   pts + ast as pa,
                                   reb + ast as ra
                            FROM box_scores
                            WHERE game_date = ?
                        """, (date_str,)).fetchall()
                        
                        for row in box_data:
                            actuals[row["player_name"]] = {
                                "PTS": row["pts"],
                                "REB": row["reb"],
                                "AST": row["ast"],
                                "STL": row["stl"],
                                "BLK": row["blk"],
                                "3PM": row["fg3m"],
                                "PRA": row["pra"],
                                "PR": row["pr"],
                                "PA": row["pa"],
                                "RA": row["ra"],
                            }
                    
                    # Grade picks
                    hits = 0
                    misses = 0
                    pick_details = []
                    
                    for pick in daily.picks:
                        actual = actuals.get(pick.player_name, {}).get(pick.prop_type)
                        if actual is not None:
                            if pick.direction == "OVER":
                                hit = actual > pick.line
                            else:
                                hit = actual < pick.line
                            
                            if hit:
                                hits += 1
                            else:
                                misses += 1
                            
                            pick_details.append({
                                "player": pick.player_name,
                                "prop": pick.prop_type,
                                "direction": pick.direction,
                                "line": pick.line,
                                "projection": pick.projected_value,
                                "actual": actual,
                                "hit": hit,
                                "confidence_stars": pick.confidence_stars,
                            })
                    
                    results.append({
                        "date": date_str,
                        "picks": len(daily.picks),
                        "graded": len(pick_details),
                        "hits": hits,
                        "misses": misses,
                        "hit_rate": hits / (hits + misses) * 100 if hits + misses > 0 else None,
                        "details": pick_details,
                    })
                    
                except Exception as e:
                    results.append({
                        "date": date_str,
                        "error": str(e),
                    })
                
                current += timedelta(days=1)
            
            # Calculate totals
            total_picks = sum(r.get("picks", 0) for r in results if "error" not in r)
            total_hits = sum(r.get("hits", 0) for r in results if "error" not in r)
            total_misses = sum(r.get("misses", 0) for r in results if "error" not in r)
            
            return jsonify({
                "results": results,
                "summary": {
                    "total_picks": total_picks,
                    "total_graded": total_hits + total_misses,
                    "total_hits": total_hits,
                    "total_misses": total_misses,
                    "overall_hit_rate": total_hits / (total_hits + total_misses) * 100 if total_hits + total_misses > 0 else None,
                },
                "params": params,
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/modellab/compare-models", methods=["POST"])
    def api_modellab_compare_models():
        """
        Compare multiple model versions over a date range.
        """
        data = request.json or {}
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        models = data.get("models", ["v8", "production"])
        
        if not start_date or not end_date:
            return jsonify({"error": "Missing dates"}), 400
        
        try:
            from datetime import datetime, timedelta
            
            model_results = {}
            
            for model_version in models:
                # Import model
                if model_version == "v8":
                    from ..engine.model_v8 import get_daily_picks, ModelV8Config as Config
                    config = Config()
                elif model_version == "production":
                    from ..engine.model_production import get_daily_picks, ModelConfig as Config
                    config = Config()
                elif model_version == "v5":
                    from ..engine.model_v5 import get_daily_picks, ModelV5Config as Config
                    config = Config()
                else:
                    continue
                
                db = get_db()
                total_picks = 0
                total_hits = 0
                total_misses = 0
                
                current = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                
                while current <= end:
                    date_str = current.strftime("%Y-%m-%d")
                    
                    try:
                        daily = get_daily_picks(date_str, config=config)
                        
                        with db.connect() as conn:
                            # Get actuals
                            actuals = {}
                            for row in conn.execute("""
                                SELECT player_name, pts, reb, ast, stl, blk, fg3m,
                                       pts + reb + ast as pra
                                FROM box_scores WHERE game_date = ?
                            """, (date_str,)).fetchall():
                                actuals[row["player_name"]] = {
                                    "PTS": row["pts"], "REB": row["reb"], "AST": row["ast"],
                                    "STL": row["stl"], "BLK": row["blk"], "3PM": row["fg3m"],
                                    "PRA": row["pra"],
                                }
                        
                        for pick in daily.picks:
                            actual = actuals.get(pick.player_name, {}).get(pick.prop_type)
                            if actual is not None:
                                total_picks += 1
                                if pick.direction == "OVER":
                                    hit = actual > pick.line
                                else:
                                    hit = actual < pick.line
                                if hit:
                                    total_hits += 1
                                else:
                                    total_misses += 1
                    except:
                        pass
                    
                    current += timedelta(days=1)
                
                model_results[model_version] = {
                    "picks": total_picks,
                    "hits": total_hits,
                    "misses": total_misses,
                    "hit_rate": total_hits / (total_hits + total_misses) * 100 if total_hits + total_misses > 0 else None,
                }
            
            return jsonify({"models": model_results})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    # -------------------------------------------------------------------------
    # Web Scraping API Endpoints
    # -------------------------------------------------------------------------
    
    @app.route("/api/scrape/injuries", methods=["POST"])
    def api_scrape_injuries():
        """
        Scrape current injury report from ESPN.
        
        Returns:
            JSON with scraped injuries and formatted text
        """
        if not HAS_SCRAPING_DEPS:
            return jsonify({
                "error": "Web scraping dependencies not installed. Run: pip install requests beautifulsoup4"
            }), 400
        
        try:
            report = fetch_injuries()
            
            injuries_list = []
            for injury in report.injuries:
                injuries_list.append({
                    "team_name": injury.team_name,
                    "player_name": injury.player_name,
                    "position": injury.position,
                    "status": injury.status,
                    "est_return_date": injury.est_return_date,
                    "comment": injury.comment,
                })
            
            return jsonify({
                "success": True,
                "scrape_time": report.scrape_time,
                "count": len(injuries_list),
                "injuries": injuries_list,
                "text": injuries_to_text(report),
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to scrape injuries: {str(e)}"}), 500
    
    @app.route("/api/scrape/matchups", methods=["POST"])
    def api_scrape_matchups():
        """
        Scrape matchups from ESPN for a specific date.
        
        Request body:
            - date: Date in format "YYYY-MM-DD" or "YYYYMMDD" (required)
        
        Returns:
            JSON with scraped matchups and formatted text
        """
        if not HAS_SCRAPING_DEPS:
            return jsonify({
                "error": "Web scraping dependencies not installed. Run: pip install requests beautifulsoup4"
            }), 400
        
        data = request.get_json() or {}
        date_str = data.get("date", "").strip()
        
        if not date_str:
            return jsonify({"error": "Date is required. Provide 'date' in YYYY-MM-DD format."}), 400
        
        try:
            matchups = fetch_matchups(date_str)
            
            matchups_list = []
            for m in matchups:
                matchups_list.append({
                    "game_date": m.game_date,
                    "away_team": m.away_team,
                    "home_team": m.home_team,
                    "game_time": m.game_time,
                    "tv_channel": m.tv_channel,
                    "spread": m.spread,
                    "favorite": m.favorite,
                    "over_under": m.over_under,
                    "status": m.status,
                })
            
            return jsonify({
                "success": True,
                "date": date_str,
                "count": len(matchups_list),
                "matchups": matchups_list,
                "text": matchups_to_text(matchups),
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to scrape matchups: {str(e)}"}), 500
    
    @app.route("/api/scrape/boxscores", methods=["POST"])
    def api_scrape_boxscores():
        """
        Scrape box scores from NBA.com for a specific date.
        
        Request body:
            - date: Date in format "YYYY-MM-DD" or "YYYYMMDD" (required)
        
        Returns:
            JSON with scraped box scores and formatted text
        """
        if not HAS_SCRAPING_DEPS:
            return jsonify({
                "error": "Web scraping dependencies not installed. Run: pip install requests beautifulsoup4"
            }), 400
        
        data = request.get_json() or {}
        date_str = data.get("date", "").strip()
        
        if not date_str:
            return jsonify({"error": "Date is required. Provide 'date' in YYYY-MM-DD format."}), 400
        
        try:
            box_scores = fetch_box_scores(date_str)
            
            box_scores_list = []
            for bs in box_scores:
                players_list = []
                for ps in bs.player_stats:
                    players_list.append({
                        "player_name": ps.player_name,
                        "team": ps.team,
                        "minutes": ps.minutes,
                        "pts": ps.pts,
                        "reb": ps.reb,
                        "ast": ps.ast,
                        "stl": ps.stl,
                        "blk": ps.blk,
                        "tov": ps.tov,
                        "fg": ps.fg,
                        "tp": ps.tp,
                        "ft": ps.ft,
                        "plus_minus": ps.plus_minus,
                    })
                
                box_scores_list.append({
                    "game_date": bs.game_date,
                    "away_team": bs.away_team,
                    "home_team": bs.home_team,
                    "away_score": bs.away_score,
                    "home_score": bs.home_score,
                    "box_score_url": bs.box_score_url,
                    "player_stats": players_list,
                })
            
            return jsonify({
                "success": True,
                "date": date_str,
                "count": len(box_scores_list),
                "box_scores": box_scores_list,
                "text": box_scores_to_text(box_scores),
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to scrape box scores: {str(e)}"}), 500
    
    return app


def run_web_app(host: str = "127.0.0.1", port: int = 5050, debug: bool = True) -> None:
    """Run the Flask web application."""
    app = create_app()
    print(f"\n🏀 NBA Props Predictor")
    print(f"   Running at: http://{host}:{port}")
    print(f"   Press Ctrl+C to stop\n")
    app.run(host=host, port=port, debug=debug)


from __future__ import annotations

from pathlib import Path

from ..db import (
    find_game_id,
    get_or_create_player,
    get_or_create_team,
)
from ..util import normalize_team_name, sha256_text
from .boxscore_parser import ParsedGame, parse_boxscore_text


REGULAR_SEASON_START_BY_SEASON: dict[str, str] = {
    "2025-26": "2025-10-21",
}


def _infer_season(game_date: str) -> str:
    # game_date: YYYY-MM-DD
    yyyy = int(game_date[0:4])
    mm = int(game_date[5:7])
    start_year = yyyy if mm >= 10 else yyyy - 1
    return f"{start_year}-{str(start_year + 1)[2:]}"


def ingest_boxscore_file(conn, source_file: Path) -> int:
    """
    Parse a single game boxscore text file and persist it into SQLite.
    Returns the inserted games.id.
    """
    text = source_file.read_text(encoding="utf-8", errors="replace")
    source_hash = sha256_text(text)
    parsed: ParsedGame = parse_boxscore_text(text=text, source_path=source_file)

    if len(parsed.teams) < 2:
        raise ValueError(f"Expected 2 teams, got {parsed.teams!r}")

    team1 = normalize_team_name(parsed.teams[0])
    team2 = normalize_team_name(parsed.teams[1])
    team1_id = get_or_create_team(conn, team1)
    team2_id = get_or_create_team(conn, team2)

    season = _infer_season(parsed.game_date)
    regular_season_start = REGULAR_SEASON_START_BY_SEASON.get(season)
    if regular_season_start and parsed.game_date < regular_season_start:
        raise ValueError(
            f"Refusing to ingest preseason game on {parsed.game_date} for season {season} "
            f"(regular season starts {regular_season_start})."
        )
    source_file_str = str(source_file.resolve())

    existing = find_game_id(
        conn=conn,
        game_date=parsed.game_date,
        team1_id=team1_id,
        team2_id=team2_id,
    )
    if existing:
        game_id = existing
        conn.execute(
            "UPDATE games SET source_hash = ?, season = ?, source_file = ? WHERE id = ?",
            (source_hash, season, source_file_str, game_id),
        )
    else:
        cur = conn.execute(
            """
            INSERT INTO games(season, game_date, team1_id, team2_id, source_file, source_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (season, parsed.game_date, team1_id, team2_id, source_file_str, source_hash),
        )
        game_id = int(cur.lastrowid)

    # Team totals (optional)
    for team_name, totals in parsed.team_totals.items():
        team_id = get_or_create_team(conn, team_name)
        conn.execute(
            """
            INSERT INTO boxscore_team_totals(
              game_id, team_id, pts, reb, ast, oreb, dreb, stl, blk, tov, pf,
              fgm, fga, tpm, tpa, ftm, fta, plus_minus, raw_line
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game_id, team_id) DO UPDATE SET
              pts=excluded.pts,
              reb=excluded.reb,
              ast=excluded.ast,
              oreb=excluded.oreb,
              dreb=excluded.dreb,
              stl=excluded.stl,
              blk=excluded.blk,
              tov=excluded.tov,
              pf=excluded.pf,
              fgm=excluded.fgm,
              fga=excluded.fga,
              tpm=excluded.tpm,
              tpa=excluded.tpa,
              ftm=excluded.ftm,
              fta=excluded.fta,
              plus_minus=excluded.plus_minus,
              raw_line=excluded.raw_line
            """,
            (
                game_id,
                team_id,
                totals.pts,
                totals.reb,
                totals.ast,
                totals.oreb,
                totals.dreb,
                totals.stl,
                totals.blk,
                totals.tov,
                totals.pf,
                totals.fgm,
                totals.fga,
                totals.tpm,
                totals.tpa,
                totals.ftm,
                totals.fta,
                totals.plus_minus,
                totals.raw_line,
            ),
        )

    # Player lines
    for pl in parsed.player_lines:
        team_id = get_or_create_team(conn, pl.team)
        player_id = get_or_create_player(conn, pl.player)
        conn.execute(
            """
            INSERT INTO boxscore_player(
              game_id, team_id, player_id, status, pos, minutes,
              pts, reb, ast, oreb, dreb, stl, blk, tov, pf,
              fgm, fga, fg_pct, tpm, tpa, tp_pct, ftm, fta, ft_pct,
              plus_minus, raw_line
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game_id, team_id, player_id) DO UPDATE SET
              status=excluded.status,
              pos=excluded.pos,
              minutes=excluded.minutes,
              pts=excluded.pts,
              reb=excluded.reb,
              ast=excluded.ast,
              oreb=excluded.oreb,
              dreb=excluded.dreb,
              stl=excluded.stl,
              blk=excluded.blk,
              tov=excluded.tov,
              pf=excluded.pf,
              fgm=excluded.fgm,
              fga=excluded.fga,
              fg_pct=excluded.fg_pct,
              tpm=excluded.tpm,
              tpa=excluded.tpa,
              tp_pct=excluded.tp_pct,
              ftm=excluded.ftm,
              fta=excluded.fta,
              ft_pct=excluded.ft_pct,
              plus_minus=excluded.plus_minus,
              raw_line=excluded.raw_line
            """,
            (
                game_id,
                team_id,
                player_id,
                pl.status,
                pl.pos,
                pl.minutes,
                pl.pts,
                pl.reb,
                pl.ast,
                pl.oreb,
                pl.dreb,
                pl.stl,
                pl.blk,
                pl.tov,
                pl.pf,
                pl.fgm,
                pl.fga,
                pl.fg_pct,
                pl.tpm,
                pl.tpa,
                pl.tp_pct,
                pl.ftm,
                pl.fta,
                pl.ft_pct,
                pl.plus_minus,
                pl.raw_line,
            ),
        )

    # Inactive lists
    # Make inactive ingestion idempotent: if the same game is re-ingested, replace the prior list.
    conn.execute("DELETE FROM inactive_players WHERE game_id = ?", (game_id,))
    for team_name, names in parsed.inactive_by_team.items():
        if team_name == "_raw":
            continue
        team_id = get_or_create_team(conn, team_name)
        for nm in names:
            conn.execute(
                """
                INSERT INTO inactive_players(game_id, team_id, player_name, reason)
                VALUES (?, ?, ?, ?)
                """,
                (game_id, team_id, nm, None),
            )

    return game_id



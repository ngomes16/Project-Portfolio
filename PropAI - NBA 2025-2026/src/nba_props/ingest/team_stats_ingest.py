from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from ..db import get_or_create_player, get_or_create_team
from ..team_aliases import team_name_from_abbrev
from ..util import normalize_team_name, sha256_text
from .team_stats_parser import ParsedTeamStats, parse_team_stats_text


_TEAM_ABBR_IN_FILENAME_RE = re.compile(r"team_stats__([A-Za-z]{2,4})__")


def _infer_team_name_from_path(source_path: Path) -> Optional[str]:
    """
    Try to infer team from canonical raw metadata filenames like:
      team_stats__PHX__2026-01-01.txt
    """
    m = _TEAM_ABBR_IN_FILENAME_RE.search(source_path.name)
    if not m:
        return None
    abbr = m.group(1).upper()
    return team_name_from_abbrev(abbr)


def ingest_team_stats_file(
    conn,
    *,
    source_file: Path,
    team_name: str | None = None,
    as_of_date: str | None = None,
) -> int:
    """
    Ingest a single Team Stats markdown file (per-team season averages) into SQLite.

    Returns the inserted/updated team_stats_snapshot.id.
    """
    text = source_file.read_text(encoding="utf-8", errors="replace")
    source_hash = sha256_text(text)

    team = team_name or _infer_team_name_from_path(source_file)
    if not team:
        raise ValueError(
            "Could not infer team from filename. Pass team_name explicitly (e.g. 'Phoenix Suns')."
        )
    team = normalize_team_name(team)

    parsed: ParsedTeamStats = parse_team_stats_text(text=text, source_path=source_file, as_of_date=as_of_date)

    # If we can't infer season from as_of_date, fall back to existing snapshot season or leave NULL.
    season = parsed.season
    as_of = parsed.as_of_date

    team_id = get_or_create_team(conn, team)
    source_file_str = str(source_file.resolve())

    # Upsert snapshot (team_id + season + as_of_date is unique; as_of_date may be NULL)
    cur = conn.execute(
        """
        INSERT INTO team_stats_snapshot(season, as_of_date, team_id, source_file, source_hash)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(team_id, season, as_of_date) DO UPDATE SET
          source_file=excluded.source_file,
          source_hash=excluded.source_hash
        """,
        (season, as_of, team_id, source_file_str, source_hash),
    )

    # If we hit conflict, lastrowid may be 0; fetch the snapshot id.
    snapshot_id = int(cur.lastrowid) if int(cur.lastrowid or 0) else int(
        conn.execute(
            """
            SELECT id FROM team_stats_snapshot
            WHERE team_id = ? AND (season IS ? OR season = ?) AND (as_of_date IS ? OR as_of_date = ?)
            ORDER BY id DESC LIMIT 1
            """,
            (team_id, season, season, as_of, as_of),
        ).fetchone()["id"]
    )

    # Replace per-player rows for this snapshot to keep it consistent.
    conn.execute("DELETE FROM team_stats_player WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM team_stats_shooting WHERE snapshot_id = ?", (snapshot_id,))

    for ps in parsed.player_stats:
        player_id = get_or_create_player(conn, ps.player)
        conn.execute(
            """
            INSERT INTO team_stats_player(
              snapshot_id, player_id, pos, gp, gs, min, pts, oreb, dreb, reb, ast, stl, blk, tov, pf, ast_to
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                player_id,
                ps.pos,
                ps.gp,
                ps.gs,
                ps.min,
                ps.pts,
                ps.oreb,
                ps.dreb,
                ps.reb,
                ps.ast,
                ps.stl,
                ps.blk,
                ps.tov,
                ps.pf,
                ps.ast_to,
            ),
        )

    for sh in parsed.shooting_stats:
        player_id = get_or_create_player(conn, sh.player)
        conn.execute(
            """
            INSERT INTO team_stats_shooting(
              snapshot_id, player_id, pos, fgm, fga, fg_pct, tpm, tpa, tp_pct, ftm, fta, ft_pct,
              twopm, twopa, twop_pct, sc_eff, sh_eff
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                player_id,
                sh.pos,
                sh.fgm,
                sh.fga,
                sh.fg_pct,
                sh.tpm,
                sh.tpa,
                sh.tp_pct,
                sh.ftm,
                sh.fta,
                sh.ft_pct,
                sh.twopm,
                sh.twopa,
                sh.twop_pct,
                sh.sc_eff,
                sh.sh_eff,
            ),
        )

    return snapshot_id



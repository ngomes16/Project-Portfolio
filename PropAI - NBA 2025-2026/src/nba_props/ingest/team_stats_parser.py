from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..util import normalize_player_name, parse_float, parse_int


@dataclass(frozen=True)
class TeamStatsPlayerPerGame:
    player: str
    pos: Optional[str]
    gp: Optional[int]
    gs: Optional[int]
    min: Optional[float]
    pts: Optional[float]
    oreb: Optional[float]
    dreb: Optional[float]
    reb: Optional[float]
    ast: Optional[float]
    stl: Optional[float]
    blk: Optional[float]
    tov: Optional[float]
    pf: Optional[float]
    ast_to: Optional[float]


@dataclass(frozen=True)
class TeamStatsShooting:
    player: str
    pos: Optional[str]
    fgm: Optional[float]
    fga: Optional[float]
    fg_pct: Optional[float]
    tpm: Optional[float]
    tpa: Optional[float]
    tp_pct: Optional[float]
    ftm: Optional[float]
    fta: Optional[float]
    ft_pct: Optional[float]
    twopm: Optional[float]
    twopa: Optional[float]
    twop_pct: Optional[float]
    sc_eff: Optional[float]
    sh_eff: Optional[float]


@dataclass
class ParsedTeamStats:
    season: Optional[str]
    as_of_date: Optional[str]
    player_stats: list[TeamStatsPlayerPerGame] = field(default_factory=list)
    shooting_stats: list[TeamStatsShooting] = field(default_factory=list)


_ASOF_IN_FILENAME_RE = re.compile(r"__([0-9]{4}-[0-9]{2}-[0-9]{2})\b")


def _strip_md_bold(s: str) -> str:
    return s.replace("**", "").strip()


def _parse_md_table(lines: list[str], start_idx: int) -> tuple[list[dict[str, str]], int]:
    """
    Parse a markdown pipe table starting at or after start_idx.

    Returns: (rows, next_idx)
    - rows is a list[dict[col_name -> cell_str]]
    - next_idx is the first line index after the table
    """
    i = start_idx
    while i < len(lines) and "| " not in lines[i]:
        i += 1
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        i += 1
    if i >= len(lines):
        return [], i

    header = [c.strip() for c in lines[i].split("|")[1:-1]]
    i += 1
    if i < len(lines) and lines[i].lstrip().startswith("|"):
        # separator row
        i += 1

    rows: list[dict[str, str]] = []
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = [c.strip() for c in lines[i].split("|")[1:-1]]
        i += 1
        if not cells or len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells)))
    return rows, i


def _infer_as_of_date_from_filename(source_path: Path) -> Optional[str]:
    m = _ASOF_IN_FILENAME_RE.search(source_path.name)
    return m.group(1) if m else None


def _infer_season_from_as_of_date(as_of_date: Optional[str]) -> Optional[str]:
    if not as_of_date:
        return None
    yyyy = int(as_of_date[0:4])
    mm = int(as_of_date[5:7])
    start_year = yyyy if mm >= 10 else yyyy - 1
    return f"{start_year}-{str(start_year + 1)[2:]}"


def parse_team_stats_text(*, text: str, source_path: Path, as_of_date: str | None = None) -> ParsedTeamStats:
    """
    Parse your Team Stats markdown file format (example: team_stats__PHX__2026-01-01.txt).
    We focus on:
      - ## Player Stats (per-game averages)
      - ## Shooting Stats (per-game shooting)
    """
    inferred_as_of = as_of_date or _infer_as_of_date_from_filename(source_path)
    season = _infer_season_from_as_of_date(inferred_as_of)

    out = ParsedTeamStats(season=season, as_of_date=inferred_as_of)
    lines = text.splitlines()

    # --- Player Stats ---
    # Find "## Player Stats" header, then parse the next markdown table.
    for idx, ln in enumerate(lines):
        if ln.strip().lower() == "## player stats":
            rows, _ = _parse_md_table(lines, idx + 1)
            for r in rows:
                name_raw = _strip_md_bold(r.get("Name", ""))
                if not name_raw or name_raw.lower() == "total":
                    continue
                player = normalize_player_name(name_raw)
                pos = _strip_md_bold(r.get("Pos", "")) or None

                ast_to_raw = _strip_md_bold(r.get("AST/TO", ""))
                ast_to = None if ast_to_raw.upper() == "INF" else parse_float(ast_to_raw)

                out.player_stats.append(
                    TeamStatsPlayerPerGame(
                        player=player,
                        pos=pos,
                        gp=parse_int(_strip_md_bold(r.get("GP"))),
                        gs=parse_int(_strip_md_bold(r.get("GS"))),
                        min=parse_float(_strip_md_bold(r.get("MIN"))),
                        pts=parse_float(_strip_md_bold(r.get("PTS"))),
                        oreb=parse_float(_strip_md_bold(r.get("OR"))),
                        dreb=parse_float(_strip_md_bold(r.get("DR"))),
                        reb=parse_float(_strip_md_bold(r.get("REB"))),
                        ast=parse_float(_strip_md_bold(r.get("AST"))),
                        stl=parse_float(_strip_md_bold(r.get("STL"))),
                        blk=parse_float(_strip_md_bold(r.get("BLK"))),
                        tov=parse_float(_strip_md_bold(r.get("TO"))),
                        pf=parse_float(_strip_md_bold(r.get("PF"))),
                        ast_to=ast_to,
                    )
                )
            break

    # --- Shooting Stats ---
    for idx, ln in enumerate(lines):
        if ln.strip().lower() == "## shooting stats":
            rows, _ = _parse_md_table(lines, idx + 1)
            for r in rows:
                name_raw = _strip_md_bold(r.get("Name", ""))
                if not name_raw or name_raw.lower() == "total":
                    continue
                player = normalize_player_name(name_raw)
                pos = _strip_md_bold(r.get("Pos", "")) or None
                out.shooting_stats.append(
                    TeamStatsShooting(
                        player=player,
                        pos=pos,
                        fgm=parse_float(_strip_md_bold(r.get("FGM"))),
                        fga=parse_float(_strip_md_bold(r.get("FGA"))),
                        fg_pct=parse_float(_strip_md_bold(r.get("FG%"))),
                        tpm=parse_float(_strip_md_bold(r.get("3PM"))),
                        tpa=parse_float(_strip_md_bold(r.get("3PA"))),
                        tp_pct=parse_float(_strip_md_bold(r.get("3P%"))),
                        ftm=parse_float(_strip_md_bold(r.get("FTM"))),
                        fta=parse_float(_strip_md_bold(r.get("FTA"))),
                        ft_pct=parse_float(_strip_md_bold(r.get("FT%"))),
                        twopm=parse_float(_strip_md_bold(r.get("2PM"))),
                        twopa=parse_float(_strip_md_bold(r.get("2PA"))),
                        twop_pct=parse_float(_strip_md_bold(r.get("2P%"))),
                        sc_eff=parse_float(_strip_md_bold(r.get("SC-EFF"))),
                        sh_eff=parse_float(_strip_md_bold(r.get("SH-EFF"))),
                    )
                )
            break

    return out



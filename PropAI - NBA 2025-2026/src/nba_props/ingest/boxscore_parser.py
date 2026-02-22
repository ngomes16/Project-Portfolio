from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..team_aliases import build_abbrev_to_team_map, normalize_team_abbrev
from ..util import (
    normalize_player_name,
    normalize_team_name,
    parse_float,
    parse_int,
    parse_minutes,
)


@dataclass(frozen=True)
class PlayerLine:
    team: str
    player: str
    status: str
    pos: Optional[str] = None
    minutes: Optional[float] = None
    pts: Optional[int] = None
    reb: Optional[int] = None
    ast: Optional[int] = None
    oreb: Optional[int] = None
    dreb: Optional[int] = None
    stl: Optional[int] = None
    blk: Optional[int] = None
    tov: Optional[int] = None
    pf: Optional[int] = None
    fgm: Optional[int] = None
    fga: Optional[int] = None
    fg_pct: Optional[float] = None
    tpm: Optional[int] = None
    tpa: Optional[int] = None
    tp_pct: Optional[float] = None
    ftm: Optional[int] = None
    fta: Optional[int] = None
    ft_pct: Optional[float] = None
    plus_minus: Optional[int] = None
    raw_line: Optional[str] = None


@dataclass(frozen=True)
class TeamTotals:
    team: str
    pts: Optional[int] = None
    reb: Optional[int] = None
    ast: Optional[int] = None
    oreb: Optional[int] = None
    dreb: Optional[int] = None
    stl: Optional[int] = None
    blk: Optional[int] = None
    tov: Optional[int] = None
    pf: Optional[int] = None
    fgm: Optional[int] = None
    fga: Optional[int] = None
    tpm: Optional[int] = None
    tpa: Optional[int] = None
    ftm: Optional[int] = None
    fta: Optional[int] = None
    plus_minus: Optional[int] = None
    raw_line: Optional[str] = None


@dataclass
class ParsedGame:
    game_date: str  # YYYY-MM-DD
    teams: list[str] = field(default_factory=list)  # ordered
    player_lines: list[PlayerLine] = field(default_factory=list)
    team_totals: dict[str, TeamTotals] = field(default_factory=dict)
    inactive_by_team: dict[str, list[str]] = field(default_factory=dict)


_CSV_MARKER = "CSV Version of File:"
# Some files are truly tab-separated, others are space-aligned columns.
_TAB_HEADER_RE = re.compile(r"^PLAYER\s+MIN\s+FGM\b", re.IGNORECASE | re.MULTILINE)
_DATE_IN_FILENAME = re.compile(r"(\d{2})-(\d{2})-(\d{2})")
_DATE_IN_DIRNAME = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_MD_TEAM_HEADER_RE = re.compile(r"^##\s+(.*?)\s+—\s+Box Score\s*$", re.MULTILINE)
_MD_INACTIVE_HEADER_RE = re.compile(r"^##\s+Inactive Players\s*$", re.MULTILINE)


def _infer_date_from_path(source_path: Path) -> Optional[str]:
    m = _DATE_IN_FILENAME.search(source_path.name)
    if not m:
        # If file was renamed (e.g. HOU_vs_BKN__source.txt), infer from parent dir:
        # .../2026-01-01/HOU_vs_BKN__source.txt
        for parent in source_path.resolve().parents:
            dm = _DATE_IN_DIRNAME.match(parent.name)
            if dm:
                yyyy, mm, dd = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
                return f"{yyyy:04d}-{mm:02d}-{dd:02d}"
        return None
    mm, dd, yy = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    yyyy = 2000 + yy
    return f"{yyyy:04d}-{mm:02d}-{dd:02d}"


def parse_boxscore_text(text: str, source_path: Path) -> ParsedGame:
    game_date = _infer_date_from_path(source_path)
    if not game_date:
        raise ValueError(f"Could not infer date from filename: {source_path.name}")

    if _CSV_MARKER in text:
        return _parse_csv_section(text=text, game_date=game_date)

    if _TAB_HEADER_RE.search(text):
        return _parse_tabbed_boxscore(text=text, game_date=game_date)

    if _MD_TEAM_HEADER_RE.search(text):
        return _parse_markdown_tables(text=text, game_date=game_date)

    raise ValueError("Unrecognized box score format (no CSV marker, no tabbed header, no markdown tables).")


def _strip_md_bold(s: str) -> str:
    return s.replace("**", "").strip()


def _parse_inactive_payload(payload: str) -> tuple[Optional[str], list[str]]:
    """
    Parse payload like:
      "HOU: Fred VanVleet; Tyler Smith; Isaiah Crawford"
    Returns (abbrev, [names...])
    """
    txt = payload.strip().strip('"')
    if not txt:
        return None, []
    if ":" not in txt:
        # If we can't see a team prefix, return just a list.
        names = [normalize_player_name(x) for x in re.split(r"[;,]", txt) if x.strip()]
        return None, names
    abbr, rest = txt.split(":", 1)
    abbr = normalize_team_abbrev(abbr)
    names = [normalize_player_name(x) for x in re.split(r"[;,]", rest) if x.strip()]
    return abbr, names


def _parse_csv_section(text: str, game_date: str) -> ParsedGame:
    lines = text.splitlines()
    idx = next(i for i, ln in enumerate(lines) if _CSV_MARKER in ln)
    # Advance to first non-empty line after marker
    j = idx + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j >= len(lines):
        raise ValueError("CSV marker found but no CSV content.")

    # Find header row "Team,Player,..."
    while j < len(lines) and not lines[j].startswith("Team,Player"):
        j += 1
    if j >= len(lines):
        raise ValueError("CSV marker found but header row not found.")

    csv_text = "\n".join(lines[j:])
    reader = csv.DictReader(csv_text.splitlines())

    parsed = ParsedGame(game_date=game_date)

    for row in reader:
        team_raw = (row.get("Team") or "").strip()
        if not team_raw:
            continue

        if team_raw == "Inactive Players":
            # Example rows:
            # Team=Inactive Players, Player="HOU: Fred VanVleet; ...", ...
            payload = (row.get("Player") or "").strip().strip('"')
            if payload:
                abbr, names = _parse_inactive_payload(payload)
                # We'll map abbrev -> full team name after we know the two teams.
                key = abbr or "UNKNOWN"
                parsed.inactive_by_team.setdefault(key, []).extend(names)
            continue

        team = normalize_team_name(team_raw)
        if team not in parsed.teams:
            parsed.teams.append(team)

        player_raw = (row.get("Player") or "").strip()
        status_raw = (row.get("Status") or "").strip() or "UNKNOWN"
        pos = (row.get("Pos") or "").strip() or None

        if normalize_player_name(player_raw).upper() == "TOTALS" or status_raw == "Team Totals":
            parsed.team_totals[team] = TeamTotals(
                team=team,
                pts=parse_int(row.get("PTS")),
                reb=parse_int(row.get("REB")),
                ast=parse_int(row.get("AST")),
                oreb=parse_int(row.get("OREB")),
                dreb=parse_int(row.get("DREB")),
                stl=parse_int(row.get("STL")),
                blk=parse_int(row.get("BLK")),
                tov=parse_int(row.get("TO")),
                pf=parse_int(row.get("PF")),
                fgm=parse_int(row.get("FGM")),
                fga=parse_int(row.get("FGA")),
                tpm=parse_int(row.get("3PM")),
                tpa=parse_int(row.get("3PA")),
                ftm=parse_int(row.get("FTM")),
                fta=parse_int(row.get("FTA")),
                plus_minus=parse_int(row.get("+/-")),
                raw_line=str(row),
            )
            continue

        player = normalize_player_name(player_raw)
        pl = PlayerLine(
            team=team,
            player=player,
            status=status_raw,
            pos=pos,
            minutes=parse_minutes(row.get("MIN")),
            fgm=parse_int(row.get("FGM")),
            fga=parse_int(row.get("FGA")),
            fg_pct=parse_float(row.get("FG%")),
            tpm=parse_int(row.get("3PM")),
            tpa=parse_int(row.get("3PA")),
            tp_pct=parse_float(row.get("3P%")),
            ftm=parse_int(row.get("FTM")),
            fta=parse_int(row.get("FTA")),
            ft_pct=parse_float(row.get("FT%")),
            oreb=parse_int(row.get("OREB")),
            dreb=parse_int(row.get("DREB")),
            reb=parse_int(row.get("REB")),
            ast=parse_int(row.get("AST")),
            stl=parse_int(row.get("STL")),
            blk=parse_int(row.get("BLK")),
            tov=parse_int(row.get("TO")),
            pf=parse_int(row.get("PF")),
            pts=parse_int(row.get("PTS")),
            plus_minus=parse_int(row.get("+/-")),
            raw_line=str(row),
        )
        parsed.player_lines.append(pl)

    # Post-process inactive lists: map abbrev to full team name where possible.
    abbr_map = build_abbrev_to_team_map(parsed.teams)
    inactive_mapped: dict[str, list[str]] = {}
    for key, names in parsed.inactive_by_team.items():
        if key == "_raw":
            inactive_mapped[key] = names
            continue
        team_name = abbr_map.get(key) if key != "UNKNOWN" else None
        if team_name:
            inactive_mapped[team_name] = names
        else:
            inactive_mapped[key] = names
    parsed.inactive_by_team = inactive_mapped

    return parsed


def _parse_tabbed_boxscore(text: str, game_date: str) -> ParsedGame:
    """
    Parse the "tabbed header" style boxscore found in Sample Data/12-31-25 Warriors vs Hornets.txt
    """
    lines = text.splitlines()
    parsed = ParsedGame(game_date=game_date)

    i = 0
    current_team: Optional[str] = None
    teams_seen: list[str] = []
    inactive_payloads: list[str] = []

    def set_team(name: str) -> None:
        nonlocal current_team
        team = normalize_team_name(name)
        current_team = team
        if team not in parsed.teams:
            parsed.teams.append(team)
            teams_seen.append(team)

    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue

        if s == "Inactive Players":
            i += 1
            while i < len(lines):
                t = lines[i].strip()
                if t:
                    inactive_payloads.append(t)
                i += 1
            break

        if "\t" not in s and not s.lower().startswith("click on any linked stat"):
            # Likely a team header (e.g. "Golden State Warriors")
            set_team(s)
            i += 1
            continue

        if _TAB_HEADER_RE.match(s):
            # Parse player blocks until TOTALS (then expect totals line).
            if not current_team:
                raise ValueError("Found tabbed header but no team name above it.")

            i += 1
            while i < len(lines):
                s2 = lines[i].strip()
                if not s2:
                    i += 1
                    continue
                if s2 == "TOTALS":
                    i += 1
                    totals_line = lines[i] if i < len(lines) else ""
                    parsed.team_totals[current_team] = _parse_tabbed_totals(
                        team=current_team, totals_line=totals_line
                    )
                    i += 1
                    break
                if s2.lower().startswith("undefined headshot"):
                    i += 1
                    continue

                # Player block begins with name line
                player_name = normalize_player_name(s2)
                i += 1
                if i >= len(lines):
                    break
                pos_or_status = lines[i].strip()
                i += 1

                # Some files have a separate position line (G/F/C), others go straight to the stats.
                if pos_or_status in {"G", "F", "C"}:
                    pos = pos_or_status
                    if i >= len(lines):
                        break
                    stats_line = lines[i].strip()
                    i += 1
                    parsed.player_lines.append(
                        _parse_tabbed_player_stats(
                            team=current_team,
                            player=player_name,
                            pos=pos,
                            stats_line=stats_line,
                        )
                    )
                    continue

                # If this line looks like MIN (MM:SS), it's actually the stats line and pos is unknown.
                if re.match(r"^\d+:\d{2}\b", pos_or_status):
                    stats_line = pos_or_status
                    parsed.player_lines.append(
                        _parse_tabbed_player_stats(
                            team=current_team,
                            player=player_name,
                            pos="",
                            stats_line=stats_line,
                        )
                    )
                    continue

                # DNP/DND row
                status = pos_or_status if pos_or_status else "UNKNOWN"
                parsed.player_lines.append(
                    PlayerLine(
                        team=current_team,
                        player=player_name,
                        status=status,
                        pos=None,
                        raw_line=f"{player_name} | {status}",
                    )
                )
            continue

        i += 1

    # Map inactive payloads to teams. Prefer explicit abbrev prefixes (e.g. "GSW: ..."),
    # otherwise fall back to team order (first line -> first team, second -> second team).
    abbr_map = build_abbrev_to_team_map(parsed.teams)
    for idx, payload in enumerate(inactive_payloads):
        if not payload:
            continue
        raw = payload
        abbr, names = _parse_inactive_payload(payload)

        team: str
        if abbr and abbr in abbr_map:
            team = abbr_map[abbr]
        else:
            team = teams_seen[idx] if idx < len(teams_seen) else "UNKNOWN_TEAM"

        parsed.inactive_by_team.setdefault(team, []).extend(names)
        parsed.inactive_by_team.setdefault("_raw", []).append(raw)

    return parsed


def _parse_markdown_tables(text: str, game_date: str) -> ParsedGame:
    """
    Parse markdown tables like Sample Data/01-01-26 Heat vs Pistons.txt.
    This supports files that do NOT have the CSV section.
    """
    lines = text.splitlines()
    parsed = ParsedGame(game_date=game_date)

    # 1) Parse each "## <Team> — Box Score" section and its subsequent markdown table.
    for m in _MD_TEAM_HEADER_RE.finditer(text):
        team = normalize_team_name(m.group(1))
        if team not in parsed.teams:
            parsed.teams.append(team)

        # Find the line index of this header.
        header_line_idx = text[: m.start()].count("\n")
        i = header_line_idx + 1

        # Scan forward to the table header (line containing "| Player")
        while i < len(lines) and "| Player" not in lines[i]:
            i += 1
        if i >= len(lines):
            continue

        table_header = [c.strip() for c in lines[i].split("|")[1:-1]]
        i += 2  # skip separator row

        while i < len(lines) and lines[i].strip().startswith("|"):
            row_cells = [c.strip() for c in lines[i].split("|")[1:-1]]
            i += 1
            if not row_cells or len(row_cells) != len(table_header):
                continue

            row = dict(zip(table_header, row_cells))

            player_raw = _strip_md_bold(row.get("Player", ""))
            if not player_raw:
                continue

            if player_raw.upper() == "TOTALS":
                parsed.team_totals[team] = TeamTotals(
                    team=team,
                    pts=parse_int(_strip_md_bold(row.get("PTS"))),
                    reb=parse_int(_strip_md_bold(row.get("REB"))),
                    ast=parse_int(_strip_md_bold(row.get("AST"))),
                    oreb=parse_int(_strip_md_bold(row.get("OREB"))),
                    dreb=parse_int(_strip_md_bold(row.get("DREB"))),
                    stl=parse_int(_strip_md_bold(row.get("STL"))),
                    blk=parse_int(_strip_md_bold(row.get("BLK"))),
                    tov=parse_int(_strip_md_bold(row.get("TO"))),
                    pf=parse_int(_strip_md_bold(row.get("PF"))),
                    fgm=parse_int(_strip_md_bold(row.get("FGM"))),
                    fga=parse_int(_strip_md_bold(row.get("FGA"))),
                    tpm=parse_int(_strip_md_bold(row.get("3PM"))),
                    tpa=parse_int(_strip_md_bold(row.get("3PA"))),
                    ftm=parse_int(_strip_md_bold(row.get("FTM"))),
                    fta=parse_int(_strip_md_bold(row.get("FTA"))),
                    plus_minus=parse_int(_strip_md_bold(row.get("+/-"))),
                    raw_line=lines[i - 1],
                )
                continue

            min_str = _strip_md_bold(row.get("MIN"))
            minutes = parse_minutes(min_str)
            if minutes is not None:
                status = "Played"
            else:
                status = min_str if min_str else "UNKNOWN"

            pl = PlayerLine(
                team=team,
                player=normalize_player_name(player_raw),
                status=status,
                pos=_strip_md_bold(row.get("Pos") or "") or None,
                minutes=minutes,
                fgm=parse_int(_strip_md_bold(row.get("FGM"))),
                fga=parse_int(_strip_md_bold(row.get("FGA"))),
                fg_pct=parse_float(_strip_md_bold(row.get("FG%"))),
                tpm=parse_int(_strip_md_bold(row.get("3PM"))),
                tpa=parse_int(_strip_md_bold(row.get("3PA"))),
                tp_pct=parse_float(_strip_md_bold(row.get("3P%"))),
                ftm=parse_int(_strip_md_bold(row.get("FTM"))),
                fta=parse_int(_strip_md_bold(row.get("FTA"))),
                ft_pct=parse_float(_strip_md_bold(row.get("FT%"))),
                oreb=parse_int(_strip_md_bold(row.get("OREB"))),
                dreb=parse_int(_strip_md_bold(row.get("DREB"))),
                reb=parse_int(_strip_md_bold(row.get("REB"))),
                ast=parse_int(_strip_md_bold(row.get("AST"))),
                stl=parse_int(_strip_md_bold(row.get("STL"))),
                blk=parse_int(_strip_md_bold(row.get("BLK"))),
                tov=parse_int(_strip_md_bold(row.get("TO"))),
                pf=parse_int(_strip_md_bold(row.get("PF"))),
                pts=parse_int(_strip_md_bold(row.get("PTS"))),
                plus_minus=parse_int(_strip_md_bold(row.get("+/-"))),
                raw_line=lines[i - 1],
            )
            parsed.player_lines.append(pl)

    # 2) Parse inactive players section like:
    # * **MIA:** Terry Rozier, Tyler Herro, ...
    inactive_section = _MD_INACTIVE_HEADER_RE.search(text)
    if inactive_section:
        tail_lines = text[inactive_section.end() :].splitlines()
        for ln in tail_lines:
            s = ln.strip()
            if not s.startswith("*"):
                continue
            m = re.match(r"^\*\s+\*\*([A-Za-z]{2,4})\:\*\*\s*(.*)\s*$", s)
            if not m:
                continue
            abbr = normalize_team_abbrev(m.group(1))
            names = [normalize_player_name(x) for x in m.group(2).split(",") if x.strip()]
            parsed.inactive_by_team.setdefault(abbr, []).extend(names)

        # Map abbrev -> full team name if possible.
        abbr_map = build_abbrev_to_team_map(parsed.teams)
        inactive_mapped: dict[str, list[str]] = {}
        for key, names in parsed.inactive_by_team.items():
            team_name = abbr_map.get(key)
            inactive_mapped[team_name or key] = names
        parsed.inactive_by_team = inactive_mapped

    return parsed


def _parse_tabbed_player_stats(team: str, player: str, pos: str, stats_line: str) -> PlayerLine:
    # Stats lines are numeric columns; split on whitespace (tabs or spaces).
    parts = [p.strip() for p in re.split(r"\s+", stats_line.strip()) if p.strip()]
    # Expected columns:
    # MIN,FGM,FGA,FG%,3PM,3PA,3P%,FTM,FTA,FT%,OREB,DREB,REB,AST,STL,BLK,TO,PF,PTS,+/-
    if len(parts) < 20:
        raise ValueError(f"Could not parse stats line for {player}: {stats_line}")

    return PlayerLine(
        team=team,
        player=player,
        status="Played",
        pos=pos,
        minutes=parse_minutes(parts[0]),
        fgm=parse_int(parts[1]),
        fga=parse_int(parts[2]),
        fg_pct=parse_float(parts[3]),
        tpm=parse_int(parts[4]),
        tpa=parse_int(parts[5]),
        tp_pct=parse_float(parts[6]),
        ftm=parse_int(parts[7]),
        fta=parse_int(parts[8]),
        ft_pct=parse_float(parts[9]),
        oreb=parse_int(parts[10]),
        dreb=parse_int(parts[11]),
        reb=parse_int(parts[12]),
        ast=parse_int(parts[13]),
        stl=parse_int(parts[14]),
        blk=parse_int(parts[15]),
        tov=parse_int(parts[16]),
        pf=parse_int(parts[17]),
        pts=parse_int(parts[18]),
        plus_minus=parse_int(parts[19]),
        raw_line=stats_line,
    )


def _parse_tabbed_totals(team: str, totals_line: str) -> TeamTotals:
    parts = [p.strip() for p in re.split(r"\s+", totals_line.strip()) if p.strip()]
    # Expected:
    # FGM,FGA,FG%,3PM,3PA,3P%,FTM,FTA,FT%,OREB,DREB,REB,AST,STL,BLK,TO,PF,PTS,+/-
    if len(parts) < 19:
        return TeamTotals(team=team, raw_line=totals_line)

    return TeamTotals(
        team=team,
        fgm=parse_int(parts[0]),
        fga=parse_int(parts[1]),
        tpm=parse_int(parts[3]),
        tpa=parse_int(parts[4]),
        ftm=parse_int(parts[6]),
        fta=parse_int(parts[7]),
        oreb=parse_int(parts[9]),
        dreb=parse_int(parts[10]),
        reb=parse_int(parts[11]),
        ast=parse_int(parts[12]),
        stl=parse_int(parts[13]),
        blk=parse_int(parts[14]),
        tov=parse_int(parts[15]),
        pf=parse_int(parts[16]),
        pts=parse_int(parts[17]),
        plus_minus=parse_int(parts[18]) if len(parts) > 18 else None,
        raw_line=totals_line,
    )



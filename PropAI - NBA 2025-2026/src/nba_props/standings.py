from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .team_aliases import abbrev_from_team_name, normalize_team_abbrev, team_name_from_abbrev


EAST_ABBREVS = {
    "ATL",
    "BOS",
    "BKN",
    "CHA",
    "CHI",
    "CLE",
    "DET",
    "IND",
    "MIA",
    "MIL",
    "NYK",
    "ORL",
    "PHI",
    "TOR",
    "WAS",
}

WEST_ABBREVS = {
    "DAL",
    "DEN",
    "GSW",
    "HOU",
    "LAC",
    "LAL",
    "MEM",
    "MIN",
    "NOP",
    "OKC",
    "PHX",
    "POR",
    "SAC",
    "SAS",
    "UTA",
}

ALL_ABBREVS = tuple(sorted(EAST_ABBREVS | WEST_ABBREVS))


def conference_for_abbrev(abbrev: str) -> Optional[str]:
    ab = normalize_team_abbrev(abbrev)
    if ab in EAST_ABBREVS:
        return "East"
    if ab in WEST_ABBREVS:
        return "West"
    return None


@dataclass(frozen=True)
class TeamRecord:
    wins: int
    losses: int
    pts_for: int
    pts_against: int

    @property
    def gp(self) -> int:
        return int(self.wins + self.losses)

    @property
    def win_pct(self) -> Optional[float]:
        gp = self.gp
        if gp <= 0:
            return None
        return self.wins / gp


@dataclass(frozen=True)
class TeamStandingRow:
    conference: str  # "East" / "West"
    seed: int
    abbr: str
    team_name: str
    wins: int
    losses: int
    win_pct: Optional[float]


def _team_ids_by_abbrev(conn) -> dict[str, list[int]]:
    """
    Map an NBA abbrev (e.g. PHX) -> list of team ids in our DB that represent that team.
    This intentionally collapses aliases (e.g. "LA Clippers" vs "Los Angeles Clippers") by abbrev.
    """
    rows = conn.execute("SELECT id, name FROM teams").fetchall()
    out: dict[str, list[int]] = {}
    for r in rows:
        tid = int(r["id"])
        name = str(r["name"])
        abbr = abbrev_from_team_name(name)
        if not abbr:
            continue
        abbr = normalize_team_abbrev(abbr)
        out.setdefault(abbr, []).append(tid)
    return out


def compute_team_records(conn) -> dict[str, TeamRecord]:
    """
    Compute W/L from ingested games by comparing final team points.

    Points source (priority):
    1) `boxscore_team_totals.pts` if present
    2) SUM of `boxscore_player.pts` for players who played (minutes not null)
    """
    team_ids_by_abbr = _team_ids_by_abbrev(conn)

    # Preload points from team totals
    totals_pts: dict[tuple[int, int], int] = {}
    for r in conn.execute(
        "SELECT game_id, team_id, pts FROM boxscore_team_totals WHERE pts IS NOT NULL"
    ).fetchall():
        totals_pts[(int(r["game_id"]), int(r["team_id"]))] = int(r["pts"])

    # Preload fallback points from player sums
    sum_pts: dict[tuple[int, int], int] = {}
    for r in conn.execute(
        """
        SELECT game_id, team_id, SUM(pts) AS pts_sum
        FROM boxscore_player
        WHERE minutes IS NOT NULL AND pts IS NOT NULL
        GROUP BY game_id, team_id
        """
    ).fetchall():
        pts_sum = r["pts_sum"]
        if pts_sum is None:
            continue
        sum_pts[(int(r["game_id"]), int(r["team_id"]))] = int(pts_sum)

    def pts_for(game_id: int, team_id: int) -> Optional[int]:
        return totals_pts.get((game_id, team_id)) or sum_pts.get((game_id, team_id))

    # Compute records by abbreviation
    wins: dict[str, int] = {ab: 0 for ab in ALL_ABBREVS}
    losses: dict[str, int] = {ab: 0 for ab in ALL_ABBREVS}
    pf: dict[str, int] = {ab: 0 for ab in ALL_ABBREVS}
    pa: dict[str, int] = {ab: 0 for ab in ALL_ABBREVS}

    games = conn.execute("SELECT id, team1_id, team2_id FROM games").fetchall()
    for g in games:
        game_id = int(g["id"])
        t1_id = int(g["team1_id"])
        t2_id = int(g["team2_id"])

        # Find abbrev keys for these team ids
        ab1 = next((ab for ab, ids in team_ids_by_abbr.items() if t1_id in ids), None)
        ab2 = next((ab for ab, ids in team_ids_by_abbr.items() if t2_id in ids), None)
        if not ab1 or not ab2:
            continue

        p1 = pts_for(game_id, t1_id)
        p2 = pts_for(game_id, t2_id)
        if p1 is None or p2 is None:
            continue

        pf[ab1] += p1
        pa[ab1] += p2
        pf[ab2] += p2
        pa[ab2] += p1

        if p1 > p2:
            wins[ab1] += 1
            losses[ab2] += 1
        elif p2 > p1:
            wins[ab2] += 1
            losses[ab1] += 1
        else:
            # Ignore ties (shouldn't happen in NBA)
            continue

    out: dict[str, TeamRecord] = {}
    for ab in ALL_ABBREVS:
        out[ab] = TeamRecord(wins=wins[ab], losses=losses[ab], pts_for=pf[ab], pts_against=pa[ab])
    return out


def compute_conference_standings(conn) -> dict[str, list[TeamStandingRow]]:
    """
    Returns standings per conference, seeded based on the games ingested so far.
    """
    records = compute_team_records(conn)

    def build(conf: str, abbrevs: set[str]) -> list[TeamStandingRow]:
        items = []
        for ab in sorted(abbrevs):
            rec = records.get(ab) or TeamRecord(wins=0, losses=0, pts_for=0, pts_against=0)
            team_name = team_name_from_abbrev(ab) or ab
            items.append(
                {
                    "abbr": ab,
                    "team_name": team_name,
                    "wins": rec.wins,
                    "losses": rec.losses,
                    "win_pct": rec.win_pct,
                }
            )

        # Sort by win% desc (None last), then wins desc, then losses asc, then name.
        def key(x):
            wp = x["win_pct"]
            return (wp is None, -(wp or 0.0), -x["wins"], x["losses"], x["team_name"])

        items.sort(key=key)

        out_rows: list[TeamStandingRow] = []
        for i, x in enumerate(items, start=1):
            out_rows.append(
                TeamStandingRow(
                    conference=conf,
                    seed=i,
                    abbr=x["abbr"],
                    team_name=x["team_name"],
                    wins=int(x["wins"]),
                    losses=int(x["losses"]),
                    win_pct=x["win_pct"],
                )
            )
        return out_rows

    return {"East": build("East", EAST_ABBREVS), "West": build("West", WEST_ABBREVS)}


def compute_player_averages_for_team(conn, team_abbrev: str) -> list[dict[str, object]]:
    """
    Compute per-player averages from ingested boxscores for a given team abbrev.
    """
    team_abbrev = normalize_team_abbrev(team_abbrev)
    team_ids_by_abbr = _team_ids_by_abbrev(conn)
    team_ids = team_ids_by_abbr.get(team_abbrev) or []
    if not team_ids:
        return []

    placeholders = ",".join(["?"] * len(team_ids))
    rows = conn.execute(
        f"""
        SELECT
          p.name AS player,
          MAX(COALESCE(b.pos, '')) AS pos,
          COUNT(*) AS gp,
          AVG(b.minutes) AS avg_min,
          AVG(b.pts) AS avg_pts,
          AVG(b.reb) AS avg_reb,
          AVG(b.ast) AS avg_ast
        FROM boxscore_player b
        JOIN players p ON p.id = b.player_id
        WHERE b.team_id IN ({placeholders})
          AND b.minutes IS NOT NULL
        GROUP BY b.player_id
        ORDER BY avg_min DESC, gp DESC, p.name
        """,
        tuple(team_ids),
    ).fetchall()

    out: list[dict[str, object]] = []
    for r in rows:
        out.append(
            {
                "player": r["player"],
                "pos": r["pos"] or "",
                "gp": int(r["gp"] or 0),
                "avg_min": float(r["avg_min"] or 0.0),
                "avg_pts": float(r["avg_pts"] or 0.0),
                "avg_reb": float(r["avg_reb"] or 0.0),
                "avg_ast": float(r["avg_ast"] or 0.0),
            }
        )
    return out



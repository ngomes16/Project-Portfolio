"""Parse and store NBA salary data."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class PlayerSalary:
    """Parsed player salary information."""
    rank: int
    name: str
    position: Optional[str]
    team: str
    salary: int  # In dollars


def parse_salary_text(text: str) -> list[PlayerSalary]:
    """
    Parse salary text file format.
    
    Expected format:
    RK	NAME	TEAM	SALARY
    1	Stephen Curry, G	Golden State Warriors	$59,606,817
    """
    salaries = []
    
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # Skip header lines
        if line.startswith("RK") or line.startswith("2025-"):
            continue
        
        # Try to parse as salary line
        # Format: RANK<tab>NAME, POS<tab>TEAM<tab>$SALARY
        parts = re.split(r"\t+", line)
        if len(parts) < 4:
            continue
        
        try:
            rank = int(parts[0])
        except ValueError:
            continue
        
        # Parse name and position
        name_pos = parts[1].strip()
        if ", " in name_pos:
            name, pos = name_pos.rsplit(", ", 1)
        else:
            name, pos = name_pos, None
        
        team = parts[2].strip()
        
        # Parse salary (remove $, commas)
        salary_str = parts[3].strip().replace("$", "").replace(",", "")
        try:
            salary = int(salary_str)
        except ValueError:
            continue
        
        salaries.append(PlayerSalary(
            rank=rank,
            name=name,
            position=pos,
            team=team,
            salary=salary,
        ))
    
    return salaries


def ingest_salaries(conn: sqlite3.Connection, salaries: list[PlayerSalary]) -> int:
    """
    Store salaries in the database.
    
    Creates/updates the player_salaries table.
    
    Returns:
        Number of salaries stored
    """
    # Create table if needed
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_salaries (
            id INTEGER PRIMARY KEY,
            player_name TEXT NOT NULL,
            position TEXT,
            team TEXT NOT NULL,
            salary INTEGER NOT NULL,
            salary_rank INTEGER,
            season TEXT DEFAULT '2025-26',
            UNIQUE(player_name, season)
        )
    """)
    
    count = 0
    for sal in salaries:
        conn.execute(
            """
            INSERT OR REPLACE INTO player_salaries 
            (player_name, position, team, salary, salary_rank, season)
            VALUES (?, ?, ?, ?, ?, '2025-26')
            """,
            (sal.name, sal.position, sal.team, sal.salary, sal.rank),
        )
        count += 1
    
    conn.commit()
    return count


def get_player_salary(conn: sqlite3.Connection, player_name: str) -> Optional[PlayerSalary]:
    """Get salary info for a player."""
    row = conn.execute(
        """
        SELECT salary_rank, player_name, position, team, salary
        FROM player_salaries
        WHERE player_name = ?
        ORDER BY season DESC
        LIMIT 1
        """,
        (player_name,),
    ).fetchone()
    
    if not row:
        return None
    
    return PlayerSalary(
        rank=row["salary_rank"],
        name=row["player_name"],
        position=row["position"],
        team=row["team"],
        salary=row["salary"],
    )


def get_top_paid_players(conn: sqlite3.Connection, team: Optional[str] = None, limit: int = 50) -> list[PlayerSalary]:
    """Get top paid players, optionally filtered by team."""
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
    
    return [
        PlayerSalary(
            rank=r["salary_rank"],
            name=r["player_name"],
            position=r["position"],
            team=r["team"],
            salary=r["salary"],
        )
        for r in rows
    ]


from __future__ import annotations

import re
from dataclasses import dataclass

from ..util import normalize_player_name


@dataclass(frozen=True)
class LineItem:
    prop_type: str  # PTS/REB/AST
    player: str
    line: float
    odds_american: int | None


_SECTION_MAP = {
    "points": "PTS",
    "points line": "PTS",
    "player points": "PTS",
    "rebounds": "REB",
    "player rebounds": "REB",
    "assists": "AST",
    "player assists": "AST",
}


def parse_lines_text(text: str) -> list[LineItem]:
    """
    Accepts text like:
      Points line:
      CJ McCollum: 18.5   -125
      ...
      Player Rebounds:
      ...

    Returns a list of LineItem.
    """
    items: list[LineItem] = []
    current_prop: str | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Section headers
        if line.endswith(":"):
            key = line[:-1].strip().lower()
            current_prop = _SECTION_MAP.get(key)
            continue

        # Also allow headers without colon, e.g. "Player Assists"
        key2 = line.strip().lower()
        if key2 in _SECTION_MAP:
            current_prop = _SECTION_MAP[key2]
            continue

        if not current_prop:
            # ignore until we find a section
            continue

        # Line format: "<name>: <num> <odds>"
        # odds is optional; can be -125, +110
        m = re.match(r"^(.*?):\s*([0-9]+(?:\.[0-9]+)?)\s*([+-]\d+)?\s*$", line)
        if not m:
            continue

        player = normalize_player_name(m.group(1))
        line_val = float(m.group(2))
        odds = int(m.group(3)) if m.group(3) else None

        items.append(
            LineItem(
                prop_type=current_prop,
                player=player,
                line=line_val,
                odds_american=odds,
            )
        )

    return items



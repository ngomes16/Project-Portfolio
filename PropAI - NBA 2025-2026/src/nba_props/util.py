from __future__ import annotations

import hashlib
import re
from typing import Optional


_MIN_RE = re.compile(r"^\s*(\d+):(\d{2})\s*$")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def parse_minutes(min_str: str | None) -> Optional[float]:
    """
    Parse 'MM:SS' into minutes as a float.
    Returns None for blanks, em-dashes, 'DNP', etc.
    """
    if min_str is None:
        return None
    s = str(min_str).strip()
    if not s or s in {"—", "-", "DNP", "DND"}:
        return None
    m = _MIN_RE.match(s)
    if not m:
        return None
    mm = int(m.group(1))
    ss = int(m.group(2))
    return mm + ss / 60.0


def parse_int(x: str | None) -> Optional[int]:
    if x is None:
        return None
    s = str(x).strip()
    if not s or s in {"—", "-"}:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_float(x: str | None) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip().replace("%", "")
    if not s or s in {"—", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def normalize_team_name(name: str) -> str:
    # For now, just normalize whitespace. Later we can add aliases.
    return " ".join(name.strip().split())


def normalize_player_name(name: str) -> str:
    return " ".join(name.strip().split())



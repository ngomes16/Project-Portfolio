from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..paths import Paths


_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


@dataclass(frozen=True)
class PastedSaveResult:
    game_date: str
    season: str
    path: Path


def _infer_season_from_date(game_date: str) -> str:
    yyyy = int(game_date[0:4])
    mm = int(game_date[5:7])
    start_year = yyyy if mm >= 10 else yyyy - 1
    return f"{start_year}-{str(start_year + 1)[2:]}"


def validate_game_date(game_date: str) -> str:
    s = game_date.strip()
    m = _DATE_RE.match(s)
    if not m:
        raise ValueError("game_date must be YYYY-MM-DD (example: 2026-01-01)")
    yyyy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= mm <= 12 and 1 <= dd <= 31 and 2000 <= yyyy <= 2100):
        raise ValueError("game_date is out of expected range")
    return s


def save_pasted_boxscore_text(
    *,
    text: str,
    game_date: str,
    paths: Paths,
    label: str | None = None,
) -> PastedSaveResult:
    if not text.strip():
        raise ValueError("No text provided")
    game_date = validate_game_date(game_date)
    season = _infer_season_from_date(game_date)

    safe_label = (label or "PASTE").strip() or "PASTE"
    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", safe_label)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    out_dir = paths.raw_dir / "boxscores" / season / game_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{safe_label}__{ts}.txt"
    out_path.write_text(text, encoding="utf-8", errors="replace")

    return PastedSaveResult(game_date=game_date, season=season, path=out_path)



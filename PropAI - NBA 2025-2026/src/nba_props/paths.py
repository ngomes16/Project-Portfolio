from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    repo_root: Path

    @property
    def data_dir(self) -> Path:
        return self.repo_root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def db_dir(self) -> Path:
        return self.data_dir / "db"

    @property
    def db_path(self) -> Path:
        return self.db_dir / "nba_props.sqlite3"


def get_paths() -> Paths:
    # repo_root = .../Sports Algorithm/ (this file lives in src/nba_props/)
    repo_root = Path(__file__).resolve().parents[2]
    return Paths(repo_root=repo_root)



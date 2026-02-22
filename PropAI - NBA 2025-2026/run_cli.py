#!/usr/bin/env python3
"""
NBA Props Predictor CLI
=======================

Run the web application:
    python run_cli.py gui

Or use specific commands:
    python run_cli.py init-db
    python run_cli.py summary
    python run_cli.py list-games
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(repo_root / "src"))
    from nba_props.cli import main as cli_main

    # Default to 'gui' command if no arguments
    if argv is None:
        argv = sys.argv[1:]
    
    if not argv:
        argv = ["gui"]
    
    return int(cli_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())



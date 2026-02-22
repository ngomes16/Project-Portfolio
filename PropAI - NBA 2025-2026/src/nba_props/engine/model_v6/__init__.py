"""
Model V6 - Archetype-Aware Defense-Focused NBA Props Model
============================================================

This model emphasizes player archetypes and defensive matchups as primary
factors in prop projections, moving beyond simple historical averages.

Key Features:
-------------
1. Player Archetype Analysis
   - Groups players by offensive/defensive roles
   - Tracks how different archetypes perform vs different defenses
   
2. Defense-First Projections
   - Position-based defense ratings
   - Archetype-specific matchup adjustments
   - Elite defender tracking
   
3. Player Groupings
   - By tier (MVP, Star, Role Player, etc.)
   - By playing style (Heliocentric, 3-and-D, Hub Big, etc.)
   - By position flexibility
   
4. Comprehensive Backtesting
   - Breakdown by archetype
   - Breakdown by defense matchup quality
   - Breakdown by player tier
   - Breakdown by prop type

Module Structure:
-----------------
- config.py: Model configuration and parameters
- player_groups.py: Player classification and grouping system
- defense_analysis.py: Defense-focused projection adjustments
- projector.py: Core projection engine
- confidence.py: Confidence scoring system
- picks.py: Pick generation and selection
- backtester.py: Comprehensive backtesting framework
- lab.py: Model Lab interface for testing and comparison

Usage:
------
    from src.nba_props.engine.model_v6 import get_daily_picks, run_backtest
    
    # Get picks for a date
    picks = get_daily_picks("2026-01-09")
    
    # Run backtest with archetype analysis
    results = run_backtest("2025-12-15", "2026-01-09")
    
    # Access performance by archetype
    print(results.by_archetype)
    print(results.by_defense_quality)

Author: NBA Props Team - Model V6
Version: 1.0
Last Updated: January 2026
"""

from .config import ModelV6Config, DEFAULT_CONFIG
from .picks import get_daily_picks, generate_game_picks, PropPick, DailyPicks
from .backtester import run_backtest, BacktestResult, quick_backtest
from .lab import ModelLab
from .player_groups import (
    PlayerGroup,
    PlayerTier,
    OffensiveStyle,
    get_player_group,
    classify_player,
    ARCHETYPE_GROUPS,
)
from .defense_analysis import (
    DefenseMatchup,
    get_defense_matchup,
    get_team_defense_summary,
)
from .projector import (
    project_all_props,
    Projection,
)
from .confidence import (
    calculate_confidence,
)

__all__ = [
    # Config
    "ModelV6Config",
    "DEFAULT_CONFIG",
    # Pick generation
    "get_daily_picks",
    "generate_game_picks",
    "PropPick",
    "DailyPicks",
    # Backtesting
    "run_backtest",
    "quick_backtest",
    "BacktestResult",
    # Lab
    "ModelLab",
    # Player groups
    "PlayerGroup",
    "PlayerTier",
    "OffensiveStyle",
    "get_player_group",
    "classify_player",
    "ARCHETYPE_GROUPS",
    # Defense
    "DefenseMatchup",
    "get_defense_matchup",
    "get_team_defense_summary",
    # Projection
    "project_all_props",
    "Projection",
    # Confidence
    "calculate_confidence",
]

__version__ = "1.0.0"

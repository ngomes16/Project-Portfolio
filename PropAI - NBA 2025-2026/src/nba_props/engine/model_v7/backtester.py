"""
Comprehensive Backtesting Framework - Model V7
===============================================

Tests the ensemble model against historical data with detailed breakdowns.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .config import ModelV7Config, DEFAULT_CONFIG
from .picks import PropPick, DailyPicks, generate_daily_picks, grade_picks
from ...db import Db
from ...paths import get_paths


@dataclass
class CategoryResult:
    """Results for a specific category."""
    name: str
    total: int = 0
    hits: int = 0
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total > 0 else 0.0
    
    def add_result(self, hit: bool):
        self.total += 1
        if hit:
            self.hits += 1


@dataclass
class DailyResult:
    """Results for a single day."""
    date: str
    games: int = 0
    picks: int = 0
    hits: int = 0
    high_picks: int = 0
    high_hits: int = 0
    medium_picks: int = 0
    medium_hits: int = 0
    over_picks: int = 0
    over_hits: int = 0
    under_picks: int = 0
    under_hits: int = 0
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.picks if self.picks > 0 else 0.0
    
    @property
    def high_hit_rate(self) -> float:
        return self.high_hits / self.high_picks if self.high_picks > 0 else 0.0
    
    @property
    def under_hit_rate(self) -> float:
        return self.under_hits / self.under_picks if self.under_picks > 0 else 0.0


@dataclass
class BacktestResult:
    """Comprehensive backtest results with all breakdowns."""
    start_date: str
    end_date: str
    config_name: str = "default"
    
    # Overall
    total_games: int = 0
    total_picks: int = 0
    total_hits: int = 0
    
    # By prop type
    pts_picks: int = 0
    pts_hits: int = 0
    reb_picks: int = 0
    reb_hits: int = 0
    ast_picks: int = 0
    ast_hits: int = 0
    
    # By direction
    over_picks: int = 0
    over_hits: int = 0
    under_picks: int = 0
    under_hits: int = 0
    
    # By confidence
    high_picks: int = 0
    high_hits: int = 0
    medium_picks: int = 0
    medium_hits: int = 0
    low_picks: int = 0
    low_hits: int = 0
    
    # By archetype group
    by_archetype: Dict[str, CategoryResult] = field(default_factory=dict)
    
    # By defense matchup quality
    by_defense_quality: Dict[str, CategoryResult] = field(default_factory=dict)
    
    # By player tier
    by_player_tier: Dict[int, CategoryResult] = field(default_factory=dict)
    
    # By signal agreement
    by_signal_agreement: Dict[int, CategoryResult] = field(default_factory=dict)
    
    # Daily results
    daily_results: List[DailyResult] = field(default_factory=list)
    
    # All picks for detailed analysis
    all_picks: List[PropPick] = field(default_factory=list)
    
    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================
    
    @property
    def overall_hit_rate(self) -> float:
        return self.total_hits / self.total_picks if self.total_picks > 0 else 0.0
    
    @property
    def pts_hit_rate(self) -> float:
        return self.pts_hits / self.pts_picks if self.pts_picks > 0 else 0.0
    
    @property
    def reb_hit_rate(self) -> float:
        return self.reb_hits / self.reb_picks if self.reb_picks > 0 else 0.0
    
    @property
    def ast_hit_rate(self) -> float:
        return self.ast_hits / self.ast_picks if self.ast_picks > 0 else 0.0
    
    @property
    def over_hit_rate(self) -> float:
        return self.over_hits / self.over_picks if self.over_picks > 0 else 0.0
    
    @property
    def under_hit_rate(self) -> float:
        return self.under_hits / self.under_picks if self.under_picks > 0 else 0.0
    
    @property
    def high_hit_rate(self) -> float:
        return self.high_hits / self.high_picks if self.high_picks > 0 else 0.0
    
    @property
    def medium_hit_rate(self) -> float:
        return self.medium_hits / self.medium_picks if self.medium_picks > 0 else 0.0
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def add_pick(self, pick: PropPick):
        """Add a graded pick to the results."""
        if pick.hit is None:
            return
        
        self.total_picks += 1
        if pick.hit:
            self.total_hits += 1
        
        # By prop type
        if pick.prop_type == "PTS":
            self.pts_picks += 1
            if pick.hit:
                self.pts_hits += 1
        elif pick.prop_type == "REB":
            self.reb_picks += 1
            if pick.hit:
                self.reb_hits += 1
        elif pick.prop_type == "AST":
            self.ast_picks += 1
            if pick.hit:
                self.ast_hits += 1
        
        # By direction
        if pick.direction == "OVER":
            self.over_picks += 1
            if pick.hit:
                self.over_hits += 1
        else:
            self.under_picks += 1
            if pick.hit:
                self.under_hits += 1
        
        # By confidence tier
        if pick.confidence_tier == "HIGH":
            self.high_picks += 1
            if pick.hit:
                self.high_hits += 1
        elif pick.confidence_tier == "MEDIUM":
            self.medium_picks += 1
            if pick.hit:
                self.medium_hits += 1
        else:
            self.low_picks += 1
            if pick.hit:
                self.low_hits += 1
        
        # By archetype
        arch = pick.archetype_group or "unknown"
        if arch not in self.by_archetype:
            self.by_archetype[arch] = CategoryResult(name=arch)
        self.by_archetype[arch].add_result(pick.hit)
        
        # By defense quality
        defense = pick.defense_rating or "unknown"
        if defense not in self.by_defense_quality:
            self.by_defense_quality[defense] = CategoryResult(name=defense)
        self.by_defense_quality[defense].add_result(pick.hit)
        
        # By player tier
        tier = pick.player_tier
        if tier not in self.by_player_tier:
            self.by_player_tier[tier] = CategoryResult(name=f"Tier {tier}")
        self.by_player_tier[tier].add_result(pick.hit)
        
        # By signal agreement
        signals = pick.signals_agreeing
        if signals not in self.by_signal_agreement:
            self.by_signal_agreement[signals] = CategoryResult(name=f"{signals} signals")
        self.by_signal_agreement[signals].add_result(pick.hit)
        
        self.all_picks.append(pick)
    
    def summary(self) -> str:
        """Generate comprehensive text summary."""
        lines = [
            "=" * 70,
            f"MODEL V7 ENSEMBLE - BACKTEST RESULTS",
            "=" * 70,
            f"Config: {self.config_name}",
            f"Period: {self.start_date} to {self.end_date}",
            f"Games: {self.total_games}",
            "",
            f"OVERALL: {self.overall_hit_rate*100:.1f}% ({self.total_hits}/{self.total_picks})",
            "",
            "BY CONFIDENCE TIER:",
            f"  HIGH:   {self.high_hit_rate*100:.1f}% ({self.high_hits}/{self.high_picks})",
            f"  MEDIUM: {self.medium_hit_rate*100:.1f}% ({self.medium_hits}/{self.medium_picks})",
            "",
            "BY PROP TYPE:",
            f"  PTS: {self.pts_hit_rate*100:.1f}% ({self.pts_hits}/{self.pts_picks})",
            f"  REB: {self.reb_hit_rate*100:.1f}% ({self.reb_hits}/{self.reb_picks})",
            f"  AST: {self.ast_hit_rate*100:.1f}% ({self.ast_hits}/{self.ast_picks})",
            "",
            "BY DIRECTION:",
            f"  OVER:  {self.over_hit_rate*100:.1f}% ({self.over_hits}/{self.over_picks})",
            f"  UNDER: {self.under_hit_rate*100:.1f}% ({self.under_hits}/{self.under_picks})",
            "",
        ]
        
        # Archetype breakdown
        if self.by_archetype:
            lines.append("BY ARCHETYPE:")
            sorted_archs = sorted(
                self.by_archetype.items(),
                key=lambda x: x[1].hit_rate,
                reverse=True
            )
            for arch, result in sorted_archs:
                if result.total >= 5:
                    lines.append(
                        f"  {arch:25s}: {result.hit_rate*100:.1f}% ({result.hits}/{result.total})"
                    )
            lines.append("")
        
        # Defense breakdown
        if self.by_defense_quality:
            lines.append("BY DEFENSE QUALITY:")
            for rating in ["elite", "good", "average", "poor", "terrible"]:
                if rating in self.by_defense_quality:
                    result = self.by_defense_quality[rating]
                    lines.append(
                        f"  {rating.upper():10s}: {result.hit_rate*100:.1f}% ({result.hits}/{result.total})"
                    )
            lines.append("")
        
        # Tier breakdown
        if self.by_player_tier:
            lines.append("BY PLAYER TIER:")
            for tier in sorted(self.by_player_tier.keys()):
                result = self.by_player_tier[tier]
                lines.append(
                    f"  Tier {tier}: {result.hit_rate*100:.1f}% ({result.hits}/{result.total})"
                )
            lines.append("")
        
        # Signal agreement
        if self.by_signal_agreement:
            lines.append("BY SIGNAL AGREEMENT:")
            for signals in sorted(self.by_signal_agreement.keys()):
                result = self.by_signal_agreement[signals]
                if result.total >= 10:
                    lines.append(
                        f"  {signals} signals: {result.hit_rate*100:.1f}% ({result.hits}/{result.total})"
                    )
            lines.append("")
        
        lines.append("=" * 70)
        return "\n".join(lines)


def run_backtest(
    start_date: str,
    end_date: str,
    config: ModelV7Config = DEFAULT_CONFIG,
    config_name: str = "default",
    verbose: bool = True,
) -> BacktestResult:
    """
    Run comprehensive backtest over date range.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        config: Model configuration
        config_name: Name for this config (for reporting)
        verbose: Print progress
    
    Returns:
        BacktestResult with all breakdowns
    """
    result = BacktestResult(
        start_date=start_date,
        end_date=end_date,
        config_name=config_name,
    )
    
    paths = get_paths()
    db = Db(paths.db_path)
    
    with db.connect() as conn:
        # Get all dates with games
        dates = _get_game_dates(conn, start_date, end_date)
        
        if verbose:
            print(f"Running backtest from {start_date} to {end_date}")
            print(f"Found {len(dates)} days with games")
            print()
        
        for i, date in enumerate(dates):
            if verbose and i % 10 == 0:
                print(f"Processing {date} ({i+1}/{len(dates)})...")
            
            try:
                # Generate picks for this date
                daily = generate_daily_picks(conn, date, config)
                
                # Grade picks
                grade_picks(conn, daily.picks)
                
                # Track daily results
                daily_result = DailyResult(
                    date=date,
                    games=daily.games_count,
                    picks=len(daily.picks),
                )
                
                result.total_games += daily.games_count
                
                # Add each pick to results
                for pick in daily.picks:
                    if pick.hit is not None:
                        result.add_pick(pick)
                        
                        daily_result.hits += 1 if pick.hit else 0
                        
                        if pick.confidence_tier == "HIGH":
                            daily_result.high_picks += 1
                            if pick.hit:
                                daily_result.high_hits += 1
                        else:
                            daily_result.medium_picks += 1
                            if pick.hit:
                                daily_result.medium_hits += 1
                        
                        if pick.direction == "OVER":
                            daily_result.over_picks += 1
                            if pick.hit:
                                daily_result.over_hits += 1
                        else:
                            daily_result.under_picks += 1
                            if pick.hit:
                                daily_result.under_hits += 1
                
                result.daily_results.append(daily_result)
                
            except Exception as e:
                if verbose:
                    print(f"Error on {date}: {e}")
                continue
    
    if verbose:
        print()
        print(result.summary())
    
    return result


def _get_game_dates(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> List[str]:
    """Get all dates with games in the range."""
    rows = conn.execute(
        """
        SELECT DISTINCT game_date
        FROM games
        WHERE game_date >= ? AND game_date <= ?
        ORDER BY game_date
        """,
        (start_date, end_date),
    ).fetchall()
    
    return [r["game_date"] for r in rows]


def quick_backtest(
    days: int = 14,
    config: ModelV7Config = DEFAULT_CONFIG,
    verbose: bool = True,
) -> BacktestResult:
    """
    Quick backtest over recent days.
    
    Args:
        days: Number of days to backtest
        config: Model configuration
        verbose: Print progress
    
    Returns:
        BacktestResult
    """
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days+1)).strftime("%Y-%m-%d")
    
    return run_backtest(start_date, end_date, config, "quick", verbose)


def compare_configs(
    start_date: str,
    end_date: str,
    configs: Dict[str, ModelV7Config],
    verbose: bool = True,
) -> Dict[str, BacktestResult]:
    """
    Compare multiple configurations.
    
    Args:
        start_date: Start date
        end_date: End date
        configs: Dict of config_name -> ModelV7Config
        verbose: Print progress
    
    Returns:
        Dict of config_name -> BacktestResult
    """
    results = {}
    
    for name, config in configs.items():
        if verbose:
            print(f"\n{'='*60}")
            print(f"Testing config: {name}")
            print(f"{'='*60}")
        
        result = run_backtest(start_date, end_date, config, name, verbose=False)
        results[name] = result
        
        if verbose:
            print(f"  Overall: {result.overall_hit_rate*100:.1f}%")
            print(f"  HIGH:    {result.high_hit_rate*100:.1f}%")
            print(f"  UNDER:   {result.under_hit_rate*100:.1f}%")
    
    # Print comparison table
    if verbose:
        print("\n" + "=" * 80)
        print("CONFIGURATION COMPARISON")
        print("=" * 80)
        print(f"{'Config':<20} {'Overall':>10} {'HIGH':>10} {'UNDER':>10} {'Picks':>10}")
        print("-" * 80)
        
        for name, result in sorted(results.items(), key=lambda x: x[1].overall_hit_rate, reverse=True):
            print(
                f"{name:<20} "
                f"{result.overall_hit_rate*100:>9.1f}% "
                f"{result.high_hit_rate*100:>9.1f}% "
                f"{result.under_hit_rate*100:>9.1f}% "
                f"{result.total_picks:>10}"
            )
        
        print("=" * 80)
    
    return results


def analyze_best_picks(
    result: BacktestResult,
    min_confidence: int = 75,
) -> Dict[str, Any]:
    """
    Analyze what makes the best picks.
    
    Returns insights on highest-confidence hits.
    """
    # Filter to high confidence picks that hit
    best_hits = [
        p for p in result.all_picks 
        if p.hit and p.confidence_score >= min_confidence
    ]
    
    # Find common characteristics
    archetypes = {}
    defenses = {}
    tiers = {}
    directions = {"OVER": 0, "UNDER": 0}
    prop_types = {"PTS": 0, "REB": 0, "AST": 0}
    
    for pick in best_hits:
        arch = pick.archetype_group or "unknown"
        archetypes[arch] = archetypes.get(arch, 0) + 1
        
        defense = pick.defense_rating or "unknown"
        defenses[defense] = defenses.get(defense, 0) + 1
        
        tier = pick.player_tier
        tiers[tier] = tiers.get(tier, 0) + 1
        
        directions[pick.direction] += 1
        prop_types[pick.prop_type] += 1
    
    return {
        "total_best": len(best_hits),
        "archetypes": archetypes,
        "defenses": defenses,
        "tiers": tiers,
        "directions": directions,
        "prop_types": prop_types,
    }

"""
Comprehensive Backtesting Framework
====================================

Provides detailed backtesting with breakdowns by:
1. Overall performance
2. By prop type (PTS, REB, AST)
3. By confidence tier (HIGH, MEDIUM, LOW)
4. By direction (OVER, UNDER)
5. By player archetype group
6. By defense matchup quality
7. By player tier
8. Daily performance tracking
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .config import ModelV6Config, DEFAULT_CONFIG
from .picks import PropPick, DailyPicks, generate_game_picks, grade_picks


@dataclass
class CategoryResult:
    """Results for a specific category (e.g., archetype, defense quality)."""
    name: str
    total: int = 0
    hits: int = 0
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate
    
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
    
    @property
    def hit_rate(self) -> float:
        return self.hits / self.picks if self.picks > 0 else 0.0
    
    @property
    def high_hit_rate(self) -> float:
        return self.high_hits / self.high_picks if self.high_picks > 0 else 0.0
    
    @property
    def medium_hit_rate(self) -> float:
        return self.medium_hits / self.medium_picks if self.medium_picks > 0 else 0.0


@dataclass
class BacktestResult:
    """Comprehensive backtest results with all breakdowns."""
    start_date: str
    end_date: str
    config: ModelV6Config
    
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
    
    @property
    def low_hit_rate(self) -> float:
        return self.low_hits / self.low_picks if self.low_picks > 0 else 0.0
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def add_pick(self, pick: PropPick):
        """Add a graded pick to the results."""
        if pick.hit is None:
            return  # Not graded
        
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
        
        # By archetype group
        archetype = pick.archetype_group or "unknown"
        if archetype not in self.by_archetype:
            self.by_archetype[archetype] = CategoryResult(name=archetype)
        self.by_archetype[archetype].add_result(pick.hit)
        
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
        
        self.all_picks.append(pick)
    
    def summary(self) -> str:
        """Generate a comprehensive text summary."""
        lines = [
            "=" * 70,
            "MODEL V6 BACKTEST RESULTS",
            "=" * 70,
            f"Period: {self.start_date} to {self.end_date}",
            f"Total Games: {self.total_games}",
            f"Total Picks: {self.total_picks}",
            "",
            "OVERALL PERFORMANCE",
            "-" * 40,
            f"Hit Rate: {self.overall_hit_rate*100:.1f}% ({self.total_hits}/{self.total_picks})",
            "",
            "BY CONFIDENCE TIER",
            "-" * 40,
            f"HIGH:   {self.high_hit_rate*100:.1f}% ({self.high_hits}/{self.high_picks})",
            f"MEDIUM: {self.medium_hit_rate*100:.1f}% ({self.medium_hits}/{self.medium_picks})",
            f"LOW:    {self.low_hit_rate*100:.1f}% ({self.low_hits}/{self.low_picks})",
            "",
            "BY PROP TYPE",
            "-" * 40,
            f"PTS: {self.pts_hit_rate*100:.1f}% ({self.pts_hits}/{self.pts_picks})",
            f"REB: {self.reb_hit_rate*100:.1f}% ({self.reb_hits}/{self.reb_picks})",
            f"AST: {self.ast_hit_rate*100:.1f}% ({self.ast_hits}/{self.ast_picks})",
            "",
            "BY DIRECTION",
            "-" * 40,
            f"OVER:  {self.over_hit_rate*100:.1f}% ({self.over_hits}/{self.over_picks})",
            f"UNDER: {self.under_hit_rate*100:.1f}% ({self.under_hits}/{self.under_picks})",
            "",
        ]
        
        # By archetype
        if self.by_archetype:
            lines.extend([
                "BY ARCHETYPE GROUP",
                "-" * 40,
            ])
            for key, result in sorted(self.by_archetype.items(), key=lambda x: x[1].hit_rate, reverse=True):
                if result.total >= 5:  # Only show groups with enough samples
                    lines.append(f"{key:25s}: {result.hit_rate*100:.1f}% ({result.hits}/{result.total})")
            lines.append("")
        
        # By defense quality
        if self.by_defense_quality:
            lines.extend([
                "BY DEFENSE MATCHUP QUALITY",
                "-" * 40,
            ])
            defense_order = ["terrible", "poor", "average", "good", "elite", "unknown"]
            for defense in defense_order:
                if defense in self.by_defense_quality:
                    result = self.by_defense_quality[defense]
                    if result.total >= 3:
                        lines.append(f"{defense.upper():12s}: {result.hit_rate*100:.1f}% ({result.hits}/{result.total})")
            lines.append("")
        
        # By player tier
        if self.by_player_tier:
            lines.extend([
                "BY PLAYER TIER",
                "-" * 40,
            ])
            for tier in sorted(self.by_player_tier.keys()):
                result = self.by_player_tier[tier]
                if result.total >= 5:
                    tier_name = {1: "MVP", 2: "All-Star", 3: "Starter", 4: "Role", 5: "Specialist", 6: "Bench"}.get(tier, f"Tier {tier}")
                    lines.append(f"{tier_name:15s}: {result.hit_rate*100:.1f}% ({result.hits}/{result.total})")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "period": {"start": self.start_date, "end": self.end_date},
            "overall": {
                "games": self.total_games,
                "picks": self.total_picks,
                "hits": self.total_hits,
                "hit_rate": round(self.overall_hit_rate * 100, 1),
            },
            "by_confidence": {
                "high": {"picks": self.high_picks, "hits": self.high_hits, "rate": round(self.high_hit_rate * 100, 1)},
                "medium": {"picks": self.medium_picks, "hits": self.medium_hits, "rate": round(self.medium_hit_rate * 100, 1)},
                "low": {"picks": self.low_picks, "hits": self.low_hits, "rate": round(self.low_hit_rate * 100, 1)},
            },
            "by_prop_type": {
                "pts": {"picks": self.pts_picks, "hits": self.pts_hits, "rate": round(self.pts_hit_rate * 100, 1)},
                "reb": {"picks": self.reb_picks, "hits": self.reb_hits, "rate": round(self.reb_hit_rate * 100, 1)},
                "ast": {"picks": self.ast_picks, "hits": self.ast_hits, "rate": round(self.ast_hit_rate * 100, 1)},
            },
            "by_direction": {
                "over": {"picks": self.over_picks, "hits": self.over_hits, "rate": round(self.over_hit_rate * 100, 1)},
                "under": {"picks": self.under_picks, "hits": self.under_hits, "rate": round(self.under_hit_rate * 100, 1)},
            },
            "by_archetype": {
                k: {"picks": v.total, "hits": v.hits, "rate": round(v.hit_rate * 100, 1)}
                for k, v in self.by_archetype.items()
                if v.total >= 5
            },
            "by_defense_quality": {
                k: {"picks": v.total, "hits": v.hits, "rate": round(v.hit_rate * 100, 1)}
                for k, v in self.by_defense_quality.items()
                if v.total >= 3
            },
            "by_player_tier": {
                str(k): {"picks": v.total, "hits": v.hits, "rate": round(v.hit_rate * 100, 1)}
                for k, v in self.by_player_tier.items()
                if v.total >= 5
            },
        }


def run_backtest(
    start_date: str,
    end_date: str,
    config: ModelV6Config = DEFAULT_CONFIG,
    verbose: bool = False,
) -> BacktestResult:
    """
    Run a comprehensive backtest over a date range.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        config: Model configuration
        verbose: Print progress updates
    
    Returns:
        BacktestResult with all performance metrics
    """
    from ...db import Db
    from ...paths import get_paths
    
    paths = get_paths()
    db = Db(paths.db_path)
    
    result = BacktestResult(
        start_date=start_date,
        end_date=end_date,
        config=config,
    )
    
    with db.connect() as conn:
        # Get all games in date range
        games = conn.execute(
            """
            SELECT g.id, g.game_date, t1.name as team1, t2.name as team2
            FROM games g
            JOIN teams t1 ON t1.id = g.team1_id
            JOIN teams t2 ON t2.id = g.team2_id
            WHERE g.game_date >= ?
              AND g.game_date <= ?
            ORDER BY g.game_date
            """,
            (start_date, end_date),
        ).fetchall()
        
        result.total_games = len(games)
        
        if verbose:
            print(f"Backtesting {len(games)} games from {start_date} to {end_date}")
        
        # Group games by date
        games_by_date: Dict[str, List] = {}
        for game in games:
            date = game["game_date"]
            if date not in games_by_date:
                games_by_date[date] = []
            games_by_date[date].append(game)
        
        # Process each date
        for date, date_games in sorted(games_by_date.items()):
            if verbose:
                print(f"  Processing {date}: {len(date_games)} games...")
            
            daily = DailyResult(date=date, games=len(date_games))
            
            for game in date_games:
                # Generate picks for this game
                picks = generate_game_picks(
                    conn=conn,
                    game_id=game["id"],
                    game_date=game["game_date"],
                    team1_name=game["team1"],
                    team2_name=game["team2"],
                    config=config,
                )
                
                # Grade picks
                picks = grade_picks(picks, conn)
                
                # Add to results
                for pick in picks:
                    if pick.hit is not None:
                        result.add_pick(pick)
                        daily.picks += 1
                        if pick.hit:
                            daily.hits += 1
                        
                        if pick.confidence_tier == "HIGH":
                            daily.high_picks += 1
                            if pick.hit:
                                daily.high_hits += 1
                        elif pick.confidence_tier == "MEDIUM":
                            daily.medium_picks += 1
                            if pick.hit:
                                daily.medium_hits += 1
            
            result.daily_results.append(daily)
        
        if verbose:
            print(f"\nBacktest complete!")
            print(f"Total picks: {result.total_picks}")
            print(f"Overall hit rate: {result.overall_hit_rate*100:.1f}%")
    
    return result


def quick_backtest(
    days: int = 7,
    config: ModelV6Config = DEFAULT_CONFIG,
    verbose: bool = True,
) -> BacktestResult:
    """
    Run a quick backtest over the last N days.
    
    Args:
        days: Number of days to backtest
        config: Model configuration
        verbose: Print progress
    
    Returns:
        BacktestResult
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    return run_backtest(start_date, end_date, config, verbose)


def compare_configurations(
    configs: List[ModelV6Config],
    config_names: List[str],
    start_date: str,
    end_date: str,
    verbose: bool = False,
) -> Dict[str, BacktestResult]:
    """
    Compare multiple model configurations.
    
    Args:
        configs: List of configurations to compare
        config_names: Names for each configuration
        start_date: Start date
        end_date: End date
        verbose: Print progress
    
    Returns:
        Dict mapping config name to BacktestResult
    """
    results = {}
    
    for config, name in zip(configs, config_names):
        if verbose:
            print(f"\n{'='*50}")
            print(f"Testing configuration: {name}")
            print(f"{'='*50}")
        
        result = run_backtest(start_date, end_date, config, verbose)
        results[name] = result
        
        if verbose:
            print(f"\n{name} Results:")
            print(f"  Overall: {result.overall_hit_rate*100:.1f}%")
            print(f"  HIGH:    {result.high_hit_rate*100:.1f}%")
    
    return results


def generate_backtest_report(result: BacktestResult) -> str:
    """
    Generate a detailed markdown report from backtest results.
    
    Args:
        result: BacktestResult to report on
    
    Returns:
        Markdown formatted report string
    """
    lines = [
        "# Model V6 Backtest Report",
        "",
        f"**Period:** {result.start_date} to {result.end_date}",
        f"**Games:** {result.total_games}",
        f"**Total Picks:** {result.total_picks}",
        "",
        "## Overall Performance",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Hit Rate | {result.overall_hit_rate*100:.1f}% |",
        f"| Hits/Picks | {result.total_hits}/{result.total_picks} |",
        "",
        "## Performance by Confidence",
        "",
        "| Tier | Picks | Hits | Hit Rate |",
        "|------|-------|------|----------|",
        f"| HIGH | {result.high_picks} | {result.high_hits} | **{result.high_hit_rate*100:.1f}%** |",
        f"| MEDIUM | {result.medium_picks} | {result.medium_hits} | {result.medium_hit_rate*100:.1f}% |",
        f"| LOW | {result.low_picks} | {result.low_hits} | {result.low_hit_rate*100:.1f}% |",
        "",
        "## Performance by Prop Type",
        "",
        "| Prop | Picks | Hits | Hit Rate |",
        "|------|-------|------|----------|",
        f"| PTS | {result.pts_picks} | {result.pts_hits} | {result.pts_hit_rate*100:.1f}% |",
        f"| REB | {result.reb_picks} | {result.reb_hits} | {result.reb_hit_rate*100:.1f}% |",
        f"| AST | {result.ast_picks} | {result.ast_hits} | {result.ast_hit_rate*100:.1f}% |",
        "",
        "## Performance by Direction",
        "",
        "| Direction | Picks | Hits | Hit Rate |",
        "|-----------|-------|------|----------|",
        f"| OVER | {result.over_picks} | {result.over_hits} | {result.over_hit_rate*100:.1f}% |",
        f"| UNDER | {result.under_picks} | {result.under_hits} | {result.under_hit_rate*100:.1f}% |",
        "",
    ]
    
    # By archetype
    if result.by_archetype:
        lines.extend([
            "## Performance by Archetype",
            "",
            "| Archetype | Picks | Hits | Hit Rate |",
            "|-----------|-------|------|----------|",
        ])
        for key, cat in sorted(result.by_archetype.items(), key=lambda x: x[1].hit_rate, reverse=True):
            if cat.total >= 5:
                lines.append(f"| {key} | {cat.total} | {cat.hits} | {cat.hit_rate*100:.1f}% |")
        lines.append("")
    
    # By defense
    if result.by_defense_quality:
        lines.extend([
            "## Performance by Defense Matchup",
            "",
            "| Defense Quality | Picks | Hits | Hit Rate |",
            "|-----------------|-------|------|----------|",
        ])
        defense_order = ["terrible", "poor", "average", "good", "elite"]
        for defense in defense_order:
            if defense in result.by_defense_quality:
                cat = result.by_defense_quality[defense]
                if cat.total >= 3:
                    lines.append(f"| {defense.upper()} | {cat.total} | {cat.hits} | {cat.hit_rate*100:.1f}% |")
        lines.append("")
    
    # By player tier
    if result.by_player_tier:
        lines.extend([
            "## Performance by Player Tier",
            "",
            "| Tier | Picks | Hits | Hit Rate |",
            "|------|-------|------|----------|",
        ])
        tier_names = {1: "MVP", 2: "All-Star", 3: "Starter", 4: "Role Player", 5: "Specialist", 6: "Bench"}
        for tier in sorted(result.by_player_tier.keys()):
            cat = result.by_player_tier[tier]
            if cat.total >= 5:
                name = tier_names.get(tier, f"Tier {tier}")
                lines.append(f"| {name} | {cat.total} | {cat.hits} | {cat.hit_rate*100:.1f}% |")
        lines.append("")
    
    return "\n".join(lines)

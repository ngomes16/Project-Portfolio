"""
Model Lab - Comprehensive Model Testing & Analysis Interface
=============================================================

Redesigned Model Lab with:
1. Player grouping analysis
2. Archetype performance tracking
3. Defense matchup effectiveness
4. Configuration comparison
5. Interactive testing
6. Detailed statistics visualization
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from .config import ModelV6Config, DEFAULT_CONFIG
from .player_groups import (
    PlayerGroup, 
    PlayerTier, 
    OffensiveStyle,
    ARCHETYPE_GROUPS,
    get_player_group,
    get_players_in_group,
    get_group_summary,
)
from .defense_analysis import (
    DefenseMatchup,
    get_defense_matchup,
    get_team_defense_summary,
    find_best_matchups,
)
from .picks import PropPick, DailyPicks, generate_game_picks
from .backtester import (
    BacktestResult,
    CategoryResult,
    run_backtest,
    quick_backtest,
    compare_configurations,
    generate_backtest_report,
)


@dataclass
class ArchetypeAnalysis:
    """Analysis of a specific archetype's performance."""
    group_key: str
    group_name: str
    description: str
    
    # Players in group
    player_count: int = 0
    example_players: List[str] = field(default_factory=list)
    
    # Performance stats
    total_picks: int = 0
    hits: int = 0
    hit_rate: float = 0.0
    
    # By prop type
    pts_picks: int = 0
    pts_hits: int = 0
    reb_picks: int = 0
    reb_hits: int = 0
    ast_picks: int = 0
    ast_hits: int = 0
    
    # Matchup notes
    best_matchups: List[str] = field(default_factory=list)
    worst_matchups: List[str] = field(default_factory=list)


@dataclass
class DefenseAnalysisReport:
    """Analysis of picks performance by defense quality."""
    # Performance by defense rating
    elite_defense: CategoryResult = field(default_factory=lambda: CategoryResult(name="elite"))
    good_defense: CategoryResult = field(default_factory=lambda: CategoryResult(name="good"))
    average_defense: CategoryResult = field(default_factory=lambda: CategoryResult(name="average"))
    poor_defense: CategoryResult = field(default_factory=lambda: CategoryResult(name="poor"))
    terrible_defense: CategoryResult = field(default_factory=lambda: CategoryResult(name="terrible"))
    
    # Insights
    over_vs_weak_defense: float = 0.0
    under_vs_strong_defense: float = 0.0
    
    # Team rankings
    best_over_targets: List[str] = field(default_factory=list)  # Teams with worst defense
    best_under_targets: List[str] = field(default_factory=list)  # Teams with best defense


@dataclass
class LabExperiment:
    """A single experiment/configuration test."""
    name: str
    config: ModelV6Config
    result: Optional[BacktestResult] = None
    run_time_seconds: float = 0.0


class ModelLab:
    """
    Model Lab - Comprehensive testing and analysis interface.
    
    Usage:
        lab = ModelLab()
        
        # Quick backtest
        result = lab.run_quick_test(days=14)
        print(lab.get_summary(result))
        
        # Analyze archetypes
        archetype_report = lab.analyze_archetypes(result)
        
        # Compare configurations
        comparison = lab.compare_configs([config1, config2])
        
        # Get player group performance
        helio_perf = lab.get_group_performance("heliocentric", result)
    """
    
    def __init__(self, config: ModelV6Config = DEFAULT_CONFIG):
        """Initialize the Model Lab."""
        self.config = config
        self.experiments: List[LabExperiment] = []
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            from ...db import Db
            from ...paths import get_paths
            paths = get_paths()
            db = Db(paths.db_path)
            self._conn = db.connect()
        return self._conn
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    # =========================================================================
    # BACKTESTING METHODS
    # =========================================================================
    
    def run_quick_test(
        self, 
        days: int = 14, 
        verbose: bool = True,
    ) -> BacktestResult:
        """
        Run a quick backtest over recent days.
        
        Args:
            days: Number of days to test
            verbose: Print progress
        
        Returns:
            BacktestResult with all metrics
        """
        return quick_backtest(days=days, config=self.config, verbose=verbose)
    
    def run_full_backtest(
        self,
        start_date: str,
        end_date: str,
        verbose: bool = True,
    ) -> BacktestResult:
        """
        Run a full backtest over a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            verbose: Print progress
        
        Returns:
            BacktestResult
        """
        return run_backtest(start_date, end_date, self.config, verbose)
    
    def run_experiment(
        self,
        name: str,
        config: ModelV6Config,
        start_date: str,
        end_date: str,
        verbose: bool = False,
    ) -> LabExperiment:
        """
        Run a named experiment with a specific configuration.
        
        Args:
            name: Experiment name
            config: Configuration to test
            start_date: Start date
            end_date: End date
            verbose: Print progress
        
        Returns:
            LabExperiment with results
        """
        import time
        start_time = time.time()
        
        result = run_backtest(start_date, end_date, config, verbose)
        
        experiment = LabExperiment(
            name=name,
            config=config,
            result=result,
            run_time_seconds=time.time() - start_time,
        )
        
        self.experiments.append(experiment)
        return experiment
    
    def compare_configs(
        self,
        configs: List[Tuple[str, ModelV6Config]],
        start_date: str,
        end_date: str,
        verbose: bool = True,
    ) -> Dict[str, BacktestResult]:
        """
        Compare multiple configurations.
        
        Args:
            configs: List of (name, config) tuples
            start_date: Start date
            end_date: End date
            verbose: Print progress
        
        Returns:
            Dict mapping name to results
        """
        config_list = [c[1] for c in configs]
        name_list = [c[0] for c in configs]
        
        return compare_configurations(
            configs=config_list,
            config_names=name_list,
            start_date=start_date,
            end_date=end_date,
            verbose=verbose,
        )
    
    # =========================================================================
    # ARCHETYPE ANALYSIS
    # =========================================================================
    
    def analyze_archetypes(
        self,
        backtest_result: BacktestResult,
    ) -> List[ArchetypeAnalysis]:
        """
        Analyze performance by archetype group.
        
        Args:
            backtest_result: Results to analyze
        
        Returns:
            List of ArchetypeAnalysis for each group
        """
        analyses = []
        
        for group_key, group_data in ARCHETYPE_GROUPS.items():
            analysis = ArchetypeAnalysis(
                group_key=group_key,
                group_name=group_data.get("name", group_key),
                description=group_data.get("description", ""),
                example_players=group_data.get("example_players", [])[:5],
            )
            
            # Get stats from backtest
            if group_key in backtest_result.by_archetype:
                cat = backtest_result.by_archetype[group_key]
                analysis.total_picks = cat.total
                analysis.hits = cat.hits
                analysis.hit_rate = cat.hit_rate
            
            # Count players and get prop-specific stats
            for pick in backtest_result.all_picks:
                if pick.archetype_group == group_key and pick.hit is not None:
                    if pick.prop_type == "PTS":
                        analysis.pts_picks += 1
                        if pick.hit:
                            analysis.pts_hits += 1
                    elif pick.prop_type == "REB":
                        analysis.reb_picks += 1
                        if pick.hit:
                            analysis.reb_hits += 1
                    elif pick.prop_type == "AST":
                        analysis.ast_picks += 1
                        if pick.hit:
                            analysis.ast_hits += 1
            
            analyses.append(analysis)
        
        # Sort by hit rate
        analyses.sort(key=lambda a: a.hit_rate, reverse=True)
        
        return analyses
    
    def get_group_performance(
        self,
        group_key: str,
        backtest_result: BacktestResult,
    ) -> Optional[ArchetypeAnalysis]:
        """
        Get detailed performance for a specific archetype group.
        
        Args:
            group_key: Archetype group key
            backtest_result: Results to analyze
        
        Returns:
            ArchetypeAnalysis or None if group not found
        """
        analyses = self.analyze_archetypes(backtest_result)
        
        for analysis in analyses:
            if analysis.group_key == group_key:
                return analysis
        
        return None
    
    def get_archetype_leaderboard(
        self,
        backtest_result: BacktestResult,
        min_picks: int = 10,
    ) -> List[Dict]:
        """
        Get a leaderboard of archetypes sorted by performance.
        
        Args:
            backtest_result: Results to analyze
            min_picks: Minimum picks to include
        
        Returns:
            List of dicts with archetype performance
        """
        analyses = self.analyze_archetypes(backtest_result)
        
        leaderboard = []
        for analysis in analyses:
            if analysis.total_picks >= min_picks:
                leaderboard.append({
                    "rank": len(leaderboard) + 1,
                    "group": analysis.group_name,
                    "key": analysis.group_key,
                    "picks": analysis.total_picks,
                    "hits": analysis.hits,
                    "hit_rate": f"{analysis.hit_rate*100:.1f}%",
                    "pts_rate": f"{analysis.pts_hits/analysis.pts_picks*100:.1f}%" if analysis.pts_picks else "N/A",
                    "reb_rate": f"{analysis.reb_hits/analysis.reb_picks*100:.1f}%" if analysis.reb_picks else "N/A",
                    "ast_rate": f"{analysis.ast_hits/analysis.ast_picks*100:.1f}%" if analysis.ast_picks else "N/A",
                })
        
        return leaderboard
    
    # =========================================================================
    # DEFENSE ANALYSIS
    # =========================================================================
    
    def analyze_defense_performance(
        self,
        backtest_result: BacktestResult,
    ) -> DefenseAnalysisReport:
        """
        Analyze performance by defense matchup quality.
        
        Args:
            backtest_result: Results to analyze
        
        Returns:
            DefenseAnalysisReport with insights
        """
        report = DefenseAnalysisReport()
        
        # Populate from backtest
        defense_map = {
            "elite": report.elite_defense,
            "good": report.good_defense,
            "average": report.average_defense,
            "poor": report.poor_defense,
            "terrible": report.terrible_defense,
        }
        
        for key, cat in backtest_result.by_defense_quality.items():
            if key in defense_map:
                defense_map[key].total = cat.total
                defense_map[key].hits = cat.hits
        
        # Calculate insights
        # OVER vs weak defense (poor + terrible)
        weak_over = []
        strong_under = []
        
        for pick in backtest_result.all_picks:
            if pick.hit is not None:
                if pick.defense_rating in ("poor", "terrible") and pick.direction == "OVER":
                    weak_over.append(pick.hit)
                elif pick.defense_rating in ("elite", "good") and pick.direction == "UNDER":
                    strong_under.append(pick.hit)
        
        report.over_vs_weak_defense = sum(weak_over) / len(weak_over) if weak_over else 0.0
        report.under_vs_strong_defense = sum(strong_under) / len(strong_under) if strong_under else 0.0
        
        return report
    
    def get_defense_leaderboard(
        self,
        backtest_result: BacktestResult,
    ) -> List[Dict]:
        """
        Get defense matchup performance leaderboard.
        
        Args:
            backtest_result: Results to analyze
        
        Returns:
            List of defense quality performance stats
        """
        report = self.analyze_defense_performance(backtest_result)
        
        leaderboard = []
        for name, cat in [
            ("Terrible Defense", report.terrible_defense),
            ("Poor Defense", report.poor_defense),
            ("Average Defense", report.average_defense),
            ("Good Defense", report.good_defense),
            ("Elite Defense", report.elite_defense),
        ]:
            if cat.total > 0:
                leaderboard.append({
                    "defense": name,
                    "picks": cat.total,
                    "hits": cat.hits,
                    "hit_rate": f"{cat.hit_rate*100:.1f}%",
                })
        
        return leaderboard
    
    # =========================================================================
    # PLAYER ANALYSIS
    # =========================================================================
    
    def get_player_tier_performance(
        self,
        backtest_result: BacktestResult,
    ) -> List[Dict]:
        """
        Get performance breakdown by player tier.
        
        Args:
            backtest_result: Results to analyze
        
        Returns:
            List of tier performance stats
        """
        tier_names = {
            1: "MVP Candidates",
            2: "All-Stars", 
            3: "Quality Starters",
            4: "Role Players",
            5: "Specialists",
            6: "Bench Players",
        }
        
        results = []
        for tier in sorted(backtest_result.by_player_tier.keys()):
            cat = backtest_result.by_player_tier[tier]
            if cat.total >= 5:
                results.append({
                    "tier": tier,
                    "name": tier_names.get(tier, f"Tier {tier}"),
                    "picks": cat.total,
                    "hits": cat.hits,
                    "hit_rate": f"{cat.hit_rate*100:.1f}%",
                })
        
        return results
    
    def get_top_players(
        self,
        backtest_result: BacktestResult,
        min_picks: int = 5,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Get top performing players from backtest.
        
        Args:
            backtest_result: Results to analyze
            min_picks: Minimum picks to include
            limit: Max players to return
        
        Returns:
            List of player performance stats
        """
        # Aggregate by player
        player_stats: Dict[str, Dict] = {}
        
        for pick in backtest_result.all_picks:
            if pick.hit is None:
                continue
            
            name = pick.player_name
            if name not in player_stats:
                player_stats[name] = {
                    "name": name,
                    "team": pick.team_abbrev,
                    "tier": pick.player_tier,
                    "picks": 0,
                    "hits": 0,
                }
            
            player_stats[name]["picks"] += 1
            if pick.hit:
                player_stats[name]["hits"] += 1
        
        # Calculate hit rates and filter
        players = []
        for stats in player_stats.values():
            if stats["picks"] >= min_picks:
                stats["hit_rate"] = stats["hits"] / stats["picks"]
                players.append(stats)
        
        # Sort by hit rate
        players.sort(key=lambda p: p["hit_rate"], reverse=True)
        
        # Format for output
        return [
            {
                "player": p["name"],
                "team": p["team"],
                "tier": p["tier"],
                "picks": p["picks"],
                "hits": p["hits"],
                "hit_rate": f"{p['hit_rate']*100:.1f}%",
            }
            for p in players[:limit]
        ]
    
    # =========================================================================
    # REPORTING
    # =========================================================================
    
    def get_summary(self, result: BacktestResult) -> str:
        """Get text summary of backtest results."""
        return result.summary()
    
    def get_full_report(self, result: BacktestResult) -> str:
        """Get markdown report of backtest results."""
        return generate_backtest_report(result)
    
    def get_experiment_summary(self) -> str:
        """Get summary of all experiments run."""
        if not self.experiments:
            return "No experiments run yet."
        
        lines = [
            "=" * 60,
            "MODEL LAB EXPERIMENT SUMMARY",
            "=" * 60,
            "",
        ]
        
        for exp in self.experiments:
            if exp.result:
                lines.append(f"{exp.name}:")
                lines.append(f"  Hit Rate: {exp.result.overall_hit_rate*100:.1f}%")
                lines.append(f"  HIGH:     {exp.result.high_hit_rate*100:.1f}%")
                lines.append(f"  Runtime:  {exp.result.run_time_seconds:.1f}s")
                lines.append("")
        
        return "\n".join(lines)
    
    # =========================================================================
    # PRESET CONFIGURATIONS FOR TESTING
    # =========================================================================
    
    @staticmethod
    def get_preset_configs() -> List[Tuple[str, ModelV6Config]]:
        """
        Get preset configurations for comparison testing.
        
        Returns:
            List of (name, config) tuples
        """
        configs = [
            ("Default", ModelV6Config()),
            
            # Defense-Heavy
            ("Defense-Heavy", ModelV6Config(
                elite_defense_adjustment=0.12,
                good_defense_adjustment=0.06,
                poor_defense_adjustment=0.06,
                terrible_defense_adjustment=0.12,
            )),
            
            # Trend-Heavy
            ("Trend-Heavy", ModelV6Config(
                hot_streak_boost=0.06,
                cold_streak_penalty=0.06,
                hot_streak_threshold=12.0,
                cold_streak_threshold=-12.0,
            )),
            
            # Star-Focused
            ("Star-Focused", ModelV6Config(
                star_player_defense_dampening=0.4,  # Less defense impact on stars
                min_minutes_threshold=28.0,
            )),
            
            # Conservative
            ("Conservative", ModelV6Config(
                min_edge_threshold=8.0,
                medium_edge_threshold=12.0,
                high_edge_threshold=18.0,
                high_confidence_min=78.0,
            )),
            
            # Aggressive
            ("Aggressive", ModelV6Config(
                min_edge_threshold=5.0,
                medium_edge_threshold=7.0,
                high_edge_threshold=11.0,
                high_confidence_min=65.0,
            )),
        ]
        
        return configs
    
    def run_all_presets(
        self,
        start_date: str,
        end_date: str,
        verbose: bool = True,
    ) -> Dict[str, BacktestResult]:
        """
        Run all preset configurations.
        
        Args:
            start_date: Start date
            end_date: End date
            verbose: Print progress
        
        Returns:
            Dict of results by preset name
        """
        presets = self.get_preset_configs()
        return self.compare_configs(presets, start_date, end_date, verbose)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def run_model_lab(
    days: int = 14,
    verbose: bool = True,
) -> Tuple[ModelLab, BacktestResult]:
    """
    Quick convenience function to run the model lab.
    
    Args:
        days: Number of days to backtest
        verbose: Print progress
    
    Returns:
        (ModelLab instance, BacktestResult)
    """
    lab = ModelLab()
    result = lab.run_quick_test(days=days, verbose=verbose)
    
    if verbose:
        print("\n" + lab.get_summary(result))
        print("\nArchetype Leaderboard:")
        for entry in lab.get_archetype_leaderboard(result):
            print(f"  {entry['rank']}. {entry['group']}: {entry['hit_rate']} ({entry['picks']} picks)")
    
    return lab, result

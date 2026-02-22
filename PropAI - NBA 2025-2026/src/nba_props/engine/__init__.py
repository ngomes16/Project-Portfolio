"""
NBA Props Projection Engine - "The Edge Engine"
================================================

This module contains the core prediction and analysis logic for NBA player props.

Model Name: "The Edge Engine"

Architecture:
-------------
1. Data Validation Layer - Check data freshness and quality
2. Minutes Projection Layer - Project playing time (minutes-first approach)
3. Per-Minute Rate Layer - Calculate production rates
4. Matchup Adjustment Layer - Apply defense and context factors
5. Probability & Edge Layer - Calculate betting edges
6. Recommendation Filter Layer - Filter and rank picks

Submodules:
-----------
- **edge_engine**: Main orchestrator (NEW - recommended entry point)
- **projector**: Core player projection calculations
- **minutes_projection**: Minutes-first projection with context adjustments (NEW)
- **game_context**: Game context data (B2B status, team defense ratings)
- **edge_calculator**: Prop bet edge and probability calculations
- **matchup_advisor**: Advanced defense metrics and ADVISOR reports
- **under_picks_analyzer**: Separate UNDER picks model
- **archetypes**: Player archetype definitions
- **usage_redistribution**: Usage rate calculations when stars are out
- **accuracy_tracker**: Historical prediction tracking and calibration (NEW)
- **alerts**: Edge alert scanning system
- **backtesting**: Historical accuracy testing

Main Entry Points:
-----------------
For full matchup analysis using The Edge Engine (RECOMMENDED):
    >>> from nba_props.engine import analyze_matchup, quick_edge_check
    >>> slate = analyze_matchup(conn, "LAL", "BOS", "2026-01-03")
    >>> for pick in slate.high_confidence_picks:
    ...     print(f"{pick.player_name} {pick.prop_type} {pick.direction}")

For comprehensive matchup report:
    >>> from nba_props.engine import generate_comprehensive_matchup_report
    >>> report = generate_comprehensive_matchup_report(conn, "LAL", "BOS", "2026-01-03")

For quick single-prop check:
    >>> edge = quick_edge_check(conn, "LeBron James", "PTS", 24.5, "BOS", "2026-01-03")
    >>> if edge and edge.is_actionable:
    ...     print(f"Edge: {edge.edge_pct}% on {edge.direction}")

For minutes-first projection:
    >>> from nba_props.engine import project_player_minutes_first
    >>> projection = project_player_minutes_first(conn, player_id, game_context)
"""
from .projector import (
    PlayerProjection,
    ProjectionConfig,
    project_player_stats,
    project_team_players,
)
from .game_context import (
    BackToBackStatus,
    get_back_to_back_status,
    get_team_defense_rating,
    get_all_team_defense_ratings,
    apply_matchup_adjustments,
    MatchupRecommendation,
    get_position_defense_rating,
    get_player_vs_team_history,
    generate_matchup_recommendations,
)
from .edge_calculator import (
    PropEdge,
    calculate_prop_edge,
    rank_prop_opportunities,
    generate_prop_report,
)
from .matchup_advisor import (
    # Data classes for defense analysis
    PositionDefenseProfile,
    ArchetypeDefenseProfile,
    PlayerVsTeamProfile,
    PlayerTrend,
    MatchupEdge,
    ComprehensiveMatchupReport,
    # Position-based defense functions
    get_position_defense_profile,
    get_all_position_defense_profiles,
    rank_position_defense_profiles,
    # Player analysis functions
    get_player_vs_team_profile,
    get_player_trend,
    # Edge calculation
    calculate_matchup_edge,
    # Team defense summary
    get_team_defense_summary,
    # MAIN ADVISOR FUNCTION
    generate_comprehensive_matchup_report,
)
from .usage_redistribution import (
    PlayerUsageProfile,
    UsageRedistributionResult,
    get_team_usage_profiles,
    calculate_usage_redistribution,
    get_historical_impact,
    get_usage_boost_for_player,
    get_team_usage_boosts,
    UsageBoost,
)

# New modules
from .edge_engine import (
    EdgeResult,
    SlateRecommendation,
    DataQualityReport,
    analyze_matchup,
    quick_edge_check,
    analyze_and_track,
    validate_data_quality,
    get_projection_with_context,
    calculate_edge_for_prop,
    filter_and_rank_picks,
)
from .minutes_projection import (
    MinutesProjection,
    PerMinuteRates,
    FullStatProjection,
    project_minutes,
    calculate_per_minute_rates,
    project_full_stat_line,
    project_player_minutes_first,
)
from .accuracy_tracker import (
    PredictionRecord,
    AccuracyReport,
    CalibrationBucket,
    FactorPerformance,
    create_tracking_tables,
    record_prediction,
    update_prediction_outcome,
    batch_update_outcomes,
    generate_accuracy_report,
    analyze_factor_performance,
    get_recommended_confidence_adjustment,
    get_player_prediction_history,
    get_recent_hit_rate,
)

__all__ = [
    # Projector
    "PlayerProjection",
    "ProjectionConfig",
    "project_player_stats",
    "project_team_players",
    # Game Context (B2B, defense ratings)
    "BackToBackStatus",
    "get_back_to_back_status",
    "get_team_defense_rating",
    "get_all_team_defense_ratings",
    "apply_matchup_adjustments",
    "MatchupRecommendation",
    "get_position_defense_rating",
    "get_player_vs_team_history",
    "generate_matchup_recommendations",
    # Edge Calculator
    "PropEdge",
    "calculate_prop_edge",
    "rank_prop_opportunities",
    "generate_prop_report",
    # Matchup Advisor (MAIN OUTPUT)
    "PositionDefenseProfile",
    "ArchetypeDefenseProfile",
    "PlayerVsTeamProfile",
    "PlayerTrend",
    "MatchupEdge",
    "ComprehensiveMatchupReport",
    "get_position_defense_profile",
    "get_all_position_defense_profiles",
    "rank_position_defense_profiles",
    "get_player_vs_team_profile",
    "get_player_trend",
    "calculate_matchup_edge",
    "get_team_defense_summary",
    "generate_comprehensive_matchup_report",
    # Usage Redistribution
    "PlayerUsageProfile",
    "UsageRedistributionResult",
    "UsageBoost",
    "get_team_usage_profiles",
    "calculate_usage_redistribution",
    "get_historical_impact",
    "get_usage_boost_for_player",
    "get_team_usage_boosts",
    # Edge Engine (NEW - Main Entry Point)
    "EdgeResult",
    "SlateRecommendation",
    "DataQualityReport",
    "analyze_matchup",
    "quick_edge_check",
    "analyze_and_track",
    "validate_data_quality",
    "get_projection_with_context",
    "calculate_edge_for_prop",
    "filter_and_rank_picks",
    # Minutes Projection (NEW)
    "MinutesProjection",
    "PerMinuteRates",
    "FullStatProjection",
    "project_minutes",
    "calculate_per_minute_rates",
    "project_full_stat_line",
    "project_player_minutes_first",
    # Accuracy Tracking (NEW)
    "PredictionRecord",
    "AccuracyReport",
    "CalibrationBucket",
    "FactorPerformance",
    "create_tracking_tables",
    "record_prediction",
    "update_prediction_outcome",
    "batch_update_outcomes",
    "generate_accuracy_report",
    "analyze_factor_performance",
    "get_recommended_confidence_adjustment",
    "get_player_prediction_history",
    "get_recent_hit_rate",
]

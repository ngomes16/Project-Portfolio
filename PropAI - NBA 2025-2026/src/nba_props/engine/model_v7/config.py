"""
Model V7 Configuration - Ensemble Model
========================================

Combines the best insights from all previous models:
- V2: OVER focus, L15 emphasis
- V3: Stat-specific weights, floor/ceiling
- V4: Value scoring, prop type balance
- V5: H2H data, defense vs position, momentum (L3)
- V6: Archetype analysis, UNDER outperformance
- Final: Simple but effective confidence scoring

KEY INSIGHTS INTEGRATED:
------------------------
1. UNDER picks outperform (V6: 61% vs 56.3%)
2. Certain archetypes are more predictable (Stretch Bigs, Traditional Bigs)
3. Scoring Guards are unpredictable - reduce weight or avoid
4. Starter tier is most predictable (65.4%)
5. H2H data adds significant value
6. Defense vs position is crucial
7. Trend alignment with direction matters

APPROACH: Multi-Signal Voting with Confidence Weighting
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple, List, Optional


# ============================================================================
# ARCHETYPE RELIABILITY SCORES
# ============================================================================
# Based on V6 backtest: higher score = more predictable
ARCHETYPE_RELIABILITY: Dict[str, float] = {
    "stretch_bigs": 1.15,           # 64.9% hit rate - boost
    "corner_specialists": 1.14,     # 64.0% hit rate
    "traditional_bigs": 1.14,       # 64.0% hit rate
    "movement_shooters": 1.10,      # 62.5% hit rate
    "heliocentric": 1.08,           # 61.6% hit rate
    "slashers": 1.03,               # 58.3% - near average
    "hub_bigs": 0.97,               # 56.7% - below average
    "two_way_wings": 0.97,          # 56.7% - below average
    "scoring_guards": 0.90,         # 51.5% - AVOID
}

# Player tiers by reliability (from V6 backtest)
TIER_RELIABILITY: Dict[int, float] = {
    3: 1.10,    # Starter tier - 65.4% hit rate (most predictable)
    1: 1.05,    # MVP - 61.4% hit rate
    4: 1.03,    # Role Player - 59.6% hit rate
    5: 1.00,    # Specialist - 58.4% hit rate
    6: 0.95,    # Bench - 55.4% hit rate
    2: 0.92,    # All-Star - 51.7% hit rate (high variance)
}


@dataclass
class ModelV7Config:
    """
    Ensemble Model Configuration combining best features from all models.
    """
    
    # =========================================================================
    # PROJECTION WEIGHTS BY STAT TYPE
    # =========================================================================
    # From V5's momentum analysis + V2/V3's stability weights
    # Format: (L3_weight, L5_weight, L10_weight, L20_weight, Season_weight)
    
    # Points: Balance recent form with season baseline
    pts_weights: Tuple[float, float, float, float, float] = (
        0.10,  # L3: Light momentum
        0.20,  # L5: Recent form
        0.30,  # L10: Baseline
        0.20,  # L20: Medium-term
        0.20,  # Season: Stability
    )
    
    # Rebounds: More season weight (more consistent stat)
    reb_weights: Tuple[float, float, float, float, float] = (
        0.05,  # L3
        0.15,  # L5
        0.25,  # L10
        0.25,  # L20
        0.30,  # Season
    )
    
    # Assists: Recent form matters more
    ast_weights: Tuple[float, float, float, float, float] = (
        0.10,  # L3
        0.25,  # L5
        0.30,  # L10
        0.20,  # L20
        0.15,  # Season
    )
    
    # =========================================================================
    # DIRECTION PREFERENCE (KEY INSIGHT FROM V6)
    # =========================================================================
    # UNDER picks hit at 61% vs 56.3% for OVER in V6
    under_preference_weight: float = 1.08  # Slight boost to UNDER picks
    over_preference_weight: float = 0.96   # Slight penalty to OVER picks
    
    # When to prefer UNDER vs OVER
    prefer_under_when_elite_defense: bool = True    # 64% hit rate
    prefer_under_when_cold_streak: bool = True
    prefer_over_when_terrible_defense: bool = True  # 54% - less reliable
    
    # =========================================================================
    # DEFENSE ADJUSTMENT BY QUALITY (From V6 optimized)
    # =========================================================================
    # Elite defense boosts UNDER confidence
    elite_defense_adjustment: float = 0.12      # 12% reduction for OVER
    good_defense_adjustment: float = 0.06       # 6% reduction
    avg_defense_adjustment: float = 0.0         # No adjustment
    poor_defense_adjustment: float = 0.06       # 6% boost
    terrible_defense_adjustment: float = 0.12   # 12% boost
    
    # Star players are more matchup-proof (V6 insight)
    star_player_defense_dampening: float = 0.60
    
    # =========================================================================
    # HEAD-TO-HEAD WEIGHTING (From V5)
    # =========================================================================
    h2h_enabled: bool = True
    h2h_min_games: int = 2                      # Need at least 2 H2H games
    h2h_weight: float = 0.25                    # 25% weight when available
    h2h_max_lookback_days: int = 365            # Only consider last year
    
    # =========================================================================
    # TREND DETECTION
    # =========================================================================
    hot_streak_threshold: float = 15.0          # % above L10
    cold_streak_threshold: float = -15.0        # % below L10
    
    # V6 finding: Trend alignment with direction is crucial
    trend_aligned_boost: float = 0.05           # 5% when trend matches direction
    trend_opposed_penalty: float = 0.07         # 7% penalty when opposed
    
    # =========================================================================
    # ARCHETYPE-SPECIFIC ADJUSTMENTS (From V6)
    # =========================================================================
    # Avoid scoring guards entirely?
    filter_scoring_guards: bool = True          # They hit at only 51.5%
    scoring_guard_confidence_penalty: int = 15  # Or just penalize confidence
    
    # Boost predictable archetypes
    use_archetype_reliability: bool = True
    
    # =========================================================================
    # PLAYER TIER FILTERING (From V6)
    # =========================================================================
    # Starter tier (3) is most predictable at 65.4%
    boost_starter_tier: bool = True
    starter_tier_boost: int = 8                 # +8 confidence points
    
    # All-Star tier (2) is least predictable at 51.7%
    penalize_allstar_tier: bool = True
    allstar_tier_penalty: int = 10              # -10 confidence points
    
    # =========================================================================
    # EDGE THRESHOLDS
    # =========================================================================
    min_edge_threshold: float = 6.0             # Minimum to consider
    medium_edge_threshold: float = 10.0
    high_edge_threshold: float = 14.0
    
    # =========================================================================
    # CONFIDENCE SCORING (Multi-Factor)
    # =========================================================================
    # Total: 100 points possible
    edge_max_score: int = 20                    # Points for edge size
    defense_matchup_max_score: int = 20         # Defense quality
    consistency_max_score: int = 15             # Low variance
    trend_alignment_max_score: int = 15         # Trend matches direction
    h2h_max_score: int = 10                     # Head-to-head history
    archetype_max_score: int = 10               # Archetype reliability
    tier_max_score: int = 10                    # Player tier
    
    # Confidence tier thresholds (raised for selectivity)
    high_confidence_min: float = 75.0           # Was 72 in V6
    medium_confidence_min: float = 60.0         # Was 55 in V6
    
    # =========================================================================
    # PICK SELECTION
    # =========================================================================
    picks_per_game: int = 3                     # Target 3 per game
    max_picks_per_player: int = 2               # Max 2 props per player
    min_minutes_threshold: float = 22.0
    min_games_required: int = 7
    star_minutes_threshold: float = 28.0
    
    # Minimum line thresholds (avoid trivial picks)
    min_pts_line: float = 8.0
    min_reb_line: float = 3.0
    min_ast_line: float = 3.5                   # Raised from V4
    
    # =========================================================================
    # CONSISTENCY THRESHOLDS
    # =========================================================================
    very_consistent_cv: float = 0.15            # CV below this = very consistent
    consistent_cv: float = 0.22
    volatile_cv: float = 0.35
    
    # =========================================================================
    # BACK-TO-BACK ADJUSTMENTS
    # =========================================================================
    b2b_penalty: float = 0.05                   # 5% reduction
    rest_bonus: float = 0.02                    # 2% boost for 2+ days rest
    
    # =========================================================================
    # ENSEMBLE VOTING WEIGHTS
    # =========================================================================
    # Counter-intuitive finding: 1-signal picks hit at 78.7%!
    # This suggests that extreme agreement may indicate overfit/noise
    multi_signal_agreement_boost: int = 10      # +10 when 3+ factors agree
    
    # NEW: Prefer picks with fewer signals (1 signal = 78.7% hit rate!)
    prefer_low_signal_count: bool = False       # Enable to prefer 1-2 signals
    low_signal_bonus: int = 15                  # +15 for 1-signal picks
    medium_signal_bonus: int = 5                # +5 for 2-signal picks
    high_signal_penalty: int = 5                # -5 for 3+ signal picks
    
    # =========================================================================
    # DEFENSE QUALITY FILTER
    # =========================================================================
    # GOOD/AVERAGE defense -> 71.4% hit rate; ELITE -> 64.7%
    prefer_mid_tier_defense: bool = False       # Filter to GOOD/AVERAGE defense
    exclude_terrible_defense: bool = False      # Exclude TERRIBLE (49%)
    
    # =========================================================================
    # ARCHETYPE FILTER
    # =========================================================================
    # Filter out consistently bad archetypes
    exclude_hub_bigs: bool = False              # 14.3% hit rate!
    exclude_slashers: bool = False              # 41.7% hit rate
    
    def get_weights(self, prop_type: str) -> Tuple[float, float, float, float, float]:
        """Get weights for a specific prop type (L3, L5, L10, L20, Season)."""
        pt = prop_type.upper()
        if pt == "PTS":
            return self.pts_weights
        elif pt == "REB":
            return self.reb_weights
        else:
            return self.ast_weights
    
    def get_defense_adjustment(self, rating: str) -> float:
        """Get defense adjustment based on rating."""
        rating = rating.lower()
        if rating == "elite":
            return -self.elite_defense_adjustment
        elif rating == "good":
            return -self.good_defense_adjustment
        elif rating == "poor":
            return self.poor_defense_adjustment
        elif rating == "terrible":
            return self.terrible_defense_adjustment
        return self.avg_defense_adjustment
    
    def get_archetype_reliability(self, archetype: str) -> float:
        """Get reliability multiplier for archetype."""
        archetype = archetype.lower().replace(" ", "_")
        return ARCHETYPE_RELIABILITY.get(archetype, 1.0)
    
    def get_tier_reliability(self, tier: int) -> float:
        """Get reliability multiplier for player tier."""
        return TIER_RELIABILITY.get(tier, 1.0)
    
    def get_min_line(self, prop_type: str) -> float:
        """Get minimum line for prop type."""
        pt = prop_type.upper()
        if pt == "PTS":
            return self.min_pts_line
        elif pt == "REB":
            return self.min_reb_line
        return self.min_ast_line


# Default configuration
DEFAULT_CONFIG = ModelV7Config()


# Alternative configurations for testing
UNDER_FOCUS_CONFIG = ModelV7Config(
    under_preference_weight=1.12,
    over_preference_weight=0.92,
    prefer_under_when_elite_defense=True,
    prefer_under_when_cold_streak=True,
)

CONSERVATIVE_CONFIG = ModelV7Config(
    min_edge_threshold=8.0,
    high_confidence_min=80.0,
    medium_confidence_min=65.0,
    picks_per_game=2,
)

AGGRESSIVE_CONFIG = ModelV7Config(
    min_edge_threshold=5.0,
    high_confidence_min=70.0,
    medium_confidence_min=55.0,
    picks_per_game=4,
)

# =============================================================================
# OPTIMIZED CONFIGURATION - Based on backtesting insights
# =============================================================================
# Key findings:
# - 1-signal picks: 78.7% hit rate
# - UNDER picks: 68.1% hit rate  
# - GOOD/AVERAGE defense: 71.4% hit rate
# - hub_bigs: 14.3% (avoid)
# - slashers: 41.7% (avoid)
# - heliocentric: 64.7%
# - stretch_bigs: 60.6%

OPTIMIZED_CONFIG = ModelV7Config(
    # Higher edge thresholds for quality picks
    min_edge_threshold=11.0,
    medium_edge_threshold=14.0,
    high_edge_threshold=18.0,
    
    # Higher confidence thresholds
    high_confidence_min=76.0,
    medium_confidence_min=65.0,
    
    # UNDER preference (68.1% vs 49.1%)
    under_preference_weight=1.12,
    over_preference_weight=0.90,
    
    # Prefer low signal count (78.7% hit rate!)
    prefer_low_signal_count=True,
    low_signal_bonus=15,
    medium_signal_bonus=5,
    high_signal_penalty=5,
    
    # Exclude bad archetypes
    exclude_hub_bigs=True,
    exclude_slashers=True,
    
    # Defense filtering (GOOD/AVG = 71.4%)
    exclude_terrible_defense=True,
    
    # Picks per game
    picks_per_game=3,
    max_picks_per_player=2,
)

# More aggressive but still quality-focused
OPTIMIZED_AGGRESSIVE_CONFIG = ModelV7Config(
    min_edge_threshold=9.0,
    medium_edge_threshold=12.0,
    high_edge_threshold=16.0,
    
    high_confidence_min=74.0,
    medium_confidence_min=62.0,
    
    under_preference_weight=1.10,
    over_preference_weight=0.92,
    
    prefer_low_signal_count=True,
    low_signal_bonus=12,
    medium_signal_bonus=4,
    high_signal_penalty=3,
    
    exclude_hub_bigs=True,
    exclude_slashers=True,
    
    picks_per_game=4,
)

# =============================================================================
# BEST PERFORMING CONFIGURATIONS - Verified backtesting results
# =============================================================================

# ELITE CONFIG - 86.7% HIGH confidence, 61.8% overall
# Best for: Premium picks with very high accuracy
# Trade-off: Lower volume (30 HIGH confidence picks over 42 days)
ELITE_CONFIG = ModelV7Config(
    min_edge_threshold=12.0,
    high_confidence_min=85.0,
    medium_confidence_min=72.0,
    
    under_preference_weight=1.15,
    over_preference_weight=0.88,
    
    prefer_low_signal_count=True,
    low_signal_bonus=20,
    medium_signal_bonus=8,
    high_signal_penalty=10,
    
    exclude_hub_bigs=True,
    exclude_slashers=True,
    filter_scoring_guards=True,
    scoring_guard_confidence_penalty=35,
    
    exclude_terrible_defense=True,
    
    boost_starter_tier=True,
    starter_tier_boost=15,
    penalize_allstar_tier=True,
    allstar_tier_penalty=22,
    
    picks_per_game=2,
)

# BALANCED CONFIG - 70% HIGH confidence, 63.4% overall
# Best for: Good balance of accuracy and volume
# Good for: Daily betting with reasonable pick counts
BALANCED_CONFIG = ModelV7Config(
    min_edge_threshold=12.0,
    high_confidence_min=80.0,
    medium_confidence_min=68.0,
    
    under_preference_weight=1.25,
    over_preference_weight=0.80,
    
    prefer_low_signal_count=True,
    low_signal_bonus=15,
    
    exclude_hub_bigs=True,
    exclude_slashers=True,
    exclude_terrible_defense=True,
    
    elite_defense_adjustment=0.20,
    good_defense_adjustment=0.12,
    
    picks_per_game=2,
)

# VOLUME CONFIG - 82.9% HIGH confidence, 61.2% overall, more picks
# Best for: When you want more picks but still high quality
VOLUME_CONFIG = ModelV7Config(
    min_edge_threshold=10.0,
    high_confidence_min=82.0,
    medium_confidence_min=68.0,
    
    under_preference_weight=1.12,
    over_preference_weight=0.90,
    
    prefer_low_signal_count=True,
    low_signal_bonus=18,
    medium_signal_bonus=6,
    high_signal_penalty=8,
    
    exclude_hub_bigs=True,
    exclude_slashers=True,
    filter_scoring_guards=True,
    scoring_guard_confidence_penalty=30,
    
    use_archetype_reliability=True,
    exclude_terrible_defense=True,
    
    boost_starter_tier=True,
    starter_tier_boost=12,
    penalize_allstar_tier=True,
    allstar_tier_penalty=18,
    
    picks_per_game=3,
)

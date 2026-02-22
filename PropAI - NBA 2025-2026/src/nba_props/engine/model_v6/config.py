"""
Model V6 Configuration
======================

Centralized configuration for the Model V6 prediction system.
All parameters are organized by category and documented.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple, List


@dataclass
class ModelV6Config:
    """
    Configuration for Model V6 - Archetype-Aware Defense-Focused Model.
    
    This configuration emphasizes:
    1. Defense matchup quality
    2. Player archetype-based adjustments
    3. Tier-specific weighting
    """
    
    # =========================================================================
    # PROJECTION WEIGHTS BY STAT TYPE
    # =========================================================================
    # Format: (L5_weight, L10_weight, L20_weight, Season_weight)
    # These determine how much recent vs historical data matters
    
    pts_weights: Tuple[float, float, float, float] = (0.25, 0.25, 0.30, 0.20)
    reb_weights: Tuple[float, float, float, float] = (0.20, 0.25, 0.30, 0.25)
    ast_weights: Tuple[float, float, float, float] = (0.25, 0.30, 0.25, 0.20)
    
    # =========================================================================
    # DEFENSE ADJUSTMENT STRENGTH BY DEFENSE QUALITY
    # =========================================================================
    # How much to adjust projection based on opponent defense rating
    # Format: defense_rating -> adjustment_multiplier_range
    
    # Elite defense (rank 1-5): Reduce projection
    elite_defense_adjustment: float = 0.12   # 12% reduction (optimized)
    
    # Good defense (rank 6-10): Slight reduction
    good_defense_adjustment: float = 0.06   # 6% reduction
    
    # Average defense (rank 11-20): No adjustment
    avg_defense_adjustment: float = 0.0
    
    # Poor defense (rank 21-25): Slight boost
    poor_defense_adjustment: float = 0.06   # 6% boost
    
    # Terrible defense (rank 26-30): Boost projection  
    terrible_defense_adjustment: float = 0.12  # 12% boost (optimized)
    
    # =========================================================================
    # ARCHETYPE-SPECIFIC ADJUSTMENTS
    # =========================================================================
    # Some archetypes perform better/worse against certain defense types
    
    # Heliocentric creators struggle vs elite POA defense
    heliocentric_vs_elite_defense: float = -0.05  # Additional 5% penalty
    
    # Slashers struggle vs rim protectors
    slasher_vs_anchor_big: float = -0.04  # 4% penalty
    
    # Movement shooters excel vs poor perimeter D
    movement_shooter_vs_poor_chase: float = 0.05  # 5% boost
    
    # Hub bigs excel vs poor interior D
    hub_big_vs_poor_interior: float = 0.05  # 5% boost
    
    # Stretch bigs struggle vs mobile defenses
    stretch_big_vs_switch_defense: float = -0.03  # 3% penalty
    
    # =========================================================================
    # TIER-SPECIFIC CONFIGURATION
    # =========================================================================
    # Different tiers may need different treatment
    
    # Tier 1-2 players are more matchup-proof
    star_player_defense_dampening: float = 0.6  # Apply only 60% of defense adj
    
    # Tier 5-6 players are more volatile
    role_player_consistency_penalty: float = 0.85  # Reduce confidence by 15%
    
    # =========================================================================
    # TREND DETECTION
    # =========================================================================
    
    hot_streak_threshold: float = 15.0    # % above L15 to be considered hot
    cold_streak_threshold: float = -15.0  # % below L15 to be considered cold
    hot_streak_boost: float = 0.04        # 4% boost for hot streak
    cold_streak_penalty: float = 0.04     # 4% penalty for cold streak
    
    # Trend alignment bonus (when streak matches direction)
    trend_alignment_confidence_bonus: int = 10
    
    # =========================================================================
    # EDGE THRESHOLDS
    # =========================================================================
    
    min_edge_threshold: float = 6.0       # Minimum edge to consider
    medium_edge_threshold: float = 9.0    # Medium confidence threshold
    high_edge_threshold: float = 14.0     # High confidence threshold
    
    # =========================================================================
    # CONFIDENCE SCORING WEIGHTS
    # =========================================================================
    # Total possible: 100 points
    
    edge_max_score: int = 25              # Points for edge size
    defense_matchup_max_score: int = 20   # Points for favorable matchup
    consistency_max_score: int = 20       # Points for low variance
    trend_max_score: int = 15             # Points for trend alignment
    sample_size_max_score: int = 10       # Points for games played
    archetype_match_max_score: int = 10   # Points for favorable archetype
    
    # =========================================================================
    # CONFIDENCE TIERS
    # =========================================================================
    
    high_confidence_min: float = 72.0
    medium_confidence_min: float = 55.0
    
    # =========================================================================
    # PICK SELECTION
    # =========================================================================
    
    picks_per_game: int = 4               # Target picks per game
    max_picks_per_player: int = 2         # Max props per player
    min_minutes_threshold: float = 22.0   # Minimum average minutes
    min_games_required: int = 7           # Minimum games played
    
    # =========================================================================
    # PLAYER FILTERING
    # =========================================================================
    
    # Assist props: Only for players averaging this many assists
    min_ast_for_ast_props: float = 4.0
    
    # Star player threshold: Auto-considered for all props
    star_player_min_minutes: float = 30.0
    
    # =========================================================================
    # BACK-TO-BACK ADJUSTMENTS
    # =========================================================================
    
    b2b_second_game_penalty: float = 0.05  # 5% reduction
    rest_advantage_boost: float = 0.02     # 2% boost for 2+ days rest
    
    # =========================================================================
    # CONSISTENCY THRESHOLDS (Coefficient of Variation)
    # =========================================================================
    
    very_consistent_cv: float = 0.18      # CV < 18% = very consistent
    consistent_cv: float = 0.25           # CV < 25% = consistent
    volatile_cv: float = 0.35             # CV > 35% = volatile
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def get_weights(self, prop_type: str) -> Tuple[float, float, float, float]:
        """Get projection weights for a prop type."""
        pt = prop_type.upper()
        if pt == "PTS":
            return self.pts_weights
        elif pt == "REB":
            return self.reb_weights
        elif pt == "AST":
            return self.ast_weights
        else:
            return self.pts_weights
    
    def get_defense_adjustment(self, rating: str) -> float:
        """Get defense adjustment multiplier based on rating."""
        rating = rating.lower()
        if rating == "elite":
            return -self.elite_defense_adjustment
        elif rating == "good":
            return -self.good_defense_adjustment
        elif rating == "average":
            return self.avg_defense_adjustment
        elif rating == "poor":
            return self.poor_defense_adjustment
        elif rating == "terrible":
            return self.terrible_defense_adjustment
        return 0.0


# Default configuration instance
DEFAULT_CONFIG = ModelV6Config()


# =========================================================================
# ARCHETYPE DEFENSE INTERACTIONS
# =========================================================================
# Maps archetype -> defense type -> adjustment

ARCHETYPE_DEFENSE_MATRIX: Dict[str, Dict[str, float]] = {
    # Ball Handlers
    "Heliocentric Creator": {
        "POA Defender": -0.06,     # Struggle vs elite POA
        "Wing Stopper": -0.03,
        "Chased Target": 0.0,
    },
    "PnR Maestro": {
        "Switch Big": -0.04,       # Struggle vs switching
        "Anchor Big": 0.02,        # Can exploit drop coverage
    },
    "Scoring Guard": {
        "POA Defender": -0.05,
        "Chased Target": 0.0,
    },
    
    # Wings
    "Slasher": {
        "Anchor Big": -0.06,       # Rim protection hurts
        "Wing Stopper": -0.04,
        "Roamer": -0.02,           # Help defense hurts
    },
    "Isolation Scorer": {
        "Wing Stopper": -0.05,
        "POA Defender": -0.03,
    },
    "3-and-D Wing": {
        "Chaser": -0.03,           # Struggle vs chasers
        "Roamer": 0.0,
    },
    "Movement Shooter": {
        "Chaser": -0.05,           # Really struggle vs good chasers
        "Low Activity": 0.04,      # Exploit lazy defenders
    },
    "Spot Up Shooter": {
        "Chaser": -0.02,
        "Roamer": -0.02,
    },
    "Point Forward": {
        "Wing Stopper": -0.04,
        "Switch Big": -0.02,
    },
    
    # Bigs
    "Hub Big": {
        "Switch Big": -0.04,       # Struggle vs switching
        "Anchor Big": 0.0,
    },
    "Rim Runner": {
        "Anchor Big": -0.06,       # Really struggle vs rim protection
        "Switch Big": -0.02,
    },
    "Stretch Big": {
        "Switch Big": -0.04,       # Mobility limits spacing
        "Anchor Big": 0.03,        # Can pull them out
    },
    "Post Scorer": {
        "Anchor Big": -0.04,
        "Switch Big": 0.02,        # Exploit smaller mismatches
    },
}


# =========================================================================
# POSITION TO DEFENSE POSITION MAPPING
# =========================================================================
# Maps player position to defense vs position lookup

POSITION_MAPPING: Dict[str, str] = {
    "PG": "PG",
    "SG": "SG", 
    "SF": "SF",
    "PF": "PF",
    "C": "C",
    "G": "PG",    # Default guards to PG
    "F": "SF",    # Default forwards to SF
    "G-F": "SG",
    "F-G": "SF",
    "F-C": "PF",
    "C-F": "C",
}

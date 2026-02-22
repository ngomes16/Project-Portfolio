"""
Ensemble Confidence Scoring
===========================

Multi-factor confidence scoring that combines insights from all previous models:
1. Edge magnitude (larger edge = higher confidence)
2. Defense matchup quality + alignment
3. Signal agreement (multiple signals pointing same direction)
4. Historical consistency (low variance players)
5. Trend alignment (trend matches direction)
6. Head-to-head history strength
7. Archetype reliability (some archetypes are more predictable)
8. Player tier reliability (some tiers hit better)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import ModelV7Config, DEFAULT_CONFIG
from .projector import EnsembleProjection


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence score components."""
    # Component scores
    edge_score: int = 0
    defense_score: int = 0
    signal_agreement_score: int = 0
    consistency_score: int = 0
    trend_score: int = 0
    h2h_score: int = 0
    archetype_score: int = 0
    tier_score: int = 0
    
    # Total and tier
    total_score: int = 0
    confidence_tier: str = "LOW"
    
    # Direction preference adjustment (UNDER picks get boost)
    direction_adjustment: int = 0
    
    # Explanations
    explanations: dict = None
    
    def __post_init__(self):
        if self.explanations is None:
            self.explanations = {}


def calculate_confidence(
    projection: EnsembleProjection,
    config: ModelV7Config = DEFAULT_CONFIG,
) -> ConfidenceBreakdown:
    """
    Calculate comprehensive confidence score for an ensemble projection.
    
    Components (100 points max):
    - Edge: 0-20
    - Defense: 0-20
    - Signal Agreement: 0-15
    - Consistency: 0-15
    - Trend: 0-10
    - H2H: 0-10
    - Archetype: 0-5
    - Tier: 0-5
    
    Plus directional adjustment (UNDER bias from V6 insights)
    """
    breakdown = ConfidenceBreakdown()
    
    edge_pct = abs(projection.edge_pct)
    direction = projection.direction
    player_stats = projection.player_stats
    defense_profile = projection.defense_profile
    signal = projection.signal_strength
    
    # =========================================================================
    # 1. EDGE SCORE (0-20 points)
    # =========================================================================
    if edge_pct >= 20:
        breakdown.edge_score = 20
        breakdown.explanations["edge"] = f"Excellent edge ({edge_pct:.1f}%)"
    elif edge_pct >= 16:
        breakdown.edge_score = 18
        breakdown.explanations["edge"] = f"Very strong edge ({edge_pct:.1f}%)"
    elif edge_pct >= 13:
        breakdown.edge_score = 15
        breakdown.explanations["edge"] = f"Strong edge ({edge_pct:.1f}%)"
    elif edge_pct >= 10:
        breakdown.edge_score = 12
        breakdown.explanations["edge"] = f"Good edge ({edge_pct:.1f}%)"
    elif edge_pct >= 8:
        breakdown.edge_score = 9
        breakdown.explanations["edge"] = f"Moderate edge ({edge_pct:.1f}%)"
    elif edge_pct >= 6:
        breakdown.edge_score = 6
        breakdown.explanations["edge"] = f"Small edge ({edge_pct:.1f}%)"
    else:
        breakdown.edge_score = 3
        breakdown.explanations["edge"] = f"Minimal edge ({edge_pct:.1f}%)"
    
    # =========================================================================
    # 2. DEFENSE MATCHUP SCORE (0-20 points)
    # =========================================================================
    if defense_profile:
        rating = defense_profile.overall_rating
        
        # Score based on direction alignment with defense
        if direction == "UNDER":
            # UNDER picks benefit from strong defense
            if rating == "elite":
                breakdown.defense_score = 20
                breakdown.explanations["defense"] = "Elite defense - ideal for UNDER"
            elif rating == "good":
                breakdown.defense_score = 16
                breakdown.explanations["defense"] = "Good defense - favorable for UNDER"
            elif rating == "average":
                breakdown.defense_score = 12
                breakdown.explanations["defense"] = "Average defense - neutral"
            elif rating == "poor":
                breakdown.defense_score = 6
                breakdown.explanations["defense"] = "Poor defense - risky for UNDER"
            else:  # terrible
                breakdown.defense_score = 3
                breakdown.explanations["defense"] = "Terrible defense - bad for UNDER"
        else:  # OVER
            # OVER picks benefit from weak defense
            if rating == "terrible":
                breakdown.defense_score = 16  # Slightly lower than UNDER+elite
                breakdown.explanations["defense"] = "Terrible defense - good for OVER"
            elif rating == "poor":
                breakdown.defense_score = 14
                breakdown.explanations["defense"] = "Poor defense - favorable for OVER"
            elif rating == "average":
                breakdown.defense_score = 12
                breakdown.explanations["defense"] = "Average defense - neutral"
            elif rating == "good":
                breakdown.defense_score = 6
                breakdown.explanations["defense"] = "Good defense - risky for OVER"
            else:  # elite
                breakdown.defense_score = 3
                breakdown.explanations["defense"] = "Elite defense - bad for OVER"
    else:
        breakdown.defense_score = 10
        breakdown.explanations["defense"] = "No defense data"
    
    # =========================================================================
    # 3. SIGNAL AGREEMENT SCORE (0-15 points)
    # =========================================================================
    agreement = signal.signal_agreement
    
    if agreement >= 4:
        breakdown.signal_agreement_score = 15
        breakdown.explanations["signals"] = f"Strong consensus ({agreement} signals agree)"
    elif agreement >= 3:
        breakdown.signal_agreement_score = 12
        breakdown.explanations["signals"] = f"Good consensus ({agreement} signals agree)"
    elif agreement >= 2:
        breakdown.signal_agreement_score = 8
        breakdown.explanations["signals"] = f"Moderate consensus ({agreement} signals agree)"
    else:
        breakdown.signal_agreement_score = 4
        breakdown.explanations["signals"] = "Mixed signals"
    
    # =========================================================================
    # 4. CONSISTENCY SCORE (0-15 points)
    # =========================================================================
    if player_stats:
        pt = projection.prop_type.lower()
        cv = getattr(player_stats, f"{pt}_cv", 0.25)
        
        if cv < config.very_consistent_cv:
            breakdown.consistency_score = 15
            breakdown.explanations["consistency"] = f"Very consistent (CV: {cv:.0%})"
        elif cv < config.consistent_cv:
            breakdown.consistency_score = 12
            breakdown.explanations["consistency"] = f"Consistent (CV: {cv:.0%})"
        elif cv < 0.28:
            breakdown.consistency_score = 9
            breakdown.explanations["consistency"] = f"Moderate consistency (CV: {cv:.0%})"
        elif cv < config.volatile_cv:
            breakdown.consistency_score = 5
            breakdown.explanations["consistency"] = f"Somewhat volatile (CV: {cv:.0%})"
        else:
            breakdown.consistency_score = 2
            breakdown.explanations["consistency"] = f"High variance (CV: {cv:.0%})"
        
        # Bonus for stable minutes
        min_cv = player_stats.min_cv
        if min_cv < 0.10:
            breakdown.consistency_score = min(15, breakdown.consistency_score + 2)
    else:
        breakdown.consistency_score = 7
        breakdown.explanations["consistency"] = "No stats available"
    
    # =========================================================================
    # 5. TREND SCORE (0-10 points)
    # =========================================================================
    if player_stats:
        pt = projection.prop_type.lower()
        trend = getattr(player_stats, f"{pt}_trend", "stable")
        trend_pct = abs(getattr(player_stats, f"{pt}_trend_pct", 0))
        
        # Check alignment
        trend_aligned = (
            (trend == "hot" and direction == "OVER") or
            (trend == "cold" and direction == "UNDER")
        )
        trend_opposed = (
            (trend == "hot" and direction == "UNDER") or
            (trend == "cold" and direction == "OVER")
        )
        
        if trend_aligned:
            if trend_pct >= 20:
                breakdown.trend_score = 10
                breakdown.explanations["trend"] = f"Strong {trend} streak aligned with {direction}"
            else:
                breakdown.trend_score = 8
                breakdown.explanations["trend"] = f"{trend.capitalize()} streak aligned"
        elif trend_opposed:
            breakdown.trend_score = 2
            breakdown.explanations["trend"] = f"Trend opposes {direction}"
        else:
            breakdown.trend_score = 6
            breakdown.explanations["trend"] = "Stable trend"
    else:
        breakdown.trend_score = 5
        breakdown.explanations["trend"] = "No trend data"
    
    # =========================================================================
    # 6. HEAD-TO-HEAD SCORE (0-10 points)
    # =========================================================================
    h2h_stats = projection.h2h_stats
    if h2h_stats and h2h_stats.games_count >= config.h2h_min_games:
        pt = projection.prop_type.upper()
        
        if pt == "PTS":
            h2h_avg = h2h_stats.pts_avg
            season_avg = player_stats.l10_pts if player_stats else h2h_avg
        elif pt == "REB":
            h2h_avg = h2h_stats.reb_avg
            season_avg = player_stats.l10_reb if player_stats else h2h_avg
        else:
            h2h_avg = h2h_stats.ast_avg
            season_avg = player_stats.l10_ast if player_stats else h2h_avg
        
        h2h_diff = ((h2h_avg - season_avg) / season_avg * 100) if season_avg > 0 else 0
        
        # Check if H2H supports direction
        h2h_supports = (
            (direction == "OVER" and h2h_diff > 5) or
            (direction == "UNDER" and h2h_diff < -5)
        )
        
        if h2h_supports:
            if h2h_stats.games_count >= 4:
                breakdown.h2h_score = 10
                breakdown.explanations["h2h"] = f"Strong H2H support ({h2h_stats.games_count} games)"
            else:
                breakdown.h2h_score = 7
                breakdown.explanations["h2h"] = f"H2H supports ({h2h_stats.games_count} games)"
        elif abs(h2h_diff) < 5:
            breakdown.h2h_score = 5
            breakdown.explanations["h2h"] = "H2H neutral"
        else:
            breakdown.h2h_score = 2
            breakdown.explanations["h2h"] = "H2H opposes direction"
    else:
        breakdown.h2h_score = 5
        breakdown.explanations["h2h"] = "No H2H data"
    
    # =========================================================================
    # 7. ARCHETYPE SCORE (0-5 points)
    # =========================================================================
    archetype = projection.archetype_group.lower().replace(" ", "_")
    archetype_reliability = config.get_archetype_reliability(archetype)
    
    if archetype_reliability >= 1.12:
        breakdown.archetype_score = 5
        breakdown.explanations["archetype"] = f"Highly predictable archetype"
    elif archetype_reliability >= 1.05:
        breakdown.archetype_score = 4
        breakdown.explanations["archetype"] = f"Predictable archetype"
    elif archetype_reliability >= 0.98:
        breakdown.archetype_score = 3
        breakdown.explanations["archetype"] = f"Average archetype"
    elif archetype_reliability >= 0.93:
        breakdown.archetype_score = 1
        breakdown.explanations["archetype"] = f"Below-average archetype"
    else:
        breakdown.archetype_score = 0
        breakdown.explanations["archetype"] = f"Unpredictable archetype (scoring guard)"
    
    # Apply scoring guard penalty if configured
    if config.filter_scoring_guards and archetype == "scoring_guards":
        breakdown.archetype_score = max(0, breakdown.archetype_score - 3)
    
    # =========================================================================
    # 8. TIER SCORE (0-5 points)
    # =========================================================================
    tier = projection.player_tier
    tier_reliability = config.get_tier_reliability(tier)
    
    if tier_reliability >= 1.08:
        breakdown.tier_score = 5
        breakdown.explanations["tier"] = f"Highly predictable tier (Starter)"
    elif tier_reliability >= 1.03:
        breakdown.tier_score = 4
        breakdown.explanations["tier"] = f"Predictable tier"
    elif tier_reliability >= 0.98:
        breakdown.tier_score = 3
        breakdown.explanations["tier"] = f"Average tier"
    elif tier_reliability >= 0.94:
        breakdown.tier_score = 1
        breakdown.explanations["tier"] = f"Less predictable tier"
    else:
        breakdown.tier_score = 0
        breakdown.explanations["tier"] = f"High variance tier (All-Star)"
    
    # Apply tier adjustments if configured
    if config.boost_starter_tier and tier == 3:
        breakdown.tier_score = min(5, breakdown.tier_score + 1)
    if config.penalize_allstar_tier and tier == 2:
        breakdown.tier_score = max(0, breakdown.tier_score - 2)
    
    # =========================================================================
    # 9. DIRECTION PREFERENCE (UNDER bonus from V6 insight)
    # =========================================================================
    if direction == "UNDER":
        breakdown.direction_adjustment = 3  # Small boost for UNDERs
        breakdown.explanations["direction"] = "UNDER picks historically outperform"
    else:
        breakdown.direction_adjustment = 0
    
    # =========================================================================
    # CALCULATE TOTAL
    # =========================================================================
    base_total = (
        breakdown.edge_score +
        breakdown.defense_score +
        breakdown.signal_agreement_score +
        breakdown.consistency_score +
        breakdown.trend_score +
        breakdown.h2h_score +
        breakdown.archetype_score +
        breakdown.tier_score
    )
    
    # Apply direction adjustment
    breakdown.total_score = base_total + breakdown.direction_adjustment
    
    # =========================================================================
    # 10. SIGNAL COUNT ADJUSTMENT (NEW - based on 78.7% hit rate for 1-signal)
    # =========================================================================
    if config.prefer_low_signal_count:
        if agreement == 1:
            breakdown.total_score += config.low_signal_bonus
            breakdown.explanations["signal_count"] = f"1-signal pick bonus (+{config.low_signal_bonus})"
        elif agreement == 2:
            breakdown.total_score += config.medium_signal_bonus
            breakdown.explanations["signal_count"] = f"2-signal pick bonus (+{config.medium_signal_bonus})"
        elif agreement >= 3:
            breakdown.total_score -= config.high_signal_penalty
            breakdown.explanations["signal_count"] = f"High consensus penalty (-{config.high_signal_penalty})"
    
    # Cap at 100
    breakdown.total_score = min(100, breakdown.total_score)
    
    # Determine tier
    if breakdown.total_score >= config.high_confidence_min:
        breakdown.confidence_tier = "HIGH"
    elif breakdown.total_score >= config.medium_confidence_min:
        breakdown.confidence_tier = "MEDIUM"
    else:
        breakdown.confidence_tier = "LOW"
    
    return breakdown


def calculate_quick_confidence(
    edge_pct: float,
    direction: str,
    defense_rating: str,
    consistency_cv: float,
    trend_aligned: bool,
    has_h2h_support: bool,
    archetype_reliable: bool,
    config: ModelV7Config = DEFAULT_CONFIG,
) -> int:
    """
    Quick confidence calculation for filtering.
    
    Returns approximate confidence score (0-100).
    """
    score = 0
    
    # Edge (0-20)
    if edge_pct >= 15:
        score += 18
    elif edge_pct >= 10:
        score += 12
    elif edge_pct >= 6:
        score += 6
    else:
        score += 3
    
    # Defense alignment (0-20)
    if direction == "UNDER" and defense_rating in ["elite", "good"]:
        score += 16
    elif direction == "OVER" and defense_rating in ["terrible", "poor"]:
        score += 14
    elif defense_rating == "average":
        score += 10
    else:
        score += 4
    
    # Consistency (0-15)
    if consistency_cv < 0.20:
        score += 13
    elif consistency_cv < 0.30:
        score += 9
    else:
        score += 4
    
    # Trend (0-10)
    if trend_aligned:
        score += 9
    else:
        score += 5
    
    # H2H (0-10)
    if has_h2h_support:
        score += 8
    else:
        score += 4
    
    # Archetype (0-5)
    if archetype_reliable:
        score += 4
    else:
        score += 1
    
    # Tier bonus
    score += 3
    
    # Direction bonus
    if direction == "UNDER":
        score += 3
    
    return min(100, score)

"""
Confidence Scoring System
=========================

Multi-factor confidence scoring that considers:
1. Edge size
2. Defense matchup quality
3. Historical consistency
4. Trend alignment
5. Sample size
6. Archetype matchup favorability
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .config import ModelV6Config, DEFAULT_CONFIG
from .projector import Projection
from .player_groups import PlayerGroup
from .defense_analysis import DefenseMatchup


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence score components."""
    # Component scores
    edge_score: int = 0
    defense_matchup_score: int = 0
    consistency_score: int = 0
    trend_score: int = 0
    sample_size_score: int = 0
    archetype_score: int = 0
    
    # Total and tier
    total_score: int = 0
    confidence_tier: str = "LOW"  # "HIGH", "MEDIUM", "LOW"
    
    # Explanations
    edge_explanation: str = ""
    defense_explanation: str = ""
    consistency_explanation: str = ""
    trend_explanation: str = ""
    sample_explanation: str = ""
    archetype_explanation: str = ""


def calculate_confidence(
    projection: Projection,
    config: ModelV6Config = DEFAULT_CONFIG,
) -> ConfidenceBreakdown:
    """
    Calculate comprehensive confidence score for a projection.
    
    Args:
        projection: The projection to score
        config: Model configuration
    
    Returns:
        ConfidenceBreakdown with all component scores
    """
    breakdown = ConfidenceBreakdown()
    
    edge_pct = abs(projection.edge_pct)
    player_stats = projection.player_stats
    player_group = projection.player_group
    defense_matchup = projection.defense_matchup
    prop_type = projection.prop_type.lower()
    direction = projection.direction
    
    # =========================================================================
    # 1. EDGE SCORE (0-25 points)
    # =========================================================================
    if edge_pct >= 20:
        breakdown.edge_score = 25
        breakdown.edge_explanation = f"Excellent edge ({edge_pct:.1f}%)"
    elif edge_pct >= 16:
        breakdown.edge_score = 22
        breakdown.edge_explanation = f"Very strong edge ({edge_pct:.1f}%)"
    elif edge_pct >= 13:
        breakdown.edge_score = 18
        breakdown.edge_explanation = f"Strong edge ({edge_pct:.1f}%)"
    elif edge_pct >= 10:
        breakdown.edge_score = 14
        breakdown.edge_explanation = f"Good edge ({edge_pct:.1f}%)"
    elif edge_pct >= 7:
        breakdown.edge_score = 10
        breakdown.edge_explanation = f"Moderate edge ({edge_pct:.1f}%)"
    else:
        breakdown.edge_score = 5
        breakdown.edge_explanation = f"Small edge ({edge_pct:.1f}%)"
    
    # =========================================================================
    # 2. DEFENSE MATCHUP SCORE (0-20 points)
    # =========================================================================
    if defense_matchup:
        rating = defense_matchup.defense_rating
        
        # Base score from defense rating
        if rating == "terrible":
            if direction == "OVER":
                breakdown.defense_matchup_score = 20
                breakdown.defense_explanation = "Terrible defense - ideal for OVER"
            else:
                breakdown.defense_matchup_score = 5
                breakdown.defense_explanation = "Terrible defense - risky for UNDER"
        elif rating == "poor":
            if direction == "OVER":
                breakdown.defense_matchup_score = 16
                breakdown.defense_explanation = "Poor defense - favorable for OVER"
            else:
                breakdown.defense_matchup_score = 8
                breakdown.defense_explanation = "Poor defense - moderate risk for UNDER"
        elif rating == "average":
            breakdown.defense_matchup_score = 12
            breakdown.defense_explanation = "Average defense - neutral matchup"
        elif rating == "good":
            if direction == "UNDER":
                breakdown.defense_matchup_score = 16
                breakdown.defense_explanation = "Good defense - favorable for UNDER"
            else:
                breakdown.defense_matchup_score = 8
                breakdown.defense_explanation = "Good defense - moderate risk for OVER"
        elif rating == "elite":
            if direction == "UNDER":
                breakdown.defense_matchup_score = 20
                breakdown.defense_explanation = "Elite defense - ideal for UNDER"
            else:
                breakdown.defense_matchup_score = 5
                breakdown.defense_explanation = "Elite defense - risky for OVER"
        
        # Bonus for archetype-favorable matchup
        if defense_matchup.archetype_adjustment > 0:
            breakdown.defense_matchup_score = min(20, breakdown.defense_matchup_score + 3)
            breakdown.defense_explanation += " + favorable archetype"
        elif defense_matchup.archetype_adjustment < -0.03:
            breakdown.defense_matchup_score = max(0, breakdown.defense_matchup_score - 3)
            breakdown.defense_explanation += " + tough archetype matchup"
    else:
        breakdown.defense_matchup_score = 10
        breakdown.defense_explanation = "No defense data available"
    
    # =========================================================================
    # 3. CONSISTENCY SCORE (0-20 points)
    # =========================================================================
    if player_stats:
        cv = getattr(player_stats, f"{prop_type}_cv", 0.25)
        
        if cv < config.very_consistent_cv:
            breakdown.consistency_score = 20
            breakdown.consistency_explanation = f"Very consistent (CV: {cv:.0%})"
        elif cv < config.consistent_cv:
            breakdown.consistency_score = 15
            breakdown.consistency_explanation = f"Consistent (CV: {cv:.0%})"
        elif cv < 0.30:
            breakdown.consistency_score = 10
            breakdown.consistency_explanation = f"Moderately consistent (CV: {cv:.0%})"
        elif cv < config.volatile_cv:
            breakdown.consistency_score = 6
            breakdown.consistency_explanation = f"Somewhat volatile (CV: {cv:.0%})"
        else:
            breakdown.consistency_score = 3
            breakdown.consistency_explanation = f"High variance (CV: {cv:.0%})"
        
        # Minutes stability bonus
        min_cv = player_stats.min_cv
        if min_cv < 0.10:
            breakdown.consistency_score = min(20, breakdown.consistency_score + 3)
            breakdown.consistency_explanation += " + stable minutes"
    else:
        breakdown.consistency_score = 10
        breakdown.consistency_explanation = "No stats available"
    
    # =========================================================================
    # 4. TREND SCORE (0-15 points)
    # =========================================================================
    if player_stats:
        trend = getattr(player_stats, f"{prop_type}_trend", "stable")
        trend_pct = getattr(player_stats, f"{prop_type}_trend_pct", 0)
        
        # Trend alignment with direction
        trend_aligned = (
            (trend == "hot" and direction == "OVER") or
            (trend == "cold" and direction == "UNDER")
        )
        trend_opposed = (
            (trend == "hot" and direction == "UNDER") or
            (trend == "cold" and direction == "OVER")
        )
        
        if trend_aligned:
            if abs(trend_pct) >= 20:
                breakdown.trend_score = 15
                breakdown.trend_explanation = f"Strong {trend} streak aligned with {direction}"
            else:
                breakdown.trend_score = 12
                breakdown.trend_explanation = f"{trend.capitalize()} streak aligned with {direction}"
        elif trend == "stable":
            breakdown.trend_score = 10
            breakdown.trend_explanation = "Stable recent performance"
        elif trend_opposed:
            breakdown.trend_score = 3
            breakdown.trend_explanation = f"Warning: {trend} streak opposes {direction}"
        else:
            breakdown.trend_score = 8
            breakdown.trend_explanation = "No strong trend"
    else:
        breakdown.trend_score = 8
        breakdown.trend_explanation = "No trend data"
    
    # =========================================================================
    # 5. SAMPLE SIZE SCORE (0-10 points)
    # =========================================================================
    if player_stats:
        games = player_stats.games_played
        
        if games >= 25:
            breakdown.sample_size_score = 10
            breakdown.sample_explanation = f"Excellent sample ({games} games)"
        elif games >= 20:
            breakdown.sample_size_score = 9
            breakdown.sample_explanation = f"Great sample ({games} games)"
        elif games >= 15:
            breakdown.sample_size_score = 7
            breakdown.sample_explanation = f"Good sample ({games} games)"
        elif games >= 10:
            breakdown.sample_size_score = 5
            breakdown.sample_explanation = f"Adequate sample ({games} games)"
        else:
            breakdown.sample_size_score = 2
            breakdown.sample_explanation = f"Limited sample ({games} games)"
    else:
        breakdown.sample_size_score = 5
        breakdown.sample_explanation = "Sample size unknown"
    
    # =========================================================================
    # 6. ARCHETYPE SCORE (0-10 points)
    # =========================================================================
    if player_group:
        # Star players are more reliable
        if player_group.is_matchup_proof:
            breakdown.archetype_score = 10
            breakdown.archetype_explanation = "Elite player - matchup proof"
        elif player_group.is_star:
            breakdown.archetype_score = 8
            breakdown.archetype_explanation = "Star player - reliable production"
        elif player_group.tier_value <= 4:
            breakdown.archetype_score = 6
            breakdown.archetype_explanation = "Starter - consistent role"
        elif player_group.tier_value == 5:
            breakdown.archetype_score = 4
            breakdown.archetype_explanation = "Specialist - role-dependent"
        else:
            breakdown.archetype_score = 2
            breakdown.archetype_explanation = "Bench player - variable minutes"
        
        # Bonus for favorable offensive style vs defense
        if player_group.offensive_style and defense_matchup:
            # Movement shooters vs poor defense
            from .player_groups import OffensiveStyle
            if (player_group.offensive_style == OffensiveStyle.MOVEMENT_BASED and 
                defense_matchup.defense_rating in ("poor", "terrible")):
                breakdown.archetype_score = min(10, breakdown.archetype_score + 2)
                breakdown.archetype_explanation += " + style advantage"
    else:
        breakdown.archetype_score = 5
        breakdown.archetype_explanation = "Player classification unknown"
    
    # =========================================================================
    # TOTAL SCORE AND TIER
    # =========================================================================
    breakdown.total_score = (
        breakdown.edge_score +
        breakdown.defense_matchup_score +
        breakdown.consistency_score +
        breakdown.trend_score +
        breakdown.sample_size_score +
        breakdown.archetype_score
    )
    
    # Cap at 100
    breakdown.total_score = min(100, breakdown.total_score)
    
    # Determine tier
    edge_threshold_met = projection.edge_pct >= config.high_edge_threshold
    medium_edge_met = projection.edge_pct >= config.medium_edge_threshold
    
    if edge_threshold_met and breakdown.total_score >= config.high_confidence_min:
        breakdown.confidence_tier = "HIGH"
    elif medium_edge_met and breakdown.total_score >= config.medium_confidence_min:
        breakdown.confidence_tier = "MEDIUM"
    else:
        breakdown.confidence_tier = "LOW"
    
    return breakdown


def get_confidence_summary(breakdown: ConfidenceBreakdown) -> str:
    """Generate a human-readable summary of confidence scoring."""
    lines = [
        f"Confidence Score: {breakdown.total_score}/100 ({breakdown.confidence_tier})",
        "",
        "Component Breakdown:",
        f"  Edge ({breakdown.edge_score}/25): {breakdown.edge_explanation}",
        f"  Defense ({breakdown.defense_matchup_score}/20): {breakdown.defense_explanation}",
        f"  Consistency ({breakdown.consistency_score}/20): {breakdown.consistency_explanation}",
        f"  Trend ({breakdown.trend_score}/15): {breakdown.trend_explanation}",
        f"  Sample ({breakdown.sample_size_score}/10): {breakdown.sample_explanation}",
        f"  Archetype ({breakdown.archetype_score}/10): {breakdown.archetype_explanation}",
    ]
    return "\n".join(lines)

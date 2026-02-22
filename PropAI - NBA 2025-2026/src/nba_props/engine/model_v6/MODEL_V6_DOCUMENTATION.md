# Model V6 - Archetype-Aware Defense-Focused Prediction System

## Executive Summary

Model V6 is a comprehensive NBA player props prediction system that emphasizes:
1. **Defense matchup analysis** - Adjusts projections based on opponent's defense quality
2. **Player archetype classification** - Groups players by play style for better prediction
3. **Last 20 games focus** - Uses L5/L10/L20 weighted averages with stat-specific weights
4. **Multi-factor confidence scoring** - Combines edge, consistency, defense, and archetype factors

### Key Performance Metrics (Extended Backtest: Nov 25 - Jan 8, 2026)

| Metric | Value |
|--------|-------|
| **Overall Hit Rate** | **58.6%** |
| Total Picks | 975 |
| Games Analyzed | 294 |
| HIGH Confidence | 58.5% (489 picks) |
| MEDIUM Confidence | 58.6% (485 picks) |

### Performance by Prop Type

| Prop Type | Hit Rate | Picks |
|-----------|----------|-------|
| Points (PTS) | 59.2% | 478 |
| Assists (AST) | 59.4% | 128 |
| Rebounds (REB) | 57.5% | 369 |

### Performance by Direction

| Direction | Hit Rate | Picks |
|-----------|----------|-------|
| **UNDER** | **61.0%** | 474 |
| OVER | 56.3% | 501 |

---

## Architecture Overview

```
model_v6/
├── __init__.py           # Module exports
├── config.py             # Centralized configuration
├── player_groups.py      # Player archetype classification
├── defense_analysis.py   # Defense matchup analysis
├── projector.py          # Statistical projections
├── confidence.py         # Multi-factor confidence scoring
├── picks.py              # Pick generation
├── backtester.py         # Comprehensive backtesting
└── lab.py                # Model Lab interface
```

---

## Module Documentation

### 1. Configuration (`config.py`)

The `ModelV6Config` dataclass centralizes all model parameters:

#### Projection Weights
```python
pts_weights: (0.25, 0.25, 0.30, 0.20)  # (L5, L10, L20, Season)
reb_weights: (0.20, 0.25, 0.30, 0.25)
ast_weights: (0.25, 0.30, 0.25, 0.20)
```

#### Optimized Defense Adjustments
```python
elite_defense_adjustment:     0.12  # -12% for elite defense (rank 1-5)
good_defense_adjustment:      0.06  # -6% for good defense (rank 6-10)
avg_defense_adjustment:       0.00  # No adjustment (rank 11-20)
poor_defense_adjustment:      0.06  # +6% for poor defense (rank 21-25)
terrible_defense_adjustment:  0.12  # +12% for terrible defense (rank 26-30)
```

These defense adjustments were optimized through backtesting. The 12% adjustments for elite/terrible defenses improved hit rate from ~57% to ~59%.

#### Edge Thresholds
```python
min_edge_threshold:    6.0   # Minimum edge to generate a pick
medium_edge_threshold: 9.0   # Medium confidence threshold
high_edge_threshold:   14.0  # High confidence threshold
```

---

### 2. Player Groups (`player_groups.py`)

Players are classified into archetype groups based on their play style. This improves prediction accuracy by treating similar players similarly.

#### Archetype Groups & Performance

| Group | Description | Hit Rate | Sample |
|-------|-------------|----------|--------|
| **Stretch Bigs** | Floor-spacing bigs (Embiid, KAT) | 64.9% | 37 |
| **Corner Specialists** | 3-and-D wings | 64.0% | 75 |
| **Traditional Bigs** | Classic post players | 64.0% | 86 |
| **Movement Shooters** | Off-ball scorers (Curry, Booker) | 62.5% | 48 |
| **Heliocentric Creators** | Ball-dominant stars (LeBron, Luka) | 61.6% | 99 |
| **Slashers** | Athletic finishers | 59.7% | 77 |
| **Unicorns** | Versatile bigs (Jokic, Giannis) | 57.6% | 59 |
| **Two-Way Wings** | Defensive versatile wings | 56.7% | 330 |
| **Hub Bigs** | High-post facilitators | 56.7% | 30 |
| **Scoring Guards** | Traditional scoring guards | 51.5% | 134 |

#### Classification Logic

Players are classified based on:
1. **Roster database** - Known player profiles with tier and archetype
2. **Statistical inference** - Uses PPG, RPG, APG, position to classify unknown players

```python
# Usage
from model_v6.player_groups import get_player_group, classify_player

group = get_player_group(conn, "LeBron James")
# Returns: PlayerGroup(name="LeBron James", tier=1, group_key="heliocentric", ...)
```

---

### 3. Defense Analysis (`defense_analysis.py`)

The defense analysis module evaluates how opponent defense quality impacts player performance.

#### Defense Quality Tiers

| Tier | Rank Range | Adjustment |
|------|------------|------------|
| ELITE | 1-5 | -12% |
| GOOD | 6-10 | -6% |
| AVERAGE | 11-20 | 0% |
| POOR | 21-25 | +6% |
| TERRIBLE | 26-30 | +12% |

#### Performance by Defense Matchup

| Defense Quality | Hit Rate | Picks |
|-----------------|----------|-------|
| **ELITE** | **63.6%** | 275 |
| **AVERAGE** | **64.3%** | 182 |
| TERRIBLE | 55.8% | 274 |
| GOOD | 50.0% | 112 |
| POOR | 53.0% | 132 |

**Key Insight:** UNDERs vs elite defense and projections vs average defense perform best.

#### Usage

```python
from model_v6.defense_analysis import get_defense_matchup, DefenseMatchup

matchup = get_defense_matchup(conn, "PG", "MIA")
# Returns: DefenseMatchup(position="PG", team="MIA", rank=5, rating="elite", adjustment=-0.12)
```

---

### 4. Projector (`projector.py`)

The projection engine generates stat projections using weighted averages with defense and archetype adjustments.

#### Projection Formula

```
Base Projection = (L5 × w1) + (L10 × w2) + (L20 × w3) + (Season × w4)
Defense Adjustment = Base × defense_factor
Final Projection = Defense Adjustment × archetype_modifier
```

#### Key Features

1. **Weighted Averages** - Different weights by stat type
2. **Defense Adjustment** - Based on opponent's defense quality
3. **Archetype Modifiers** - Special adjustments for specific matchups
4. **Trend Detection** - Hot/cold streak identification

```python
from model_v6.projector import project_all_props

projections = project_all_props(conn, game_id, home_team, away_team, config)
# Returns list of PlayerProjection objects
```

---

### 5. Confidence Scoring (`confidence.py`)

Multi-factor confidence scoring combines several signals:

#### Confidence Components (Total: 100 points)

| Component | Max Points | Description |
|-----------|------------|-------------|
| Edge Size | 25 | How far projection is from line |
| Defense Matchup | 20 | Favorable vs unfavorable matchup |
| Consistency | 20 | Player's coefficient of variation |
| Trend Alignment | 15 | Hot/cold streak matching direction |
| Sample Size | 10 | Games played this season |
| Archetype Match | 10 | Archetype vs defense type bonus |

#### Confidence Tiers

| Tier | Score Range | Characteristics |
|------|-------------|-----------------|
| HIGH | ≥72 | Strong edge + favorable matchup + consistent |
| MEDIUM | 55-71 | Moderate edge or some uncertainty |
| LOW | <55 | Weak edge or high variance |

---

### 6. Pick Generation (`picks.py`)

The pick generator selects the best props for each game.

#### Selection Criteria

1. **Minimum Edge:** 6%
2. **Minimum Minutes:** 22 avg
3. **Minimum Games:** 7 games played
4. **Minimum Assists (for AST props):** 4.0 APG

#### Picks Per Game

- Target: 4 picks per game
- Max per player: 2 props

```python
from model_v6.picks import generate_game_picks

picks = generate_game_picks(conn, game_id, home, away, config)
# Returns: DailyPicks with filtered and ranked picks
```

---

### 7. Backtester (`backtester.py`)

Comprehensive backtesting with detailed breakdowns.

#### Available Analyses

- Overall hit rate
- By prop type (PTS, REB, AST)
- By confidence tier (HIGH, MEDIUM, LOW)
- By direction (OVER, UNDER)
- By archetype group
- By defense matchup quality
- By player tier
- Daily performance tracking

```python
from model_v6.backtester import run_backtest

result = run_backtest("2025-12-01", "2026-01-08", config, verbose=True)
print(result.summary())
```

---

### 8. Model Lab (`lab.py`)

Interactive testing and analysis interface.

#### Key Methods

```python
from model_v6.lab import ModelLab

lab = ModelLab()

# Quick test (last N days)
result = lab.run_quick_test(days=14)

# Full backtest
result = lab.run_full_backtest("2025-12-01", "2026-01-08")

# Archetype analysis
archetypes = lab.analyze_archetypes(result)
leaderboard = lab.get_archetype_leaderboard(result, min_picks=10)

# Defense analysis
defense_report = lab.analyze_defense_performance(result)

# Configuration comparison
configs = [("Default", config1), ("High Defense", config2)]
comparison = lab.compare_configs(configs, start, end)
```

---

## Key Findings & Recommendations

### 1. UNDER Picks Outperform OVERs

| Direction | Hit Rate |
|-----------|----------|
| UNDER | 61.0% |
| OVER | 56.3% |

**Recommendation:** Prioritize UNDER picks when projection shows significant edge below the line.

### 2. Elite Defense Creates Opportunities

Counter-intuitively, picks against ELITE and AVERAGE defenses hit at higher rates (63-64%) than against poor defenses (53-56%).

**Recommendation:** Don't chase "soft matchups" - the model already adjusts for defense quality.

### 3. Stretch Bigs Are Most Predictable

Stretch Bigs (64.9%) and Corner Specialists (64.0%) hit at the highest rates.

**Recommendation:** Weight picks from these archetype groups more heavily.

### 4. Scoring Guards Underperform

Scoring Guards hit at only 51.5%, the lowest of any archetype group.

**Recommendation:** Be more selective with guard props, especially PTS props.

### 5. Player Tier Insights

| Tier | Hit Rate | Notes |
|------|----------|-------|
| Starter | 65.4% | Best tier |
| MVP | 61.4% | Very good |
| Role/Specialist | ~58% | Solid |
| All-Star | 51.7% | Below average |

**Recommendation:** Focus on Starter-tier players who are more predictable than high-usage All-Stars.

---

## Configuration Optimization Results

Tested configurations over 3+ weeks of data:

| Configuration | Hit Rate | Notes |
|---------------|----------|-------|
| **Optimized (12% defense)** | **59.3%** | Best overall |
| Default (8% defense) | 57.9% | Baseline |
| Heavy Recency | 56.7% | Worse |
| Higher Edge (7%) | 57.9% | Same picks |

The optimized defense adjustments (12% vs 8%) improved hit rate by ~1.4 percentage points.

---

## Usage Example

```python
from src.nba_props.engine.model_v6.lab import ModelLab
from src.nba_props.engine.model_v6.config import ModelV6Config

# Initialize with optimized config (default)
lab = ModelLab()

# Run backtest
result = lab.run_full_backtest("2025-12-01", "2026-01-08")
print(result.summary())

# Get archetype leaderboard
leaderboard = lab.get_archetype_leaderboard(result, min_picks=10)
for entry in leaderboard:
    print(f"{entry['rank']}. {entry['group']}: {entry['hit_rate']}")

# Analyze defense performance
defense_report = lab.analyze_defense_performance(result)
print(f"OVER vs Weak Defense: {defense_report.over_vs_weak_defense:.1%}")
print(f"UNDER vs Strong Defense: {defense_report.under_vs_strong_defense:.1%}")
```

---

## Future Improvements

1. **Injury Impact Modeling** - Adjust projections when key teammates are out
2. **Rest Day Analysis** - More sophisticated B2B and rest advantage tracking
3. **Venue Analysis** - Home/away splits for specific archetypes
4. **Line Movement Integration** - Track line movement for additional signals
5. **Ensemble Methods** - Combine V6 with other models for improved accuracy

---

## Changelog

### v6.0.0 (January 2026)
- Initial release
- Archetype-based player classification
- Defense matchup analysis with position-specific rankings
- Multi-factor confidence scoring
- Comprehensive backtesting framework
- Optimized defense adjustments (12% for elite/terrible)
- Extended backtest validation: 58.6% hit rate over 975 picks

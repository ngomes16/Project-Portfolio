# NBA Props Model Summary & Analysis

> **Last Updated:** January 15, 2026  
> **Author:** PropAI Development Team  
> **Purpose:** Comprehensive comparison and analysis of all prediction models

---

## Table of Contents

1. [Rankings](#rankings)
   - [By Performance (Success Rate)](#ranking-by-performance)
   - [By Complexity](#ranking-by-complexity)
2. [Model Overview Matrix](#model-overview-matrix)
3. [Detailed Model Analyses](#detailed-model-analyses)
4. [Key Insights & Learnings](#key-insights--learnings)
5. [Future Recommendations](#future-recommendations)

---

## Rankings

### Ranking by Performance

Models ranked by validated backtest hit rate (highest to lowest):

| Rank | Model | Hit Rate | Picks | Backtest Period | Key Strength |
|------|-------|----------|-------|-----------------|--------------|
| 🥇 1 | **Model V9 (Line-Aware)** | **68.6%** | 86 | Dec 2025 - Jan 2026 | Uses actual sportsbook lines |
| 🥈 2 | **Model Production** | **66.7%** | 348 | Oct-Jan 2026 (73 days) | Pattern detection (cold bounce, hot sustained) |
| 🥉 3 | **Hybrid Model v1.2** | **66.6%** | 311 | Dec 2025 - Jan 2026 | Combines RCM + Pattern detection |
| 4 | Model Final | ~61% | ~650 | 5 weeks, 222 games | Stat-specific weighting |
| 5 | RCM v1.4 | 60.4% | 316 | Oct-Jan 2026 (79 days) | Contribution rate methodology |
| 6 | Model V6 | 58.6% | 975 | Nov-Jan 2026 (294 games) | Archetype-aware, defense-focused |
| 7 | Under Model V2 | ~58% | 391 | Dec 2025 | UNDER-specialized |
| 8 | Enhanced Model | ~55% | Variable | - | Simple L10 average approach |
| 9 | Model V5 | ~55% | - | - | Comprehensive data sources |
| 10 | Model V8 | ~54% | - | - | Learning-based calibration |
| 11 | Model V4 | ~53% | - | - | Balanced prop distribution |
| 12 | Model V3 | ~52% | - | - | Stat-type specific weights |
| 13 | Model V2 | ~51% | - | - | Basic weighted averages |

> **Note:** Some models used derived lines rather than actual sportsbook lines. Model V9's hit rate is the most realistic reflection of real-world betting performance.

---

### Ranking by Complexity

Models ranked by implementation complexity (most complex to simplest):

| Rank | Model | Complexity Score | Key Complexity Factors |
|------|-------|------------------|------------------------|
| 1 | **Model V7 (Ensemble)** | ⭐⭐⭐⭐⭐ | Combines insights from V2-V6, archetype reliability, tier reliability, multi-signal voting |
| 2 | **Model V6** | ⭐⭐⭐⭐⭐ | Archetype classification, defense analysis, multi-factor confidence (6 components) |
| 3 | **Hybrid Model** | ⭐⭐⭐⭐☆ | Combines RCM + Pattern detection, opponent DVP adjustments, strategic direction selection |
| 4 | **Model V5** | ⭐⭐⭐⭐☆ | 10 data sources, H2H analysis, archetype tiers, 4-window projections (L3/L5/L10/Season) |
| 5 | **RCM v1.4** | ⭐⭐⭐⭐☆ | Contribution rates, Bayesian regression, team context, usage redistribution |
| 6 | **Model V9** | ⭐⭐⭐☆☆ | Line-aware with sportsbook integration, pattern detection, version tracking |
| 7 | **Model Production** | ⭐⭐⭐☆☆ | Two-pattern system (cold bounce, hot sustained), injury filtering |
| 8 | **Model V8** | ⭐⭐⭐☆☆ | Learning weights, pattern recognition, calibrated confidence |
| 9 | **Under Model V2** | ⭐⭐⭐☆☆ | Factor-based scoring (17 factors), defense vs position integration |
| 10 | **Model V4** | ⭐⭐☆☆☆ | Balanced distribution, minimum line thresholds, star player priority |
| 11 | **Model Final** | ⭐⭐☆☆☆ | Stat-specific weights, trend detection, opponent adjustment |
| 12 | **Model V3** | ⭐⭐☆☆☆ | Floor/ceiling analysis, stat-specific weights |
| 13 | **Enhanced Model** | ⭐☆☆☆☆ | Simple L10 average, basic edge calculation |
| 14 | **Model V2** | ⭐☆☆☆☆ | Basic L5/L15/Season weighted average |

---

## Model Overview Matrix

| Model | Focus | Direction | Prop Types | Picks/Game | Uses Lines | Pattern Detection |
|-------|-------|-----------|------------|------------|------------|-------------------|
| Model V9 | Line-Aware | OVER | PTS, REB | ~3 | ✅ Sportsbook | Cold bounce, Hot sustained |
| Model Production | Pattern | OVER | PTS, REB | ~5-8 | ❌ Derived | Cold bounce, Hot sustained |
| Hybrid v1.2 | Combined | Both | PTS, REB | ~7 | ❌ Derived | Cold bounce, Hot sustained |
| RCM v1.4 | Contribution | Both (PTS UNDER only) | PTS, REB | ~4 | ❌ Derived | None |
| Model V6 | Archetype | Both (UNDER preferred) | PTS, REB, AST | ~4 | ❌ Derived | Trend detection |
| Under Model V2 | UNDER Only | UNDER | PTS, REB, AST | ~3-4 | ❌ Derived | Cold streak |
| Model V8 | Learning | Both | PTS, REB, AST | ~4 | ❌ Derived | Cold bounce, Hot sustained |
| Model V5 | Comprehensive | OVER | PTS, REB, AST | ~3 | ❌ Derived | Momentum (L3) |
| Model V4 | Balanced | OVER | PTS, REB, AST | ~3 | ❌ Derived | Trend detection |
| Model V3 | Weights | OVER | PTS, REB, AST | ~3 | ❌ Derived | Hot/Cold streak |
| Model V2 | Basic | OVER | PTS, REB, AST | ~3 | ❌ Derived | None |

---

## Detailed Model Analyses

### 🥇 Model V9 - Line-Aware Model

**Date Created:** January 2026  
**File:** `src/nba_props/engine/model_v9.py`  
**Hit Rate:** 68.6%  
**Complexity:** ⭐⭐⭐☆☆

#### What It Does Well
- **Addresses the critical flaw** of previous models by using actual sportsbook lines
- **Line source tracking** - transparently reports whether picks use real or derived lines
- **Conservative projections** with equal weights across L5/L10/L15/Season
- **Pattern detection** for cold bounce-back and hot sustained streaks
- **Version tracking integration** for systematic model comparison

#### What It Does Not Do Well
- **Limited sportsbook line data** - most picks still use derived lines
- **Excludes assists** entirely (may miss opportunities)
- **Only 1 prop per player** - very conservative, limits volume
- **Less sophisticated** than V6/V7 archetype and defense analysis

#### Key Configuration
```python
weight_l5: 0.25
weight_l10: 0.25
weight_l15: 0.25
weight_season: 0.25
line_adjustment_factor: 1.05  # Derived lines typically 5% below actual
min_edge_vs_actual_line: 5.0
max_picks_per_player: 1
```

#### Potential Improvements
1. **Collect more sportsbook lines** - This is the #1 priority
2. **Integrate archetype analysis** from V6 for better player classification
3. **Add defense vs position adjustments** from RCM/Hybrid model
4. **Consider adding assist picks** for high-volume playmakers only

---

### 🥈 Model Production - Pattern-Based Model

**Date Created:** January 2026  
**File:** `src/nba_props/engine/model_production.py`  
**Hit Rate:** 66.7% (232/348 picks)  
**Complexity:** ⭐⭐⭐☆☆

#### What It Does Well
- **Simple but effective** two-pattern system (cold bounce, hot sustained)
- **66.9% hit rate on cold bounce-back** - the strongest pattern discovered
- **Excellent monthly consistency** - no single month underperformed
- **Proper injury filtering** - excludes OUT/DOUBTFUL players
- **PTS hits at 68.6%** - strongest individual prop type

#### What It Does Not Do Well
- **Uses derived lines** instead of actual sportsbook lines (inflated metrics)
- **No UNDER picks** - misses opportunities (UNDER often outperforms OVER)
- **No AST picks** - excluded entirely due to 54% hit rate
- **No opponent defense adjustments** beyond pattern detection
- **No archetype or player tier considerations**

#### Key Configuration
```python
cold_deviation_threshold: -20.0  # L5 20%+ below L15
hot_deviation_threshold: 30.0    # L5 30%+ above L15
bounce_threshold: 0.0            # Last game > L10
sustained_games_above: 3         # 3+ of L5 above L15
prop_types: ['pts', 'reb']       # No assists
```

#### Pattern Performance
| Pattern | Hit Rate | Picks |
|---------|----------|-------|
| Cold Bounce (PREMIUM) | 66.9% | 172/257 |
| Hot Sustained (HIGH) | 65.9% | 60/91 |

#### Potential Improvements
1. **Integrate sportsbook lines** from Model V9
2. **Add UNDER picks** for cold streak continuation patterns
3. **Add defense vs position adjustments** for more edge
4. **Consider archetype-based filtering** (avoid scoring guards)

---

### 🥉 Hybrid Model v1.2

**Date Created:** January 2026  
**File:** `src/nba_props/engine/hybrid_model.py`  
**Hit Rate:** 66.6% (207/311 picks)  
**Complexity:** ⭐⭐⭐⭐☆

#### What It Does Well
- **Best of both worlds** - RCM contribution rates + pattern detection
- **Strong UNDER performance** - 66.9% on UNDER picks
- **Strategic direction selection** - PTS UNDER only, REB both ways
- **Bayesian regression** provides stable projections
- **Opponent DVP adjustments** based on defense rankings

#### What It Does Not Do Well
- **Uses derived lines** (same issue as Model Production)
- **More complex** than Model Production without better results
- **No AST picks** - excluded due to poor performance
- **Pattern filtering too strict** for OVER (requires 16% edge + pattern)

#### Key Configuration
```python
contribution_l5_weight: 0.20
contribution_l10_weight: 0.35
contribution_season_weight: 0.45
regression_strength: 0.35
min_edge_over: 16.0  # Higher bar for OVER
min_edge_under: 13.0  # Lower bar for UNDER
```

#### Performance by Direction
| Direction | Hit Rate | Picks |
|-----------|----------|-------|
| UNDER | 66.9% | 162/242 |
| OVER | 65.2% | 45/69 |

#### Potential Improvements
1. **Integrate sportsbook lines** from Model V9
2. **Simplify** - may not need both RCM and pattern detection
3. **Lower OVER edge requirements** if pattern-confirmed
4. **Add archetype filtering** from Model V6

---

### Model V6 - Archetype-Aware Defense-Focused

**Date Created:** January 2026  
**Files:** `src/nba_props/engine/model_v6/` (modular architecture)  
**Hit Rate:** 58.6% (975 picks)  
**Complexity:** ⭐⭐⭐⭐⭐

#### What It Does Well
- **Most comprehensive architecture** - modular design with separate files
- **Archetype classification** - groups players by play style (10 archetypes)
- **Defense analysis** - tracks rank 1-30 for each position
- **Multi-factor confidence scoring** (6 components, 100 points total)
- **UNDER outperforms OVER** (61.0% vs 56.3%)
- **Stretch Bigs/Traditional Bigs most predictable** (64% hit rate)

#### What It Does Not Do Well
- **58.6% overall** - lower than simpler models
- **Scoring Guards hit at only 51.5%** - should be filtered
- **Complexity doesn't yield proportional improvement**
- **Uses derived lines** instead of actual sportsbook lines
- **No pattern detection** like Model Production

#### Key Configuration
```python
# Archetype-specific adjustments
heliocentric_vs_elite_defense: -0.05
slasher_vs_anchor_big: -0.04
movement_shooter_vs_poor_chase: +0.05

# Defense adjustments (optimized)
elite_defense_adjustment: 0.12  # 12% reduction
terrible_defense_adjustment: 0.12  # 12% boost
```

#### Archetype Performance (Top 5)
| Archetype | Hit Rate | Sample |
|-----------|----------|--------|
| Stretch Bigs | 64.9% | 37 |
| Corner Specialists | 64.0% | 75 |
| Traditional Bigs | 64.0% | 86 |
| Movement Shooters | 62.5% | 48 |
| Heliocentric Creators | 61.6% | 99 |

#### Potential Improvements
1. **Integrate sportsbook lines** immediately
2. **Filter out Scoring Guards** (51.5% hit rate = negative edge)
3. **Add pattern detection** from Model Production
4. **Focus on predictable archetypes** only (Bigs, Corner Specialists)

---

### Model V5 - Comprehensive Data Integration

**Date Created:** January 2026  
**File:** `src/nba_props/engine/model_v5.py`  
**Hit Rate:** ~55% (estimated)  
**Complexity:** ⭐⭐⭐⭐☆

#### What It Does Well
- **Uses ALL available data sources** (10+ data points)
- **Head-to-head history** against specific opponents
- **Archetype tier integration** from database
- **4-window projections** (L3, L5, L10, Season) for momentum tracking
- **Home/away splits** consideration
- **5-star confidence display** system

#### What It Does Not Do Well
- **Lower hit rate despite complexity** - more data ≠ better predictions
- **Still uses derived lines** for edge calculations
- **May overfit** with too many variables
- **No pattern filtering** to identify high-probability situations

#### Key Configuration
```python
# 4-window weights
pts_weight_l3: 0.15   # Momentum
pts_weight_l5: 0.25   # Recent form
pts_weight_l10: 0.35  # Baseline
pts_weight_season: 0.25  # Stability

# H2H weight when available
h2h_weight: 0.25

# Back-to-back adjustments
b2b_penalty: 0.06
extra_rest_bonus: 0.02
```

#### Potential Improvements
1. **Simplify** - remove low-value features
2. **Add pattern detection** from Model Production
3. **Integrate sportsbook lines**
4. **Focus on strongest signals** (defense, patterns, H2H)

---

### RCM v1.4 - Regression Contribution Model

**Date Created:** January 2026  
**File:** `src/nba_props/engine/regression_contribution_model.py`  
**Hit Rate:** 60.4% (191/316 picks)  
**Complexity:** ⭐⭐⭐⭐☆

#### What It Does Well
- **Novel methodology** - contribution rates instead of raw averages
- **Bayesian regression** toward season mean reduces noise
- **PTS UNDER at 63.9%** - strong strategic direction finding
- **PREMIUM tier at 87.5%** (small sample but notable)
- **Team context integration** - accounts for pace and game flow

#### What It Does Not Do Well
- **60.4% overall** - behind pattern-based models
- **Uses derived lines** for edge calculations
- **PTS OVER at only 48.3%** - correctly identified and filtered
- **Complex methodology** without proportional improvement
- **No pattern detection** integration

#### Key Configuration
```python
# Contribution rate windows
contribution_l5_weight: 0.20
contribution_l10_weight: 0.35
contribution_season_weight: 0.45
regression_strength: 0.35

# Strategic: PTS UNDER only, REB both ways
enable_pts_over: False
enable_pts_under: True
enable_reb_over: True
enable_reb_under: True
```

#### Potential Improvements
1. **Integrate pattern detection** from Model Production
2. **Use sportsbook lines** for edge calculation
3. **Add archetype filtering** from V6
4. **Consider hybrid approach** (already done in Hybrid Model)

---

### Model V8 - Learning-Based Model

**Date Created:** January 2026  
**File:** `src/nba_props/engine/model_v8.py`  
**Hit Rate:** ~54% (estimated)  
**Complexity:** ⭐⭐⭐☆☆

#### What It Does Well
- **Generates both OVER and UNDER** picks
- **Calibrated confidence system** (spread across 1-5 stars)
- **Learning weights** that can be adjusted based on performance
- **Star player identification** from archetype database
- **Injury integration** when available

#### What It Does Not Do Well
- **Lower hit rate** than simpler pattern-based models
- **Learning mechanism** not fully utilized
- **Still uses derived lines** instead of actual sportsbook lines
- **Pattern thresholds not optimized** (20% hot vs 30% in Production)

#### Key Configuration
```python
# Pattern thresholds
cold_deviation_threshold: -15.0  # Less strict than Production
hot_deviation_threshold: 20.0    # Less strict than Production (30%)

# Confidence calibration
base_confidence: 35.0
max_confidence: 95.0
edge_bonus_per_pct: 0.8
```

#### Potential Improvements
1. **Adopt Production's stricter thresholds** (30% for hot)
2. **Integrate sportsbook lines**
3. **Implement actual learning loop** with performance feedback
4. **Filter low-confidence picks** more aggressively

---

### Model V4 - Balanced Distribution Model

**Date Created:** January 2026  
**File:** `src/nba_props/engine/model_v4.py`  
**Hit Rate:** ~53% (estimated)  
**Complexity:** ⭐⭐☆☆☆

#### What It Does Well
- **Balanced prop type distribution** (minimum PTS/REB/AST per day)
- **Minimum line thresholds** to avoid trivial picks (AST > 2.5)
- **Star player priority** (>28 min avg = star)
- **Value-weighted scoring** (higher lines = more valuable picks)

#### What It Does Not Do Well
- **Lower hit rate** than pattern-based models
- **Forces variety** which may reduce quality
- **Still uses derived lines**
- **No pattern detection** for high-probability situations

#### Key Configuration
```python
min_pts_line: 5.0
min_reb_line: 2.0
min_ast_line: 2.5
star_minutes_threshold: 28.0
picks_per_game: 3
```

#### Potential Improvements
1. **Remove forced variety** - focus on best picks only
2. **Add pattern detection**
3. **Integrate sportsbook lines**
4. **Filter out AST picks** (proven underperformer)

---

### Model V3 - Stat-Specific Weights

**Date Created:** January 2026  
**File:** `src/nba_props/engine/model_v3.py`  
**Hit Rate:** ~52% (estimated)  
**Complexity:** ⭐⭐☆☆☆

#### What It Does Well
- **First model with stat-specific weights**
- **Floor/ceiling analysis** (10th/90th percentile)
- **Trend detection** (hot/cold/stable classification)
- **Opponent adjustment** integration

#### What It Does Not Do Well
- **Lower hit rate** - weights not optimized
- **Floor/ceiling** added complexity without improvement
- **No pattern detection** for high-probability situations
- **Uses derived lines**

#### Key Configuration
```python
# Stat-specific weights (L5, L15, Season)
ast_weights: (0.30, 0.40, 0.30)
pts_weights: (0.25, 0.45, 0.30)
reb_weights: (0.20, 0.40, 0.40)  # More season for REB
```

#### Potential Improvements
1. **Adopt proven weight configurations** from later models
2. **Add pattern detection**
3. **Remove floor/ceiling** (added complexity without value)
4. **Integrate sportsbook lines**

---

### Model V2 - Basic Weighted Average

**Date Created:** January 2026  
**File:** `src/nba_props/engine/model_v2.py`  
**Hit Rate:** ~51% (estimated)  
**Complexity:** ⭐☆☆☆☆

#### What It Does Well
- **Simple and understandable** methodology
- **Focus on OVER picks** (historically better)
- **Consistency factor** (trust consistent performers)
- **Foundation for later models**

#### What It Does Not Do Well
- **Lowest hit rate** among all models
- **No pattern detection**
- **No opponent adjustments**
- **Uses derived lines**
- **Basic edge calculation** without sophistication

#### Key Configuration
```python
weight_l5: 0.25
weight_l15: 0.45
weight_season: 0.30
high_edge_threshold: 10.0
medium_edge_threshold: 6.0
```

#### Potential Improvements
- Model V2 has been superseded by all later versions
- Not recommended for further development
- Key learnings incorporated into later models

---

### Enhanced Model - Simple L10 Average

**Date Created:** January 2026  
**File:** `src/nba_props/engine/enhanced_model.py`  
**Hit Rate:** ~55% (estimated, OVER focus)  
**Complexity:** ⭐☆☆☆☆

#### What It Does Well
- **Very simple** - just L10 average for projections
- **Disables UNDER picks** (per backtesting - too unreliable)
- **Only PTS and REB** (no AST per poor performance)

#### What It Does Not Do Well
- **Lower hit rate** than pattern-based models
- **Uses L10 as line** (fundamental flaw)
- **No sophisticated edge calculation**
- **No pattern detection**

#### Key Configuration
```python
min_edge_over: 15.0
min_edge_under: 999.0  # Effectively disabled
enabled_prop_types: ("PTS", "REB")
disable_unders: True
```

#### Potential Improvements
- Model is too simple for production use
- Primarily used for baseline comparison
- All improvements should go to newer models

---

### Under Model V2 - UNDER Specialist

**Date Created:** January 2026  
**File:** `src/nba_props/engine/under_model_v2.py`  
**Hit Rate:** ~58% overall, ~66% on Premium picks  
**Complexity:** ⭐⭐⭐☆☆

#### What It Does Well
- **Specialized for UNDER** - different factors than OVER
- **Factor-based scoring** (17 factors with weights)
- **Defense vs Position** as primary factor
- **Premium picks** (elite defense + cold streak) at 66.27%
- **Proper injury filtering**

#### What It Does Not Do Well
- **Overall 58%** - needs better filtering
- **Uses derived lines**
- **Low-confidence picks dilute performance**
- **Too many factors** may cause overfitting

#### Key Factors
| Factor | Weight | Adjustment |
|--------|--------|------------|
| Elite Defense | 30 | -10% |
| Severe Cold Streak | 20 | -12% |
| First Game Back | 18 | -18% |
| Good Defense | 15 | -5% |

#### Potential Improvements
1. **Only take Premium picks** (66%+ hit rate)
2. **Integrate sportsbook lines**
3. **Combine with Pattern detection** for timing
4. **Filter to fewer, higher-confidence picks**

---

### Model V7 - Ensemble Model

**Date Created:** January 2026  
**File:** `src/nba_props/engine/model_v7/` (modular architecture)  
**Hit Rate:** Not fully backtested  
**Complexity:** ⭐⭐⭐⭐⭐

#### What It Does Well
- **Combines all insights** from V2-V6
- **Archetype reliability scores** (boost predictable types)
- **Tier reliability scores** (Starter tier = 65.4% = most predictable)
- **UNDER preference** based on V6 findings
- **H2H weighting** from V5
- **Strategic filtering** (avoids Scoring Guards)

#### What It Does Not Do Well
- **Not fully validated** with backtest
- **Most complex model** - risk of overfitting
- **Still uses derived lines**
- **May be over-engineered**

#### Key Configuration
```python
# Archetype reliability
stretch_bigs: 1.15      # Boost 15%
scoring_guards: 0.90    # Penalize 10%

# Tier reliability
starter_tier: 1.10      # 65.4% hit rate
all_star_tier: 0.92     # 51.7% hit rate (high variance)

# Direction preference
under_preference_weight: 1.08
over_preference_weight: 0.96
```

#### Potential Improvements
1. **Complete backtest validation**
2. **Integrate sportsbook lines**
3. **Simplify** if complexity doesn't yield improvement
4. **Add pattern detection** from Model Production

---

## Key Insights & Learnings

### 1. Critical Flaw: Derived Lines

**Problem:** All models before V9 used player averages (L10, L15) as "betting lines" instead of actual sportsbook lines.

**Impact:** Hit rates were inflated by 5-15%. Example:
- Peyton Watson: Model "line" = 4.9 (L10), Actual sportsbook = 6.5
- Model showed OVER edge, reality showed UNDER opportunity

**Solution:** Model V9 introduced sportsbook line integration. This should be backported to all models.

---

### 2. Pattern Detection Works

**Key Finding:** Simple pattern detection (cold bounce-back, hot sustained) outperforms complex statistical models.

| Approach | Best Hit Rate |
|----------|---------------|
| Pattern-based (Production) | 66.7% |
| Contribution rates (RCM) | 60.4% |
| Archetype-aware (V6) | 58.6% |

**Why:** Patterns identify psychological and statistical regression moments that create real edges.

---

### 3. UNDER Often Outperforms OVER

| Model | UNDER Rate | OVER Rate |
|-------|------------|-----------|
| V6 | 61.0% | 56.3% |
| Hybrid | 66.9% | 65.2% |
| RCM | 60.9% | 59.4% |

**Why:** Negative factors (elite defense, cold streak, fatigue) compound more reliably than positive factors.

---

### 4. Assists Are Unpredictable

| Model | AST Hit Rate |
|-------|--------------|
| Model Production | ~54% (excluded) |
| RCM | 44.8% (excluded) |
| V6 | 59.4% (included) |

**Why:** Assists depend on teammates making shots - high variance.

**Recommendation:** Only include AST for elite playmakers (>8 APG).

---

### 5. Complexity ≠ Performance

| Model | Complexity | Hit Rate |
|-------|------------|----------|
| Model Production | ⭐⭐⭐ | 66.7% |
| Model V6 | ⭐⭐⭐⭐⭐ | 58.6% |
| Model V7 | ⭐⭐⭐⭐⭐ | Not validated |

**Lesson:** Simpler models with focused patterns outperform complex multi-factor models.

---

### 6. Archetype Predictability Varies

| Archetype | Hit Rate | Recommendation |
|-----------|----------|----------------|
| Stretch Bigs | 64.9% | ✅ Target |
| Traditional Bigs | 64.0% | ✅ Target |
| Corner Specialists | 64.0% | ✅ Target |
| Scoring Guards | 51.5% | ❌ Avoid |
| All-Star Tier | 51.7% | ⚠️ Caution |

---

## Future Recommendations

### Priority 1: Sportsbook Line Integration (CRITICAL)

**Action:** Collect and store actual sportsbook lines daily
- Build scraper for major sportsbooks (DraftKings, FanDuel, etc.)
- Backfill historical lines where possible
- Track line movement for additional signals

**Impact:** All performance metrics will become meaningful

---

### Priority 2: Unified Best Model

**Action:** Create Model V10 combining best features:

```python
# Model V10 Blueprint
class ModelV10:
    # From V9: Sportsbook line integration
    use_sportsbook_lines = True
    
    # From Production: Pattern detection
    patterns = ["cold_bounce", "hot_sustained"]
    cold_threshold = -20.0
    hot_threshold = 30.0
    
    # From V6: Archetype filtering
    filter_scoring_guards = True
    boost_predictable_archetypes = True
    
    # From Hybrid: Strategic direction
    pts_under_preferred = True
    reb_both_directions = True
    no_ast = True
    
    # From RCM: Opponent adjustments
    use_dvp_adjustments = True
```

---

### Priority 3: Confidence Calibration

**Action:** Ensure confidence scores reflect true probability
- Calibrate tiers based on historical hit rates
- HIGH confidence should hit at 65%+
- PREMIUM should hit at 70%+

---

### Priority 4: Feature Pruning

**Action:** Remove low-value features from complex models
- V6/V7: Remove archetype adjustments that don't improve performance
- V5: Remove H2H if sample size too small
- All: Focus on 3-5 strongest signals

---

### Priority 5: Real-Time Validation

**Action:** Track live performance daily
- Compare predicted vs actual results
- Update model weights based on performance
- Identify decay in pattern effectiveness

---

## Conclusion

The **Model Production** approach (pattern detection) combined with **Model V9's** sportsbook line awareness represents the best current combination. The key insight is that **simple, focused patterns with real betting lines** outperform complex multi-factor models with derived lines.

**Recommended Active Model:** Model V9 with pattern detection from Model Production

**Next Priority:** Collect sportsbook lines to validate true performance

---

*This document should be updated after each significant model change or backtest.*

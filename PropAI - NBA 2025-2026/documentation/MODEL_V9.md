# Model V9 - Line-Aware Model Documentation

## Overview

Model V9 addresses a **critical flaw** discovered in previous models: using player statistical averages as "betting lines" instead of actual sportsbook lines. This led to **inflated success rates** that didn't reflect real-world betting performance.

---

## The Problem

### Previous Model Behavior

Previous models (including model_production.py) used:

| Pattern | Line Source | What It Means |
|---------|-------------|---------------|
| Cold Bounce | L10 (10-game avg) | Uses player's recent average as the line |
| Hot Sustained | L15 (15-game avg) | Uses player's baseline average as the line |

### Real-World Example

**Peyton Watson (DEN) - Rebounds - January 14, 2026**

| Metric | Value |
|--------|-------|
| Model Projection | 4.9 rebounds |
| Previous Model "Line" | 4.9 (L10 average) |
| **Actual Sportsbook Line** | **6.5 rebounds** |

**Previous model logic:**
- Projection (4.9) vs "Line" (4.9) = No edge → Pass
- Or if hot pattern: Projection higher → OVER looks good

**Reality:**
- Player needs to beat 6.5 rebounds (the REAL line)
- 4.9 projection is BELOW the real line
- This is actually an UNDER opportunity, not OVER

### Impact on Performance Metrics

Using derived lines instead of actual lines:
- **Inflates hit rates** by 5-15% in backtests
- **Creates false confidence** in model predictions
- **Doesn't reflect actual betting profitability**

---

## Model V9 Solution

### Line Sourcing Hierarchy

1. **Sportsbook Line** (Best) - From `sportsbook_lines` table
2. **Adjusted Derived Line** - Player average × 1.05 adjustment factor
3. **Raw Average with Warning** - Flagged for user attention

### Key Changes

```python
# OLD WAY (model_production.py)
line = player_l10_average  # Using player's own average as line
edge = (projection - line) / line  # Edge vs self

# NEW WAY (model_v9.py)
sportsbook_line = get_sportsbook_line(player_id, prop_type, date)
if sportsbook_line:
    line = sportsbook_line
    line_source = "sportsbook"
else:
    line = player_l10_average * 1.05  # Conservative adjustment
    line_source = "derived"

edge_vs_line = (projection - line) / line
edge_vs_sportsbook = (projection - sportsbook_line) / sportsbook_line  # Track separately
```

### Configuration

```python
@dataclass
class ModelConfigV9:
    # Line sourcing
    use_sportsbook_lines: bool = True    # Prefer actual betting lines
    line_adjustment_factor: float = 1.05  # Derived lines typically 5% below actual
    min_edge_vs_actual_line: float = 5.0  # Need 5%+ edge vs ACTUAL line
    
    # More conservative projection weights
    weight_l5: float = 0.25
    weight_l10: float = 0.25
    weight_l15: float = 0.25
    weight_season: float = 0.25
    
    # Stricter pick limits
    max_picks_per_player: int = 1  # Only 1 prop per player (more conservative)
```

---

## Performance Comparison

### Backtest Metrics to Compare

| Metric | Description |
|--------|-------------|
| `hit_rate` | Overall hit rate |
| `sportsbook_line_hit_rate` | Hit rate when using actual sportsbook lines |
| `derived_line_hit_rate` | Hit rate when using derived lines |
| `avg_line_discrepancy` | Average (derived - sportsbook) difference |

### Expected Results

The `sportsbook_line_hit_rate` is the **true measure** of model performance:
- If significantly lower than overall hit rate → Previous model was overfit
- If similar → Model generalizes well to real betting scenarios

---

## Usage

### Daily Picks

```python
from src.nba_props.engine.model_v9 import get_daily_picks_v9

picks = get_daily_picks_v9("2026-01-14")

for pick in picks.picks:
    print(f"{pick.player_name} - {pick.prop_type} {pick.direction} {pick.line}")
    print(f"  Line Source: {pick.line_source}")
    print(f"  Projection: {pick.projection}")
    print(f"  Edge: {pick.edge_vs_line:.1f}%")
    if pick.warnings:
        print(f"  ⚠️ Warnings: {', '.join(pick.warnings)}")
```

### Backtest with Version Tracking

```python
from src.nba_props.engine.model_v9 import run_backtest_v9

result = run_backtest_v9(
    start_date="2025-12-01",
    end_date="2026-01-13",
    track_version=True,  # Saves to version tracker
)

print(result.summary())

# Key metrics to check
print(f"Overall: {result.hit_rate*100:.1f}%")
print(f"With Sportsbook Lines: {result.sportsbook_line_hit_rate*100:.1f}%")
print(f"With Derived Lines: {result.derived_line_hit_rate*100:.1f}%")
print(f"Avg Line Discrepancy: {result.avg_line_discrepancy:.2f}")
```

---

## Pattern Detection

### Cold Bounce (PREMIUM Tier)

**Criteria:**
- L5 is 15%+ below L15 (player in cold streak)
- Last game is 5%+ above L10 (showing recovery)
- Projection must beat the ACTUAL line

**Logic:**
Player is cold but bouncing back → Expect regression toward mean

### Hot Sustained (HIGH Tier)

**Criteria:**
- L5 is 20%+ above L15 (player in hot streak)
- L3 >= L5 × 0.95 (maintaining or accelerating)
- 3+ of last 5 games above L15 (sustained performance)
- Projection must beat the ACTUAL line

**Logic:**
Player is hot and maintaining → Momentum continues

### Consistency Bonus

Players with low variance (CV < 25%) get a confidence boost because their averages are more reliable predictors.

---

## Warnings System

Model V9 includes a warnings system to flag potential issues:

| Warning | Meaning |
|---------|---------|
| "No sportsbook line - using derived estimate" | Actual line not available |
| "Line diff: derived X vs actual Y" | Significant gap between our estimate and actual |

These warnings help users understand when picks may be less reliable.

---

## File Structure

```
src/nba_props/engine/
├── model_v9.py                 # This model
├── model_version_tracker.py    # Version tracking system
├── model_production.py         # Previous model (for comparison)
├── model_lab.py               # Testing framework
└── ...
```

---

## Future Improvements

1. **Historical Line Data**: Collect and store sportsbook lines historically for better backtesting
2. **Line Movement Analysis**: Track how lines move and incorporate into predictions
3. **Multi-Book Comparison**: Compare lines across multiple sportsbooks
4. **Under Picks**: Extend line-aware logic to UNDER predictions
5. **Line Prediction**: Predict what the sportsbook line SHOULD be

---

## Key Takeaways

1. **Always use actual sportsbook lines** when available
2. **Track line source** for every pick to measure true performance
3. **Be conservative** when deriving lines (adjust upward by ~5%)
4. **Sportsbook line hit rate** is the true measure of model quality
5. **Previous high hit rates** were likely inflated by 5-15%

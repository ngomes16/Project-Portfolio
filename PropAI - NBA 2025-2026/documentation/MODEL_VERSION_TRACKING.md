# Model Version Tracking System Documentation

## Overview

The Model Version Tracking System provides comprehensive infrastructure for storing, comparing, and analyzing different model iterations. This enables systematic model improvement through:

1. **Version Control**: Every model configuration gets a unique identifier
2. **Pick Tracking**: All picks are stored with detailed line source information
3. **Backtest History**: Complete backtest results are preserved
4. **Performance Grading**: Models are graded (A-F) based on performance
5. **Insights Storage**: Key learnings and takeaways are documented

---

## Database Schema

### Tables

#### `model_versions`
Core registry of all model iterations.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Human-readable model name |
| version | TEXT | Version string (e.g., "9.0") |
| config_hash | TEXT | Unique hash of configuration |
| config_json | TEXT | Full configuration as JSON |
| is_active | BOOLEAN | Currently active model |
| is_deprecated | BOOLEAN | Model no longer recommended |
| overall_grade | TEXT | A, B, C, D, or F |
| best_hit_rate | REAL | Best historical hit rate |
| avg_hit_rate | REAL | Average hit rate across backtests |

#### `model_version_picks`
All picks made by each model version.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| version_id | INTEGER | Foreign key to model_versions |
| pick_date | TEXT | Date of the pick |
| player_name | TEXT | Player name |
| prop_type | TEXT | PTS, REB, or AST |
| direction | TEXT | OVER or UNDER |
| **line_source** | TEXT | 'sportsbook' or 'derived' |
| **line** | REAL | The line used for the pick |
| **sportsbook_line** | REAL | Actual sportsbook line (if available) |
| **derived_line** | REAL | Our calculated line |
| projection | REAL | Our projection |
| edge_vs_line | REAL | Edge % vs line used |
| edge_vs_sportsbook | REAL | Edge % vs actual sportsbook line |
| actual_value | REAL | Actual result |
| hit | INTEGER | 1=hit, 0=miss, NULL=pending |
| hit_vs_sportsbook | INTEGER | Did it beat the sportsbook line? |

#### `model_version_backtests`
Historical backtest results.

| Column | Type | Description |
|--------|------|-------------|
| version_id | INTEGER | Foreign key to model_versions |
| start_date | TEXT | Backtest start |
| end_date | TEXT | Backtest end |
| total_picks | INTEGER | Total picks made |
| hits | INTEGER | Number of hits |
| hit_rate | REAL | Overall hit rate |
| **picks_with_sportsbook_line** | INTEGER | Picks using actual lines |
| **hits_vs_sportsbook** | INTEGER | Hits when using actual lines |
| **rate_vs_sportsbook** | REAL | Hit rate with actual lines |
| **avg_line_diff** | REAL | Avg (derived - sportsbook) |

#### `model_version_insights`
Key learnings from each model.

| Column | Type | Description |
|--------|------|-------------|
| version_id | INTEGER | Foreign key to model_versions |
| insight_type | TEXT | 'strength', 'weakness', 'key_finding', 'recommendation' |
| category | TEXT | 'pts', 'reb', 'ast', 'overall', 'methodology' |
| insight | TEXT | The insight/learning |
| evidence | TEXT | Supporting data |

---

## Usage Examples

### Registering a New Model Version

```python
from src.nba_props.engine.model_version_tracker import (
    ModelVersionTracker,
    register_model_version,
)

# Register a new model
version_id = register_model_version(
    name="Model V9 - Line Aware",
    version="9.0",
    config={
        "use_sportsbook_lines": True,
        "min_edge_vs_actual_line": 5.0,
        "weight_l5": 0.25,
        "weight_l10": 0.25,
    },
    description="Enhanced model using actual sportsbook lines",
    set_active=True,  # Make this the active model
)
```

### Saving Picks with Line Tracking

```python
from src.nba_props.engine.model_version_tracker import (
    ModelVersionTracker, VersionPick
)

tracker = ModelVersionTracker()

# Create picks with line source tracking
picks = [
    VersionPick(
        version_id=version_id,
        pick_date="2026-01-14",
        player_id=123,
        player_name="Peyton Watson",
        team_abbrev="DEN",
        opponent_abbrev="LAL",
        prop_type="REB",
        direction="OVER",
        line_source="sportsbook",  # Using actual betting line
        line=6.5,                  # The sportsbook line
        sportsbook_line=6.5,
        derived_line=4.9,          # What we would have calculated
        projection=7.2,            # Our projection
        edge_vs_line=10.8,         # 7.2/6.5 - 1 = 10.8%
        edge_vs_sportsbook=10.8,
    ),
]

tracker.save_picks(version_id, picks)
```

### Running Backtest with Version Tracking

```python
from src.nba_props.engine.model_v9 import run_backtest_v9

# This automatically registers the model and saves all results
result = run_backtest_v9(
    start_date="2025-12-01",
    end_date="2026-01-13",
    track_version=True,  # Enable version tracking
)

print(result.summary())
```

### Comparing Model Versions

```python
from src.nba_props.engine.model_version_tracker import ModelVersionTracker

tracker = ModelVersionTracker()

# Compare specific versions
comparison = tracker.compare_versions(
    version_ids=[1, 2, 3],
    start_date="2025-12-01",
    end_date="2026-01-13",
)

print(f"Winner: {comparison['winner']['name']}")
print(f"Hit Rate: {comparison['winner']['hit_rate']*100:.1f}%")

# Get full comparison report
print(tracker.get_comparison_report())
```

### Viewing Model Insights

```python
insights = tracker.get_insights(version_id)

for insight in insights:
    print(f"[{insight.insight_type.upper()}] {insight.category}")
    print(f"  {insight.insight}")
    if insight.evidence:
        print(f"  Evidence: {insight.evidence}")
```

---

## Key Features

### Line Source Tracking

The most critical improvement is tracking whether a pick used an actual sportsbook line or a derived estimate:

```python
# When sportsbook line is available
if sportsbook_line:
    line = sportsbook_line
    line_source = "sportsbook"
else:
    line = derived_line * 1.05  # Apply adjustment
    line_source = "derived"
```

This allows us to measure:
- **True Performance**: Hit rate when using actual betting lines
- **Line Discrepancy**: How much our estimates differ from actual lines
- **Model Calibration**: Are we over/under-estimating player performance?

### Model Grading

Models are automatically graded based on performance:

| Grade | Hit Rate |
|-------|----------|
| A | ≥ 65% |
| B | 58-64% |
| C | 52-57% |
| D | 48-51% |
| F | < 48% |

### Automated Insights

The system automatically generates insights during backtests:

```python
# Example auto-generated insights
"Sportsbook line hit rate: 58.3%"  # key_finding
"Avg line discrepancy: -1.2"       # key_finding
"Better at predicting PTS than REB" # strength
```

---

## Integration with Model Lab

The Model Lab has been enhanced to integrate with version tracking:

```python
from src.nba_props.engine.model_lab import (
    register_and_backtest_model,
    compare_all_tracked_models,
    lab_comprehensive_test,
)

# Run comprehensive test with tracking
results = lab_comprehensive_test(
    days_back=60,
    track_versions=True,
)

# View all tracked models
print(compare_all_tracked_models())
```

---

## Best Practices

1. **Always Track Line Source**: Never assume the line; always track whether it's from sportsbook or derived
2. **Use Actual Lines When Available**: Sportsbook lines are more accurate for measuring real-world performance
3. **Apply Adjustment Factor**: Derived lines tend to be ~5% below actual lines
4. **Grade Picks Promptly**: Grade picks as soon as game results are available
5. **Document Insights**: Add insights manually for key learnings not captured automatically
6. **Compare Regularly**: Run version comparisons periodically to track improvement

---

## File Locations

- **Model Version Tracker**: `src/nba_props/engine/model_version_tracker.py`
- **Model V9 (Line-Aware)**: `src/nba_props/engine/model_v9.py`
- **Model Lab (Enhanced)**: `src/nba_props/engine/model_lab.py`
- **This Documentation**: `documentation/MODEL_VERSION_TRACKING.md`

# Enhanced UNDER Model V2 Documentation

## Overview

The Under Model V2 is a specialized NBA player props prediction model focused exclusively on identifying **UNDER** opportunities. Unlike general models that try to predict both over and under, this model leverages specific factors that historically correlate with underperformance.

**Target Performance:** 66%+ hit rate on HIGH confidence picks

**Backtested Results (Oct 2025 - Jan 2026):**
- Overall: ~55% hit rate (all picks)
- HIGH Confidence: 60-65% hit rate
- **Premium Picks (Elite Defense + Cold Streak):** 66.27% hit rate

---

## Core Philosophy

> **UNDER picks are more predictable than OVER picks because negative factors compound more reliably than positive ones.**

Key insights:
1. Elite defenses consistently limit player production across positions
2. Cold streaks tend to persist longer than hot streaks due to psychology
3. Fatigue effects (back-to-back games) are measurable and consistent
4. High variance players are more likely to hit unders on any given night

---

## Data Sources

### 1. Defense vs Position (PRIMARY SOURCE)
**Source:** Hashtag Basketball  
**Update Frequency:** Weekly during season

This is the most important data source for the model. It provides:
- Defense rankings per position (PG, SG, SF, PF, C)
- Stats allowed per 48 minutes (normalized)
- Overall rank (1-150 across all positions)
- Position-specific ranks (1-30)

**How to Parse:**
```bash
# CLI command to parse defense data
python -m src.nba_props.cli parse-defense "raw_text_file.txt"
```

**Table:** `team_defense_vs_position`
```sql
CREATE TABLE team_defense_vs_position (
    position TEXT,           -- PG, SG, SF, PF, C
    team_abbrev TEXT,        -- BOS, LAL, etc.
    overall_rank INTEGER,    -- 1-150 (cross-position)
    pts_allowed REAL,        -- Points allowed per 48 min
    pts_rank INTEGER,        -- 1-30 at position
    reb_allowed REAL,        -- Rebounds allowed per 48 min  
    reb_rank INTEGER,        -- 1-30 at position
    ast_allowed REAL,        -- Assists allowed per 48 min
    ast_rank INTEGER,        -- 1-30 at position
    source TEXT,             -- Data source
    last_updated TEXT        -- Timestamp
);
```

### 2. Box Score History
**Source:** Internal database from boxscore ingestion

Provides:
- Season averages
- Recent averages (L5, L10, L20)
- Standard deviation (variance)
- Historical vs specific opponent

### 3. Player Position Mapping
Maps player positions to the 5 defensive categories:
- **PG:** Point Guard
- **SG:** Shooting Guard
- **SF:** Small Forward
- **PF:** Power Forward
- **C:** Center

Hybrid positions (G-F, F-C) are mapped to primary defensive assignments.

---

## Factor Analysis

### Primary Factors (Highest Weight)

| Factor | Weight | Adjustment | Description |
|--------|--------|------------|-------------|
| `defense_elite` | 30 | 0.90 | Top 5 defense at position (10% reduction) |
| `cold_streak_severe` | 20 | 0.88 | L5 avg < 80% of season avg (12% reduction) |
| `injury_first_back` | 18 | 0.82 | First game back from injury (18% reduction) |

### Secondary Factors (Medium Weight)

| Factor | Weight | Adjustment | Description |
|--------|--------|------------|-------------|
| `defense_good` | 15 | 0.95 | Top 10 defense at position (5% reduction) |
| `cold_streak_mild` | 12 | 0.94 | L5 avg < 90% of season avg (6% reduction) |
| `injury_second_back` | 12 | 0.90 | Second game back from injury |
| `elite_defender` | 10 | 0.92 | Facing elite defender matchup |
| `historical_struggle` | 10 | 0.94 | Poor history vs opponent |

### Tertiary Factors (Lower Weight)

| Factor | Weight | Adjustment | Description |
|--------|--------|------------|-------------|
| `b2b_second` | 8 | 0.96 | Second game of back-to-back |
| `low_minutes_proj` | 8 | 0.92 | Expected low minutes |
| `high_variance` | 6 | 0.97 | Inconsistent performer |
| `injury_third_back` | 6 | 0.95 | Third game back from injury |
| `b2b_third_in_four` | 5 | 0.98 | Third game in 4 nights |
| `defense_average` | 5 | 0.98 | Top 15 defense (minimal impact) |
| `home_disadvantage` | 3 | 0.99 | Away player vs strong home defense |

---

## Confidence Scoring

### Confidence Thresholds (REVISED v2.2)

The confidence scoring has been recalibrated to be more discriminating:

- **HIGH:** Score ≥ 85 (Premium picks - elite defense + cold streak)
- **MEDIUM:** Score ≥ 65 (Good picks - elite defense OR multiple factors)
- **LOW:** Score ≥ 55 (Average picks - filtered out in most cases)

### Star Rating Calculation

| Stars | Score Range | Description |
|-------|-------------|-------------|
| ★★★★★ (5) | ≥ 90 | Premium picks (elite defense + cold streak + bonus factors) |
| ★★★★☆ (4) | 80-89 | HIGH tier (elite defense with supporting factors) |
| ★★★☆☆ (3) | 70-79 | MEDIUM tier high end |
| ★★☆☆☆ (2) | 60-69 | MEDIUM tier low end |
| ★☆☆☆☆ (1) | < 60 | LOW tier |

### Score Calculation (v2.2)

```python
# Raw score = sum of factor weights
raw_score = sum(weight for active_factor in factors)

# Confidence mapping (calibrated for discrimination)
if raw_score >= 50:
    # Premium tier: Elite defense + cold streak + others
    confidence_score = 85 + min(15, (raw_score - 50) * 0.3)
elif raw_score >= 30:
    # Good tier: Elite defense alone OR good defense + cold streak
    confidence_score = 65 + (raw_score - 30) * 1.0
elif raw_score >= 20:
    # Average tier: Good defense + minor factors
    confidence_score = 55 + (raw_score - 20) * 1.0
else:
    # Weak tier - filtered out
    confidence_score = 40 + raw_score

# Cap at 100
confidence_score = min(100, confidence_score)

# Tier determination
if confidence_score >= 85:
    tier = "HIGH"
elif confidence_score >= 65:
    tier = "MEDIUM"
else:
    tier = "LOW"
```

### Premium Pick Identification
A pick is considered "premium" when it has multiple strong factors:
- Elite Defense (rank ≤ 5) + Cold Streak Severe = best combination
- This combination indicates both external (defense) and internal (form) factors align

---

## Injury Filtering (NEW v2.2)

**Players marked OUT in the injury report are automatically excluded from picks.**

The model queries the `injury_report` table for the game date and filters out any players with `status = 'OUT'`. This ensures:
- No picks are made for players who won't play
- Users don't waste bets on unavailable players
- Results can be accurately graded

---

## Backtest Results

### December 2025 Analysis (v2.2)

**Overall Performance:**
| Metric | Value |
|--------|-------|
| Total Picks Analyzed | 391 |
| Overall Hit Rate | 57.8% |

**By Confidence Tier:**
| Tier | Picks | Hit Rate |
|------|-------|----------|
| HIGH (≥85) | 183 | **59.6%** |
| MEDIUM (65-84) | 208 | 56.2% |

**By Prop Type:**
| Prop | Picks | Hit Rate |
|------|-------|----------|
| PTS | 352 | 57.1% |
| REB | 37 | 62.2% |
| AST | 2 | 100.0% |

**Top Factor Effectiveness:**
| Factor | Picks | Hit Rate |
|--------|-------|----------|
| Cold Streak Mild | 62 | **64.5%** |
| Defense Good | 73 | 60.3% |
| Home Disadvantage | 182 | 59.3% |
| B2B Third in Four | 150 | 58.7% |
| Defense Elite | 300 | 58.3% |

### Key Insights from Backtesting

1. **Elite Defense is the strongest single factor**
   - Top 5 defense at position correlates with consistent underperformance
   - Effect is most pronounced for scoring (PTS)

2. **Cold streaks compound with defense**
   - Players already in a slump are more vulnerable against good defenses
   - The combination effect is multiplicative, not additive

3. **Back-to-back impact is smaller than expected**
   - B2B alone: ~52% hit rate
   - Should be used as supporting factor, not primary

4. **Variance matters for selection**
   - High variance players are better under candidates
   - Consistent players rarely have blow-under games

---

## API Endpoints

### Generate Picks (Recommended - Auto-Merged)
```
POST /api/backtesting/generate-picks
{
    "date": "2026-01-05",
    "force": false
}
```
When using the default V8 model, UNDER picks from Under V2 are automatically included.
- Response includes `under_v2_count` field showing how many UNDER picks are from Under V2
- Response includes `merged_under_v2` boolean indicating auto-merge was applied

### Generate Under V2 Picks Only
```
POST /api/backtesting/generate-picks
{
    "date": "2026-01-05",
    "force": false,
    "model": "under_v2"
}
```

### Matchup Analysis (Includes Under V2 UNDER Plays)
```
POST /api/matchup-analysis
{
    "away_team": "LAL",
    "home_team": "BOS",
    "date": "2026-01-05"
}
```
Response includes `best_under_plays` with Under V2 picks marked with `source: "under_v2"`.

### Run Backtest
```
POST /api/under-v2/backtest
{
    "start_date": "2025-12-01",
    "end_date": "2025-12-31",
    "min_confidence": 60,
    "confidence_tier": "HIGH"  // Optional filter
}
```

### Analyze Specific Matchup (Under V2 Only)
```
POST /api/under-v2/analyze-matchup
{
    "away_team": "LAL",
    "home_team": "BOS", 
    "game_date": "2026-01-05"
}
```

### Get Defense Data
```
GET /api/under-v2/defense-data
```

---

## Usage in Web Interface

### Automatic Integration with V8 Model (Recommended)

When using the **V8 Combined** model (default), the system **automatically merges** Under V2 UNDER picks with V8 OVER picks:

- **V8 Model:** Generates primarily OVER picks due to strict pattern requirements
- **Under V2:** Generates specialized UNDER picks using defense and streak factors
- **Combined Result:** 30 picks = ~20 OVER (v8) + ~10 UNDER (under_v2)

This provides the best of both worlds without manual model switching.

### Model Selection (Manual Override)
1. Navigate to **Model Performance** tab
2. Use the model selector dropdown to choose:
   - **V8 Combined** (Default) - OVER picks from V8 + UNDER picks from Under V2
   - **Under V2** - UNDER picks only
   - **Production/V5/V4** - Legacy models for both directions
3. Click **Generate Picks** for the selected date

### Matchups Tab Integration

The **Matchups** tab also integrates Under V2 automatically:
- **Best OVER Plays:** From the primary model analysis
- **Best UNDER Plays:** From Under V2 analysis (shown in separate section)

Each UNDER play shows:
- **Source:** `under_v2` indicator
- **Factors:** Active factors (defense_elite, cold_streak_severe, etc.)
- **Confidence:** Score-based tier (HIGH/MEDIUM/LOW)

### Interpreting Results
- **Direction:** UNDER picks focus on underperformance prediction
- **Line:** Shows the player's season average (threshold for under)
- **Projection:** The model's projected value after adjustments
- **Confidence:** HIGH = best opportunities (66.27% historical hit rate)
- **Factors:** Shows which factors triggered the pick

### Best Practices
1. **Focus on HIGH confidence picks** - They have the best hit rate
2. **Look for multiple factors** - Elite defense + cold streak = premium
3. **Check defense data freshness** - Ensure data is recently updated
4. **Consider game context** - B2B, injury status add context
5. **Use V8 Combined for daily betting** - Gets best OVER and UNDER picks together

---

## Code Structure

### Main Files
```
src/nba_props/engine/under_model_v2.py    # Core model implementation
src/nba_props/ingest/defense_position_parser.py  # Defense data parser
src/nba_props/web/app.py                  # API endpoints
```

### Key Classes
- `PlayerStats` - Comprehensive player statistics
- `DefenseProfile` - Defense vs position data for a team
- `UnderAnalysis` - Detailed analysis for an UNDER pick
- `UnderModelResult` - Results from model execution

### Key Functions
```python
# Generate under picks for a matchup
generate_under_picks_v2(conn, away_abbrev, home_abbrev, game_date) -> UnderModelResult

# Get top under picks across all games
get_top_under_picks_v2(conn, game_date, max_picks=10, min_confidence=60.0) -> List[UnderAnalysis]

# Run comprehensive backtest
backtest_under_model_v2(conn, start_date, end_date, min_confidence=60.0, confidence_tier=None) -> Dict

# Format pick for web display
format_under_pick_for_display(analysis: UnderAnalysis) -> Dict
```

---

## Updating Defense Data

### Manual Update via CLI
```bash
# 1. Copy raw data from Hashtag Basketball (tab-separated)
# 2. Save to a file, e.g., defense_data.txt
# 3. Run parser

python -m src.nba_props.cli parse-defense "defense_data.txt"
```

### Expected Data Format
The parser expects tab-separated data from Hashtag Basketball:
```
#	TEAM	GP	W	L	MIN	PTS	REB	AST	STL	BLK	TOV	PF	FGM	FGA	FG%	...
1	BOS	45	35	10	48.0	22.5	6.8	5.2	...
2	CLE	44	33	11	48.0	23.1	7.2	5.0	...
```

Each position (PG, SG, SF, PF, C) should be parsed separately and includes:
- Overall rank (1-150 total, 1-30 per position)
- Points allowed per 48 minutes
- Rebounds allowed per 48 minutes
- Assists allowed per 48 minutes

---

## Future Improvements


### Planned Enhancements
1. **Dynamic weight learning** - Adjust weights based on recent performance
2. **Matchup-specific adjustments** - Player-vs-player historical data
3. **Rest day analysis** - Days since last game impact
4. **Pace factor** - Account for game pace effects
5. **Line value integration** - Consider where the betting line is set

### Known Limitations
1. Defense data requires manual updates
2. Position mapping may miss some hybrid players
3. ~~Injury data integration is not fully automated~~ ✅ Fixed in v2.2
4. Sample size can be small for some factor combinations

---

## Changelog

### Version 2.2 (January 2026)
- **Injury Filtering** - Players marked OUT in injury report are automatically excluded from picks
- **Confidence Scoring Recalibration**:
  - New formula maps raw_score to more discriminating confidence levels
  - HIGH tier now requires score ≥ 85 (was 75)
  - MEDIUM tier now starts at 65 (was 60)
  - Star ratings properly distributed (1-5 stars vs. all 5 stars before)
- **Improved Sorting** - Picks sorted by confidence score, then by factor count
- **Better Hit Rate** - HIGH tier picks now achieving 59.6% hit rate (Dec 2025 backtest)
- Added `_calculate_confidence_stars()` helper function for consistent star calculations
- Added `get_injured_players_for_date()` for efficient batch injury checking

### Version 2.1 (January 2026)
- **Auto-merge with V8 model** - Under V2 UNDER picks now automatically combined with V8 OVER picks
- **Matchups tab integration** - Best UNDER Plays section now shows Under V2 picks
- Fixed historical date backtesting by checking both `scheduled_games` and `games` tables
- Added `source: "under_v2"` marker to identify Under V2 picks in combined results

### Version 2.0 (January 2026)
- Initial release of enhanced UNDER model
- Integration with Hashtag Basketball defense data
- Comprehensive factor weighting system
- Web interface integration
- Backtest framework with factor analysis

---

## Contact & Support

For issues or improvements related to the UNDER model:
1. Check defense data freshness via `/api/under-v2/defense-data`
2. Run backtest to verify model performance
3. Review factor effectiveness in backtest results

**Model Maintained By:** PropAI System

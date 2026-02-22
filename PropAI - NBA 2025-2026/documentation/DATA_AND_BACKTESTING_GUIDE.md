# Data Sources & Backtesting Guide

## Overview

PropAI is a comprehensive NBA player props prediction system that ingests data from multiple sources to generate high-confidence betting recommendations. This document thoroughly explains:

1. **All Data Sources** - What data is used and where it comes from
2. **Database Schema** - How data is stored in SQLite
3. **Data Access Methods** - How to query and use the data
4. **Backtesting Procedures** - How to run thorough backtests to validate models

---

## Table of Contents

- [Data Sources](#data-sources)
  - [Box Scores](#1-box-scores)
  - [Matchups/Schedule](#2-matchupsschedule)
  - [Injury Reports](#3-injury-reports)
  - [Salary Data](#4-salary-data)
  - [Defense vs Position (Hashtag Basketball)](#5-defense-vs-position-hashtag-basketball)
  - [Player DRTG (Defensive Rating)](#6-player-drtg-defensive-rating)
  - [Sportsbook Lines](#7-sportsbook-lines)
- [Database Schema](#database-schema)
- [Accessing Data](#accessing-data)
- [Running Backtests](#running-backtests)
- [Web Interface Tabs](#web-interface-tabs)

---

## Data Sources

### 1. Box Scores

**Source:** ESPN, Basketball Reference, or manually pasted from any source  
**Parser:** `src/nba_props/ingest/boxscore_parser.py`  
**Storage:** `boxscore_player` and `boxscore_team_totals` tables

Box scores are the **foundational data** for all projections. Each box score contains:

#### Player-Level Data (PlayerLine dataclass)
```python
@dataclass
class PlayerLine:
    name: str           # Player name (e.g., "Luka Dončić")
    position: str       # Position (G, F, C, G-F, etc.)
    min: str           # Minutes played ("35:22")
    fgm: int           # Field goals made
    fga: int           # Field goals attempted
    tpm: int           # 3-pointers made
    tpa: int           # 3-pointers attempted
    ftm: int           # Free throws made
    fta: int           # Free throws attempted
    oreb: int          # Offensive rebounds
    dreb: int          # Defensive rebounds
    reb: int           # Total rebounds
    ast: int           # Assists
    stl: int           # Steals
    blk: int           # Blocks
    tov: int           # Turnovers
    pf: int            # Personal fouls
    plus_minus: int    # Plus/minus
    pts: int           # Points scored
```

#### Team Totals (TeamTotals dataclass)
```python
@dataclass
class TeamTotals:
    team_name: str      # Full team name
    team_abbrev: str    # 3-letter abbreviation
    fgm: int, fga: int  # Field goals
    tpm: int, tpa: int  # 3-pointers
    ftm: int, fta: int  # Free throws
    oreb: int, dreb: int, reb: int  # Rebounds
    ast: int, stl: int, blk: int    # Other stats
    tov: int, pf: int, pts: int     # Turnovers, fouls, points
    q1: int, q2: int, q3: int, q4: int  # Quarter scores
    ot: Optional[int]   # Overtime (if applicable)
```

#### How to Add Box Score Data

**Option 1: Web Interface (Recommended)**
1. Go to `/paste` in the web interface
2. Paste raw box score text from any source
3. System auto-parses and saves to database

**Option 2: CLI**
```bash
python -m nba_props ingest-boxscore path/to/boxscore.txt
```

**Option 3: File Drop**
Place files in `data/raw/boxscores/2025-26/YYYY-MM-DD/`

---

### 2. Matchups/Schedule

**Source:** ESPN, Vegas lines, or manually pasted  
**Parser:** `src/nba_props/ingest/matchups_parser.py`  
**Storage:** `games` table

Matchup data includes the game schedule with betting lines:

#### Parsed Data (MatchupLine dataclass)
```python
@dataclass
class MatchupLine:
    game_time: str      # "7:30 PM ET"
    away_team: str      # "Dallas Mavericks"
    home_team: str      # "Boston Celtics"
    spread: Optional[float]     # -5.5 (negative = home favored)
    over_under: Optional[float] # 225.5
```

#### Sample Input Format
```
7:30 PM ET    Dallas Mavericks @ Boston Celtics    DAL -2.5    O/U 225.5
8:00 PM ET    Lakers @ Warriors    LAL +3    O/U 230
```

#### How to Add Matchup Data

**Web Interface:**
1. Go to `/matchups` tab
2. Paste upcoming matchups
3. System parses and shows projections

---

### 3. Injury Reports

**Source:** NBA Official Injury Report, ESPN, Rotowire  
**Parser:** `src/nba_props/ingest/injury_parser.py`  
**Storage:** `injury_report` table

Injury data is **critical** for accurate projections - missing players dramatically affect teammate usage.

#### Parsed Data (InjuryEntry dataclass)
```python
@dataclass
class InjuryEntry:
    team: str           # "Phoenix Suns"
    player: str         # "Kevin Durant"
    status: str         # "OUT", "QUESTIONABLE", "PROBABLE", "DOUBTFUL"
    reason: str         # "Left Knee Soreness"
```

#### Status Definitions
| Status | Meaning | Model Treatment |
|--------|---------|-----------------|
| OUT | Will not play | Removed from projections, usage redistributed |
| DOUBTFUL | Unlikely to play | Treated as OUT |
| QUESTIONABLE | May play, uncertain | Flagged, projections adjusted |
| PROBABLE | Likely to play | Normal projections with slight caution |

#### Sample Input Format
```
Phoenix Suns
Kevin Durant - OUT - Calf Strain
Bradley Beal - QUESTIONABLE - Back Tightness

Milwaukee Bucks
Damian Lillard - PROBABLE - Rest
```

#### How to Add Injury Data

**Web Interface:**
1. Go to paste/data page
2. Paste injury report
3. Auto-parsed and stored

---

### 4. Salary Data

**Source:** Spotrac, HoopsHype, ESPN  
**Parser:** `src/nba_props/ingest/salary_parser.py`  
**Storage:** `player_salaries` table

Salary data helps identify:
- Star players (high salary = high usage)
- Role players
- Expected minutes distribution

#### Parsed Data (PlayerSalary dataclass)
```python
@dataclass
class PlayerSalary:
    rank: int           # Overall salary rank
    name: str           # "Stephen Curry"
    position: str       # "PG"
    team: str           # "GSW"
    salary: int         # 55761217 (in dollars)
```

#### How to Add Salary Data

Paste salary data with format:
```
Rank    Player          Position    Team    Salary
1       Stephen Curry   PG          GSW     $55,761,217
2       Nikola Jokic    C           DEN     $51,415,938
```

---

### 5. Defense vs Position (Hashtag Basketball)

**Source:** [Hashtag Basketball](https://hashtagbasketball.com/nba-defense-vs-position)  
**Parser:** `src/nba_props/ingest/defense_position_parser.py`  
**Storage:** `team_defense_vs_position` table

This is **THE MOST CRITICAL DATA SOURCE** for the UNDER model. It shows how each team defends against each position.

#### What It Measures

For each NBA team and each position (PG, SG, SF, PF, C):
- **PTS Allowed Rank** - How many points they allow to that position (1 = best defense)
- **REB Allowed Rank** - How many rebounds they allow (1 = best)
- **AST Allowed Rank** - How many assists they allow (1 = best)
- **3PM Allowed Rank** - How many 3-pointers they allow

#### Parsed Data (DefenseVsPositionRow dataclass)
```python
@dataclass
class DefenseVsPositionRow:
    team: str           # "BOS"
    position: str       # "PG"
    pts: float          # Points allowed per game to position
    pts_rank: int       # Rank 1-30 (1 = fewest allowed)
    reb: float          # Rebounds allowed
    reb_rank: int
    ast: float          # Assists allowed
    ast_rank: int
    tpm: float          # 3-pointers made allowed
    tpm_rank: int
```

#### Example: Interpreting Defense Data

If Boston Celtics have:
- PG PTS Rank: 2 (elite - allow very few PTS to opposing PGs)
- PG AST Rank: 3 (elite - allow very few AST to opposing PGs)
- PG REB Rank: 15 (average)

**Implication:** When a PG faces Boston, bet UNDER on their PTS and AST, but avoid REB unders.

#### How to Add Defense vs Position Data

1. Visit [Hashtag Basketball Defense vs Position](https://hashtagbasketball.com/nba-defense-vs-position)
2. Select a position (PG, SG, SF, PF, C)
3. Copy the table
4. Paste in PropAI's data page
5. Repeat for all 5 positions

**Sample Format:**
```
TEAM	PTS	Rank	REB	Rank	AST	Rank	3PM	Rank
BOS	18.2	1	2.4	8	5.1	2	2.1	3
CLE	19.5	4	2.8	15	5.8	7	2.5	10
```

#### Defense Rating Thresholds
```python
ELITE_DEFENSE_THRESHOLD = 5      # Top 5 = elite defense
GOOD_DEFENSE_THRESHOLD = 10      # Top 10 = good defense
AVERAGE_DEFENSE_THRESHOLD = 15   # Top 15 = average
POOR_DEFENSE_THRESHOLD = 25      # 16-25 = below average
```

---

### 6. Player DRTG (Defensive Rating)

**Source:** NBA.com, Basketball Reference Advanced Stats  
**Parser:** `src/nba_props/ingest/player_drtg_parser.py`  
**Storage:** `player_drtg` table

Individual player defensive ratings - lower = better defender.

#### Parsed Data (PlayerDRTG dataclass)
```python
@dataclass
class PlayerDRTG:
    name: str           # "Jrue Holiday"
    team: str           # "BOS"
    drtg: float         # 102.3 (lower = better)
```

#### DRTG Scale
- **Elite (< 105):** Outstanding individual defender
- **Good (105-110):** Above-average defender
- **Average (110-115):** League average
- **Poor (> 115):** Defensive liability

#### Use Cases
- Identify elite defenders for matchup adjustments
- Flag difficult defensive assignments
- Adjust UNDER confidence when facing elite defenders

---

### 7. Sportsbook Lines

**Source:** DraftKings, FanDuel, BetMGM, ESPN  
**Parser:** `src/nba_props/ingest/lines_parser.py`  
**Storage:** `sportsbook_lines` table

**CRITICAL:** Actual sportsbook lines are essential for accurate model validation.

#### Parsed Data
```python
# Lines table stores:
- player_id: int
- game_id: int
- prop_type: str      # "PTS", "REB", "AST", "3PM", "BLK", "STL"
- line_value: float   # 25.5
- over_odds: int      # -110
- under_odds: int     # -110
- source: str         # "DraftKings"
- captured_at: datetime
```

#### Why Sportsbook Lines Matter

**The Problem We Solved:**
Previous model versions used player averages (L10, L15) as "lines" for backtesting. This artificially inflated hit rates because:
- Player averages ARE their expected performance
- Sportsbook lines include juice/edge for the house
- Real lines are often different from simple averages

**Model V9 Fix:**
- Fetches actual sportsbook lines from database when available
- Tracks whether each pick used real or derived lines
- Reports hit rates separately for sportsbook vs derived lines

#### How to Add Sportsbook Lines

```
Player          Prop    Line    Over    Under
LeBron James    PTS     25.5    -115    -105
LeBron James    REB     7.5     -110    -110
LeBron James    AST     8.5     -120    +100
```

---

## Database Schema

All data is stored in SQLite at `data/db/nba_props.sqlite3`.

### Core Tables

```sql
-- Teams
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    name TEXT,
    abbrev TEXT UNIQUE
);

-- Players
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    name TEXT,
    team_id INTEGER REFERENCES teams(id),
    position TEXT
);

-- Games
CREATE TABLE games (
    id INTEGER PRIMARY KEY,
    date TEXT,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_score INTEGER,
    away_score INTEGER,
    status TEXT
);

-- Box Score (Player Stats)
CREATE TABLE boxscore_player (
    id INTEGER PRIMARY KEY,
    game_id INTEGER REFERENCES games(id),
    player_id INTEGER REFERENCES players(id),
    team_id INTEGER REFERENCES teams(id),
    minutes TEXT,
    pts INTEGER, reb INTEGER, ast INTEGER,
    fgm INTEGER, fga INTEGER,
    tpm INTEGER, tpa INTEGER,
    ftm INTEGER, fta INTEGER,
    oreb INTEGER, dreb INTEGER,
    stl INTEGER, blk INTEGER,
    tov INTEGER, pf INTEGER,
    plus_minus INTEGER
);

-- Sportsbook Lines
CREATE TABLE sportsbook_lines (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    game_id INTEGER REFERENCES games(id),
    prop_type TEXT,
    line_value REAL,
    over_odds INTEGER,
    under_odds INTEGER,
    source TEXT,
    captured_at TEXT
);

-- Injury Report
CREATE TABLE injury_report (
    id INTEGER PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    player_id INTEGER REFERENCES players(id),
    status TEXT,
    reason TEXT,
    report_date TEXT
);

-- Team Defense vs Position (Hashtag Basketball)
CREATE TABLE team_defense_vs_position (
    id INTEGER PRIMARY KEY,
    team_abbrev TEXT,
    position TEXT,
    pts_allowed REAL, pts_rank INTEGER,
    reb_allowed REAL, reb_rank INTEGER,
    ast_allowed REAL, ast_rank INTEGER,
    tpm_allowed REAL, tpm_rank INTEGER,
    updated_at TEXT
);

-- Player Defensive Rating
CREATE TABLE player_drtg (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    drtg REAL,
    season TEXT
);

-- Player Salaries
CREATE TABLE player_salaries (
    id INTEGER PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    salary INTEGER,
    rank INTEGER,
    season TEXT
);
```

### Model Version Tracking Tables (NEW)

```sql
-- Model Versions
CREATE TABLE model_versions (
    id INTEGER PRIMARY KEY,
    version_name TEXT UNIQUE,
    description TEXT,
    config_json TEXT,
    created_at TEXT
);

-- Model Picks
CREATE TABLE model_version_picks (
    id INTEGER PRIMARY KEY,
    version_id INTEGER REFERENCES model_versions(id),
    game_id INTEGER,
    game_date TEXT,
    player_name TEXT,
    prop_type TEXT,
    direction TEXT,
    projected REAL,
    line REAL,
    line_source TEXT,
    edge_pct REAL,
    confidence_score REAL,
    confidence_tier TEXT,
    actual_value REAL,
    hit INTEGER
);

-- Backtest Results
CREATE TABLE model_version_backtests (
    id INTEGER PRIMARY KEY,
    version_id INTEGER REFERENCES model_versions(id),
    start_date TEXT,
    end_date TEXT,
    total_picks INTEGER,
    hits INTEGER,
    hit_rate REAL,
    results_json TEXT,
    run_at TEXT
);
```

---

## Accessing Data

### Direct SQL Access

```bash
# Open database
sqlite3 data/db/nba_props.sqlite3

# Example queries
.tables                          # List all tables
.schema boxscore_player          # Show table schema

-- Get player averages
SELECT p.name, 
       AVG(bp.pts) as avg_pts,
       AVG(bp.reb) as avg_reb,
       AVG(bp.ast) as avg_ast,
       COUNT(*) as games
FROM boxscore_player bp
JOIN players p ON bp.player_id = p.id
GROUP BY p.id
ORDER BY avg_pts DESC
LIMIT 20;

-- Get defense vs position data
SELECT * FROM team_defense_vs_position 
WHERE position = 'PG' 
ORDER BY pts_rank;

-- Get recent games for a player
SELECT g.date, bp.pts, bp.reb, bp.ast
FROM boxscore_player bp
JOIN games g ON bp.game_id = g.id
JOIN players p ON bp.player_id = p.id
WHERE p.name LIKE '%Dončić%'
ORDER BY g.date DESC
LIMIT 10;
```

### Python API Access

```python
from src.nba_props.db import Db

# Connect
db = Db(path="data/db/nba_props.sqlite3")

# Query
with db.connect() as conn:
    cursor = conn.execute("""
        SELECT * FROM boxscore_player 
        WHERE player_id = ?
        ORDER BY game_id DESC LIMIT 10
    """, (player_id,))
    rows = cursor.fetchall()
```

### Web API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/players` | GET | List all players |
| `/api/teams` | GET | List all teams |
| `/api/games` | GET | List recent games |
| `/api/projections` | POST | Generate projections |
| `/api/backtesting/generate-picks` | POST | Generate picks for date |
| `/api/backtesting/compare-results` | POST | Compare picks to actuals |
| `/api/modellab/backtest` | POST | Run model backtest |

---

## Running Backtests

### What is Backtesting?

Backtesting validates model accuracy by:
1. Generating picks for historical dates (as if we didn't know the outcome)
2. Comparing predictions to actual results
3. Calculating hit rates and ROI

### Web Interface Backtesting

1. Navigate to `/modellab` (Model Lab)
2. Select date range
3. Choose model version
4. Click "Run Backtest"
5. View results by confidence tier, prop type, etc.

### CLI Backtesting

```bash
# Using model_v9 (recommended)
python -c "
from src.nba_props.engine.model_v9 import run_backtest_v9

results = run_backtest_v9(
    start_date='2025-11-01',
    end_date='2025-12-31',
    db_path='data/db/nba_props.sqlite3'
)
print(f'Hit Rate: {results.hit_rate:.1%}')
print(f'Total Picks: {results.total_picks}')
print(f'By Tier: {results.by_tier}')
"
```

### Model Lab Functions

```python
from src.nba_props.engine.model_lab import (
    lab_comprehensive_test,
    compare_all_tracked_models,
    register_and_backtest_model
)

# Run comprehensive test
results = lab_comprehensive_test(
    start_date="2025-11-01",
    end_date="2025-12-31"
)

# Compare all tracked model versions
comparison = compare_all_tracked_models(
    start_date="2025-11-01",
    end_date="2025-12-31"
)
```

### Model Version Tracker

```python
from src.nba_props.engine.model_version_tracker import ModelVersionTracker

tracker = ModelVersionTracker(db_path="data/db/nba_props.sqlite3")

# Register a new model version
version_id = tracker.register_version(
    version_name="production_v9_calibrated",
    description="Line-aware model with 5% conservative adjustment",
    config={"model": "v9", "adjustment": 0.05}
)

# Save backtest results
tracker.save_backtest(
    version_id=version_id,
    start_date="2025-11-01",
    end_date="2025-12-31",
    results=backtest_results
)

# Compare versions
comparison = tracker.compare_versions(
    version_ids=[1, 2, 3],
    start_date="2025-11-01",
    end_date="2025-12-31"
)
```

### Thorough Backtest Checklist

For a comprehensive backtest, ensure:

1. **Sufficient Data:**
   - ✅ At least 30 days of box scores
   - ✅ Defense vs Position data updated
   - ✅ Injury reports for historical dates

2. **Test Multiple Conditions:**
   - ✅ Different date ranges
   - ✅ Multiple prop types (PTS, REB, AST)
   - ✅ Various confidence tiers
   - ✅ OVER vs UNDER direction

3. **Validation Metrics:**
   - ✅ Overall hit rate
   - ✅ Hit rate by confidence tier
   - ✅ Hit rate by prop type
   - ✅ Model calibration (predicted vs actual)
   - ✅ ROI simulation

4. **Line Source Analysis (Model V9):**
   - ✅ Hit rate with actual sportsbook lines
   - ✅ Hit rate with derived lines
   - ✅ Line difference (derived vs actual)

---

## Web Interface Tabs

### Model Performance Tab (`/modellab`)

Shows:
- Daily hit rates chart
- Cumulative performance
- Best/worst picks
- Model comparison table
- Confidence calibration

How to update:
1. Run backtests through the interface
2. Results auto-populate charts
3. Use "Compare Models" to see version differences

### Matchups Tab (`/matchups`)

Shows:
- Today's games with predictions
- Prop recommendations with confidence
- Defense matchup breakdowns
- Injury impact analysis

How to update:
1. Add today's matchups via paste
2. Add latest injury reports
3. Update defense vs position data
4. Refresh page to see new predictions

### Data Quality Indicators

The app shows data freshness:
- 🟢 Fresh (< 1 day old)
- 🟡 Stale (1-3 days old)
- 🔴 Outdated (> 3 days old)

---

## Best Practices

### Daily Workflow

1. **Morning:** Update defense vs position from Hashtag Basketball
2. **Pre-Game:** Add injury reports
3. **Post-Game:** Ingest box scores
4. **Analysis:** Review model performance, run backtests

### Data Quality

- Update defense data at least weekly
- Verify injury reports before games
- Check for missing box scores
- Monitor sportsbook line accuracy

### Model Validation

- Run backtests on 30+ day windows
- Compare multiple model versions
- Track performance by prop type
- Monitor confidence tier accuracy

---

## Troubleshooting

### Missing Data

```sql
-- Check for games without box scores
SELECT g.id, g.date, ht.abbrev || ' vs ' || at.abbrev as matchup
FROM games g
JOIN teams ht ON g.home_team_id = ht.id
JOIN teams at ON g.away_team_id = at.id
LEFT JOIN boxscore_player bp ON bp.game_id = g.id
WHERE bp.id IS NULL
ORDER BY g.date DESC;
```

### Defense Data Not Loading

1. Check table exists: `SELECT COUNT(*) FROM team_defense_vs_position;`
2. Verify position coverage: `SELECT DISTINCT position FROM team_defense_vs_position;`
3. Re-paste from Hashtag Basketball

### Low Hit Rates

1. Check data freshness
2. Verify sportsbook lines are accurate
3. Review confidence tier thresholds
4. Run longer backtest period

---

## Summary

PropAI combines multiple data sources to generate informed betting recommendations:

| Data Source | Primary Use | Update Frequency |
|------------|-------------|------------------|
| Box Scores | Player averages, trends | Daily (post-game) |
| Matchups | Schedule, game lines | Daily (pre-game) |
| Injuries | Usage redistribution | Daily (pre-game) |
| Defense vs Position | UNDER targeting | Weekly |
| Player DRTG | Individual matchups | Monthly |
| Sportsbook Lines | Model validation | As available |
| Salaries | Role identification | Yearly |

By maintaining fresh data and running regular backtests, you can achieve 65-70%+ hit rates on high-confidence picks.

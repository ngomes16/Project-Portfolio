# PropAI — NBA Player Props Predictor

A fully local NBA player prop betting analysis tool with multiple prediction models, a Flask web interface, and a CLI. Runs entirely on your machine with no cloud dependencies, no subscriptions, and no data leaving your computer.

## Features

### Data Ingestion
- **Box Score Parsing** — Copy-paste raw box scores from ESPN in multiple formats (raw, markdown, CSV) with automatic team detection
- **Sportsbook Lines** — Manually paste lines from DraftKings, FanDuel, and other books
- **Injury Tracking** — Automatically captures DND, DNP, and inactive players
- **Defense Data** — Ingest team defense-vs-position stats and individual defensive ratings

### Player Analysis
- **Player Archetypes** — Modern NBA roles (Point Centers, Stretch Fives, 3-and-D Wings, Rim Runners) stored in the database and editable after trades
- **Tier System** — Players ranked from Tier 1 (MVP candidates) to Tier 6 (rotation pieces)
- **Elite Defender Tracking** — Flags matchups against top defenders to adjust projections downward

### Projection Engine
- **Weighted Averages** — Blends last-5, last-15, and season averages with stat-specific weights
- **Matchup Adjustments** — Factors in opponent defense ratings, defense-vs-position, and elite defender matchups
- **Fatigue Detection** — Automatically applies back-to-back penalties and rest bonuses
- **Edge Calculator** — Uses normal distribution CDF to compute the probability of clearing a sportsbook line

### Multiple Models
- **Model V9 (Line-Aware)** — 68.6% hit rate using actual sportsbook lines
- **Model Production** — 66.7% hit rate using pattern detection (cold bounce-back, hot sustained)
- **Hybrid Model** — 66.6% hit rate combining regression contribution with pattern analysis
- **Under Model V2** — Specialist model for identifying Under plays
- **Backtesting** — Historical accuracy testing across all model versions

### Interface
- **Web GUI** — Flask-based dashboard with projections, matchup reports, model lab, and data management
- **CLI** — 30+ commands for headless operation and scripting
- **SQLite Database** — Everything stored locally in a single file

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.10+, Flask 3.1, Click (CLI) |
| **Database** | SQLite3 (20+ tables) |
| **Data Science** | pandas, NumPy, SciPy, scikit-learn |
| **Web Scraping** | BeautifulSoup4, Requests (optional) |
| **Frontend** | Jinja2 templates, vanilla JavaScript |

## Project Structure

```
PropAI - NBA 2025-2026/
├── run_cli.py                     # Entry point for CLI and web GUI
├── src/nba_props/
│   ├── cli.py                     # 30+ CLI commands
│   ├── db.py                      # Database schema (20+ tables)
│   ├── engine/
│   │   ├── projector.py           # Core projection logic
│   │   ├── edge_calculator.py     # Prop edge computation
│   │   ├── matchup_advisor.py     # Matchup analysis
│   │   ├── model_v9.py            # Best-performing model
│   │   ├── model_production.py    # Pattern-based model
│   │   ├── hybrid_model.py        # Combined approach
│   │   ├── under_model_v2.py      # Under specialist
│   │   ├── backtesting.py         # Historical accuracy testing
│   │   └── archetypes.py          # Player archetype definitions
│   ├── ingest/
│   │   ├── boxscore_parser.py     # ESPN box score parsing
│   │   ├── lines_parser.py        # Sportsbook line parsing
│   │   ├── injury_parser.py       # Injury report parsing
│   │   └── defense_position_parser.py
│   └── web/
│       ├── app.py                 # Flask application (50+ routes)
│       ├── templates/             # Jinja2 HTML templates
│       └── static/                # CSS, JS assets
├── data/db/nba_props.sqlite3      # Local SQLite database
└── documentation/                 # Extensive model and usage docs
```

## Getting Started

### Install

```bash
# CLI only
pip install -e .

# With web interface (recommended)
pip install -e ".[web]"
```

### Initialize and Seed

```bash
python3 run_cli.py init-db
python3 run_cli.py seed-archetypes
```

### Launch Web Interface

```bash
python3 run_cli.py gui              # Default port 5050
python3 run_cli.py gui --port 8080  # Custom port
```

### Daily Workflow (CLI)

```bash
# Ingest last night's box scores
python3 run_cli.py ingest-boxscore-stdin --date 2026-01-15

# Generate picks for today's games
python3 run_cli.py model-picks --date 2026-01-15

# View data summary
python3 run_cli.py summary
```

## How It Works

### Projection Formula

```
Base = (Last5_Avg × W5) + (Last15_Avg × W15) + (Season_Avg × WS)
```

Weights are stat-specific — points lean toward recent form (W5=0.25), while rebounds favor season averages (WS=0.45).

### Matchup Adjustments

The base projection is adjusted for opponent defense rating (position-specific), back-to-back fatigue (-8%), rest advantages (+3% for 3+ days off), and elite defender matchups (-6% to -12%).

### Edge Calculation

The system computes the probability of a player clearing a sportsbook line using a normal distribution CDF over the projection and historical standard deviation, then compares this to the implied probability from the odds.

### Confidence Scoring

Picks are scored on a 0-100 scale combining edge size (0-30), consistency (0-25), trend alignment (0-15), sample size (0-15), and minutes stability (0-10). Only HIGH confidence picks (~70% hit rate) are surfaced by default.

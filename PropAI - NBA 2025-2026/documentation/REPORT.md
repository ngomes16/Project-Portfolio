# NBA Player Props Finder — Project Report (Local)

## 1) Objective (What we are building)

You will run this locally and **manually provide data** (no scraping). The system should:

- Ingest full-game **box scores** you provide (your `.txt` files).
- Maintain an updatable local dataset of **games, players, teams, and derived stats**.
- Ingest **sportsbook lines** (points / rebounds / assists over-under, plus spread).
- Produce a ranked list of the **best prop opportunities** (edge vs line), focusing only on the **top 7 players per team**.
- Optionally output a **game winner / spread lean**.

Key challenges we must model:

- Player roles/archetypes within positions (e.g., “stretch 5” vs “rim runner”).
- Injuries / players out / minutes limitations.
- Back-to-backs (fatigue) and schedule effects.
- Opponent matchups: how specific player types perform vs specific defenses/styles.
- Avoid being misled by “position average” alone (stars differ from role players).

---

## 2) Inputs You Provide (Source-of-truth data)

### 2.1 Box score files (per game)

We support **two formats** found in your `Sample Data/`:

#### Format A — Markdown tables + explicit CSV section (preferred)

Your `01-01-26 Rockets vs Nets.txt` contains a `CSV Version of File:` section we can parse reliably.

Properties:

- Two teams with player rows
- Player row statuses like `Played`, `DNP - Coach's Decision`, `DND - Injury/Illness`
- A `TOTALS` row per team (team totals)
- An `Inactive Players` section at the end

#### Format B — Tabbed “PLAYER MIN FGM ...” lines (fallback)

Your `12-31-25 Warriors vs Hornets.txt` contains:

- Team name header
- A `PLAYER    MIN    FGM ... +/-` tabbed header
- Repeating blocks like:
  - `undefined Headshot` (noise)
  - player name
  - position line OR a `DNP - ...` line
  - stats line (tab-separated)
- A `TOTALS` row
- `Inactive Players` lines for both teams

**Important ingestion rule:** if `CSV Version of File:` exists, we will ingest from that section and ignore the markdown tables above it.

---

### 2.2 Sportsbook lines (daily)

You will provide (manually entered, or pasted into a CSV):

- Player props: **PTS**, **REB**, **AST** (and later maybe PRA, 3PM, etc.)
- Game spread (we will focus on spread ≤ 6 for “closer games”)
- Optional moneyline and totals
- Book name and timestamp (optional but helpful)

---

### 2.3 Injuries / availability (daily)

You will mark:

- Out / Questionable / Doubtful / Probable
- Minutes limits (if known)
- Late scratches (if known)

This is critical because it changes:

- Player minutes projections
- Usage distribution (who absorbs shots/assists/rebounds)
- Team quality (win probability)

---

### 2.4 Team defense / standings / roster metadata (periodic)

From your samples:

- `teamdefense25-26.txt` (team defense rating table)
- `Conference Rankings.txt` (standings)
- `NBA Salaries.txt` (salary ranks; proxy for “star-ness”)
- Team stats files (example: `Phoenix Suns Stats 2025-26.txt`)

We will store these as:

- **raw source files** (exactly what you provide, archived)
- **normalized tables** (cleaned values used by the model)

---

## 3) Data Storage Strategy (82 games x 30 teams, scalable)

### 3.1 Guiding principles

- Keep **raw inputs immutable** (audit trail, easy debugging).
- Parse into a **single local database** for fast queries (SQLite).
- Derive “features” and projections from DB tables, not from raw text files.

### 3.2 Directory layout (recommended)

```
Sports Algorithm/
  REPORT.md
  README.md
  src/
    nba_props/
      ...
  data/
    raw/
      boxscores/
        2025-26/
          2026-01-01/
            HOU_vs_BKN__source.txt
          2025-12-31/
            GSW_vs_CHA__source.txt
      lines/
        2025-26/
          2026-01-02__lines.csv
      metadata/
        2025-26/
          salaries__2026-01-01.txt
          team_defense__2026-01-01.txt
          standings__2026-01-01.txt
    db/
      nba_props.sqlite3
    exports/
      picks__2026-01-02.csv
```

### 3.3 Database tables (initial)

Minimum viable schema (we can expand later):

- **`teams`**: team_id, name
- **`players`**: player_id, name (later: canonical IDs)
- **`games`**: game_id, season, game_date, team1_id, team2_id, source_file
- **`boxscore_player`**: game_id, team_id, player_id, status, pos, minutes, pts, reb, ast, plus raw shooting/TO/etc.
- **`boxscore_team_totals`**: game_id, team_id, pts, reb, ast, etc.
- **`inactive_players`**: game_id, team_id, player_name, reason
- **`sportsbook_lines`**: as_of_date, game_id, player_id, prop_type, line, odds, book
- **`player_role_labels`**: player_id, season, base_pos, archetype, confidence, method
- **`injury_report`**: game_date, team_id, player_id (or name), status, minutes_limit, notes

Why SQLite:

- Zero setup
- Great for local analytics
- Easy to export to CSV

---

## 4) Player Roles / Archetypes (How we classify “center types”, etc.)

We will store two layers:

### 4.1 Base position (coarse)

From your box score: `G`, `F`, `C` (sometimes blank).

### 4.2 Archetype (fine)

Examples (extendable):

- **Centers**: rim runner, stretch 5, point center, two-way, post scorer
- **Guards**: primary creator, secondary creator, 3&D, off-ball shooter, slasher
- **Forwards**: wing stopper, stretch 4, point forward, rim pressure finisher

### 4.3 How we assign archetypes (practical + incremental)

Phase 1 (MVP): **rules + season-to-date rates** derived from box scores:

- 3PA per minute, AST per minute, REB per minute, BLK per minute, etc.
- Salary rank as a weak “star prior”
- Minutes share (top 7 proxy)

Phase 2: clustering within position groups (k-means / GMM), once we have enough games.

We will always keep a way for you to **override** a player label (manual truth beats automation).

---

## 5) Core Prop Model (How we project PTS/REB/AST)

We will build projections in layers, so each layer is testable:

### 5.1 Minutes projection (most important)

Minutes drives everything. We’ll estimate:

- Baseline minutes from last N games (e.g., 10)
- Adjustment for player status (out/questionable/returning)
- Adjustment for blowout risk (based on spread)
- Adjustment for back-to-back / rest days

### 5.2 Per-minute production projection

For each stat (PTS/REB/AST):

- Player baseline per-minute
- Role/archetype adjustments
- Opponent adjustments (team defense / style)
- Context adjustments (pace proxy, team strength, injuries)

### 5.3 Variance / uncertainty

We need uncertainty to rank props by **edge probability**:

- Use rolling standard deviation (last N) as a first approximation
- Later: add matchup-conditional variance

### 5.4 Prop edge scoring

For each candidate prop:

- Predicted mean \( \mu \)
- Predicted std \( \sigma \)
- Book line \( L \)
- Compute \( P(\text{Over}) \) and \( P(\text{Under}) \) (normal approx for MVP)
- Rank by expected value / probability edge

### 5.5 “Top 7 players only” rule

Define “top 7” by a stable metric:

- Primary: season average minutes (or last-10 average minutes)
- Tie-breakers: salary rank, usage proxy (FGA+FTA+AST), coach DNP frequency

We’ll enforce this rule in the recommendation layer.

---

## 6) Team Winner Prediction (Optional)

MVP approach:

- Start from team strength proxy (standings + net rating proxies if available)
- Adjust for injuries (missing top minutes/production)
- Adjust for rest/back-to-back
- Apply spread filter (we care most when spread ≤ 6)

Later we can model win probability directly once you provide enough historical results + spreads.

---

## 7) How You Will Run & Test This Locally

### 7.1 Daily workflow (intended)

1. Drop new box score `.txt` files into `data/raw/boxscores/<season>/<date>/`
2. Run ingestion to update SQLite
3. Add tomorrow’s lines to `data/raw/lines/...`
4. Enter injuries for tomorrow (file or GUI form)
5. Run “recommend props” for the slate
6. Export picks to CSV

### 7.2 Testing strategy (important for trust)

- **Parser tests**: each sample file becomes a regression test (Format A + B)
- **DB consistency checks**: totals rows, minutes parsing, duplicates
- **Projection sanity checks**: mean projections close to recent averages on neutral matchups
- **Backtesting** (once you provide historical lines):
  - Compare predicted over probability vs actual outcomes
  - Track calibration (are 60% picks hitting ~60%?)
  - Track ROI by threshold

---

## 8) GUI Plan (Local, easy data entry)

We’ll start with a simple local GUI that:

- Lets you choose a box score file and ingest it
- Shows parsed games/teams
- Lets you enter injuries and lines (simple table form)
- Runs projections and shows ranked props

Implementation options:

- **Tkinter (stdlib)**: no installs, runs anywhere, simplest MVP.
- **Streamlit**: much nicer UI, but requires installing dependencies.

We will scaffold Tkinter first so it works immediately; we can upgrade later.

---

## 9) What Other Data Would Be Useful (If you can provide it)

High value:

- **Game location** (home/away), start time, travel (optional)
- **Starting lineup** (or “who started”)
- **Team pace / possessions** (even approximate)
- **Opponent positional stats** (allowed points/reb/ast by position/archetype)
- **Sportsbook odds** (American odds) in addition to the line (for EV)
- **Closing line vs open** (optional)
- **Rest days** / schedule (we can compute if we have all game dates)

Nice-to-have:

- Player usage rate, touches, potential assists (advanced tracking) — only if you have it.

---

## 10) Development Phases (How we will build it)

### Phase 0 — Setup (now)

- Project structure
- SQLite schema
- Box score ingestion (Format A + B)
- Store raw files + parsed rows
- Basic CLI + basic GUI stub

### Phase 1 — Core analytics

- Season-to-date player and team aggregates
- “Top 7 players” selection logic
- Basic minutes model
- Basic projections for PTS/REB/AST

### Phase 2 — Matchup intelligence

- Archetype labeling (rules → clustering)
- Team defense/style adjustments
- Injury redistribution logic (who benefits when a star is out)

### Phase 3 — Backtesting & iteration

- Lines ingestion
- Prop edge scoring
- Backtest reports and calibration


---

## 11) Implementation Status (What’s been built so far)

This section documents the **current working state** of the repo as of now.

### 11.1 Repository structure created

- **`src/nba_props/`**: Python package (stdlib-only so far)
- **`data/`**:
  - **`data/raw/boxscores/<season>/<YYYY-MM-DD>/...`**: raw game inputs (files you import or paste)
  - **`data/raw/metadata/<season>/...`**: standings/defense/team stats raw files
  - **`data/raw/lines/<season>/...`**: (reserved; current paste-lines writes to DB directly)
  - **`data/db/nba_props.sqlite3`**: SQLite database (created on demand)
  - **`data/exports/`**: (reserved for later picks exports)

We also copied your sample inputs into the new `data/raw/...` structure as examples.

---

### 11.2 Database implemented (SQLite)

SQLite schema is created in `src/nba_props/db.py`. Tables currently used:

- **`teams`**: unique team names
- **`players`**: unique player names
- **`games`**: one row per ingested game:
  - stores **game_date** (YYYY-MM-DD), teams, source file path, and source hash
  - de-duplication now happens by **(game_date + matchup)** (order-insensitive)
- **`boxscore_player`**: one row per (game, team, player) with minutes + stats (PTS/REB/AST, etc.)
- **`boxscore_team_totals`**: team totals per game (when present)
- **`inactive_players`**: inactive lists per game/team
- **`sportsbook_lines`**: pasted/ingested lines per as-of date (PTS/REB/AST)
- **`injury_report`**: schema exists (UI + ingestion not built yet)

---

### 11.3 Box score ingestion implemented (3 input formats)

The ingestion pipeline is:

- raw file (or pasted text) → `parse_boxscore_text(...)` → normalized `ParsedGame`
- insert/update DB rows in `games`, `boxscore_player`, `boxscore_team_totals`, `inactive_players`

Supported formats:

1) **CSV-section format** (preferred): files containing `CSV Version of File:`  
   - We parse the CSV section for robustness.

2) **Tabbed/space-aligned “PLAYER MIN FGM ...” format** (your “undefined Headshot” style)  
   - Handles:
     - optional separate position line (`G/F/C`)
     - or missing pos line (stats line begins with `MM:SS`)
     - DNP/DND entries
     - totals rows

3) **Markdown-table format** (no CSV section)  
   - Parses the `## <Team> — Box Score` tables and the `## Inactive Players` section.

Inactive player mapping improvements:

- Inactive sections like `PHI: ...` or `* **MIA:** ...` are mapped to full team names using `src/nba_props/team_aliases.py`.

Date inference:

- If filename contains `MM-DD-YY`, we infer date from it.
- Otherwise, we infer date from parent folder named `YYYY-MM-DD` (supports canonical filenames like `HOU_vs_BKN__source.txt`).

---

### 11.4 Paste-first workflow implemented (so you don’t have to format anything)

You can now paste raw unformatted text directly and the app will:

- save the pasted text as a raw file under `data/raw/boxscores/<season>/<YYYY-MM-DD>/...`
- ingest it into SQLite

This exists in both CLI and GUI.

---

### 11.5 Sportsbook lines ingestion implemented (paste format)

We implemented a parser for your lines format:

- Section headers like:
  - `Points line:`
  - `Player Rebounds:`
  - `Player Assists:`
- Rows like:
  - `CJ McCollum: 18.5 -125`

The parsed lines are stored in `sportsbook_lines` with:

- `as_of_date`
- `player_id`
- `prop_type` in `{PTS, REB, AST}`
- `line`
- `odds_american` (optional)
- `book` (optional)

Current limitation (intentional for MVP):

- Lines are not yet linked to a specific **game_id/team_id** (we’ll add matchup binding next).

---

### 11.6 CLI commands added (for visibility + overlap checking)

Run commands from the repo root using:

- **`python3 run_cli.py <command>`**

Implemented commands:

- **`init-db`**: initialize SQLite
- **`ingest-boxscore <file>`**: ingest a `.txt` file
- **`ingest-boxscore-stdin --date YYYY-MM-DD --label LABEL`**: paste boxscore into stdin and ingest
- **`list-games --limit N`**: list ingested games (shows dates)
- **`show-game <game_id>`**: show parsed player lines for a game
- **`summary`**: counts of teams/players/games/rows/lines
- **`audit-duplicates`**: overlap check (duplicate games by date+matchup)
- **`ingest-lines-stdin --date YYYY-MM-DD --book NAME`**: paste sportsbook lines into stdin and ingest
- **`list-lines [--date YYYY-MM-DD]`**: view ingested lines
- **`gui`**: run the GUI app

**New Analysis Commands:**

- **`validate [--fix] [--verbose]`**: run data validation checks, optionally fix issues
- **`cleanup [--dry-run]`**: remove orphaned data (teams with no games, etc.)
- **`project --team TEAM [--opponent OPP] [--date DATE]`**: generate projections for a team
- **`usage-impact --team TEAM --out PLAYER [--historical]`**: show usage redistribution when a player is out
- **`matchup --away TEAM --home TEAM [--date DATE]`**: generate matchup-specific prop recommendations
- **`backtest [--start DATE] [--end DATE] [--min-edge PCT]`**: run backtest on historical lines
- **`accuracy --player NAME [--stat PTS|REB|AST]`**: analyze projection accuracy for a player
- **`bias-analysis [--min-games N]`**: analyze systematic projection biases
- **`alerts [--date DATE] [--min-edge PCT] [--team TEAM]`**: find edge alerts where projection differs from line

---

### 11.7 GUI improvements implemented

GUI is Tkinter-based (stdlib) and launched with:

- `python3 run_cli.py gui`

Tabs currently available:

- **Games**
  - shows game list (with **date**)
  - button: “Use selected game’s date in Paste tab”
  - import `.txt` file button
- **Paste Box Score**
  - paste raw text + set date + label + ingest
  - **clears the paste box after successful ingest**
  - “Recent dates” dropdown to speed up multi-game entry on same date
  - “Ingest pasted text” button moved to its own bar to avoid disappearing on smaller windows
- **Standings**
  - displays the latest `data/raw/metadata/<season>/standings__*.txt`
- **Team Defense**
  - displays the latest `data/raw/metadata/<season>/team_defense__*.txt`
- **Team Stats**
  - dropdown to open a `team_stats__*__*.txt` file

Bottom status bar:

- Shows: `Games | Players | Lines | Duplicate games`

---

### 11.8 Database-Backed Player Archetypes (NEW)

The player archetype system has been completely redesigned:

**Problem (before):**
- Player archetypes were stored in giant hard-coded Python dictionaries (`roster.py`, `archetypes.py`)
- ~2000+ lines of static data that would go stale with trades, roster changes
- No way to edit without changing code

**Solution (now):**
- New `player_archetypes` table in SQLite database
- New `player_similarity_groups` and `elite_defenders` tables
- Database-backed functions that:
  1. First check the database for player data
  2. Fall back to built-in defaults if not found
  3. Allow manual overrides without code changes

**New CLI Commands:**
- `seed-archetypes` - Populate database from built-in defaults (~200 players)
- `list-archetypes` - List archetypes with filtering
- `show-archetype <player>` - Show detailed player info

**New API Endpoints:**
- `GET /api/archetypes-db` - List all archetypes (DB + defaults)
- `GET /api/archetypes-db/player/<name>` - Get player archetype
- `PUT /api/archetypes-db/player/<name>` - Update player archetype
- `DELETE /api/archetypes-db/player/<name>` - Delete (reverts to defaults)
- `POST /api/archetypes-db/seed` - Seed database from defaults
- `GET /api/archetypes-db/stats` - Get archetype statistics

**Benefits:**
- User can update player teams after trades
- User can add new players not in defaults
- User can adjust archetypes based on game observations
- All without touching code

---

### 11.9 Flask Made Optional (NEW)

The application now runs stdlib-only for core functionality:

**Before:**
- Flask was a required dependency
- Couldn't run any CLI commands without Flask installed

**After:**
- Flask is an optional dependency (`pip install -e ".[web]"`)
- All CLI commands work without Flask:
  - `init-db`, `ingest-boxscore`, `list-games`, `show-game`
  - `summary`, `audit-duplicates`, `list-lines`
  - `seed-archetypes`, `list-archetypes`, `show-archetype`
- Web GUI requires Flask and shows helpful error message if not installed

---

### 11.10 Unders Logic Segregation (NEW)

The logic for determining "UNDER" picks has been decoupled from the main projection engine to improve accuracy.

**Problem:**
- Forcing the main model (designed for finding OVER edges via offensive production) to identify UNDERs led to a significant drop in accuracy (falling to ~40% pass rate).
- The factors that drive a good UNDER bet (fatigue, specific defender matchups, blowout risk) differ from standard value projections.

**Solution:**
- **New Module:** Created `src/nba_props/engine/under_picks_analyzer.py` to house specialized logic for UNDER picks.
- **Main Model Updates:** The primary advisor (`matchup_advisor.py`) and API now focus strictly on OVER edges (`direction="OVER"`).
- **UI Updates:** The web interface (Backtesting and Matchups pages) now displays a "Model Being Refined" status for UNDER picks while the new logic is being implemented.
- **Goal:** restore the main model's pass rate to ~75% by removing forced high-variance UNDER selections.

---

### 11.11 Defense vs Position Integration (NEW)

The system now incorporates **Defense vs Position** data from Hashtag Basketball to improve both OVER and UNDER predictions.

**Data Source:**
- Hashtag Basketball's "NBA Defense vs Position" page
- Tracks how each team defends against each position (PG, SG, SF, PF, C)
- Stats include: PTS, REB, AST, FG%, FT%, 3PM, STL, BLK, TO allowed

**Data Structure:**
- **"Best Defense" section (Top 5):** Teams with the STRONGEST defense against that position — Good for UNDER bets
- **"Worst Defense" section (Top 5):** Teams with the WEAKEST defense against that position — Good for OVER bets
- **"Position data" (All 150 entries):** Complete rankings across all team-position combinations

**How It Works:**

The system calculates a **defense factor** for each matchup:
```
factor = stat_allowed_by_opponent / league_average_for_position
```

| Factor | Meaning | Betting Implication |
|--------|---------|---------------------|
| 0.85 | Team allows 15% LESS than average | Strong defense → UNDER |
| 1.00 | Team allows league average | Neutral |
| 1.15 | Team allows 15% MORE than average | Weak defense → OVER |

**Rating Classifications (Position-Specific Rank):**
- **Elite** (Rank 1-5): Factor typically 0.85-0.92
- **Good** (Rank 6-10): Factor typically 0.92-0.97
- **Average** (Rank 11-20): Factor typically 0.97-1.03
- **Poor** (Rank 21-25): Factor typically 1.03-1.08
- **Terrible** (Rank 26-30): Factor typically 1.08+

**UNDERS Model Usage:**
- Factor < 1.0 triggers positive confidence boost
- Elite defense (rank 1-5) adds +20 confidence points
- Good defense (rank 6-10) adds +15 confidence points
- Weak defense (factor > 1.05) triggers WARNING that this is a poor UNDER candidate

**OVERS Model Usage:**
- Factor > 1.02 triggers projection boost
- Boost is dampened: `1.0 + (factor - 1.0) * 0.45`
- Maximum boost capped at 15% to avoid overfitting
- Strong defense (factor < 1.0) → No boost applied

**Example:**
- **Luka Dončić (PG) vs Boston (elite PG defense)**
  - Factor: 0.878 (BOS allows 21.3 PTS, league avg 24.3)
  - UNDERS: ✅ Good candidate (strong defense)
  - OVERS: No boost applied
  
- **Luka Dončić (PG) vs Orlando (terrible PG defense)**
  - Factor: 1.150 (ORL allows 27.9 PTS, league avg 24.3)
  - UNDERS: ⚠️ Warning (weak defense)
  - OVERS: +2.1 PTS boost applied

**Data Entry:**
- Use the **Data Management** page → **Defense vs Position Import** section
- Paste raw data from Hashtag Basketball
- Select the position (PG, SG, SF, PF, C)
- System auto-detects position from data and stores in database

**Database Table:** `team_defense_vs_position`
- 150 records total (30 teams × 5 positions)
- Updated manually by user when fresh data is available
- Tracks `as_of_date` for data freshness warnings

---

### 11.12 Player Defensive Rating (DRTG) Integration (NEW)

The system now tracks **individual player Defensive Ratings (DRTG)** from StatMuse to provide player-level defensive analysis.

**Data Source:**
- StatMuse (e.g., "Phoenix Suns players defensive rating 2024-25")
- Per-player DRTG with contextual stats (games, minutes, +/-)
- Parsed from raw page content with intelligent noise filtering

**What DRTG Means:**
- **DRTG** = Points allowed per 100 possessions when player is on court
- **Lower DRTG = Better Defender**
- League average is typically around 110
- Elite defenders are under 105

**Rating Classifications:**
| DRTG Range | Rating | Description |
|------------|--------|-------------|
| < 100 | Elite | Top-tier defender, significantly impacts opponent scoring |
| 100-105 | Good | Above average defender |
| 105-115 | Average | League average defensive impact |
| > 115 | Poor | Below average defender |

**Where DRTG Appears:**
1. **Team Detail Page** → Defense section shows player DRTG rankings
2. **Players Tab** → New "DRTG Rankings" tab with league-wide rankings
3. **Data Management** → Import interface for pasting StatMuse data

**Data Entry:**
- Navigate to **Data Management** page → **Import Player DRTG** section
- Select the team (optional - parser can auto-detect)
- Paste raw data from StatMuse
- System extracts player names, DRTG values, and supporting stats

**CLI Commands:**
```bash
# Ingest DRTG data from stdin
python run_cli.py ingest-drtg-stdin --team PHX < raw_data.txt

# List DRTG for a team
python run_cli.py list-drtg --team PHX

# Check which teams need DRTG updates
python run_cli.py drtg-freshness
```

**API Endpoints:**
- `POST /api/ingest/player-drtg` - Import DRTG data
- `GET /api/player-drtg/<team>` - Get team's player DRTG rankings
- `GET /api/player-drtg/league` - Get league-wide rankings
- `GET /api/player-drtg/status` - Data freshness for all 30 teams
- `GET /api/player/<name>/drtg` - Get specific player's DRTG

**Database Table:** `player_drtg`
- Stores per-player defensive ratings
- Includes: games_played, minutes_per_game, ppg, rpg, plus_minus
- Tracks `as_of_date` for freshness monitoring
- Data should be updated weekly for accuracy

**Use Cases:**
- Identify elite defenders to factor into UNDER predictions
- Complement team-level defense data with player granularity
- Track defensive development/decline throughout season
- Find mismatches where offensive players face weak defenders

---

## DETAILED MODEL BREAKDOWN: How Picks Are Made

This section provides a comprehensive explanation of how the NBA Props Predictor generates betting recommendations, including all mathematical formulas and algorithmic logic.

### Overview: Two-Model Architecture

The system uses **two separate models** optimized for different bet types:

| Model | Module | Purpose | Primary Output |
|-------|--------|---------|----------------|
| **OVER Model** | `matchup_advisor.py` + `edge_calculator.py` | Find players likely to exceed their line | OVER recommendations with confidence |
| **UNDER Model** | `under_picks_analyzer.py` | Find players likely to fall short of line | UNDER recommendations with confidence |

This separation exists because the factors that make a good OVER bet (high offensive potential) differ fundamentally from factors that make a good UNDER bet (defensive pressure, fatigue, role reduction).

---

### MODEL 1: The OVER Projection System

**Files Involved:**
- `projector.py` - Core stat projections
- `game_context.py` - B2B status, opponent context
- `edge_calculator.py` - Probability calculations
- `matchup_advisor.py` - Final recommendations

#### Step 1: Base Projection Calculation (`projector.py`)

The system calculates a baseline projection using **weighted historical averages**:

```
Base_Projection = (L5_Avg × 0.35) + (L20_Avg × 0.40) + (Season_Avg × 0.25)
```

Where:
- **L5_Avg** = Average from last 5 games (35% weight) — captures hot/cold streaks
- **L20_Avg** = Average from last 20 games (40% weight) — primary baseline
- **Season_Avg** = Full season average (25% weight) — long-term stability

**Why these weights?**
- Recent games (L5) are most predictive for short-term performance
- 20-game window captures role/minutes stabilization
- Season average prevents overreaction to small samples

#### Step 2: Minutes Projection

Minutes are the strongest predictor of counting stats. The system estimates expected minutes:

```
Expected_Minutes = (Baseline_Mins × Rest_Adjustment × Role_Factor)
```

Where:
- **Baseline_Mins** = Average minutes from recent games
- **Rest_Adjustment** = 0.94 for B2B (6% reduction), 1.03 for rest advantage
- **Role_Factor** = Based on injuries (if star is out, bench players get boost)

#### Step 3: Per-Minute Rate Calculation

For each stat (PTS, REB, AST), the system calculates per-minute production:

```
Points_Per_Minute = Total_Points / Total_Minutes (from sample period)
Rebounds_Per_Minute = Total_Rebounds / Total_Minutes
Assists_Per_Minute = Total_Assists / Total_Minutes
```

#### Step 4: Matchup Adjustments (`game_context.py`)

The raw projection is then adjusted based on opponent factors:

```
Adjusted_Projection = Base_Projection × Defense_Factor × Context_Multiplier
```

**Defense vs Position Factor:**
```python
defense_factor = opponent_allowed_stat / league_average_for_position

# Examples:
# Boston allows 21.3 PTS to PGs, league avg = 24.3
# factor = 21.3 / 24.3 = 0.878 (strong defense = lower projection)

# Orlando allows 27.9 PTS to PGs, league avg = 24.3  
# factor = 27.9 / 24.3 = 1.148 (weak defense = higher projection)
```

**How the factor is applied for OVERs:**
```python
if factor > 1.02:  # Weak defense threshold
    boost = 1.0 + (factor - 1.0) * 0.45  # Dampened boost
    boost = min(boost, 1.15)  # Cap at 15%
    adjusted = base_projection * boost
else:
    adjusted = base_projection  # No boost for average/strong defense
```

**Back-to-Back Adjustment:**
```python
if is_back_to_back:
    projection *= 0.94  # 6% fatigue penalty
elif rest_days >= 3:
    projection *= 1.03  # 3% rest bonus
```

#### Step 5: Edge & Probability Calculation (`edge_calculator.py`)

The system uses **normal distribution statistics** to calculate the probability of exceeding the line:

```python
from scipy.stats import norm

# Calculate z-score
z_score = (projection - line) / standard_deviation

# Probability of OVER
p_over = 1 - norm.cdf(z_score)

# Probability of UNDER  
p_under = norm.cdf(z_score)

# Edge calculation
edge = (2 * p_over - 1) * 100  # Expressed as percentage
```

**Example:**
```
Player: LeBron James
Prop: Points
Line: 26.5
Projection: 28.7
Std Dev: 6.2

z_score = (28.7 - 26.5) / 6.2 = 0.355
p_over = 1 - norm.cdf(0.355) = 0.361
p_over = 63.9%

edge = (2 × 0.639 - 1) × 100 = 27.8% edge on OVER
```

#### Step 6: Confidence Scoring (`matchup_advisor.py`)

Each pick receives a **confidence score** (0-100) based on multiple factors:

```python
confidence = 50  # Base score

# Position Defense Match (±15 points)
if defense_factor > 1.08:      # Terrible defense
    confidence += 15
elif defense_factor > 1.03:    # Poor defense  
    confidence += 10
elif defense_factor < 0.92:    # Elite defense
    confidence -= 15
elif defense_factor < 0.97:    # Good defense
    confidence -= 10

# Historical Performance vs Opponent (+10)
if player_exceeds_line_vs_opponent_historically:
    confidence += 10

# Trend Alignment (+12)
if recent_trend_supports_bet:
    confidence += 12

# Warnings (-8 each)
confidence -= (number_of_warnings * 8)
```

**Confidence Tiers:**
| Score | Tier | Meaning |
|-------|------|---------|
| 75+ | HIGH | Strong conviction, all factors align |
| 60-74 | MEDIUM | Solid play, some uncertainty |
| 45-59 | LOW | Marginal edge, higher variance |
| <45 | AVOID | Too many red flags |

#### Step 7: Final Report Generation

The `ComprehensiveMatchupReport` class aggregates all analysis:

```python
@dataclass
class ComprehensiveMatchupReport:
    best_over_plays: List[MatchupEdge]     # Sorted by confidence
    best_under_plays: List[MatchupEdge]    # From UNDER model
    avoid_players: List[AvoidPlayer]       # Too risky to bet
    key_matchup_storylines: List[str]      # Narrative insights
    analysis_timestamp: datetime
```

---

### MODEL 2: The UNDER Picks Analyzer

**File:** `under_picks_analyzer.py`

The UNDER model uses **different factors** than the OVER model because the psychology and mechanics of missing a line differ from exceeding it.

#### Primary UNDER Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| **Elite Defense at Position** | +20 | Opponent ranks top-5 at defending this position |
| **Good Defense at Position** | +15 | Opponent ranks top-10 at defending this position |
| **B2B Fatigue** | +12 | Player on second game of back-to-back |
| **Cold Streak** | +10 | Player below average last 3-5 games |
| **Injury Rust** | +8 | Recently returned from absence |
| **Role Reduction** | +10 | Minutes/usage trending down |

#### UNDER Warning Signals

```python
# Factors that WARN AGAINST taking an UNDER:
if defense_factor > 1.05:  # Weak defense
    add_warning("Opponent has weak defense - poor UNDER candidate")
    
if player_on_hot_streak:
    add_warning("Player trending UP - risky UNDER")
    
if opponent_plays_fast_pace:
    add_warning("High-pace game = more possessions = more stats")
```

#### UNDER Confidence Formula

```python
under_confidence = 50  # Base

# Defense factors (primary signal)
if defense_rank_at_position <= 5:
    under_confidence += 20
elif defense_rank_at_position <= 10:
    under_confidence += 15

# Fatigue/context
if is_back_to_back:
    under_confidence += 12
    
# Recent performance
if last_3_games_avg < season_avg * 0.85:
    under_confidence += 10  # Cold streak

# Player DRTG (defender quality)
if matchup_defender_drtg < 105:
    under_confidence += 8  # Facing elite defender

# Subtract for warning signals
under_confidence -= (warnings * 8)
```

---

### MATHEMATICAL FOUNDATIONS

#### Normal Distribution Assumption

The system assumes player performance follows a **normal (Gaussian) distribution**:

$$P(X > line) = 1 - \Phi\left(\frac{line - \mu}{\sigma}\right)$$

Where:
- $X$ = Player's actual stat
- $\mu$ = Projected mean (our projection)
- $\sigma$ = Standard deviation from historical games
- $\Phi$ = Cumulative distribution function of standard normal

**Validity:** This assumption holds reasonably well for PTS/REB/AST over 20+ game samples.

#### Standard Deviation Calculation

```python
def calculate_std_dev(games: List[int]) -> float:
    """Calculate standard deviation from recent games."""
    n = len(games)
    mean = sum(games) / n
    variance = sum((x - mean) ** 2 for x in games) / n
    return math.sqrt(variance)
```

The system uses **last 10 games** for std dev calculation to balance recency with sample size.

#### Edge-to-Bet-Size Relationship

The calculated edge informs bet sizing (not implemented in app, but useful):

```
Kelly Criterion: f* = (bp - q) / b

Where:
b = odds (decimal) - 1
p = probability of winning (our calculation)
q = probability of losing (1 - p)
f* = fraction of bankroll to bet
```

---

### DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA INGESTION LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  Box Scores → boxscore_parser.py → boxscore_player table        │
│  Lines      → lines_parser.py    → sportsbook_lines table       │
│  Defense    → defense_position_parser.py → team_defense_vs_pos  │
│  DRTG       → player_drtg_parser.py → player_drtg table         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROJECTION ENGINE                            │
├─────────────────────────────────────────────────────────────────┤
│  projector.py                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. Query historical stats (L5, L20, Season)               │ │
│  │  2. Calculate weighted average                              │ │
│  │  3. Calculate per-minute rates                              │ │
│  │  4. Project expected minutes                                │ │
│  │  5. Generate base projection = rate × minutes               │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MATCHUP ADJUSTMENTS                           │
├─────────────────────────────────────────────────────────────────┤
│  game_context.py                                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. Check B2B status → apply fatigue factor                │ │
│  │  2. Query defense vs position → calculate factor            │ │
│  │  3. Query player DRTG → identify elite defenders            │ │
│  │  4. Apply all adjustments to base projection                │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│      OVER MODEL             │  │      UNDER MODEL            │
├─────────────────────────────┤  ├─────────────────────────────┤
│  edge_calculator.py         │  │  under_picks_analyzer.py    │
│  ┌───────────────────────┐  │  │  ┌───────────────────────┐  │
│  │ 1. Compare to line    │  │  │  │ 1. Check elite defense │  │
│  │ 2. Calculate z-score  │  │  │  │ 2. Check B2B fatigue  │  │
│  │ 3. Get P(over)        │  │  │  │ 3. Check cold streak  │  │
│  │ 4. Calculate edge %   │  │  │  │ 4. Sum confidence pts │  │
│  └───────────────────────┘  │  │  └───────────────────────┘  │
└─────────────────────────────┘  └─────────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ADVISOR OUTPUT                                │
├─────────────────────────────────────────────────────────────────┤
│  matchup_advisor.py → ComprehensiveMatchupReport                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  - best_over_plays: List[MatchupEdge]                      │ │
│  │  - best_under_plays: List[MatchupEdge]                     │ │
│  │  - avoid_players: List[AvoidPlayer]                        │ │
│  │  - key_matchup_storylines: List[str]                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

### EXAMPLE: Full Pick Calculation

**Scenario:** Luka Dončić PTS prop, line 29.5, DAL @ ORL

**Step 1: Base Projection**
```
L5 Average: 31.2 PTS
L20 Average: 30.1 PTS  
Season Average: 29.8 PTS

Base = (31.2 × 0.35) + (30.1 × 0.40) + (29.8 × 0.25)
Base = 10.92 + 12.04 + 7.45 = 30.41 PTS
```

**Step 2: Defense vs Position**
```
Orlando allows 27.9 PTS to PGs (rank 28)
League average: 24.3 PTS

Factor = 27.9 / 24.3 = 1.148 (weak defense)

Since factor > 1.02:
  boost = 1.0 + (1.148 - 1.0) × 0.45 = 1.067
  
Adjusted = 30.41 × 1.067 = 32.45 PTS
```

**Step 3: Context Adjustments**
```
B2B: No → no fatigue penalty
Rest: 2 days → no rest bonus

Final Projection: 32.45 PTS
```

**Step 4: Probability Calculation**
```
Line: 29.5
Projection: 32.45
Std Dev (L10): 5.8

z_score = (32.45 - 29.5) / 5.8 = 0.509
P(over) = 1 - norm.cdf(0.509) = 0.305
P(over) = 69.5%

Edge = (2 × 0.695 - 1) × 100 = 39.0% edge
```

**Step 5: Confidence Score**
```
Base: 50
+ Position Defense (terrible, rank 28): +15
+ Historical vs ORL (Luka avg 33.5): +10
+ Hot streak (L5 > season): +8
- Warnings: 0

Confidence: 83 → HIGH
```

**Final Recommendation:**
```
OVER Luka Dončić 29.5 PTS
Projection: 32.5 | Edge: 39.0% | Confidence: HIGH
Reasons: Weak defense, historical dominance, hot streak
```

---

### KEY CONFIGURATION PARAMETERS

| Parameter | Value | Location | Purpose |
|-----------|-------|----------|---------|
| L5 Weight | 0.35 | `projector.py` | Recent game weight |
| L20 Weight | 0.40 | `projector.py` | Medium-term weight |
| Season Weight | 0.25 | `projector.py` | Long-term stability |
| B2B Penalty | 0.94 | `game_context.py` | Fatigue adjustment |
| Rest Bonus | 1.03 | `game_context.py` | Recovery boost |
| Defense Boost Cap | 1.15 | `game_context.py` | Max projection increase |
| Elite Defense Threshold | Rank 1-5 | `under_picks_analyzer.py` | UNDER boost trigger |
| High Confidence | 75+ | `matchup_advisor.py` | Tier threshold |
| Medium Confidence | 60-74 | `matchup_advisor.py` | Tier threshold |

---

## 12) Idea.txt Requirements Checklist

This section tracks all requirements from `Idea.txt` and their implementation status.

### ✅ Fully Implemented

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Run locally, no hosting | ✅ | Runs at `http://127.0.0.1:5050` |
| Store full box scores | ✅ | SQLite `boxscore_player` table |
| Parse raw ESPN format | ✅ | `boxscore_parser.py` handles "undefined Headshot" format |
| Parse formatted tables | ✅ | Markdown table parser |
| Target PTS/REB/AST props | ✅ | Projector generates these three stats |
| Good GUI for data entry | ✅ | Flask web interface |
| Copy-paste box scores | ✅ | Paste page in web UI |
| Player archetypes (point centers, stretch 5s, etc.) | ✅ | DB-backed `player_archetypes` table |
| Handle different player types | ✅ | 20+ offensive/defensive archetype classifications |
| Track injuries (DND/DNP) | ✅ | Captured from box scores, stored in DB |
| Top 7 players only | ✅ | `is_top_7` flag in projector |
| Back-to-back detection | ✅ | `matchups.py` → `get_back_to_back_status()` |
| Close game targeting (spread ≤ 6) | ✅ | `game_lines` table, `close_only` filter in API |
| Player salaries storage | ✅ | `player_salaries` table |
| Similar player groupings | ✅ | `player_similarity_groups` table |
| Elite defender tracking | ✅ | `elite_defenders` table, `is_elite_defender` flag |
| Report documentation | ✅ | This REPORT.md file |
| Database storage | ✅ | SQLite at `data/db/nba_props.sqlite3` |
| Team defense ratings | ✅ | `team_defense_ratings` table |
| Inactive player tracking | ✅ | `inactive_players` table |
| Avoid hard-coded data going stale | ✅ | DB-backed archetypes (can edit without code changes) |

### ⚠️ Partially Implemented

| Requirement | Status | Notes |
|-------------|--------|-------|
| Sportsbook lines comparison | ✅ | Full edge calculation with `alerts` command and API |
| Team win prediction | ⚠️ | Basic spread/line storage; needs win probability model |
| Projections vs lines | ✅ | `matchup` and `alerts` CLI commands, full API support |

### 📋 Recently Implemented (New)

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Usage redistribution when star out | ✅ | `usage-impact` CLI command, calculates stat redistribution |
| Matchup-specific prop recommendations | ✅ | `matchup` CLI command, position/player vs team analysis |
| Backtesting with historical lines | ✅ | `backtest`, `accuracy`, `bias-analysis` CLI commands |
| Automated edge alerts | ✅ | `alerts` CLI command, scans lines vs projections |
| Data validation & safety checks | ✅ | `validate` and `cleanup` CLI commands |
| Defense vs Position analysis | ✅ | `team_defense_vs_position` table, factor-based adjustments |
| Position-specific defense matchups | ✅ | Integrated into UNDERS and OVERS models |
| Hashtag Basketball data import | ✅ | Copy-paste import in Data Management page |
| Player Defensive Rating (DRTG) | ✅ | `player_drtg` table, StatMuse import, DRTG Rankings tab |
| DRTG display in Teams/Players pages | ✅ | Team detail defense section, Players DRTG Rankings tab |

### 📋 Not Yet Implemented

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Team playing style comparisons | Low | "Teams with similar styles" |
| Full 82-game workflow guide | Low | Documentation for season-long use |
| Team win probability model | Low | More sophisticated spread analysis |

---

## 13) Running the Application Locally

### How It Works

This application runs **entirely on your computer**. When you run:

```bash
python3 run_cli.py gui
```

You'll see:

```
🏀 NBA Props Predictor
   Running at: http://127.0.0.1:5050
   Press Ctrl+C to stop

 * Serving Flask app 'nba_props.web.app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
```

**This is completely normal!** Here's what it means:

- `127.0.0.1` = "localhost" = your computer only
- `5050` = the port number
- The "WARNING" is just Flask being cautious - for personal use, this is perfect
- `200` responses mean everything is working

### To Access the App

1. Keep the terminal running
2. Open any web browser
3. Go to: **http://127.0.0.1:5050**
4. That's it! The app is running locally.

### No Internet Required

- All data is stored on your computer
- No cloud hosting needed
- No subscription fees
- Your data never leaves your machine

---

## 14) Next Steps (Recommended Order)

### Immediate: Add More Game Data

The projection system improves with more data. Priority:

1. **Add recent games** - Paste box scores from the last week
2. **Seed archetypes** - Run `python3 run_cli.py seed-archetypes`
3. **Add today's lines** - Use the Data page to enter sportsbook lines

### Short-term: Use the Projections

1. Go to Projections page
2. Select a matchup (e.g., LAL @ BOS)
3. Review projections for each player
4. Compare to your sportsbook's lines
5. Look for edges (projection significantly above/below line)

### Medium-term: Improve Accuracy

1. Track which predictions hit/miss
2. Adjust player archetypes if needed
3. Note which defenders actually limit players
4. Update the DB with your observations

### Long-term: Build History

- Enter games daily throughout the season
- Build up enough data for backtesting
- Calibrate the projection model
- Export winning patterns

---

## 15) Data Entry Workflow (Daily)

### Morning Routine (After Last Night's Games)

```bash
# 1. Start the web app
python3 run_cli.py gui

# 2. For each game from last night:
#    - Go to ESPN box score
#    - Select all (Ctrl+A) and copy (Ctrl+C)
#    - Go to Paste page in the app
#    - Set the correct date
#    - Paste and click "Ingest Box Score"

# 3. Check your data
python3 run_cli.py summary
```

### Before Tonight's Games

```bash
# 1. Add injury info if any key players are out
#    (Use Data page → Injuries section)

# 2. Add sportsbook lines for tonight's games
#    (Use Data page → Lines section)

# 3. Go to Projections page
#    - Select tonight's matchups
#    - Compare projections to lines
#    - Look for edges
```

### Weekly Maintenance

```bash
# Update archetypes if there were trades
python3 run_cli.py seed-archetypes --overwrite

# Check data quality
python3 run_cli.py audit-duplicates
python3 run_cli.py summary
```


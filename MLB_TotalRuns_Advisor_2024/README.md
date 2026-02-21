# MLB Total Runs Advisor

A Python-based MLB betting advisor that scrapes real-time over/under lines from Yahoo Sports, compares them against historical matchup data from the 2022-2023 season, and posts automated betting recommendations to Twitter.

## Features

- **Real-Time Line Scraping** — Pulls current MLB over/under lines from Yahoo Sports
- **Historical Analysis** — Compares today's lines against 2022-2023 season matchup data to identify statistical edges
- **Betting Strength Score** — Rates each matchup on a 0-10 scale based on the percentage of historical games that exceeded the current line
- **Tiered Recommendations** — Classifies bets as "very favored," "favored," or "slightly favored" for both over and under picks
- **Twitter Integration** — Automatically posts daily recommendations via the Twitter API v2
- **Data Pipeline** — Includes scripts to scrape, format, and structure historical game data from Baseball Reference

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Core** | Python 3 |
| **Web Scraping** | BeautifulSoup4, Requests |
| **Social Media** | Tweepy (Twitter API v2) |
| **Data Processing** | Pandas, CSV, collections |
| **Data Sources** | Yahoo Sports (live odds), Baseball Reference (historical data) |

## Project Structure

```
MLB_TotalRuns_Advisor_2024/
├── main.py                # Entry point — orchestrates scrape → analyze → tweet
├── yahoo_scraper.py       # Scrapes Yahoo Sports for current over/under lines
├── data_processing.py     # Betting strength calculation and recommendation logic
├── twitter.py             # Twitter API authentication and posting
├── data_creation/
│   ├── games_scraper.py   # Scrapes Baseball Reference for historical scores
│   ├── format_games.py    # Aggregates scores by team matchup pairs
│   └── csv_converter.py   # Converts game data to CSV format
└── games_data/
    ├── formatted_data.txt # Historical matchup database (team pairs → scores)
    ├── games_sample.txt   # Raw scraped game data
    └── games.csv          # CSV format of historical data
```

## Getting Started

### Prerequisites

- Python 3
- Twitter Developer account with API v2 access

### Install Dependencies

```bash
pip install requests beautifulsoup4 tweepy pandas
```

### Configure Twitter API

Set the following environment variables:

```bash
export BEARER_TOKEN="your_bearer_token"
export API_KEY="your_api_key"
export API_KEY_SECRET="your_api_key_secret"
export ACCESS_TOKEN="your_access_token"
export ACCESS_TOKEN_SECRET="your_access_token_secret"
```

### Run

```bash
python main.py
```

This will scrape current odds, analyze them against historical data, and post recommendations to Twitter.

### Rebuild Historical Data (Optional)

```bash
cd data_creation
python games_scraper.py    # Scrape Baseball Reference
python format_games.py     # Format into matchup pairs
```

## How It Works

### Betting Strength Algorithm
For each matchup on today's schedule, the system looks up all historical games between the two teams and calculates what percentage of those games had total runs exceeding the current Yahoo Sports line. This percentage is scaled to a 0-10 betting strength score.

### Recommendation Tiers

| Score Range | Recommendation |
|-------------|---------------|
| 8.0 - 10.0 | Very favored for the Over |
| 7.2 - 7.9 | Favored for the Over |
| 6.7 - 7.1 | Slightly favored for the Over |
| 3.4 - 6.6 | No recommendation (skip) |
| 2.9 - 3.3 | Slightly favored for the Under |
| 2.1 - 2.8 | Favored for the Under |
| 0.0 - 2.0 | Very favored for the Under |

### Pipeline Flow
1. `yahoo_scraper.py` parses Yahoo Sports HTML for upcoming games and their over/under lines
2. `data_processing.py` loads historical data, calculates betting strength for each matchup, and generates recommendations
3. `twitter.py` authenticates with the Twitter API and posts each recommendation as an individual tweet

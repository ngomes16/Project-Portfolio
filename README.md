# Project Portfolio

A collection of full-stack applications, data tools, and systems spanning web development, data science, mobile development, and algorithm design.

---

## Projects

### [CUMTD Bus Mapper](./CUMTD_Bus_Mapper)

A graph-based transit routing system that models the Champaign-Urbana Mass Transit District bus network and finds optimal routes between stations.

**Summary** — Built as a CS 225 (Data Structures) final project, this application downloads real GTFS schedule data from CUMTD, constructs a weighted directed graph of the bus network, and applies the A* search algorithm with a great-circle distance heuristic to find the fastest route between any two stations. It also generates PNG visualizations of the network using both geographic and force-directed layouts.

**Key Features**
- A* pathfinding with time-aware edge filtering (routes are filtered by day and departure time)
- Force-directed graph visualization with iterative physics simulation
- BFS traversal for connected component analysis
- Python pipeline for downloading and parsing GTFS transit data

**Technologies** — C++11, CMake, Python 3, nlohmann/json, lodepng, Catch2

**Implementation Highlights**
- Generic template-based graph ADT (`Graph<Data, Weight, CompareHash>`) with a functor pattern for pluggable heuristics
- Great-circle distance heuristic guarantees admissibility for A*
- Edge weights represent travel time (arrival - departure), with real schedule filtering
- Force-directed layout uses repulsive/attractive forces with a cooling schedule over 50 iterations

---

### [FanFocus](./FanFocus)

A personalized sports news aggregator that recommends articles based on your favorite teams and interests using information retrieval techniques.

**Summary** — FanFocus scrapes articles from ESPN, AP News, and Sports Illustrated, then uses TF-IDF vectorization and cosine similarity to rank content by relevance to each user's interests. A feedback loop adjusts recommendations over time — upvoting an article boosts similar content, while downvoting suppresses it.

**Key Features**
- TF-IDF document retrieval with cosine similarity ranking
- Multi-source web scraping (ESPN, AP News, Sports Illustrated)
- Feedback-driven learning that propagates vote weights to similar articles
- Custom interest keywords and team selection for NBA/NFL

**Technologies** — Python 3.8, Flask, React 19, scikit-learn, NLTK, BeautifulSoup4

**Implementation Highlights**
- Precomputed TF-IDF vectors stored in Pickle for fast retrieval at query time
- Inverted index maps terms to articles for efficient lookup
- Upvotes boost article vector weights by 5%; downvotes reduce by 5%, with propagation to articles above 0.15 cosine similarity
- NLTK Porter Stemmer and stopword removal for text preprocessing

---

### [MLB Total Runs Advisor](./MLB_TotalRuns_Advisor_2024)

A Python-based MLB betting advisor that compares real-time over/under lines against historical matchup data and posts recommendations to Twitter.

**Summary** — The system scrapes current over/under lines from Yahoo Sports, looks up historical total runs for each team matchup from the 2022-2023 season, and calculates a betting strength score. Recommendations are automatically posted to Twitter via the API. The pipeline handles everything from data collection to social media publishing.

**Key Features**
- Real-time odds scraping from Yahoo Sports
- Historical analysis against 2022-2023 season matchup data
- Betting strength scoring on a 0-10 scale with tiered recommendations
- Automated Twitter posting via Tweepy (API v2)

**Technologies** — Python 3, BeautifulSoup4, Tweepy, Pandas, Requests

**Implementation Highlights**
- Betting strength = percentage of historical games exceeding the current line, scaled to 0-10
- Tiered recommendation system: scores above 6.7 favor the over, below 3.3 favor the under, with "very favored," "favored," and "slightly favored" tiers
- Data creation pipeline scrapes Baseball Reference and aggregates scores by sorted team pair tuples for consistent lookups

---

### [PropAI — NBA Player Props Predictor](./PropAI%20-%20NBA%202025-2026)

A fully local NBA player prop betting analysis tool with multiple prediction models, a web interface, and a CLI.

**Summary** — PropAI ingests NBA box scores, sportsbook lines, and defensive data to project player stats (PTS/REB/AST) and identify valuable prop bets. It runs entirely on your machine with no cloud dependencies. Multiple model iterations have been developed and backtested, with the best (Model V9) achieving a 68.6% hit rate. The tool includes a Flask web dashboard, 30+ CLI commands, and a SQLite database with 20+ tables.

**Key Features**
- Statistical projections blending last-5, last-15, and season averages with stat-specific weights
- Matchup adjustments for opponent defense, back-to-back fatigue, rest advantage, and elite defenders
- Multiple prediction models (V2-V9, Production, Hybrid, RCM, Under Model V2) with backtesting
- Player archetype system (Point Centers, Stretch Fives, 3-and-D Wings) stored in the database
- Edge calculator using normal distribution CDF to find where projections diverge from sportsbook lines

**Technologies** — Python 3.10+, Flask, SQLite, pandas, NumPy, SciPy, scikit-learn, Click

**Implementation Highlights**
- Projection formula: `(L5_Avg × W5) + (L15_Avg × W15) + (Season_Avg × WS)` with stat-specific weight tuning
- Confidence scoring (0-100) combines edge size, consistency, trend alignment, sample size, and minutes stability
- Pattern detection identifies cold bounce-back (L5 20%+ below L15, last game above L10) and hot sustained (L5 30%+ above L15) scenarios
- Database-backed archetypes allow player role updates after trades without code changes

---

### [Railroad — D&D Campaign Manager](./Railroad-Dungeons_and_Dragons_Tool)

A full-stack web application for Dungeons & Dragons campaign management with granular information sharing.

**Summary** — Railroad solves the problem of progressive information reveal in D&D campaigns. Dungeon Masters store all campaign notes (locations, characters, items) as Artifacts containing individual Facts, each with a UUID-based visibility key. Facts can be revealed to players one at a time, in groups, or automatically with their parent Artifact — eliminating the need for players to take redundant notes.

**Key Features**
- Artifact and Fact system with independent visibility keys for granular sharing
- Campaign workspaces with role-based access (Game Master, players)
- Relevance-ranked keyword search across Artifacts and Facts
- Markdown editor for rich text content creation
- Campaign member directory

**Technologies** — TypeScript, Express.js, React 18, Redux Toolkit, Material-UI, MySQL, bcrypt

**Implementation Highlights**
- UUID-based access key system: each Fact/Artifact has a key that can be shared independently or grouped for batch reveals
- Search ranking uses a SQL UNION combining title and content matches, with CASE-based ordering (prefix > substring)
- Router pattern: all Express route handlers extend a `BaseRouter` for shared database access
- Three-column React layout with Redux Toolkit for artifact selection state

---

### [Trippi](./Trippi)

An all-in-one trip planner and budget tracker for group travel, built as a cross-platform mobile app with real-time sync.

**Summary** — Trippi helps groups plan trips together with shared itineraries, categorized budgets, expense splitting, and balance settlement. The Expo/React Native app syncs in real time through Firebase Firestore, so all group members stay updated. It includes a web landing page deployed to GitHub Pages and supports demo mode for trying the app without Firebase credentials.

**Key Features**
- Day-by-day itinerary builder with calendar filtering and timeline view
- Category-based budgets (Lodging, Flights, Transport, Activities, Food) with savings progress tracking
- Three-way expense splitting (equal, weighted, custom) with payer tracking
- Balance calculation and "Settle Up" feature for group settlements
- Role-based group management (Owner, Manager, Member, Viewer)
- Real-time Firestore sync across all group members

**Technologies** — React Native, Expo SDK 54, TypeScript, Firebase (Firestore, Auth), react-native-svg, GitHub Pages

**Implementation Highlights**
- Firestore data model uses subcollections (members, events, expenses) under trip documents with denormalized `memberUids` for efficient `array-contains` membership queries
- Balance algorithm aggregates all expenses and contributions per member, then produces minimal settlement transactions
- Four React Context providers (Trips, Auth, Budget, UI) with Firestore `onSnapshot` listeners for real-time state
- File-based routing via expo-router with dynamic segments (`trip/[id]`)

---

### [iReminder](./iReminder)

A web application for students to track assignments and due dates by integrating directly with the Canvas LMS.

**Summary** — iReminder connects to Canvas through its REST API to pull in all assignments across a student's courses, then displays them in a sortable table, an interactive calendar, and a workload distribution chart. It also includes a persistent notepad for personal notes stored in a MySQL database.

**Key Features**
- Canvas LMS API integration for automatic assignment fetching
- Interactive calendar view with FullCalendar
- Assignment workload analytics via Chart.js bar charts
- Persistent personal notepad with database storage
- User authentication (registration and login)

**Technologies** — Python 3, Flask, React 18, FullCalendar, Chart.js, MySQL, Canvas LMS API

**Implementation Highlights**
- Canvas integration fetches enrolled courses first, then iterates each course for assignments, parsing ISO 8601 dates into a structured format
- Assignment data cached in browser `localStorage` after initial fetch for instant rendering across table, calendar, and chart views
- Chart component counts assignments per course to visualize workload distribution
- Flask backend serves as both an auth layer and a proxy for Canvas API calls

---

## Tech Stack Overview

| Domain | Technologies Used |
|--------|-------------------|
| **Languages** | Python, TypeScript, JavaScript, C++ |
| **Frontend** | React, React Native, Expo, Redux Toolkit, Material-UI |
| **Backend** | Flask, Express.js, Node.js |
| **Databases** | SQLite, MySQL, Firebase Firestore |
| **Data Science** | scikit-learn, NLTK, pandas, NumPy, SciPy |
| **APIs** | Canvas LMS, Twitter API, CUMTD GTFS, ESPN, NBA.com |
| **Infrastructure** | Firebase, GitHub Pages, CMake |

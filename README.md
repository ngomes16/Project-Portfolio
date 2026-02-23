<h1 align="center">Nathaniel Gomes — Project Portfolio</h1>

<p align="center">
  <strong>Full-stack applications, machine learning systems, data tools, and mobile apps</strong><br>
  spanning deep learning, web development, data science, and algorithm design.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/C++-00599C?style=flat-square&logo=cplusplus&logoColor=white" />
  <img src="https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/TensorFlow-FF6F00?style=flat-square&logo=tensorflow&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/Firebase-FFCA28?style=flat-square&logo=firebase&logoColor=black" />
  <img src="https://img.shields.io/badge/Expo-000020?style=flat-square&logo=expo&logoColor=white" />
</p>

---

## Table of Contents

| # | Project | Domain |
|:-:|---------|--------|
| 1 | [Deep Learning LOINC Standardization](#-deep-learning-loinc-standardization) | Deep Learning · Healthcare NLP |
| 2 | [PropAI — NBA Player Props Predictor](#-propai--nba-player-props-predictor) | Data Science · Sports Analytics |
| 3 | [FanFocus](#-fanfocus) | Information Retrieval · Full-Stack |
| 4 | [Trippi](#-trippi) | Mobile Development · Real-Time Sync |
| 5 | [Railroad — D&D Campaign Manager](#-railroad--dd-campaign-manager) | Full-Stack Web · CRUD |
| 6 | [CUMTD Bus Mapper](#-cumtd-bus-mapper) | Graph Algorithms · Visualization |
| 7 | [MLB Total Runs Advisor](#-mlb-total-runs-advisor) | Data Science · Automation |
| 8 | [iReminder](#-ireminder) | Full-Stack Web · API Integration |

---

## 🧠 Deep Learning LOINC Standardization

**Contrastive learning system for mapping laboratory test descriptions to standardized medical codes using a fine-tuned Sentence-T5 encoder.**

> [View Project →](./Deep%20Learning%20Loinc%20Standardization)

<details>
<summary><strong>Expand for details</strong></summary>
<br>

**Summary** — Implements the methodology from *"Automated LOINC Standardization Using Pre-trained Large Language Models"* (Tu et al., Google Research). The system addresses a critical healthcare interoperability challenge: hospitals encode lab tests with proprietary names, acronyms, and abbreviations, making cross-institutional data sharing nearly impossible. This project fine-tunes a Sentence-T5 encoder with contrastive triplet loss to embed lab descriptions into a shared vector space where cosine similarity retrieves the correct standardized LOINC code. A two-stage training strategy first learns the LOINC ontology from 46,000+ target codes, then adapts to source-target mappings from MIMIC-III clinical data. The project also extends the original paper with scale token integration, no-match detection for unmappable tests, and a contribution to the PyHealth open-source framework.

**Key Features**
- Two-stage contrastive fine-tuning: Stage 1 on 46,449 LOINC targets, Stage 2 on MIMIC-III source-target pairs
- Triplet loss with hard and semi-hard negative mining strategies
- Four data augmentation techniques: character deletion, word swapping, word insertion, acronym substitution
- Scale token integration to distinguish qualitative vs. quantitative LOINC codes
- No-match detection with confidence calibration for unmappable lab tests
- Stratified 5-fold cross-validation with special handling for rare LOINC classes
- Comprehensive error analysis categorizing misclassifications by type (specimen, property, method)
- Ablation studies quantifying contribution of each component
- PyHealth framework contribution for broader accessibility

**Technologies** — Python 3, TensorFlow, TensorFlow Hub, Sentence-T5 (ST5-base), scikit-learn, pandas, NumPy, matplotlib, seaborn

**Implementation Highlights**
- Frozen ST5-base backbone (768-d) → trainable projection layer (128-d) → L2 normalization, avoiding overfitting on limited labeled data
- Triplet loss: `L = max(0, D_cos(anchor, positive)² − D_cos(anchor, negative)² + α)` with margin α = 0.8
- Stage 1 learns LOINC ontology from target text variants (LCN, display name, short name, related names) at lr = 1e-4
- Stage 2 fine-tunes on 575 MIMIC-III source-target pairs with dropout (0.1) and lr = 1e-5
- Scale-aware negative mining respects qualitative/quantitative boundaries to reduce property-mismatch errors
- Custom `tf.GradientTape` training loop to handle string operations incompatible with GPU/`@tf.function`

</details>

---

## 🏀 PropAI — NBA Player Props Predictor

**Fully local NBA player prop betting analysis tool with multiple prediction models, a web dashboard, and a CLI.**

> [View Project →](./PropAI%20-%20NBA%202025-2026)

<details>
<summary><strong>Expand for details</strong></summary>
<br>

**Summary** — PropAI ingests NBA box scores, sportsbook lines, and defensive data to project player stats (PTS/REB/AST) and identify valuable prop bets. It runs entirely on your machine with no cloud dependencies. Multiple model iterations have been developed and backtested, with the best (Model V9) achieving a 68.6% hit rate. The tool includes a Flask web dashboard, 30+ CLI commands, and a SQLite database with 20+ tables.

**Key Features**
- Statistical projections blending last-5, last-15, and season averages with stat-specific weights
- Matchup adjustments for opponent defense, back-to-back fatigue, rest advantage, and elite defenders
- Multiple prediction models (V2–V9, Production, Hybrid, RCM, Under Model V2) with backtesting
- Player archetype system (Point Centers, Stretch Fives, 3-and-D Wings) stored in the database
- Edge calculator using normal distribution CDF to find where projections diverge from sportsbook lines

**Technologies** — Python 3.10+, Flask, SQLite, pandas, NumPy, SciPy, scikit-learn, Click

**Implementation Highlights**
- Projection formula: `(L5_Avg × W5) + (L15_Avg × W15) + (Season_Avg × WS)` with stat-specific weight tuning
- Confidence scoring (0–100) combines edge size, consistency, trend alignment, sample size, and minutes stability
- Pattern detection identifies cold bounce-back and hot sustained scenarios
- Database-backed archetypes allow player role updates after trades without code changes

</details>

---

## 📰 FanFocus

**Personalized sports news aggregator that recommends articles based on your favorite teams using information retrieval techniques.**

> [View Project →](./FanFocus)

<details>
<summary><strong>Expand for details</strong></summary>
<br>

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

</details>

---

## ✈️ Trippi

**All-in-one trip planner and budget tracker for group travel, built as a cross-platform mobile app with real-time sync.**

> [View Project →](./Trippi)

<details>
<summary><strong>Expand for details</strong></summary>
<br>

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
- Firestore data model uses subcollections under trip documents with denormalized `memberUids` for efficient `array-contains` membership queries
- Balance algorithm aggregates all expenses and contributions per member, then produces minimal settlement transactions
- Four React Context providers (Trips, Auth, Budget, UI) with Firestore `onSnapshot` listeners for real-time state
- File-based routing via expo-router with dynamic segments (`trip/[id]`)

</details>

---

## 🐉 Railroad — D&D Campaign Manager

**Full-stack web application for Dungeons & Dragons campaign management with granular information sharing.**

> [View Project →](./Railroad-Dungeons_and_Dragons_Tool)

<details>
<summary><strong>Expand for details</strong></summary>
<br>

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

</details>

---

## 🚌 CUMTD Bus Mapper

**Graph-based transit routing system that models the Champaign-Urbana bus network and finds optimal routes between stations.**

> [View Project →](./CUMTD_Bus_Mapper)

<details>
<summary><strong>Expand for details</strong></summary>
<br>

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
- Edge weights represent travel time (arrival − departure), with real schedule filtering
- Force-directed layout uses repulsive/attractive forces with a cooling schedule over 50 iterations

</details>

---

## ⚾ MLB Total Runs Advisor

**MLB betting advisor that compares real-time over/under lines against historical matchup data and posts recommendations to Twitter.**

> [View Project →](./MLB_TotalRuns_Advisor_2024)

<details>
<summary><strong>Expand for details</strong></summary>
<br>

**Summary** — The system scrapes current over/under lines from Yahoo Sports, looks up historical total runs for each team matchup from the 2022–2023 season, and calculates a betting strength score. Recommendations are automatically posted to Twitter via the API. The pipeline handles everything from data collection to social media publishing.

**Key Features**
- Real-time odds scraping from Yahoo Sports
- Historical analysis against 2022–2023 season matchup data
- Betting strength scoring on a 0–10 scale with tiered recommendations
- Automated Twitter posting via Tweepy (API v2)

**Technologies** — Python 3, BeautifulSoup4, Tweepy, pandas, Requests

**Implementation Highlights**
- Betting strength = percentage of historical games exceeding the current line, scaled to 0–10
- Tiered recommendation system: scores above 6.7 favor the over, below 3.3 favor the under, with "very favored," "favored," and "slightly favored" tiers
- Data creation pipeline scrapes Baseball Reference and aggregates scores by sorted team pair tuples for consistent lookups

</details>

---

## 📋 iReminder

**Web application for students to track assignments and due dates by integrating directly with the Canvas LMS.**

> [View Project →](./iReminder)

<details>
<summary><strong>Expand for details</strong></summary>
<br>

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

</details>

---

## Tech Stack Overview

| Domain | Technologies |
|--------|-------------|
| **Languages** | Python, TypeScript, JavaScript, C++ |
| **Machine Learning** | TensorFlow, TensorFlow Hub, Sentence-T5, scikit-learn, SciPy |
| **NLP / Data** | NLTK, pandas, NumPy, BeautifulSoup4, TF-IDF |
| **Frontend** | React, React Native, Expo, Redux Toolkit, Material-UI |
| **Backend** | Flask, Express.js, Node.js |
| **Databases** | SQLite, MySQL, Firebase Firestore |
| **APIs & Services** | Canvas LMS, Twitter API, CUMTD GTFS, ESPN, NBA.com |
| **Infrastructure** | Firebase, GitHub Pages, CMake |

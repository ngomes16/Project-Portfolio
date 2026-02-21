# FanFocus

A personalized sports news aggregator that scrapes articles from major sports outlets and uses TF-IDF vectorization with cosine similarity to recommend content tailored to your favorite teams and interests. The system learns from your feedback to continuously refine recommendations.

## Features

- **Personalized Recommendations** — Uses TF-IDF vectorization and cosine similarity to rank articles based on your interests and favorite teams
- **Multi-Source Scraping** — Aggregates articles from ESPN, AP News, and Sports Illustrated for NBA and NFL coverage
- **Feedback Learning** — Upvote/downvote system dynamically adjusts article relevance weights, propagating feedback to similar articles
- **Custom Interests** — Add keywords and key terms beyond team names to fine-tune what surfaces in your feed
- **Team Selection** — Browse and select from NBA and NFL teams with a visual team picker
- **Article Tracking** — Prevents duplicate articles from appearing, with the ability to reset your reading history

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, React Router DOM, React Icons |
| **Backend** | Python 3.8, Flask 3.1 |
| **NLP / IR** | scikit-learn (TF-IDF), NLTK (tokenization, stemming, stopwords) |
| **Web Scraping** | BeautifulSoup4, Requests |
| **Data Storage** | JSON files, Pickle (serialized TF-IDF vectors) |

## Project Structure

```
FanFocus/
├── app.py                    # Flask API — endpoints for scraping, retrieval, feedback
├── update_content.py         # TF-IDF processing, vectorization, and storage
├── database_utils.py         # Data persistence utilities
├── espn.py                   # ESPN article scraper
├── apnews.py                 # AP News article scraper
├── sports_illustrated.py     # Sports Illustrated scraper
├── data/
│   ├── users.json            # User profiles and preferences
│   ├── articles.json         # Scraped article database
│   ├── inverted_index.json   # Term-to-article mapping
│   └── tfidf_data.pkl        # Precomputed TF-IDF vectors
└── fanfocus/                 # React frontend
    └── src/
        ├── App.js            # Home page — article viewer with voting
        └── Profile.js        # Profile page — team and interest management
```

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js and npm

### Backend

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
python app.py                   # Starts Flask server on http://localhost:5000
```

### Frontend

```bash
cd fanfocus
npm install
npm start                       # Opens React app at http://localhost:3000
```

## How It Works

### Data Pipeline
When you select teams and click "Fetch Articles," the backend scrapes ESPN, AP News, and Sports Illustrated for relevant content. Each article is stored in a JSON database, an inverted index is updated with extracted terms, and TF-IDF vectors are computed and serialized for fast retrieval.

### Document Retrieval
A query vector is constructed from your selected key terms and favorite teams. The system computes cosine similarity between this query and all article vectors, returning the top-k most similar articles that you haven't already seen.

### Feedback Loop
When you upvote an article, its TF-IDF vector weights are boosted by 5%. Downvotes reduce weights by 5%. The adjustment propagates to articles with cosine similarity above 0.15, so feedback on one article shifts the relevance of similar content across the entire corpus.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/scrape_articles` | Scrape articles for selected teams |
| `GET` | `/articles/one?k=5` | Retrieve top-k recommended articles |
| `POST` | `/article/one/<id>/feedback` | Submit upvote or downvote |
| `POST` | `/article/one/<id>/seen` | Mark an article as seen |
| `PUT` | `/user/one/key-terms` | Update interest keywords |
| `POST` | `/user/one/reset-seen` | Reset reading history |

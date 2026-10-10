# NewsPulse: Autonomous News Headline & Trending Topics Extractor

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Domain](https://img.shields.io/badge/Domain-Web%20Scraping%20%26%20NLP-green.svg)](#)
[![Code Style](https://img.shields.io/badge/code%20style-pep8-orange.svg)](#)

**NewsPulse** is an autonomous news extraction, natural language processing, and trend intelligence pipeline engineered in Python. It aggregates stories from multi-source feeds (RSS 2.0, Atom, custom HTML), performs n-gram phrase and keyword extraction, computes sentiment polarity distributions, monitors custom watchlists, and compiles structured executive digests for decision-makers.

---

## Key Capabilities

- **Multi-Source Scraping & Parsing**:
  - Native parsing for RSS 2.0 XML, Atom feeds, and custom CSS-selector HTML page scrapers.
  - Robust networking with User-Agent spoofing, configurable timeouts, error recovery, and deterministic offline mock fixture fallbacks.
- **NLP N-Gram & Trend Acceleration Engine**:
  - Contextual tokenization and stop-word filtering across journalistic terms.
  - Extraction of unigrams, bigrams, and trigrams (e.g., `"artificial intelligence"`, `"clean energy"`, `"zero-day"`).
  - Velocity scoring comparing current story frequency against baseline moving averages.
- **Lexicon Sentiment & Urgency Polarity**:
  - Domain-weighted sentiment engine assessing positive breakthroughs vs. crisis/risk events with negation inversion handling.
- **Interactive HTML5 & SVG Dashboard**:
  - Generates standalone, responsive analytics dashboards with custom SVG Donut Charts, horizontal Category Bar Charts, Trending N-Gram Pill Clouds, and client-side instant filtering.
- **Cross-Source Story Clustering**:
  - Pairwise Jaccard lexical similarity engine grouping multi-outlet coverage of identical breaking events to analyze comparative perspectives.
- **Continuous Monitoring Daemon**:
  - Autonomous periodic scraping loop with alert triggers and audit trail logging.
- **SQLite News Vault Storage**:
  - High-performance relational database with deterministic SHA-256 deduplication, category tagging, full-text search, and scrape run auditing.
- **Watchlist & Alert Triggering**:
  - Keyword rule monitoring across articles for automated anomaly and high-priority topic alerts.
- **Multi-Format Digest Reporting**:
  - Exports executive summaries to Markdown (ready for PDF conversion), structured JSON, tabular CSV, or formatted ASCII terminal bars.

---

## Directory Architecture

```text
news-trend-extractor/
├── news_extractor/
│   ├── __init__.py          # Package initialization & public API exports
│   ├── alerts.py            # Watchlist monitor & keyword trigger alerts
│   ├── analyzer.py          # NLP n-grams, trend scoring, sentiment classifier
│   ├── cli.py               # Command-line interface & subcommands router
│   ├── clustering.py        # Cross-source event & story clustering engine
│   ├── config.py            # Application & source configuration dataclasses
│   ├── dashboard.py         # Standalone HTML5 & vector SVG dashboard renderer
│   ├── models.py            # Article, TrendTopic, SentimentResult, Digest models
│   ├── reporter.py          # Digest formatting (Markdown, JSON, CSV, Console)
│   ├── scheduler.py         # Continuous periodic background monitoring daemon
│   ├── scraper.py           # Multi-source scraper (RSS, Atom, HTML, Offline)
│   └── storage.py           # SQLite persistence, deduplication, full-text search
├── fixtures/
│   ├── custom_page.html     # Realistic news HTML page fixture
│   ├── tech_feed.xml        # Realistic tech news RSS fixture
│   └── world_feed.xml       # Realistic world news RSS fixture
├── tests/
│   ├── __init__.py
│   ├── test_alerts.py       # Watchlist alerting tests
│   ├── test_analyzer.py     # NLP n-grams, stop-words, sentiment tests
│   ├── test_cli.py          # End-to-end CLI command execution tests
│   ├── test_clustering.py   # Pairwise similarity and clustering tests
│   ├── test_dashboard.py    # HTML and SVG dashboard generation tests
│   ├── test_models.py       # Article dataclass serialization tests
│   ├── test_scheduler.py    # Background monitor daemon tests
│   ├── test_scraper.py      # RSS, Atom, and HTML parser unit tests
│   └── test_storage.py      # SQLite CRUD, deduplication, search tests
├── config.example.json      # Sample configuration profile
├── main.py                  # CLI application entrypoint
├── requirements.txt         # Optional third-party dependencies (works with stdlib)
├── .gitignore               # Git ignore patterns
└── README.md                # Project documentation
```

---

## Quick Start Guide

### 1. Initialize Configuration

Generate a standard configuration template:

```bash
python main.py init -o config.json
```

Example `config.json`:

```json
{
  "db_path": "news_vault.db",
  "timeout_seconds": 10,
  "sources": [
    {
      "name": "Hacker News Frontpage",
      "url": "https://news.ycombinator.com/rss",
      "feed_type": "rss",
      "category": "Technology",
      "enabled": true
    },
    {
      "name": "BBC News World",
      "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
      "feed_type": "rss",
      "category": "World",
      "enabled": true
    }
  ],
  "watchlists": {
    "Artificial Intelligence": ["ai", "llm", "neural network", "agent"],
    "Cybersecurity": ["vulnerability", "breach", "zero-day", "ransomware"]
  }
}
```

### 2. Ingest Headlines

Scrape live feeds (or run in `--offline` mode with bundled fixtures):

```bash
# Ingest live feeds
python main.py fetch

# Ingest deterministic offline fixtures (no internet connection required)
python main.py fetch --offline
```

### 3. Identify Trending Topics

Extract the most discussed keywords and compound phrases:

```bash
python main.py trends --top 10 --hours 48
```

Output preview:

```text
======================================================================
 🔥 TOP 5 TRENDING TOPICS (Last 48 hours across 12 articles)
======================================================================
Rank  Phrase / Topic               Mentions   Score    Primary Sources
----------------------------------------------------------------------
1     artificial intelligence      4          66.7     TechPulse, Daily Chronicle
2     quantum computing            3          50.0     TechPulse
3     clean energy                 3          50.0     Global Dispatch, Daily Chronicle
4     cybersecurity                2          33.3     TechPulse, Daily Chronicle
5     autonomous                   2          33.3     TechPulse, Global Dispatch
======================================================================
```

### 4. Search Historical Stories

Query the SQLite vault for specific keywords or topics:

```bash
python main.py search "energy"
```

### 5. Generate Intelligence Digest

Export an executive digest report in Markdown format:

```bash
python main.py digest --format markdown -o digest.md
```

Also supports `--format json`, `--format csv`, or `--format text`.

### 6. Interactive Visual HTML Dashboard

Render an executive dashboard with animated SVG Donut & Bar Charts and live filterable article tables:

```bash
python main.py dashboard -o dashboard.html
```

### 7. Cross-Source Story Clustering

Group multi-outlet coverage into cohesive event story clusters using lexical Jaccard analysis:

```bash
python main.py cluster --threshold 0.25
```

### 8. Continuous Background Polling Daemon

Launch autonomous background polling to monitor news sources and watchlist alerts periodically:

```bash
# Run daemon polling every 60 seconds
python main.py monitor --interval 60

# Run in offline mode for testing
python main.py monitor --interval 10 --runs 3 --offline
```

### 9. Monitor Watchlist Alerts

Scan for triggers matching high-priority watchlist rules:

```bash
python main.py alerts
```

### 10. View Vault Metrics

Inspect database health, article counts, source distributions, and scrape run history:

```bash
python main.py stats
```

---

## Automated Test Suite

Run the full automated test suite using Python's built-in `unittest`:

```bash
python -m unittest discover -s tests -v
```

All tests execute self-contained unit assertions covering models, parsing, NLP, sentiment, SQLite deduplication, and CLI workflows.

---

## License

This project is licensed under the MIT License.

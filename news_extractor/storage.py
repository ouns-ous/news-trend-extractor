"""SQLite persistence layer with deduplication, full-text search, and historical trend auditing."""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from news_extractor.models import Article, ScrapeRun


class NewsVault:
    """Robust SQLite storage engine for indexed news articles and scrape history."""

    def __init__(self, db_path: Path | str = "news_vault.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def _init_db(self) -> None:
        """Create database tables and performance indexes."""
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT,
                source TEXT NOT NULL,
                summary TEXT,
                category TEXT DEFAULT 'General',
                author TEXT,
                published_at TEXT,
                scraped_at TEXT NOT NULL,
                keywords_json TEXT,
                sentiment_score REAL DEFAULT 0.0,
                sentiment_label TEXT DEFAULT 'Neutral'
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS article_keywords (
                article_id TEXT NOT NULL,
                keyword TEXT NOT NULL,
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scrape_runs (
                run_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                total_fetched INTEGER NOT NULL,
                new_added INTEGER NOT NULL,
                duplicates INTEGER NOT NULL,
                errors_json TEXT
            )
            """
        )

        # Performance and lookup indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_scraped_at ON articles(scraped_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON articles(sentiment_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_kw ON article_keywords(keyword)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_art ON article_keywords(article_id)")

        self.conn.commit()

    def save_article(self, article: Article) -> bool:
        """Insert or ignore an article. Returns True if inserted as new, False if duplicate."""
        cursor = self.conn.cursor()

        pub_str = article.published_at.isoformat() if article.published_at else None
        scrape_str = article.scraped_at.isoformat()
        kw_json = json.dumps(article.keywords)

        cursor.execute(
            """
            INSERT OR IGNORE INTO articles (
                id, title, url, source, summary, category, author,
                published_at, scraped_at, keywords_json, sentiment_score, sentiment_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article.id,
                article.title,
                article.url,
                article.source,
                article.summary,
                article.category,
                article.author,
                pub_str,
                scrape_str,
                kw_json,
                article.sentiment_score,
                article.sentiment_label,
            ),
        )

        inserted = cursor.rowcount > 0
        if inserted and article.keywords:
            cursor.executemany(
                "INSERT INTO article_keywords (article_id, keyword) VALUES (?, ?)",
                [(article.id, kw.lower()) for kw in article.keywords],
            )

        self.conn.commit()
        return inserted

    def save_articles(self, articles: List[Article]) -> Tuple[int, int]:
        """Save a batch of articles, returning count of (new_added, duplicates)."""
        new_count = 0
        dup_count = 0
        for art in articles:
            if self.save_article(art):
                new_count += 1
            else:
                dup_count += 1
        return new_count, dup_count

    def _row_to_article(self, row: sqlite3.Row) -> Article:
        """Convert a database row into an Article model."""
        keywords = []
        if row["keywords_json"]:
            try:
                keywords = json.loads(row["keywords_json"])
            except Exception:
                keywords = []

        pub_dt = None
        if row["published_at"]:
            try:
                pub_dt = datetime.fromisoformat(row["published_at"])
            except Exception:
                pub_dt = None

        scraped_dt = datetime.fromisoformat(row["scraped_at"])

        return Article(
            id=row["id"],
            title=row["title"],
            url=row["url"] or "",
            source=row["source"],
            summary=row["summary"] or "",
            category=row["category"] or "General",
            author=row["author"] or "",
            published_at=pub_dt,
            scraped_at=scraped_dt,
            keywords=keywords,
            sentiment_score=float(row["sentiment_score"] or 0.0),
            sentiment_label=row["sentiment_label"] or "Neutral",
        )

    def get_article(self, article_id: str) -> Optional[Article]:
        """Retrieve a specific article by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()
        return self._row_to_article(row) if row else None

    def get_articles(
        self,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None,
        source: Optional[str] = None,
        timeframe_hours: Optional[int] = None,
    ) -> List[Article]:
        """Query articles with filtering by category, source, or recency."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM articles WHERE 1=1"
        params: List[Any] = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if source:
            query += " AND source = ?"
            params.append(source)

        if timeframe_hours is not None:
            cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=timeframe_hours)).isoformat()
            query += " AND scraped_at >= ?"
            params.append(cutoff)

        query += " ORDER BY scraped_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [self._row_to_article(r) for r in cursor.fetchall()]

    def search(self, query_text: str, limit: int = 30) -> List[Article]:
        """Search articles matching title, summary, or keyword tags."""
        cursor = self.conn.cursor()
        term = f"%{query_text.strip()}%"
        sql = """
            SELECT DISTINCT a.* FROM articles a
            LEFT JOIN article_keywords k ON a.id = k.article_id
            WHERE a.title LIKE ? OR a.summary LIKE ? OR k.keyword LIKE ?
            ORDER BY a.scraped_at DESC
            LIMIT ?
        """
        cursor.execute(sql, (term, term, term, limit))
        return [self._row_to_article(r) for r in cursor.fetchall()]

    def record_scrape_run(self, run: ScrapeRun) -> None:
        """Store metadata regarding a scraping run."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO scrape_runs (
                run_id, timestamp, sources_json, total_fetched, new_added, duplicates, errors_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.timestamp.isoformat(),
                json.dumps(run.sources),
                run.total_fetched,
                run.new_added,
                run.duplicates,
                json.dumps(run.errors),
            ),
        )
        self.conn.commit()

    def get_scrape_runs(self, limit: int = 10) -> List[ScrapeRun]:
        """Retrieve recent scraping audit runs."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM scrape_runs ORDER BY timestamp DESC LIMIT ?", (limit,))
        runs = []
        for row in cursor.fetchall():
            runs.append(
                ScrapeRun(
                    run_id=row["run_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    sources=json.loads(row["sources_json"]),
                    total_fetched=row["total_fetched"],
                    new_added=row["new_added"],
                    duplicates=row["duplicates"],
                    errors=json.loads(row["errors_json"]) if row["errors_json"] else [],
                )
            )
        return runs

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate statistical metrics from the vault."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]

        cursor.execute("SELECT source, COUNT(*) FROM articles GROUP BY source ORDER BY COUNT(*) DESC")
        sources = dict(cursor.fetchall())

        cursor.execute("SELECT category, COUNT(*) FROM articles GROUP BY category ORDER BY COUNT(*) DESC")
        categories = dict(cursor.fetchall())

        cursor.execute("SELECT sentiment_label, COUNT(*) FROM articles GROUP BY sentiment_label")
        sentiment_dist = dict(cursor.fetchall())

        cursor.execute("SELECT MIN(scraped_at), MAX(scraped_at) FROM articles")
        min_date, max_date = cursor.fetchone()

        return {
            "total_articles": total_articles,
            "sources": sources,
            "categories": categories,
            "sentiment_distribution": sentiment_dist,
            "first_scraped_at": min_date,
            "latest_scraped_at": max_date,
        }

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> NewsVault:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

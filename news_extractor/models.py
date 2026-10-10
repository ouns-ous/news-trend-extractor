"""Data models for news extraction, analysis, trends, and reporting."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional


def _utc_now() -> datetime:
    """Return timezone-naive UTC timestamp."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class Article:
    """Represents an ingested news article or headline."""
    title: str
    url: str
    source: str
    summary: str = ""
    category: str = "General"
    author: str = ""
    published_at: Optional[datetime] = None
    scraped_at: datetime = field(default_factory=_utc_now)
    id: str = ""
    keywords: List[str] = field(default_factory=list)
    sentiment_score: float = 0.0
    sentiment_label: str = "Neutral"

    def __post_init__(self) -> None:
        """Compute deterministic content ID based on canonical URL or normalized title."""
        if not self.id:
            raw_key = (self.url.strip() or self.title.strip().lower()).encode("utf-8")
            self.id = hashlib.sha256(raw_key).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary representation."""
        data = asdict(self)
        if self.published_at:
            data["published_at"] = self.published_at.isoformat()
        data["scraped_at"] = self.scraped_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Article:
        """Construct Article from dictionary representation."""
        pub_at = data.get("published_at")
        if isinstance(pub_at, str):
            try:
                pub_at = datetime.fromisoformat(pub_at)
            except ValueError:
                pub_at = None

        scraped_at = data.get("scraped_at")
        if isinstance(scraped_at, str):
            try:
                scraped_at = datetime.fromisoformat(scraped_at)
            except ValueError:
                scraped_at = _utc_now()
        elif not isinstance(scraped_at, datetime):
            scraped_at = _utc_now()

        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            source=data.get("source", "Unknown"),
            summary=data.get("summary", ""),
            category=data.get("category", "General"),
            author=data.get("author", ""),
            published_at=pub_at,
            scraped_at=scraped_at,
            id=data.get("id", ""),
            keywords=data.get("keywords", []),
            sentiment_score=float(data.get("sentiment_score", 0.0)),
            sentiment_label=data.get("sentiment_label", "Neutral"),
        )


@dataclass
class TrendTopic:
    """Represents an extracted trending keyword, entity, or n-gram phrase."""
    phrase: str
    frequency: int
    score: float = 0.0
    velocity: float = 0.0
    sources: List[str] = field(default_factory=list)
    sample_titles: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SentimentResult:
    """Sentiment classification and polarity score."""
    score: float
    label: str  # 'Positive', 'Neutral', 'Negative'
    positive_words: List[str] = field(default_factory=list)
    negative_words: List[str] = field(default_factory=list)


@dataclass
class SentimentSummary:
    """Aggregate sentiment distribution across a dataset."""
    total_articles: int
    positive_count: int
    neutral_count: int
    negative_count: int
    average_score: float

    @property
    def positive_percentage(self) -> float:
        return (self.positive_count / self.total_articles * 100) if self.total_articles else 0.0

    @property
    def negative_percentage(self) -> float:
        return (self.negative_count / self.total_articles * 100) if self.total_articles else 0.0

    @property
    def neutral_percentage(self) -> float:
        return (self.neutral_count / self.total_articles * 100) if self.total_articles else 0.0


@dataclass
class ScrapeRun:
    """Metadata describing a completed scraping run."""
    run_id: str
    timestamp: datetime
    sources: List[str]
    total_fetched: int
    new_added: int
    duplicates: int
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class WatchlistAlert:
    """Trigger alert generated when an article matches watchlist patterns."""
    watchlist_name: str
    keyword: str
    article: Article
    timestamp: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "watchlist_name": self.watchlist_name,
            "keyword": self.keyword,
            "article": self.article.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class Digest:
    """Compiled intelligence digest report."""
    generated_at: datetime
    timeframe_hours: int
    total_articles: int
    top_trends: List[TrendTopic]
    sentiment: SentimentSummary
    source_breakdown: Dict[str, int]
    category_breakdown: Dict[str, int]
    alerts: List[WatchlistAlert] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "timeframe_hours": self.timeframe_hours,
            "total_articles": self.total_articles,
            "top_trends": [t.to_dict() for t in self.top_trends],
            "sentiment": asdict(self.sentiment),
            "source_breakdown": self.source_breakdown,
            "category_breakdown": self.category_breakdown,
            "alerts": [a.to_dict() for a in self.alerts],
        }

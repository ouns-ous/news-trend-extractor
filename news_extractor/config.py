"""Configuration loader and predefined news sources catalog."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SourceConfig:
    """Configuration for an individual news feed source."""
    name: str
    url: str
    feed_type: str = "rss"  # 'rss', 'atom', 'html'
    category: str = "General"
    enabled: bool = True
    html_selector: Optional[str] = None
    max_items: int = 30


@dataclass
class AppConfig:
    """Master application configuration."""
    db_path: str = "news_vault.db"
    timeout_seconds: int = 12
    user_agent: str = "NewsPulseBot/1.0 (+https://github.com/ouns-ous/news-trend-extractor)"
    min_keyword_length: int = 3
    min_trend_frequency: int = 2
    top_trends_count: int = 15
    sources: List[SourceConfig] = field(default_factory=list)
    watchlists: Dict[str, List[str]] = field(default_factory=dict)
    custom_stop_words: List[str] = field(default_factory=list)

    @classmethod
    def default(cls) -> AppConfig:
        """Create a default populated application configuration."""
        sources = [
            SourceConfig(
                name="Hacker News Frontpage",
                url="https://news.ycombinator.com/rss",
                feed_type="rss",
                category="Technology",
                enabled=True,
                max_items=30,
            ),
            SourceConfig(
                name="BBC News World",
                url="http://feeds.bbci.co.uk/news/world/rss.xml",
                feed_type="rss",
                category="World",
                enabled=True,
                max_items=25,
            ),
            SourceConfig(
                name="BBC News Technology",
                url="http://feeds.bbci.co.uk/news/technology/rss.xml",
                feed_type="rss",
                category="Technology",
                enabled=True,
                max_items=25,
            ),
            SourceConfig(
                name="ArXiv AI Preprints",
                url="https://rss.arxiv.org/rss/cs.AI",
                feed_type="rss",
                category="Science",
                enabled=True,
                max_items=25,
            ),
        ]

        watchlists = {
            "Artificial Intelligence": ["ai", "llm", "deep learning", "neural network", "openai", "agent", "gpu"],
            "Cybersecurity": ["vulnerability", "breach", "zero-day", "ransomware", "malware", "hack", "cve"],
            "Markets & Economy": ["inflation", "federal reserve", "stock", "interest rate", "revenue", "recession"],
        }

        return cls(
            db_path="news_vault.db",
            timeout_seconds=10,
            user_agent="NewsPulseBot/1.0 (+https://github.com/ouns-ous/news-trend-extractor)",
            min_keyword_length=3,
            min_trend_frequency=2,
            top_trends_count=15,
            sources=sources,
            watchlists=watchlists,
            custom_stop_words=["said", "also", "new", "one", "two", "years", "time", "week"],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert AppConfig to serializable dictionary."""
        return {
            "db_path": self.db_path,
            "timeout_seconds": self.timeout_seconds,
            "user_agent": self.user_agent,
            "min_keyword_length": self.min_keyword_length,
            "min_trend_frequency": self.min_trend_frequency,
            "top_trends_count": self.top_trends_count,
            "sources": [asdict(s) for s in self.sources],
            "watchlists": self.watchlists,
            "custom_stop_words": self.custom_stop_words,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppConfig:
        """Instantiate AppConfig from dictionary."""
        raw_sources = data.get("sources", [])
        sources = [
            SourceConfig(
                name=s.get("name", "Unknown"),
                url=s.get("url", ""),
                feed_type=s.get("feed_type", "rss"),
                category=s.get("category", "General"),
                enabled=s.get("enabled", True),
                html_selector=s.get("html_selector"),
                max_items=int(s.get("max_items", 30)),
            )
            for s in raw_sources
        ]

        return cls(
            db_path=data.get("db_path", "news_vault.db"),
            timeout_seconds=int(data.get("timeout_seconds", 10)),
            user_agent=data.get("user_agent", "NewsPulseBot/1.0"),
            min_keyword_length=int(data.get("min_keyword_length", 3)),
            min_trend_frequency=int(data.get("min_trend_frequency", 2)),
            top_trends_count=int(data.get("top_trends_count", 15)),
            sources=sources or cls.default().sources,
            watchlists=data.get("watchlists", cls.default().watchlists),
            custom_stop_words=data.get("custom_stop_words", []),
        )

    @classmethod
    def load_from_file(cls, path: Path | str) -> AppConfig:
        """Load configuration from a JSON file, or return default if missing."""
        file_path = Path(path)
        if not file_path.exists():
            return cls.default()
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_file(self, path: Path | str) -> None:
        """Save current configuration to JSON file."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

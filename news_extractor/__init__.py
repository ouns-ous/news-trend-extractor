"""NewsPulse: Autonomous News Headline & Trending Topics Extractor.

A modular intelligence engine for scraping multi-source news headlines,
extracting n-gram trending topics, computing sentiment, and generating digests.
"""

__version__ = "1.1.0"
__author__ = "ouns oussama"

from news_extractor.models import Article, TrendTopic, SentimentResult, ScrapeRun, Digest
from news_extractor.storage import NewsVault
from news_extractor.scraper import MultiSourceScraper
from news_extractor.analyzer import TrendAnalyzer, SentimentAnalyzer
from news_extractor.alerts import WatchlistMonitor
from news_extractor.reporter import DigestReporter
from news_extractor.clustering import StoryCluster, ClusterEngine
from news_extractor.dashboard import DashboardGenerator
from news_extractor.scheduler import NewsMonitor

__all__ = [
    "Article",
    "TrendTopic",
    "SentimentResult",
    "ScrapeRun",
    "Digest",
    "NewsVault",
    "MultiSourceScraper",
    "TrendAnalyzer",
    "SentimentAnalyzer",
    "WatchlistMonitor",
    "DigestReporter",
    "StoryCluster",
    "ClusterEngine",
    "DashboardGenerator",
    "NewsMonitor",
]

"""Watchlist monitor for tracking custom keywords and generating notifications."""

from __future__ import annotations
import re
from typing import Dict, List

from news_extractor.models import Article, WatchlistAlert


class WatchlistMonitor:
    """Evaluates articles against user-defined keyword watchlists and alert criteria."""

    def __init__(self, watchlists: Dict[str, List[str]]) -> None:
        self.watchlists = watchlists

    def check_article(self, article: Article) -> List[WatchlistAlert]:
        """Check if an individual article triggers any watchlist rules."""
        alerts: List[WatchlistAlert] = []
        full_text = f"{article.title} {article.summary}".lower()

        for list_name, keywords in self.watchlists.items():
            for kw in keywords:
                pattern = r"\b" + re.escape(kw.lower()) + r"\b"
                if re.search(pattern, full_text):
                    alerts.append(
                        WatchlistAlert(
                            watchlist_name=list_name,
                            keyword=kw,
                            article=article,
                        )
                    )
                    break  # One alert per watchlist per article

        return alerts

    def evaluate_all(self, articles: List[Article]) -> List[WatchlistAlert]:
        """Scan a batch of articles and aggregate all triggered alerts."""
        all_alerts: List[WatchlistAlert] = []
        for article in articles:
            all_alerts.extend(self.check_article(article))
        return all_alerts

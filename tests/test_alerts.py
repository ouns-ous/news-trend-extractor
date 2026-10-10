"""Unit tests for WatchlistMonitor."""

import unittest

from news_extractor.models import Article
from news_extractor.alerts import WatchlistMonitor


class TestAlerts(unittest.TestCase):
    """Test keyword matching and alert triggering."""

    def setUp(self) -> None:
        self.watchlists = {
            "AI Watch": ["llm", "neural network", "agent"],
            "Security Watch": ["zero-day", "ransomware", "breach"],
        }
        self.monitor = WatchlistMonitor(self.watchlists)

    def test_alert_trigger(self) -> None:
        art = Article(
            title="Critical zero-day discovered in enterprise servers",
            url="http://sec/1",
            source="SecNews",
            summary="Patch immediately to avoid ransomware infection.",
        )
        alerts = self.monitor.check_article(art)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].watchlist_name, "Security Watch")
        self.assertEqual(alerts[0].keyword, "zero-day")

    def test_no_alert_when_unmatched(self) -> None:
        art = Article(
            title="Local bakery wins prize for sourdough bread",
            url="http://bakery/1",
            source="LocalNews",
            summary="Delicious bread recognized at county fair.",
        )
        alerts = self.monitor.check_article(art)
        self.assertEqual(len(alerts), 0)


if __name__ == "__main__":
    unittest.main()

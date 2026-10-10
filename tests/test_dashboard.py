"""Unit tests for DashboardGenerator."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from news_extractor.models import Article, TrendTopic, SentimentSummary, Digest
from news_extractor.dashboard import DashboardGenerator


class TestDashboard(unittest.TestCase):
    """Test HTML and SVG dashboard rendering and file export."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.now = datetime.now(timezone.utc).replace(tzinfo=None)

        self.articles = [
            Article(title="AI Surge in Enterprise", url="http://1", source="SrcA", category="Tech", sentiment_label="Positive", sentiment_score=0.7),
            Article(title="Cyber Crisis Alert", url="http://2", source="SrcB", category="Sec", sentiment_label="Negative", sentiment_score=-0.8),
            Article(title="Markets Hold Steady", url="http://3", source="SrcC", category="Economy", sentiment_label="Neutral", sentiment_score=0.0),
        ]
        self.sentiment = SentimentSummary(total_articles=3, positive_count=1, neutral_count=1, negative_count=1, average_score=-0.03)
        self.trends = [TrendTopic(phrase="enterprise ai", frequency=2, score=66.7, velocity=1.0, sources=["SrcA"])]

        self.digest = Digest(
            generated_at=self.now,
            timeframe_hours=24,
            total_articles=3,
            top_trends=self.trends,
            sentiment=self.sentiment,
            source_breakdown={"SrcA": 1, "SrcB": 1, "SrcC": 1},
            category_breakdown={"Tech": 1, "Sec": 1, "Economy": 1},
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_render_html_content(self) -> None:
        html_str = DashboardGenerator.render(self.digest, self.articles)
        self.assertIn("<!DOCTYPE html>", html_str)
        self.assertIn("NewsPulse", html_str)
        self.assertIn("<svg", html_str)
        self.assertIn("donut-chart", html_str)
        self.assertIn("AI Surge in Enterprise", html_str)

    def test_export_dashboard_file(self) -> None:
        out_file = Path(self.temp_dir.name) / "test_dash.html"
        result_path = DashboardGenerator.export(self.digest, self.articles, out_file)
        self.assertTrue(result_path.exists())
        self.assertGreater(result_path.stat().st_size, 500)


if __name__ == "__main__":
    unittest.main()

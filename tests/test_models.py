"""Unit tests for models and dataclasses."""

from datetime import datetime
import unittest

from news_extractor.models import Article, TrendTopic, SentimentResult, SentimentSummary, Digest


class TestModels(unittest.TestCase):
    """Test Article and data structures serialization and logic."""

    def test_article_deterministic_id(self) -> None:
        art1 = Article(title="OpenAI announces new reasoning models", url="https://example.com/openai", source="Tech")
        art2 = Article(title="OpenAI announces new reasoning models", url="https://example.com/openai", source="Tech")
        self.assertEqual(art1.id, art2.id)
        self.assertTrue(len(art1.id) >= 8)

    def test_article_serialization_roundtrip(self) -> None:
        art = Article(
            title="Clean Energy Summit",
            url="https://example.com/clean",
            source="Global",
            summary="Renewables surge worldwide",
            category="Energy",
            author="Reporter A",
            published_at=datetime(2026, 10, 10, 8, 30, 0),
            keywords=["clean energy", "renewables"],
            sentiment_score=0.45,
            sentiment_label="Positive",
        )
        d = art.to_dict()
        art_reconstructed = Article.from_dict(d)
        self.assertEqual(art.title, art_reconstructed.title)
        self.assertEqual(art.url, art_reconstructed.url)
        self.assertEqual(art.keywords, art_reconstructed.keywords)
        self.assertEqual(art.sentiment_label, art_reconstructed.sentiment_label)
        self.assertEqual(art.sentiment_score, art_reconstructed.sentiment_score)

    def test_sentiment_summary_percentages(self) -> None:
        summary = SentimentSummary(
            total_articles=10,
            positive_count=5,
            neutral_count=3,
            negative_count=2,
            average_score=0.25,
        )
        self.assertAlmostEqual(summary.positive_percentage, 50.0)
        self.assertAlmostEqual(summary.neutral_percentage, 30.0)
        self.assertAlmostEqual(summary.negative_percentage, 20.0)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for NLP TrendAnalyzer and SentimentAnalyzer."""

import unittest

from news_extractor.models import Article
from news_extractor.analyzer import TrendAnalyzer, SentimentAnalyzer


class TestAnalyzer(unittest.TestCase):
    """Test text processing, n-grams, trends, and sentiment classification."""

    def setUp(self) -> None:
        self.analyzer = TrendAnalyzer(min_word_len=3, min_freq=2)
        self.sentiment = SentimentAnalyzer()

    def test_tokenization_and_stop_words(self) -> None:
        raw_text = "The latest report said that artificial intelligence is surging rapidly today!"
        tokens = self.analyzer.tokenize(raw_text)
        self.assertNotIn("the", tokens)
        self.assertNotIn("said", tokens)
        self.assertNotIn("today", tokens)
        self.assertIn("artificial", tokens)
        self.assertIn("intelligence", tokens)
        self.assertIn("surging", tokens)

    def test_extract_ngrams(self) -> None:
        tokens = ["artificial", "intelligence", "agent", "automation"]
        bigrams = self.analyzer.extract_ngrams(tokens, 2)
        self.assertEqual(bigrams, [
            "artificial intelligence",
            "intelligence agent",
            "agent automation",
        ])

    def test_compute_trends_frequency(self) -> None:
        articles = [
            Article(title="Quantum computing breakthrough announced", url="http://1", source="S1", summary="Major quantum leap"),
            Article(title="Quantum computing startups raise capital", url="http://2", source="S2", summary="Quantum computing is accelerating"),
            Article(title="Global clean energy investments surge", url="http://3", source="S3", summary="Solar power grows"),
        ]
        trends = self.analyzer.compute_trends(articles, top_n=5)
        self.assertTrue(len(trends) > 0)
        phrases = [t.phrase for t in trends]
        self.assertTrue("quantum" in phrases or "quantum computing" in phrases)

    def test_sentiment_positive_detection(self) -> None:
        res = self.sentiment.analyze_text("Scientists celebrate historic clean energy breakthrough and record gains!")
        self.assertEqual(res.label, "Positive")
        self.assertGreater(res.score, 0.3)
        self.assertIn("breakthrough", res.positive_words)

    def test_sentiment_negative_detection(self) -> None:
        res = self.sentiment.analyze_text("Severe cyber crisis and zero-day breach plunge stock markets into turmoil.")
        self.assertEqual(res.label, "Negative")
        self.assertLess(res.score, -0.3)
        self.assertIn("crisis", res.negative_words)

    def test_sentiment_negation_inversion(self) -> None:
        positive_res = self.sentiment.analyze_text("The enterprise reported huge growth and success.")
        negated_res = self.sentiment.analyze_text("The enterprise reported not growth and no success.")
        self.assertEqual(positive_res.label, "Positive")
        self.assertEqual(negated_res.label, "Negative")


if __name__ == "__main__":
    unittest.main()

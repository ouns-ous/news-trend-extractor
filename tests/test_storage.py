"""Unit tests for SQLite NewsVault storage layer."""

import tempfile
from pathlib import Path
import unittest

from news_extractor.models import Article, ScrapeRun
from news_extractor.storage import NewsVault


class TestNewsVault(unittest.TestCase):
    """Test SQLite operations, indexing, and deduplication."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_vault.db"
        self.vault = NewsVault(self.db_path)

    def tearDown(self) -> None:
        self.vault.close()
        self.temp_dir.cleanup()

    def test_save_and_deduplicate_article(self) -> None:
        art = Article(
            title="NASA Discovers Exoplanet Atmosphere",
            url="https://nasa.example.com/exoplanet",
            source="SpaceNews",
            summary="New atmosphere analyzed by space telescope.",
            category="Science",
        )
        first_save = self.vault.save_article(art)
        self.assertTrue(first_save)

        # Duplicate save should be rejected (returns False)
        second_save = self.vault.save_article(art)
        self.assertFalse(second_save)

    def test_batch_save_and_retrieval(self) -> None:
        articles = [
            Article(title="AI Breakthrough 1", url="http://test/1", source="SrcA", category="AI"),
            Article(title="AI Breakthrough 2", url="http://test/2", source="SrcA", category="AI"),
            Article(title="Economy Shift 1", url="http://test/3", source="SrcB", category="Finance"),
        ]
        new_cnt, dup_cnt = self.vault.save_articles(articles)
        self.assertEqual(new_cnt, 3)
        self.assertEqual(dup_cnt, 0)

        # Query filtered by category
        ai_articles = self.vault.get_articles(category="AI")
        self.assertEqual(len(ai_articles), 2)

        # Query filtered by source
        src_b = self.vault.get_articles(source="SrcB")
        self.assertEqual(len(src_b), 1)

    def test_search_functionality(self) -> None:
        art1 = Article(title="Deep Neural Networks in Healthcare", url="http://1", source="Med", keywords=["neural", "healthcare"])
        art2 = Article(title="Superconductor Magnetic Levitation", url="http://2", source="Physics", keywords=["levitation"])
        self.vault.save_articles([art1, art2])

        results = self.vault.search("healthcare")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Deep Neural Networks in Healthcare")

    def test_record_and_get_scrape_runs(self) -> None:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        run = ScrapeRun(
            run_id="run_001",
            timestamp=now,
            sources=["TechPulse", "GlobalNews"],
            total_fetched=20,
            new_added=15,
            duplicates=5,
            errors=[],
        )
        self.vault.record_scrape_run(run)
        runs = self.vault.get_scrape_runs(limit=5)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].run_id, "run_001")
        self.assertEqual(runs[0].new_added, 15)

    def test_vault_stats(self) -> None:
        art = Article(title="Title X", url="http://x", source="TestSrc", category="General", sentiment_label="Positive")
        self.vault.save_article(art)
        stats = self.vault.get_stats()
        self.assertEqual(stats["total_articles"], 1)
        self.assertEqual(stats["sources"].get("TestSrc"), 1)
        self.assertEqual(stats["sentiment_distribution"].get("Positive"), 1)


if __name__ == "__main__":
    unittest.main()

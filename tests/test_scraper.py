"""Unit tests for MultiSourceScraper parsing RSS, Atom, HTML and fixtures."""

from pathlib import Path
import unittest

from news_extractor.scraper import MultiSourceScraper


class TestScraper(unittest.TestCase):
    """Test RSS, Atom, and HTML parsers."""

    def setUp(self) -> None:
        self.fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
        self.scraper = MultiSourceScraper(fixtures_dir=self.fixtures_dir)

    def test_parse_rss_from_fixture(self) -> None:
        tech_xml = (self.fixtures_dir / "tech_feed.xml").read_text(encoding="utf-8")
        articles = self.scraper.parse_rss(tech_xml, source_name="TechFeed", default_category="Technology")
        self.assertGreaterEqual(len(articles), 4)

        first = articles[0]
        self.assertIn("AI Agents", first.title)
        self.assertEqual(first.source, "TechFeed")
        self.assertTrue(first.url.startswith("https://"))
        self.assertIsNotNone(first.published_at)

    def test_parse_atom_sample(self) -> None:
        atom_sample = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Example Atom Feed</title>
          <entry>
            <title>Quantum Computing Algorithms Advance</title>
            <link href="https://example.com/quantum-atom"/>
            <id>urn:uuid:12345</id>
            <updated>2026-10-10T12:00:00Z</updated>
            <summary>Key mathematical proofs established for quantum Shor speedups.</summary>
          </entry>
        </feed>
        """
        articles = self.scraper.parse_atom(atom_sample, source_name="AtomFeed", default_category="Science")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Quantum Computing Algorithms Advance")
        self.assertEqual(articles[0].url, "https://example.com/quantum-atom")
        self.assertIn("mathematical proofs", articles[0].summary)

    def test_parse_html_from_fixture(self) -> None:
        html_content = (self.fixtures_dir / "custom_page.html").read_text(encoding="utf-8")
        articles = self.scraper.parse_html(html_content, source_name="Chronicle", default_category="General")
        self.assertGreaterEqual(len(articles), 3)
        titles = [a.title for a in articles]
        self.assertTrue(any("AI Robotics Assistants" in t for t in titles))
        self.assertTrue(any("Green Hydrogen Power Plant" in t for t in titles))

    def test_fetch_offline_fixtures(self) -> None:
        fixtures_articles = self.scraper.fetch_offline_fixtures()
        self.assertGreaterEqual(len(fixtures_articles), 10)
        sources = {a.source for a in fixtures_articles}
        self.assertIn("TechPulse (Offline)", sources)
        self.assertIn("Global Dispatch (Offline)", sources)


if __name__ == "__main__":
    unittest.main()

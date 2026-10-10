"""Unit tests for ClusterEngine and StoryCluster."""

import unittest

from news_extractor.models import Article
from news_extractor.clustering import ClusterEngine, StoryCluster


class TestClustering(unittest.TestCase):
    """Test pairwise similarity and story clustering."""

    def setUp(self) -> None:
        self.engine = ClusterEngine(similarity_threshold=0.30)

    def test_jaccard_similarity(self) -> None:
        set_a = {"quantum", "computing", "breakthrough", "algorithms"}
        set_b = {"quantum", "computing", "researchers", "hardware"}
        sim = self.engine.jaccard_similarity(set_a, set_b)
        self.assertAlmostEqual(sim, 2 / 6)  # 2 in intersection, 6 in union

    def test_cluster_articles_grouping(self) -> None:
        articles = [
            Article(title="Quantum computing breakthrough achieves logical qubits", url="http://1", source="Outlet A", keywords=["quantum", "qubits"]),
            Article(title="Researchers celebrate quantum computing milestone with qubits", url="http://2", source="Outlet B", keywords=["quantum", "qubits"]),
            Article(title="Federal Reserve signals interest rate cuts amid cooling inflation", url="http://3", source="Outlet C", keywords=["inflation", "rates"]),
        ]
        clusters = self.engine.cluster_articles(articles)
        self.assertGreaterEqual(len(clusters), 2)

        # First cluster should group the two quantum articles
        top_cluster = clusters[0]
        self.assertEqual(len(top_cluster.articles), 2)
        self.assertIn("Outlet A", top_cluster.sources)
        self.assertIn("Outlet B", top_cluster.sources)
        d = top_cluster.to_dict()
        self.assertEqual(d["article_count"], 2)


if __name__ == "__main__":
    unittest.main()

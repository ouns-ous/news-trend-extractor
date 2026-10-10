"""Story clustering engine for grouping cross-source coverage of the same event."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple
import hashlib

from news_extractor.models import Article


@dataclass
class StoryCluster:
    """Represents a cohesive cluster of articles covering the same breaking story."""
    cluster_id: str
    representative_title: str
    articles: List[Article] = field(default_factory=list)
    common_keywords: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    average_sentiment: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        return {
            "cluster_id": self.cluster_id,
            "representative_title": self.representative_title,
            "article_count": len(self.articles),
            "sources": self.sources,
            "common_keywords": self.common_keywords,
            "average_sentiment": round(self.average_sentiment, 2),
            "articles": [a.to_dict() for a in self.articles],
        }


class ClusterEngine:
    """Clusters news articles across distinct outlets based on lexical Jaccard overlap."""

    def __init__(self, similarity_threshold: float = 0.30) -> None:
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def _get_token_set(article: Article) -> Set[str]:
        """Extract normalized words and keyword set for similarity comparisons."""
        words = set(article.title.lower().split())
        words.update(kw.lower() for kw in article.keywords)
        # Filter trivial short words
        return {w.strip(".,!?:;\"'()[]") for w in words if len(w) >= 3}

    @staticmethod
    def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
        """Compute Jaccard similarity coefficient between two token sets."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def cluster_articles(self, articles: List[Article]) -> List[StoryCluster]:
        """Group similar articles into StoryClusters."""
        if not articles:
            return []

        article_tokens = [self._get_token_set(a) for a in articles]
        visited: Set[int] = set()
        clusters: List[StoryCluster] = []

        for i in range(len(articles)):
            if i in visited:
                continue

            current_group: List[Article] = [articles[i]]
            current_tokens = set(article_tokens[i])
            visited.add(i)

            for j in range(i + 1, len(articles)):
                if j in visited:
                    continue

                sim = self.jaccard_similarity(current_tokens, article_tokens[j])
                if sim >= self.similarity_threshold:
                    current_group.append(articles[j])
                    current_tokens.update(article_tokens[j])
                    visited.add(j)

            # Determine cluster properties
            rep_title = current_group[0].title
            sources = sorted(list({a.source for a in current_group}))
            avg_sentiment = sum(a.sentiment_score for a in current_group) / len(current_group)

            # Compute shared keywords across cluster
            kw_counts: Dict[str, int] = {}
            for a in current_group:
                for kw in a.keywords:
                    kw_counts[kw] = kw_counts.get(kw, 0) + 1
            shared_kws = [k for k, cnt in sorted(kw_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

            cid = hashlib.sha256(rep_title.encode("utf-8")).hexdigest()[:12]

            clusters.append(
                StoryCluster(
                    cluster_id=cid,
                    representative_title=rep_title,
                    articles=current_group,
                    common_keywords=shared_kws,
                    sources=sources,
                    average_sentiment=avg_sentiment,
                )
            )

        # Sort clusters by size (largest cross-outlet coverage first)
        clusters.sort(key=lambda c: len(c.articles), reverse=True)
        return clusters

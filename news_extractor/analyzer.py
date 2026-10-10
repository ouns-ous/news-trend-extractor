"""Natural Language Processing, n-gram topic modeling, trend velocity, and sentiment analyzer."""

from __future__ import annotations
from collections import Counter, defaultdict
import math
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

from news_extractor.models import Article, TrendTopic, SentimentResult, SentimentSummary

# Standard high-frequency stop-words + news reporting noise
DEFAULT_STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had",
    "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
    "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves",
    # Common journalistic noise words
    "says", "said", "saying", "also", "new", "one", "two", "three", "first", "last", "year",
    "years", "time", "week", "month", "today", "day", "days", "reuters", "report", "reports",
    "reported", "according", "amid", "across", "per", "via", "could", "would", "may", "might",
    "video", "audio", "news", "update", "latest",
}

POSITIVE_LEXICON: Dict[str, float] = {
    "breakthrough": 2.0, "surge": 1.5, "record": 1.2, "triumph": 1.8, "historic": 1.5,
    "success": 1.5, "successful": 1.4, "growth": 1.3, "rally": 1.4, "gain": 1.2,
    "gains": 1.2, "boost": 1.3, "soar": 1.5, "soars": 1.5, "outperform": 1.6,
    "promising": 1.2, "optimism": 1.4, "optimistic": 1.3, "accord": 1.3, "agreement": 1.1,
    "peace": 1.5, "clean": 1.1, "renewable": 1.1, "innovation": 1.4, "innovative": 1.3,
    "advance": 1.2, "advances": 1.2, "win": 1.3, "wins": 1.3, "award": 1.2,
    "celebrate": 1.3, "celebrates": 1.3, "stable": 1.1, "stability": 1.2, "thrive": 1.5,
    "thriving": 1.5, "recovery": 1.3, "rebound": 1.3, "efficient": 1.2, "breakthroughs": 2.0,
}

NEGATIVE_LEXICON: Dict[str, float] = {
    "crisis": 2.0, "crash": 2.0, "crashes": 2.0, "plunge": 1.8, "plunges": 1.8,
    "collapse": 2.0, "collapses": 2.0, "warning": 1.4, "warns": 1.3, "threat": 1.6,
    "threatens": 1.5, "vulnerability": 1.8, "vulnerabilities": 1.8, "breach": 1.8,
    "breaches": 1.8, "hack": 1.5, "hacked": 1.6, "malware": 1.7, "ransomware": 1.9,
    "recession": 1.8, "inflation": 1.2, "war": 2.0, "conflict": 1.5, "strike": 1.3,
    "decline": 1.3, "declines": 1.3, "drop": 1.2, "drops": 1.2, "fail": 1.5,
    "fails": 1.5, "failure": 1.6, "lawsuit": 1.3, "sue": 1.3, "sued": 1.3,
    "danger": 1.6, "dangerous": 1.5, "death": 2.0, "deadly": 2.0, "kill": 1.8,
    "risk": 1.2, "risks": 1.2, "investigation": 1.2, "scandal": 1.8, "turmoil": 1.6,
}

NEGATION_WORDS: Set[str] = {"not", "no", "never", "without", "hardly", "barely", "rarely"}


class TrendAnalyzer:
    """Extracts n-grams, identifies trending entities, and calculates trend velocity."""

    def __init__(
        self,
        custom_stop_words: Optional[Iterable[str]] = None,
        min_word_len: int = 3,
        min_freq: int = 2,
    ) -> None:
        self.stop_words: Set[str] = set(DEFAULT_STOP_WORDS)
        if custom_stop_words:
            self.stop_words.update(w.lower().strip() for w in custom_stop_words)
        self.min_word_len = min_word_len
        self.min_freq = min_freq

    def tokenize(self, text: str) -> List[str]:
        """Convert text into cleaned alphanumeric token sequences."""
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9'-]*\b", text.lower())
        cleaned = [
            t.strip("'-")
            for t in tokens
            if len(t.strip("'-")) >= self.min_word_len and t.strip("'-") not in self.stop_words
        ]
        return cleaned

    def extract_ngrams(self, tokens: List[str], n: int) -> List[str]:
        """Generate n-gram phrases from a token list."""
        if len(tokens) < n:
            return []
        return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]

    def extract_article_keywords(self, article: Article, top_k: int = 5) -> List[str]:
        """Extract top relevant keywords and multi-word phrases for an article."""
        full_text = f"{article.title} {article.title} {article.summary}"
        tokens = self.tokenize(full_text)
        if not tokens:
            return []

        counts = Counter(tokens)
        bigrams = self.extract_ngrams(tokens, 2)
        bigram_counts = Counter(bigrams)

        # Boost bigrams that appear multiple times or in title
        scored_phrases: List[Tuple[str, float]] = []
        for bg, bg_cnt in bigram_counts.items():
            if bg_cnt >= 1:
                scored_phrases.append((bg, bg_cnt * 2.2))

        for unigram, u_cnt in counts.items():
            scored_phrases.append((unigram, float(u_cnt)))

        scored_phrases.sort(key=lambda x: x[1], reverse=True)
        seen_words: Set[str] = set()
        chosen: List[str] = []

        for phrase, _ in scored_phrases:
            words = phrase.split()
            # Prevent single words that are already represented by a top bigram
            if len(words) == 1 and words[0] in seen_words:
                continue
            chosen.append(phrase)
            seen_words.update(words)
            if len(chosen) >= top_k:
                break

        return chosen

    def compute_trends(
        self,
        articles: List[Article],
        top_n: int = 15,
        baseline_articles: Optional[List[Article]] = None,
    ) -> List[TrendTopic]:
        """Aggregate n-grams across all articles, compute frequency and trend velocity."""
        if not articles:
            return []

        phrase_counts: Counter[str] = Counter()
        phrase_sources: Dict[str, Set[str]] = defaultdict(set)
        phrase_samples: Dict[str, List[str]] = defaultdict(list)
        total_tokens = 0

        for article in articles:
            # Emphasize title text with higher weight
            title_tokens = self.tokenize(article.title)
            summary_tokens = self.tokenize(article.summary)
            all_tokens = title_tokens + summary_tokens
            total_tokens += len(all_tokens)

            # Collect unigrams and bigrams
            unigrams = title_tokens + summary_tokens
            bigrams = self.extract_ngrams(title_tokens, 2) + self.extract_ngrams(summary_tokens, 2)
            trigrams = self.extract_ngrams(title_tokens, 3)

            # Count unique mentions per article to avoid repetitive keyword spam
            article_phrases: Set[str] = set(unigrams) | set(bigrams) | set(trigrams)

            for phrase in article_phrases:
                phrase_counts[phrase] += 1
                phrase_sources[phrase].add(article.source)
                if len(phrase_samples[phrase]) < 3:
                    phrase_samples[phrase].append(article.title)

        # Baseline comparison for trend velocity
        baseline_counts: Counter[str] = Counter()
        if baseline_articles:
            for b_art in baseline_articles:
                b_tokens = self.tokenize(b_art.title) + self.tokenize(b_art.summary)
                b_phrases = set(b_tokens) | set(self.extract_ngrams(b_tokens, 2))
                for bp in b_phrases:
                    baseline_counts[bp] += 1

        trends: List[TrendTopic] = []
        for phrase, count in phrase_counts.items():
            if count < self.min_freq:
                continue

            # Multi-word phrases get a prominence bonus
            word_count = len(phrase.split())
            length_bonus = 1.0 + (0.5 * (word_count - 1))
            score = (count / max(1, len(articles))) * length_bonus * 100.0

            # Calculate velocity: ratio of current occurrences vs baseline
            if baseline_articles and len(baseline_articles) > 0:
                base_count = baseline_counts.get(phrase, 0)
                norm_current = count / len(articles)
                norm_base = base_count / len(baseline_articles)
                velocity = (norm_current - norm_base) / (norm_base + 0.05)
            else:
                velocity = float(count)

            trends.append(
                TrendTopic(
                    phrase=phrase,
                    frequency=count,
                    score=round(score, 2),
                    velocity=round(velocity, 2),
                    sources=sorted(list(phrase_sources[phrase])),
                    sample_titles=phrase_samples[phrase],
                )
            )

        # Sort primarily by score, breaking ties with multi-word richness
        trends.sort(key=lambda t: (t.score, len(t.phrase.split()), t.frequency), reverse=True)
        return trends[:top_n]


class SentimentAnalyzer:
    """Lexicon-based sentiment engine with negation inversion and polarity normalization."""

    def __init__(self) -> None:
        self.positive_lexicon = POSITIVE_LEXICON
        self.negative_lexicon = NEGATIVE_LEXICON
        self.negation_words = NEGATION_WORDS

    def analyze_text(self, text: str) -> SentimentResult:
        """Calculate sentiment polarity score and detected sentiment terms."""
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9'-]*\b", text.lower())
        if not words:
            return SentimentResult(score=0.0, label="Neutral")

        pos_matches: List[str] = []
        neg_matches: List[str] = []
        raw_score = 0.0
        negate_next = 0

        for i, word in enumerate(words):
            is_negated = negate_next > 0
            if negate_next > 0:
                negate_next -= 1

            if word in self.negation_words:
                negate_next = 2  # Invert polarity for the subsequent two tokens
                continue

            if word in self.positive_lexicon:
                weight = self.positive_lexicon[word]
                if is_negated:
                    raw_score -= weight
                    neg_matches.append(f"not-{word}")
                else:
                    raw_score += weight
                    pos_matches.append(word)

            elif word in self.negative_lexicon:
                weight = self.negative_lexicon[word]
                if is_negated:
                    raw_score += weight
                    pos_matches.append(f"not-{word}")
                else:
                    raw_score -= weight
                    neg_matches.append(word)

        # Normalization with hyperbolic tangent curve to bound in [-1.0, 1.0]
        score = math.tanh(raw_score / 2.5)
        score = round(score, 3)

        if score >= 0.15:
            label = "Positive"
        elif score <= -0.15:
            label = "Negative"
        else:
            label = "Neutral"

        return SentimentResult(
            score=score,
            label=label,
            positive_words=pos_matches,
            negative_words=neg_matches,
        )

    def analyze_article(self, article: Article) -> Article:
        """Compute and set sentiment properties on an Article."""
        combined_text = f"{article.title} {article.summary}"
        res = self.analyze_text(combined_text)
        article.sentiment_score = res.score
        article.sentiment_label = res.label
        return article

    def summarize(self, articles: List[Article]) -> SentimentSummary:
        """Generate aggregate sentiment metrics across a collection of articles."""
        total = len(articles)
        if total == 0:
            return SentimentSummary(0, 0, 0, 0, 0.0)

        pos = sum(1 for a in articles if a.sentiment_label == "Positive")
        neg = sum(1 for a in articles if a.sentiment_label == "Negative")
        neu = sum(1 for a in articles if a.sentiment_label == "Neutral")
        avg = sum(a.sentiment_score for a in articles) / total

        return SentimentSummary(
            total_articles=total,
            positive_count=pos,
            neutral_count=neu,
            negative_count=neg,
            average_score=round(avg, 3),
        )

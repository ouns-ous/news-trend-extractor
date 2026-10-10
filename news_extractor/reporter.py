"""Digest reporting engine with Markdown, JSON, CSV, and formatted console layouts."""

from __future__ import annotations
import csv
from datetime import datetime
import io
import json
from pathlib import Path
from typing import List, Optional

from news_extractor.models import Article, Digest, TrendTopic, SentimentSummary, WatchlistAlert


class DigestReporter:
    """Formats and exports news intelligence digests into multiple output formats."""

    @staticmethod
    def _render_bar(percentage: float, width: int = 15) -> str:
        """Render a mini ASCII progress bar."""
        filled = int(round((percentage / 100.0) * width))
        filled = max(0, min(width, filled))
        return "█" * filled + "░" * (width - filled)

    @classmethod
    def to_markdown(cls, digest: Digest) -> str:
        """Generate an executive Markdown report suitable for publishing or PDF conversion."""
        lines = [
            "# 📰 NewsPulse Intelligence & Trend Digest",
            f"*Generated on: {digest.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            f"*Timeframe: Last {digest.timeframe_hours} hours | Total Ingested Articles: {digest.total_articles}*",
            "",
            "---",
            "",
            "## 1. 📊 Executive Sentiment Overview",
            "",
            f"- **Overall Market Sentiment Index**: `{digest.sentiment.average_score:+.2f}`",
            f"- **Positive Articles**: {digest.sentiment.positive_count} ({digest.sentiment.positive_percentage:.1f}%)",
            f"- **Neutral Articles**: {digest.sentiment.neutral_count} ({digest.sentiment.neutral_percentage:.1f}%)",
            f"- **Negative / Cautionary Articles**: {digest.sentiment.negative_count} ({digest.sentiment.negative_percentage:.1f}%)",
            "",
            "| Polarity | Count | Proportion | Visual Distribution |",
            "| :--- | :---: | :---: | :--- |",
            f"| 🟢 Positive | {digest.sentiment.positive_count} | {digest.sentiment.positive_percentage:.1f}% | `{cls._render_bar(digest.sentiment.positive_percentage)}` |",
            f"| ⚪ Neutral  | {digest.sentiment.neutral_count} | {digest.sentiment.neutral_percentage:.1f}% | `{cls._render_bar(digest.sentiment.neutral_percentage)}` |",
            f"| 🔴 Negative | {digest.sentiment.negative_count} | {digest.sentiment.negative_percentage:.1f}% | `{cls._render_bar(digest.sentiment.negative_percentage)}` |",
            "",
            "---",
            "",
            "## 2. 🔥 Top Trending Topics & Extracted N-Grams",
            "",
            "| Rank | Trending Entity / Topic | Mentions | Trend Score | Velocity | Primary Sources |",
            "| :---: | :--- | :---: | :---: | :---: | :--- |",
        ]

        if not digest.top_trends:
            lines.append("| - | *No significant trends detected in this cycle* | - | - | - | - |")
        else:
            for i, trend in enumerate(digest.top_trends, start=1):
                sources_str = ", ".join(trend.sources[:3])
                lines.append(
                    f"| {i} | **{trend.phrase}** | {trend.frequency} | {trend.score:.1f} | {trend.velocity:+.1f} | {sources_str} |"
                )

        lines.extend([
            "",
            "---",
            "",
            "## 3. 🌐 Source & Category Distribution",
            "",
            "### Sources Breakdown",
        ])
        for src, count in sorted(digest.source_breakdown.items(), key=lambda x: x[1], reverse=True):
            pct = (count / digest.total_articles * 100) if digest.total_articles else 0
            lines.append(f"- **{src}**: {count} stories ({pct:.1f}%)")

        lines.extend([
            "",
            "### Categories Breakdown",
        ])
        for cat, count in sorted(digest.category_breakdown.items(), key=lambda x: x[1], reverse=True):
            pct = (count / digest.total_articles * 100) if digest.total_articles else 0
            lines.append(f"- **{cat}**: {count} stories ({pct:.1f}%)")

        lines.extend([
            "",
            "---",
            "",
            "## 4. 🚨 Watchlist Alert Matches",
            "",
        ])

        if not digest.alerts:
            lines.append("No critical watchlist alerts triggered in this time window.")
        else:
            for alert in digest.alerts:
                lines.extend([
                    f"- **[{alert.watchlist_name}]** Trigger: `{alert.keyword}`",
                    f"  - **Title**: {alert.article.title}",
                    f"  - **Source**: {alert.article.source} | **Category**: {alert.article.category}",
                    f"  - **URL**: [{alert.article.url}]({alert.article.url})" if alert.article.url else "  - *URL: None*",
                    f"  - **Sentiment**: {alert.article.sentiment_label} ({alert.article.sentiment_score:+.2f})",
                    "",
                ])

        return "\n".join(lines)

    @classmethod
    def to_json(cls, digest: Digest, indent: int = 2) -> str:
        """Serialize digest to formatted JSON."""
        return json.dumps(digest.to_dict(), indent=indent)

    @classmethod
    def to_csv(cls, digest: Digest) -> str:
        """Export trending topics from digest as tabular CSV data."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Rank", "Phrase", "Frequency", "Score", "Velocity", "Sources", "SampleTitles"])
        for idx, t in enumerate(digest.top_trends, start=1):
            writer.writerow([
                idx,
                t.phrase,
                t.frequency,
                t.score,
                t.velocity,
                ";".join(t.sources),
                ";".join(t.sample_titles),
            ])
        return output.getvalue()

    @classmethod
    def to_console(cls, digest: Digest) -> str:
        """Render concise terminal ASCII report."""
        lines = [
            "=" * 68,
            f" 📰 NEWSPULSE EXECUTIVE DIGEST - {digest.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f" Ingested: {digest.total_articles} articles | Avg Sentiment: {digest.sentiment.average_score:+.2f}",
            "=" * 68,
            "",
            "POLARITY DISTRIBUTION:",
            f"  Positive: {digest.sentiment.positive_count:>3} ({digest.sentiment.positive_percentage:5.1f}%) [{cls._render_bar(digest.sentiment.positive_percentage)}]",
            f"  Neutral:  {digest.sentiment.neutral_count:>3} ({digest.sentiment.neutral_percentage:5.1f}%) [{cls._render_bar(digest.sentiment.neutral_percentage)}]",
            f"  Negative: {digest.sentiment.negative_count:>3} ({digest.sentiment.negative_percentage:5.1f}%) [{cls._render_bar(digest.sentiment.negative_percentage)}]",
            "",
            "TOP TRENDING TOPICS & ENTITIES:",
        ]

        for i, t in enumerate(digest.top_trends[:10], start=1):
            lines.append(f"  {i:>2}. {t.phrase:<28} | Mentions: {t.frequency:>2} | Score: {t.score:>5.1f} | Accel: {t.velocity:>+4.1f}")

        if digest.alerts:
            lines.extend(["", f"WATCHLIST ALERTS ({len(digest.alerts)} triggered):"])
            for alert in digest.alerts[:5]:
                lines.append(f"  * [{alert.watchlist_name} -> {alert.keyword}] {alert.article.title[:50]}...")

        lines.extend(["", "=" * 68])
        return "\n".join(lines)

    @classmethod
    def export_digest(cls, digest: Digest, output_path: Path | str, fmt: str = "markdown") -> None:
        """Write digest output to file in requested format ('markdown', 'json', 'csv', 'text')."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fmt = fmt.lower()

        if fmt in ("md", "markdown"):
            content = cls.to_markdown(digest)
        elif fmt == "json":
            content = cls.to_json(digest)
        elif fmt == "csv":
            content = cls.to_csv(digest)
        else:
            content = cls.to_console(digest)

        path.write_text(content, encoding="utf-8")

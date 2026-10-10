"""Command-line interface (CLI) for NewsPulse extractor, trend analyzer, and reporter."""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import List, Optional


def _now() -> datetime:
    """Return naive UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from news_extractor.config import AppConfig, SourceConfig
from news_extractor.models import Article, ScrapeRun, Digest
from news_extractor.scraper import MultiSourceScraper
from news_extractor.analyzer import TrendAnalyzer, SentimentAnalyzer
from news_extractor.storage import NewsVault
from news_extractor.alerts import WatchlistMonitor
from news_extractor.reporter import DigestReporter


def build_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="newspulse",
        description="NewsPulse: Autonomous News Headline & Trending Topics Extractor",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.json",
        help="Path to JSON configuration file (default: config.json)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: init
    p_init = subparsers.add_parser("init", help="Generate a default config.json file")
    p_init.add_argument("-o", "--output", default="config.json", help="Destination file path")

    # Command: fetch
    p_fetch = subparsers.add_parser("fetch", help="Scrape headlines from configured sources")
    p_fetch.add_argument("--source", "-s", type=str, help="Specific source name to scrape")
    p_fetch.add_argument("--offline", action="store_true", help="Use local mock fixtures instead of network")

    # Command: trends
    p_trends = subparsers.add_parser("trends", help="Extract and rank trending topics and phrases")
    p_trends.add_argument("--top", "-n", type=int, default=15, help="Number of top trends to display")
    p_trends.add_argument("--hours", type=int, default=72, help="Timeframe window in hours")
    p_trends.add_argument("--min-freq", type=int, default=2, help="Minimum mention threshold")

    # Command: digest
    p_digest = subparsers.add_parser("digest", help="Generate an intelligence digest report")
    p_digest.add_argument(
        "--format", "-f",
        choices=["markdown", "json", "csv", "text"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    p_digest.add_argument("-o", "--output", type=str, help="Output file path (prints to stdout if omitted)")
    p_digest.add_argument("--hours", type=int, default=72, help="Timeframe window in hours")

    # Command: search
    p_search = subparsers.add_parser("search", help="Search ingested articles by keyword or phrase")
    p_search.add_argument("query", type=str, help="Search query string")
    p_search.add_argument("--limit", "-l", type=int, default=20, help="Maximum results to return")

    # Command: alerts
    p_alerts = subparsers.add_parser("alerts", help="Evaluate articles against keyword watchlists")
    p_alerts.add_argument("--hours", type=int, default=72, help="Timeframe window in hours")

    # Command: stats
    subparsers.add_parser("stats", help="Display storage vault metrics and scrape history")

    return parser


def handle_init(args: argparse.Namespace) -> int:
    """Generate default config file."""
    config = AppConfig.default()
    config.save_to_file(args.output)
    print(f"[OK] Generated default configuration at: {args.output}")
    return 0


def handle_fetch(args: argparse.Namespace, config: AppConfig) -> int:
    """Fetch news from feeds or offline fixtures, analyze, and save to vault."""
    scraper = MultiSourceScraper(
        user_agent=config.user_agent,
        timeout_seconds=config.timeout_seconds,
    )
    analyzer = TrendAnalyzer(
        custom_stop_words=config.custom_stop_words,
        min_word_len=config.min_keyword_length,
        min_freq=config.min_trend_frequency,
    )
    sentiment_engine = SentimentAnalyzer()

    sources = config.sources
    if args.source:
        sources = [s for s in sources if s.name.lower() == args.source.lower()]
        if not sources:
            print(f"[ERROR] Configured source '{args.source}' not found.")
            return 1

    print(f"[FETCH] Fetching news ({'Offline Mode' if args.offline else 'Live Mode'})...")
    raw_articles, errors = scraper.scrape_all(sources, offline=args.offline)

    if errors:
        for err in errors:
            print(f"[WARN] {err}")

    print(f"[INFO] Fetched {len(raw_articles)} raw headlines. Enriching with NLP & Sentiment...")
    enriched: List[Article] = []
    for art in raw_articles:
        sentiment_engine.analyze_article(art)
        art.keywords = analyzer.extract_article_keywords(art, top_k=5)
        enriched.append(art)

    with NewsVault(config.db_path) as vault:
        new_cnt, dup_cnt = vault.save_articles(enriched)

        run = ScrapeRun(
            run_id=_now().strftime("%Y%m%d_%H%M%S"),
            timestamp=_now(),
            sources=[s.name for s in sources],
            total_fetched=len(enriched),
            new_added=new_cnt,
            duplicates=dup_cnt,
            errors=errors,
        )
        vault.record_scrape_run(run)

    print(f"[OK] Ingestion complete! New articles saved: {new_cnt} | Deduplicated: {dup_cnt}")
    return 0


def handle_trends(args: argparse.Namespace, config: AppConfig) -> int:
    """Analyze and display trending topics."""
    analyzer = TrendAnalyzer(
        custom_stop_words=config.custom_stop_words,
        min_word_len=config.min_keyword_length,
        min_freq=args.min_freq,
    )

    with NewsVault(config.db_path) as vault:
        articles = vault.get_articles(limit=1000, timeframe_hours=args.hours)

    if not articles:
        print("[INFO] No articles found in vault. Run 'python main.py fetch' first.")
        return 0

    trends = analyzer.compute_trends(articles, top_n=args.top)

    print("\n" + "=" * 70)
    print(f" [TRENDS] TOP {len(trends)} TRENDING TOPICS (Last {args.hours} hours across {len(articles)} articles)")
    print("=" * 70)
    print(f"{'Rank':<5} {'Phrase / Topic':<28} {'Mentions':<10} {'Score':<8} {'Primary Sources'}")
    print("-" * 70)

    for i, t in enumerate(trends, start=1):
        sources = ", ".join(t.sources[:2])
        print(f"{i:<5} {t.phrase:<28} {t.frequency:<10} {t.score:<8.1f} {sources}")

    print("=" * 70 + "\n")
    return 0


def handle_digest(args: argparse.Namespace, config: AppConfig) -> int:
    """Generate and output a multi-format intelligence digest."""
    analyzer = TrendAnalyzer(
        custom_stop_words=config.custom_stop_words,
        min_word_len=config.min_keyword_length,
        min_freq=config.min_trend_frequency,
    )
    sentiment_engine = SentimentAnalyzer()
    monitor = WatchlistMonitor(config.watchlists)

    with NewsVault(config.db_path) as vault:
        articles = vault.get_articles(limit=1000, timeframe_hours=args.hours)

    if not articles:
        print("[INFO] No articles found in vault. Run 'python main.py fetch' first.")
        return 0

    trends = analyzer.compute_trends(articles, top_n=config.top_trends_count)
    sentiment = sentiment_engine.summarize(articles)
    alerts = monitor.evaluate_all(articles)

    src_dist = {}
    cat_dist = {}
    for a in articles:
        src_dist[a.source] = src_dist.get(a.source, 0) + 1
        cat_dist[a.category] = cat_dist.get(a.category, 0) + 1

    digest = Digest(
        generated_at=_now(),
        timeframe_hours=args.hours,
        total_articles=len(articles),
        top_trends=trends,
        sentiment=sentiment,
        source_breakdown=src_dist,
        category_breakdown=cat_dist,
        alerts=alerts,
    )

    if args.output:
        DigestReporter.export_digest(digest, args.output, fmt=args.format)
        print(f"[OK] Digest report exported successfully to: {args.output}")
    else:
        if args.format == "markdown":
            print(DigestReporter.to_markdown(digest))
        elif args.format == "json":
            print(DigestReporter.to_json(digest))
        elif args.format == "csv":
            print(DigestReporter.to_csv(digest))
        else:
            print(DigestReporter.to_console(digest))

    return 0


def handle_search(args: argparse.Namespace, config: AppConfig) -> int:
    """Search vault for articles matching a query."""
    with NewsVault(config.db_path) as vault:
        matches = vault.search(args.query, limit=args.limit)

    print(f"\n[SEARCH] Results for '{args.query}' ({len(matches)} matches found):\n")
    if not matches:
        print("  No articles matched your query.")
        return 0

    for i, a in enumerate(matches, start=1):
        print(f"{i:>2}. [{a.source}] {a.title}")
        if a.summary:
            print(f"    Summary: {a.summary[:100]}...")
        if a.url:
            print(f"    Link: {a.url}")
        print(f"    Sentiment: {a.sentiment_label} ({a.sentiment_score:+.2f}) | Keywords: {', '.join(a.keywords)}")
        print()
    return 0


def handle_alerts(args: argparse.Namespace, config: AppConfig) -> int:
    """Check stored articles against watchlists."""
    monitor = WatchlistMonitor(config.watchlists)

    with NewsVault(config.db_path) as vault:
        articles = vault.get_articles(limit=1000, timeframe_hours=args.hours)

    alerts = monitor.evaluate_all(articles)
    print(f"\n[ALERTS] Active Watchlist Alerts ({len(alerts)} triggers found):\n")

    if not alerts:
        print("  No active alerts triggered.")
        return 0

    for alert in alerts:
        print(f"* [{alert.watchlist_name}] Keyword: '{alert.keyword}'")
        print(f"  Title:  {alert.article.title}")
        print(f"  Source: {alert.article.source} | Polarity: {alert.article.sentiment_label}")
        if alert.article.url:
            print(f"  URL:    {alert.article.url}")
        print()
    return 0


def handle_stats(args: argparse.Namespace, config: AppConfig) -> int:
    """Display vault statistics."""
    with NewsVault(config.db_path) as vault:
        stats = vault.get_stats()
        recent_runs = vault.get_scrape_runs(limit=5)

    print("\n" + "=" * 60)
    print(" [STATS] NEWSPULSE VAULT STATISTICS")
    print("=" * 60)
    print(f" Total Articles:    {stats['total_articles']}")
    print(f" Earliest Ingest:   {stats['first_scraped_at'] or 'N/A'}")
    print(f" Latest Ingest:     {stats['latest_scraped_at'] or 'N/A'}")
    print("\nSentiment Distribution:")
    for label, count in stats["sentiment_distribution"].items():
        print(f"  - {label:<10}: {count}")

    print("\nTop Sources:")
    for src, count in list(stats["sources"].items())[:6]:
        print(f"  - {src:<25}: {count}")

    print("\nTop Categories:")
    for cat, count in list(stats["categories"].items())[:6]:
        print(f"  - {cat:<20}: {count}")

    if recent_runs:
        print("\nRecent Scrape Runs:")
        for r in recent_runs:
            print(f"  - {r.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: Fetched={r.total_fetched}, New={r.new_added}, Dupa={r.duplicates}")

    print("=" * 60 + "\n")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI application entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "init":
        return handle_init(args)

    config = AppConfig.load_from_file(args.config)

    if args.command == "fetch":
        return handle_fetch(args, config)
    elif args.command == "trends":
        return handle_trends(args, config)
    elif args.command == "digest":
        return handle_digest(args, config)
    elif args.command == "search":
        return handle_search(args, config)
    elif args.command == "alerts":
        return handle_alerts(args, config)
    elif args.command == "stats":
        return handle_stats(args, config)

    return 0


if __name__ == "__main__":
    sys.exit(main())

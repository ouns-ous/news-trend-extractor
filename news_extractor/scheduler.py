"""Automated periodic news scraping and watchlist monitoring daemon."""

from __future__ import annotations
from datetime import datetime, timezone
import time
from typing import Callable, List, Optional

from news_extractor.config import AppConfig
from news_extractor.models import Article, ScrapeRun, WatchlistAlert
from news_extractor.scraper import MultiSourceScraper
from news_extractor.analyzer import TrendAnalyzer, SentimentAnalyzer
from news_extractor.storage import NewsVault
from news_extractor.alerts import WatchlistMonitor


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class NewsMonitor:
    """Continuous background scheduler for scraping feeds and monitoring alerts."""

    def __init__(
        self,
        config: AppConfig,
        interval_seconds: int = 60,
        offline: bool = False,
        alert_callback: Optional[Callable[[List[WatchlistAlert]], None]] = None,
    ) -> None:
        self.config = config
        self.interval_seconds = max(1, interval_seconds)
        self.offline = offline
        self.alert_callback = alert_callback
        self.is_running = False

    def run_cycle(self) -> int:
        """Execute one complete ingestion, analysis, and alerting pass."""
        scraper = MultiSourceScraper(
            user_agent=self.config.user_agent,
            timeout_seconds=self.config.timeout_seconds,
        )
        analyzer = TrendAnalyzer(
            custom_stop_words=self.config.custom_stop_words,
            min_word_len=self.config.min_keyword_length,
            min_freq=self.config.min_trend_frequency,
        )
        sentiment_engine = SentimentAnalyzer()
        monitor = WatchlistMonitor(self.config.watchlists)

        raw_articles, errors = scraper.scrape_all(self.config.sources, offline=self.offline)
        enriched: List[Article] = []

        for art in raw_articles:
            sentiment_engine.analyze_article(art)
            art.keywords = analyzer.extract_article_keywords(art, top_k=5)
            enriched.append(art)

        with NewsVault(self.config.db_path) as vault:
            new_cnt, dup_cnt = vault.save_articles(enriched)

            run = ScrapeRun(
                run_id=_utc_now().strftime("%Y%m%d_%H%M%S"),
                timestamp=_utc_now(),
                sources=[s.name for s in self.config.sources if s.enabled],
                total_fetched=len(enriched),
                new_added=new_cnt,
                duplicates=dup_cnt,
                errors=errors,
            )
            vault.record_scrape_run(run)

        # Evaluate alerts on newly added or fetched stories
        alerts = monitor.evaluate_all(enriched)
        if alerts and self.alert_callback:
            self.alert_callback(alerts)

        return new_cnt

    def start(self, max_cycles: Optional[int] = None) -> None:
        """Start the monitoring loop until max_cycles or user cancellation."""
        self.is_running = True
        cycle_count = 0
        print(f"[MONITOR] Starting news daemon (Interval: {self.interval_seconds}s, Offline: {self.offline})...")

        try:
            while self.is_running:
                cycle_count += 1
                t_start = time.time()
                print(f"[MONITOR] Running cycle #{cycle_count} at {_utc_now().strftime('%H:%M:%S')}...")

                try:
                    new_articles = self.run_cycle()
                    print(f"[MONITOR] Cycle #{cycle_count} finished. New articles: {new_articles}")
                except Exception as e:
                    print(f"[MONITOR-ERROR] Cycle #{cycle_count} failed: {e}")

                if max_cycles and cycle_count >= max_cycles:
                    print("[MONITOR] Reached target cycle limit. Stopping.")
                    break

                elapsed = time.time() - t_start
                sleep_time = max(0.1, self.interval_seconds - elapsed)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n[MONITOR] Stopping daemon gracefully on user interrupt.")
        finally:
            self.is_running = False

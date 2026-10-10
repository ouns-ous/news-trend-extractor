"""Unit tests for NewsMonitor scheduler."""

from pathlib import Path
import tempfile
import unittest

from news_extractor.config import AppConfig
from news_extractor.scheduler import NewsMonitor


class TestScheduler(unittest.TestCase):
    """Test background polling daemon and run_cycle execution."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = AppConfig.default()
        self.config.db_path = str(Path(self.temp_dir.name) / "sched_test.db")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_run_cycle_offline(self) -> None:
        alert_log = []
        daemon = NewsMonitor(
            config=self.config,
            interval_seconds=1,
            offline=True,
            alert_callback=lambda alerts: alert_log.extend(alerts),
        )

        # Single cycle
        new_cnt = daemon.run_cycle()
        self.assertGreaterEqual(new_cnt, 5)
        self.assertGreater(len(alert_log), 0)

    def test_daemon_start_with_max_cycles(self) -> None:
        daemon = NewsMonitor(
            config=self.config,
            interval_seconds=1,
            offline=True,
        )
        # Should stop cleanly after 2 cycles
        daemon.start(max_cycles=2)
        self.assertFalse(daemon.is_running)


if __name__ == "__main__":
    unittest.main()

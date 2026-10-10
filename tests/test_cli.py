"""Unit tests for NewsPulse CLI commands."""

import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from news_extractor.cli import main
from news_extractor.config import AppConfig


class TestCLI(unittest.TestCase):
    """Test full CLI command execution workflows."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "test_config.json"
        self.db_path = Path(self.temp_dir.name) / "cli_test_vault.db"

        # Create custom test configuration
        config = AppConfig.default()
        config.db_path = str(self.db_path)
        config.save_to_file(self.config_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_cli_help(self) -> None:
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main([])
            self.assertEqual(code, 0)
            self.assertIn("NewsPulse", mock_out.getvalue())

    def test_cli_init_command(self) -> None:
        out_cfg = Path(self.temp_dir.name) / "new_init.json"
        code = main(["init", "-o", str(out_cfg)])
        self.assertEqual(code, 0)
        self.assertTrue(out_cfg.exists())

    def test_cli_fetch_offline_and_subsequent_commands(self) -> None:
        # 1. Fetch offline
        code_fetch = main(["-c", str(self.config_path), "fetch", "--offline"])
        self.assertEqual(code_fetch, 0)

        # 2. Check trends
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code_trends = main(["-c", str(self.config_path), "trends", "--top", "5"])
            self.assertEqual(code_trends, 0)
            self.assertIn("TOP", mock_out.getvalue())

        # 3. Export markdown digest
        digest_file = Path(self.temp_dir.name) / "digest.md"
        code_digest = main(["-c", str(self.config_path), "digest", "-f", "markdown", "-o", str(digest_file)])
        self.assertEqual(code_digest, 0)
        self.assertTrue(digest_file.exists())
        content = digest_file.read_text(encoding="utf-8")
        self.assertIn("NewsPulse Intelligence", content)

        # 4. Search
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code_search = main(["-c", str(self.config_path), "search", "energy"])
            self.assertEqual(code_search, 0)
            self.assertIn("Results for 'energy'", mock_out.getvalue())

        # 5. Alerts
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code_alerts = main(["-c", str(self.config_path), "alerts"])
            self.assertEqual(code_alerts, 0)
            self.assertIn("Active Watchlist Alerts", mock_out.getvalue())

        # 6. Stats
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code_stats = main(["-c", str(self.config_path), "stats"])
            self.assertEqual(code_stats, 0)
            self.assertIn("NEWSPULSE VAULT STATISTICS", mock_out.getvalue())


if __name__ == "__main__":
    unittest.main()

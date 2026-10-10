#!/usr/bin/env python3
"""Main entrypoint script for NewsPulse news headline and trending topics extractor."""

import sys
from pathlib import Path

# Ensure news_extractor package is importable when executed directly
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from news_extractor.cli import main

if __name__ == "__main__":
    sys.exit(main())

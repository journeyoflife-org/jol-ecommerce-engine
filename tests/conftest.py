"""Pytest conftest — shared fixtures and configuration for JOL Commerce Engine tests."""

import sys
from pathlib import Path

# Add backend/ to sys.path so tests can import jol_commerce without PYTHONPATH
BACKEND_DIR = Path(__file__).parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

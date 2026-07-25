"""Pytest conftest — shared fixtures and configuration for JOL Commerce Engine tests."""

import os
import sys
from pathlib import Path

# Set required secrets for test environment before any imports
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-testing-only-not-for-production")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fake_key_for_testing")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_fake_webhook_secret")

# Add backend/ to sys.path so tests can import jol_commerce without PYTHONPATH
BACKEND_DIR = Path(__file__).parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

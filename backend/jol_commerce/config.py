"""Application configuration — loaded from environment variables.

All secrets are sourced from the environment; never hardcoded.
PCI DSS: no card data configuration exists here.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the JOL Commerce Engine."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Application ──────────────────────────────────────────
    app_env: str = "development"
    app_log_level: str = "INFO"
    app_secret_key: str = ""
    app_allowed_hosts: list[str] = ["localhost", "127.0.0.1"]

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/jol_commerce"

    # ── Stripe (tokenisation only — no raw card data) ───────
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""

    # ── TLS ──────────────────────────────────────────────────
    tls_min_version: str = "1.2"
    tls_cert_path: str = ""
    tls_key_path: str = ""

    # ── Audit / SIEM ────────────────────────────────────────
    audit_log_destination: str = "file"
    audit_log_retention_months: int = 12
    audit_log_searchable_months: int = 3

    # ── CORS ─────────────────────────────────────────────────
    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()

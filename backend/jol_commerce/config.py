"""Application configuration — loaded from environment variables.

All secrets are sourced from the environment; never hardcoded.
PCI DSS: no card data configuration exists here.
"""

from __future__ import annotations

from pydantic import model_validator
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

    @model_validator(mode="after")
    def validate_required_secrets(self) -> Settings:
        """Enforce that critical secrets are set — fail fast on startup."""
        errors: list[str] = []
        if not self.app_secret_key:
            errors.append(
                "APP_SECRET_KEY must be set. "
                "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )
        if not self.stripe_secret_key:
            errors.append(
                "STRIPE_SECRET_KEY must be set. "
                "Obtain from Stripe Dashboard -> Developers -> API keys."
            )
        if not self.stripe_webhook_secret:
            errors.append(
                "STRIPE_WEBHOOK_SECRET must be set. Obtain from Stripe Dashboard -> Webhooks."
            )
        if errors:
            raise ValueError("Missing required secrets:\n  - " + "\n  - ".join(errors))
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()

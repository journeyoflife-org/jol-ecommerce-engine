"""Content Security Policy headers — PCI DSS Req. 6.4.3 / 11.6.1.

PCI DSS v4.0.1 Requirement 6.4.3 requires documented inventory of every script
on payment pages with integrity verification. CSP headers with nonces enforce
that only authorized scripts execute.

Requirement 11.6.1 requires automated detection of unauthorized HTTP
header/cookie changes on payment pages.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field


def generate_csp_nonce() -> str:
    """Generate a cryptographically random nonce for CSP headers.

    Returns:
        Base64-encoded random nonce string.
    """
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class CSPPolicy:
    """Content Security Policy configuration for payment pages.

    Enforces PCI DSS Req. 6.4.3 by restricting script sources and
    requiring nonces for inline script execution.
    """

    nonce: str = field(default_factory=generate_csp_nonce)
    stripe_js_url: str = "https://js.stripe.com"
    stripe_network_url: str = "https://*.stripe.com"

    @property
    def script_src(self) -> str:
        """Script sources including Stripe's hosted JavaScript."""
        return f"'self' 'nonce-{self.nonce}' {self.stripe_js_url} {self.stripe_network_url}"

    @property
    def frame_src(self) -> str:
        """Frame sources — Stripe Elements loads in an iframe."""
        return f"{self.stripe_js_url} {self.stripe_network_url}"

    @property
    def connect_src(self) -> str:
        """Connect sources for API calls."""
        return f"'self' {self.stripe_network_url}"

    def to_header(self) -> dict[str, str]:
        """Generate the Content-Security-Policy header value.

        Returns:
            Dictionary with CSP header name and value.
        """
        policy = (
            f"default-src 'self'; "
            f"script-src {self.script_src}; "
            f"style-src 'self' 'unsafe-inline'; "
            f"frame-src {self.frame_src}; "
            f"connect-src {self.connect_src}; "
            f"img-src 'self' data:; "
            f"font-src 'self'; "
            f"object-src 'none'; "
            f"base-uri 'self'; "
            f"form-action 'self'"
        )
        return {"Content-Security-Policy": policy}

    def security_headers(self) -> dict[str, str]:
        """Generate the full set of security headers for payment pages.

        Returns:
            Dictionary of security-related HTTP headers.
        """
        headers = self.to_header()
        headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "0",  # CSP supersedes XSS filter
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            }
        )
        return headers


def compute_script_hash(script_content: str) -> str:
    """Compute SHA-256 hash for script integrity verification.

    Used for PCI DSS Req. 6.4.3 script inventory.

    Args:
        script_content: Raw script content.

    Returns:
        SHA-256 hash as hex digest.
    """
    return hashlib.sha256(script_content.encode("utf-8")).hexdigest()

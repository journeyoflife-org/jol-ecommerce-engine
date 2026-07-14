"""TLS enforcement — PCI DSS requires TLS 1.2+ (1.3 preferred).

This module validates TLS configuration and enforces minimum protocol versions.
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass

# PCI DSS v4.0.1 mandates TLS 1.2 minimum; TLS 1.3 preferred.
# Weak cipher suites must be disabled.
WEAK_CIPHER_SUITES: list[str] = [
    "RC4",
    "DES",
    "3DES",
    "MD5",
    "EXPORT",
    "NULL",
    "aNULL",
    "eNULL",
    "ADH",
    "AECDH",
]

MINIMUM_TLS_VERSIONS: dict[str, ssl.TLSVersion] = {
    "1.2": ssl.TLSVersion.TLSv1_2,
    "1.3": ssl.TLSVersion.TLSv1_3,
}


@dataclass(frozen=True)
class TLSConfig:
    """TLS configuration validated against PCI DSS requirements."""

    min_version: str = "1.2"
    cert_path: str = ""
    key_path: str = ""

    def create_ssl_context(self) -> ssl.SSLContext:
        """Create an SSL context enforcing PCI DSS TLS requirements.

        Returns:
            Configured SSLContext with weak ciphers disabled.

        Raises:
            ValueError: If TLS version is below 1.2.
        """
        tls_version = MINIMUM_TLS_VERSIONS.get(self.min_version)
        if tls_version is None:
            raise ValueError(
                f"Unsupported TLS version: {self.min_version}. "
                f"PCI DSS requires minimum TLS 1.2. Supported: {list(MINIMUM_TLS_VERSIONS)}",
            )

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = tls_version

        # Disable weak cipher suites
        cipher_string = "!".join(WEAK_CIPHER_SUITES)
        context.set_ciphers(f"HIGH:{cipher_string}")

        if self.cert_path and self.key_path:
            context.load_cert_chain(certfile=self.cert_path, keyfile=self.key_path)

        return context

    def validate(self) -> list[str]:
        """Validate TLS configuration and return any warnings.

        Returns:
            List of warning messages. Empty list means fully compliant.
        """
        warnings: list[str] = []
        if self.min_version == "1.2":
            warnings.append(
                "TLS 1.2 is the minimum acceptable version. "
                "Consider upgrading to TLS 1.3 for enhanced security.",
            )
        if not self.cert_path or not self.key_path:
            warnings.append(
                "TLS certificate/key paths not configured. "
                "TLS termination may be handled at the load balancer.",
            )
        return warnings

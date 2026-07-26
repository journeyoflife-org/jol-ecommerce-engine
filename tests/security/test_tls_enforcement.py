"""TLS enforcement tests — PCI DSS requires TLS 1.2+."""

import ssl

import pytest
from jol_commerce.security.tls_enforcement import WEAK_CIPHER_SUITES, TLSConfig


@pytest.mark.security
class TestTLSEnforcement:
    """Verify TLS configuration meets PCI DSS requirements."""

    def test_tls_12_creates_valid_context(self) -> None:
        config = TLSConfig(min_version="1.2")
        context = config.create_ssl_context()
        assert context.minimum_version == ssl.TLSVersion.TLSv1_2

    def test_tls_13_creates_valid_context(self) -> None:
        config = TLSConfig(min_version="1.3")
        context = config.create_ssl_context()
        assert context.minimum_version == ssl.TLSVersion.TLSv1_3

    def test_unsupported_tls_version_raises_error(self) -> None:
        config = TLSConfig(min_version="1.0")
        with pytest.raises(ValueError, match="Unsupported TLS version"):
            config.create_ssl_context()

    def test_weak_cipher_suites_listed(self) -> None:
        """All known weak ciphers are in the denylist."""
        assert "RC4" in WEAK_CIPHER_SUITES
        assert "DES" in WEAK_CIPHER_SUITES
        assert "NULL" in WEAK_CIPHER_SUITES
        assert "EXPORT" in WEAK_CIPHER_SUITES

    def test_validation_warns_on_tls_12(self) -> None:
        """TLS 1.2 should produce a warning recommending 1.3."""
        config = TLSConfig(min_version="1.2")
        warnings = config.validate()
        assert any("TLS 1.3" in w for w in warnings)

    def test_validation_no_warnings_for_tls_13(self) -> None:
        """TLS 1.3 should not produce version warnings."""
        config = TLSConfig(min_version="1.3", cert_path="/cert", key_path="/key")
        warnings = config.validate()
        assert not any("TLS" in w for w in warnings)

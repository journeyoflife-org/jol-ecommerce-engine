"""Payment method management — Stripe-hosted payment methods only.

Supports Stripe Elements and Stripe Checkout for card collection.
Additional payment methods (SEPA, iDEAL, etc.) are configured
through Stripe's payment method types.

PCI DSS SAQ A: all card data is collected within Stripe's hosted
iframe. No raw card data enters the JOL server.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PaymentMethodType(str, Enum):
    """Supported payment method types via Stripe."""

    CARD = "card"
    SEPA_DEBIT = "sepa_debit"
    IDEAL = "ideal"
    BANCONTACT = "bancontact"
    GIROPAY = "giropay"
    SOFORT = "sofort"
    EPS = "eps"
    P24 = "p24"


@dataclass
class PaymentMethodConfig:
    """Configuration for available payment methods.

    Determines which payment methods are presented on the checkout page.
    """

    enabled_types: list[PaymentMethodType]
    default_type: PaymentMethodType = PaymentMethodType.CARD
    card_brand_preferences: list[str] | None = None  # e.g., ["visa", "mastercard"]

    def to_stripe_payment_method_types(self) -> list[dict[str, str]]:
        """Convert to Stripe API payment_method_types format.

        Returns:
            List of payment method type dicts for Stripe API.
        """
        return [{"type": pm.value} for pm in self.enabled_types]


class PaymentMethodService:
    """Service for managing payment method configuration.

    Does not store or process any card data. Only manages
    which payment method types are available for checkout.
    """

    # Default EU payment method configuration
    DEFAULT_EU_CONFIG = PaymentMethodConfig(
        enabled_types=[
            PaymentMethodType.CARD,
            PaymentMethodType.SEPA_DEBIT,
            PaymentMethodType.IDEAL,
            PaymentMethodType.BANCONTACT,
            PaymentMethodType.EPS,
            PaymentMethodType.SOFORT,
            PaymentMethodType.P24,
        ],
        default_type=PaymentMethodType.CARD,
    )

    # Baltic-specific configuration (card + SEPA predominant)
    BALTIC_CONFIG = PaymentMethodConfig(
        enabled_types=[
            PaymentMethodType.CARD,
            PaymentMethodType.SEPA_DEBIT,
        ],
        default_type=PaymentMethodType.CARD,
    )

    @classmethod
    def get_config_for_country(cls, country_code: str) -> PaymentMethodConfig:
        """Get the appropriate payment method config for a country.

        Args:
            country_code: ISO 3166-1 alpha-2 country code.

        Returns:
            Payment method configuration for the country.
        """
        baltic_countries = {"LT", "LV", "EE"}
        if country_code.upper() in baltic_countries:
            return cls.BALTIC_CONFIG
        return cls.DEFAULT_EU_CONFIG

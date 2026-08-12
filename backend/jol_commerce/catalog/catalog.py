"""Catalog entities — Service and Product per tenant vertical.

Blueprint v2.0 §3.3 domain model:

    Catalog
    ├── Service (funeral_package, grave_cleaning, memorial_mass)
    └── Product (casket, flowers, cross, candle — limited SKUs)

Funeral home tenants carry a deliberately limited product catalog
(Blueprint §1); the taxonomy below encodes that constraint per vertical.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from jol_commerce.tenancy.tenant import TenantVertical


class CatalogItemKind(str, Enum):
    """Whether a catalog entry is an act of work or a physical good."""

    SERVICE = "service"
    PRODUCT = "product"


class ServiceType(str, Enum):
    """Sellable service types across the three verticals (Blueprint §3.3)."""

    # Faith communities
    MEMORIAL_MASS = "memorial_mass"
    BLESSING = "blessing"
    # Funeral homes
    FUNERAL_PACKAGE = "funeral_package"
    BEREAVEMENT_COUNSELING = "bereavement_counseling"
    # Cemetery care
    GRAVE_CLEANING = "grave_cleaning"
    MONUMENT_RESTORATION = "monument_restoration"
    FLOWER_DELIVERY = "flower_delivery"


# Vertical → permitted service types (catalog governance).
VERTICAL_SERVICE_TYPES: dict[TenantVertical, set[ServiceType]] = {
    TenantVertical.FAITH_COMMUNITY: {
        ServiceType.MEMORIAL_MASS,
        ServiceType.BLESSING,
    },
    TenantVertical.FUNERAL_HOME: {
        ServiceType.FUNERAL_PACKAGE,
        ServiceType.BEREAVEMENT_COUNSELING,
        ServiceType.FLOWER_DELIVERY,
    },
    TenantVertical.CEMETERY_CARE: {
        ServiceType.GRAVE_CLEANING,
        ServiceType.MONUMENT_RESTORATION,
        ServiceType.FLOWER_DELIVERY,
    },
}

# Limited physical SKUs per vertical (Blueprint §1: funeral homes carry
# caskets, flowers, clothing).
VERTICAL_PRODUCT_KINDS: dict[TenantVertical, set[str]] = {
    TenantVertical.FAITH_COMMUNITY: {"cross", "candle", "flowers"},
    TenantVertical.FUNERAL_HOME: {"casket", "flowers", "clothing"},
    TenantVertical.CEMETERY_CARE: {"flowers", "monument_plaque"},
}


@dataclass(frozen=True)
class Service:
    """A sellable service within a tenant catalog."""

    service_id: str
    service_type: ServiceType
    name: str
    unit_price_cents: int
    currency: str = "EUR"

    @property
    def kind(self) -> CatalogItemKind:
        return CatalogItemKind.SERVICE


@dataclass(frozen=True)
class Product:
    """A physical SKU within a tenant catalog (limited per vertical)."""

    product_id: str
    product_kind: str  # casket | flowers | cross | candle | clothing | ...
    name: str
    unit_price_cents: int
    currency: str = "EUR"

    @property
    def kind(self) -> CatalogItemKind:
        return CatalogItemKind.PRODUCT


class CatalogRepository:
    """Tenant-scoped catalog store (in-memory; DB-backed in production).

    Enforces vertical catalog governance: a funeral home cannot sell a
    memorial mass, and a parish cannot sell caskets.
    """

    def __init__(self, vertical: TenantVertical) -> None:
        self._vertical = vertical
        self._services: dict[str, Service] = {}
        self._products: dict[str, Product] = {}

    @property
    def vertical(self) -> TenantVertical:
        """The vertical whose catalog governance this repository enforces."""
        return self._vertical

    def add_service(self, service: Service) -> Service:
        """Register a service; rejects types outside the tenant vertical."""
        allowed = VERTICAL_SERVICE_TYPES[self._vertical]
        if service.service_type not in allowed:
            raise ValueError(
                f"Service type {service.service_type.value} is not permitted "
                f"for vertical {self._vertical.value}",
            )
        self._services[service.service_id] = service
        return service

    def add_product(self, product: Product) -> Product:
        """Register a product SKU; rejects kinds outside the tenant vertical."""
        allowed = VERTICAL_PRODUCT_KINDS[self._vertical]
        if product.product_kind not in allowed:
            raise ValueError(
                f"Product kind '{product.product_kind}' is not permitted "
                f"for vertical {self._vertical.value}",
            )
        self._products[product.product_id] = product
        return product

    def get_service(self, service_id: str) -> Service | None:
        return self._services.get(service_id)

    def get_product(self, product_id: str) -> Product | None:
        return self._products.get(product_id)

    @property
    def services(self) -> list[Service]:
        return list(self._services.values())

    @property
    def products(self) -> list[Product]:
        return list(self._products.values())


# Placeholder onboarding prices (cents) — tenant admins replace them
# during configuration; seeding must never block tenant provisioning.
DEFAULT_SERVICE_PRICE_CENTS = 10000
DEFAULT_PRODUCT_PRICE_CENTS = 5000


def seed_default_catalog(
    repository: CatalogRepository,
    tenant_id: str,
    currency: str = "EUR",
) -> int:
    """Seed the vertical-governed starter catalog for a new tenant (§3.3).

    One service per permitted service type and one product per permitted
    SKU kind; deterministic IDs derived from the tenant ID so re-seeding
    is idempotent (existing items are overwritten, never duplicated).

    Returns:
        Number of catalog items seeded.
    """
    short = tenant_id.replace("-", "")[:8]
    seeded = 0
    for service_type in sorted(
        VERTICAL_SERVICE_TYPES[repository.vertical],
        key=lambda s: s.value,
    ):
        repository.add_service(
            Service(
                service_id=f"svc-{short}-{service_type.value}",
                service_type=service_type,
                name=service_type.value.replace("_", " ").title(),
                unit_price_cents=DEFAULT_SERVICE_PRICE_CENTS,
                currency=currency,
            ),
        )
        seeded += 1
    for kind in sorted(VERTICAL_PRODUCT_KINDS[repository.vertical]):
        repository.add_product(
            Product(
                product_id=f"prd-{short}-{kind}",
                product_kind=kind,
                name=kind.replace("_", " ").title(),
                unit_price_cents=DEFAULT_PRODUCT_PRICE_CENTS,
                currency=currency,
            ),
        )
        seeded += 1
    return seeded

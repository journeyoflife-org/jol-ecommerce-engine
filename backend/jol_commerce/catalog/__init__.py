"""Per-tenant catalog domain (Blueprint v2.0 §3.3).

Catalog splits into:
- Service: sellable acts of work (funeral_package, grave_cleaning,
  memorial_mass).
- Product: limited physical SKUs (casket, flowers, cross, candle).

Items are typed so order lifecycle, dispatch sync, and VAT treatment can
reason about services vs goods without string sniffing.
"""

from jol_commerce.catalog.catalog import (
    CatalogItemKind,
    CatalogRepository,
    Product,
    Service,
    ServiceType,
)

__all__ = [
    "CatalogItemKind",
    "CatalogRepository",
    "Product",
    "Service",
    "ServiceType",
]

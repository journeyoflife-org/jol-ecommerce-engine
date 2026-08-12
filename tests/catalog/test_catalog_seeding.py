"""Catalog seeding tests — tenant onboarding without DBA intervention (gap 4.1)."""

from jol_commerce.catalog.catalog import (
    DEFAULT_PRODUCT_PRICE_CENTS,
    DEFAULT_SERVICE_PRICE_CENTS,
    VERTICAL_PRODUCT_KINDS,
    VERTICAL_SERVICE_TYPES,
    CatalogRepository,
    seed_default_catalog,
)
from jol_commerce.tenancy.tenant import TenantVertical

TENANT_ID = "3f2a8c1e-9b4d-4e5a-8f6c-1d2e3f4a5b6c"


class TestCatalogSeeding:
    def test_seeds_exactly_the_vertical_governed_items(self) -> None:
        vertical = TenantVertical.FAITH_COMMUNITY
        repo = CatalogRepository(vertical)
        seeded = seed_default_catalog(repo, TENANT_ID)

        assert seeded == len(VERTICAL_SERVICE_TYPES[vertical]) + len(
            VERTICAL_PRODUCT_KINDS[vertical],
        )
        assert {s.service_type for s in repo.services} == VERTICAL_SERVICE_TYPES[vertical]
        assert {p.product_kind for p in repo.products} == VERTICAL_PRODUCT_KINDS[vertical]

    def test_seeding_is_idempotent_on_rerun(self) -> None:
        repo = CatalogRepository(TenantVertical.FUNERAL_HOME)
        first = seed_default_catalog(repo, TENANT_ID)
        second = seed_default_catalog(repo, TENANT_ID)
        assert second == first
        assert len(repo.services) + len(repo.products) == first  # no duplicates

    def test_ids_are_deterministic_per_tenant(self) -> None:
        repo = CatalogRepository(TenantVertical.CEMETERY_CARE)
        seed_default_catalog(repo, TENANT_ID)
        short = TENANT_ID.replace("-", "")[:8]
        assert all(s.service_id.startswith(f"svc-{short}-") for s in repo.services)
        assert all(p.product_id.startswith(f"prd-{short}-") for p in repo.products)

    def test_seed_currency_applies_to_all_items(self) -> None:
        repo = CatalogRepository(TenantVertical.FAITH_COMMUNITY)
        seed_default_catalog(repo, TENANT_ID, currency="USD")
        assert all(s.currency == "USD" for s in repo.services)
        assert all(p.currency == "USD" for p in repo.products)

    def test_placeholder_prices_are_set(self) -> None:
        repo = CatalogRepository(TenantVertical.FUNERAL_HOME)
        seed_default_catalog(repo, TENANT_ID)
        assert all(s.unit_price_cents == DEFAULT_SERVICE_PRICE_CENTS for s in repo.services)
        assert all(p.unit_price_cents == DEFAULT_PRODUCT_PRICE_CENTS for p in repo.products)

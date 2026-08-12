"""Catalog API routes — vertical-governed catalog metadata (Blueprint §3.3).

Read-only governance view: which service types and product kinds the
current tenant's vertical permits. Catalog content itself lives in the
tenant schema; this endpoint drives PWA catalog rendering constraints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from jol_commerce.api.schemas import CatalogCapabilitiesResponse
from jol_commerce.catalog.catalog import VERTICAL_PRODUCT_KINDS, VERTICAL_SERVICE_TYPES
from jol_commerce.tenancy.tenant import TenantNotFoundError, current_tenant

router = APIRouter()


@router.get("/capabilities", response_model=CatalogCapabilitiesResponse)
async def get_catalog_capabilities() -> CatalogCapabilitiesResponse:
    """Return the catalog capabilities allowed for the current tenant."""
    try:
        tenant = current_tenant()
    except TenantNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    vertical = tenant.tenant.vertical
    return CatalogCapabilitiesResponse(
        vertical=vertical.value,
        service_types=sorted(st.value for st in VERTICAL_SERVICE_TYPES[vertical]),
        product_kinds=sorted(VERTICAL_PRODUCT_KINDS[vertical]),
    )

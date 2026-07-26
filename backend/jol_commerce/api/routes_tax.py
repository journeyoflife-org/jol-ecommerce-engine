"""Tax API routes — VAT calculation endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from jol_commerce.api.schemas import VatCalculationRequest, VatCalculationResponse
from jol_commerce.tax.vat_calculator import VatCalculator

router = APIRouter()


@router.post("/calculate", response_model=VatCalculationResponse)
async def calculate_vat(request: VatCalculationRequest) -> VatCalculationResponse:
    """Calculate VAT for a given amount and country.

    Uses Decimal precision. Historical rates are applied based on
    transaction date (e.g., EE=22% before 2025-07-01, 24% after).
    """
    transaction_date = request.transaction_date or date.today()
    result = VatCalculator.calculate_from_net(
        net_amount=request.net_amount,
        country_code=request.country_code,
        transaction_date=transaction_date,
    )
    return VatCalculationResponse(
        net_amount=str(result.net_amount),
        vat_amount=str(result.vat_amount),
        gross_amount=str(result.gross_amount),
        vat_rate=str(result.vat_rate),
        country_code=result.country_code,
        transaction_date=result.transaction_date.isoformat(),
    )

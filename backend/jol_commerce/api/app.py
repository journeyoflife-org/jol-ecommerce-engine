"""FastAPI application — JOL Commerce Engine API.

Security headers are applied to all responses via middleware.
CSP nonces are generated per-request for payment pages (PCI Req. 6.4.3).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from jol_commerce.api.routes_order import router as order_router
from jol_commerce.api.routes_payment import router as payment_router
from jol_commerce.api.routes_tax import router as tax_router
from jol_commerce.config import get_settings
from jol_commerce.security.csp_headers import CSPPolicy

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply security headers (including CSP nonce) to every response.

    PCI DSS Req. 6.4.3: nonce-based script integrity on payment pages.
    PCI DSS Req. 11.6.1: automated header monitoring.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        # Generate a fresh CSP nonce per request
        policy = CSPPolicy()
        for header_name, header_value in policy.security_headers().items():
            response.headers[header_name] = header_value
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events."""
    # Startup
    yield
    # Shutdown


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title="JOL Commerce Engine",
        version="0.1.0",
        description="PCI DSS SAQ A compliant e-commerce backend",
        lifespan=lifespan,
    )

    # Security headers (CSP, HSTS, X-Content-Type-Options, etc.)
    application.add_middleware(SecurityHeadersMiddleware)

    # CORS configuration
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Stripe-Signature", "Idempotency-Key"],
    )

    # Register routers
    application.include_router(payment_router, prefix="/api/v1/payments", tags=["payments"])
    application.include_router(order_router, prefix="/api/v1/orders", tags=["orders"])
    application.include_router(tax_router, prefix="/api/v1/tax", tags=["tax"])

    @application.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "service": "jol-commerce-engine"}

    return application


app = create_app()

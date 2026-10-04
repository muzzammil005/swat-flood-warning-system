"""FastAPI main entrypoint with CORS, rate limiting, and demo endpoints.

This is a temporary MVP implementation for the demo deadline.
After demo, this will be refactored into proper layered architecture.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from domain.exceptions import DomainError, NotFoundError

from infrastructure.config import get_settings

from .rate_limiter import limiter
from .routers import admin, alerts, auth, model_analytics, reports, zones


class HealthStatus(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    print("Starting Swat Flood Early-Warning System API...")

    # Prompt 5 — SHAP TreeExplainer for explainable risk output.
    # Pure opt-in: if shap isn't installed or explainer construction fails,
    # we log a warning and continue — predictions still work, just without
    # top-contributing-features explanations.
    try:
        from infrastructure.ml.artifacts import build_shap_explainer
        build_shap_explainer()
        print("  -> SHAP explainer built successfully (explainable risk output: ON)")
    except ImportError:
        print("  -> shap not installed - explainable risk output skipped (Prompt 5 opt-in)")
    except Exception as exc:  # noqa: BLE001 — startup must not kill the process
        print(f"  -> SHAP explainer build failed: {exc!r} - continuing without explanations")

    yield
    # Shutdown
    print("Shutting down...")


# Create main app with lifespan
app = FastAPI(
    title="Swat Flood Early-Warning System API",
    description="MVP demo backend - temporary implementation for university evaluation",
    version="0.1.0",
    lifespan=lifespan,
)

# Install global rate limiter. Slowapi requires the app.state.limiter
# attribute and a 429 handler registered before any rate-limited routes run.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Map domain NotFoundError to HTTP 404."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )

@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Map all other DomainErrors to HTTP 400."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )

# Add CORS middleware (env-driven, spec-compliant with wildcard handling)
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allow_origins,
    allow_credentials=_settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(zones.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(model_analytics.router, prefix="/api/model")



@app.get("/health", response_model=HealthStatus, tags=["health"])
@app.get("/api/health", response_model=HealthStatus, tags=["health"])
def health() -> HealthStatus:
    """Healthcheck endpoint for the backend service."""
    return HealthStatus(
        status="ok",
        service="swat-flood-backend",
        version="0.1.0",
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": "Swat Flood Early-Warning System",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
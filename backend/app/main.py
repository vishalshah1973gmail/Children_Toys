"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.routers import admin, auth, cart, categories, checkout, orders, products

app = FastAPI(
    title=f"{settings.app_name} API",
    description="Backend for the ToyBox children's toy store.",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# Product images uploaded by admins are served straight off local disk.
upload_path = Path(settings.upload_dir)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount(
    f"/{settings.upload_dir.strip('/')}",
    StaticFiles(directory=str(upload_path)),
    name="uploads",
)

for router in (
    auth.router,
    categories.router,
    products.router,
    cart.router,
    orders.router,
    checkout.router,
    admin.router,
):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "stripe_enabled": settings.stripe_enabled,
    }


@app.get("/", tags=["meta"])
def root() -> dict:
    """Friendly root document."""
    return {
        "name": f"{settings.app_name} API",
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/health",
    }

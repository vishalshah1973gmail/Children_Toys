"""Pytest fixtures: an isolated SQLite database and a TestClient per test."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-used-in-production")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("ALLOW_DEV_PAYMENT", "true")

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.product import Product, ProductImage  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


@pytest.fixture
def db_path() -> Iterator[Path]:
    """A throwaway SQLite file per test."""
    handle, name = tempfile.mkstemp(suffix=".db")
    os.close(handle)
    path = Path(name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def session_factory(db_path: Path):
    """Session factory bound to the throwaway database."""
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    yield factory
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db(session_factory) -> Iterator[Session]:
    """A session for arranging test data."""
    with session_factory() as session:
        yield session


@pytest.fixture
def client(session_factory) -> Iterator[TestClient]:
    """TestClient wired to the throwaway database."""

    def _override() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def category(db: Session) -> Category:
    """One category to hang products off."""
    record = Category(name="Test Blocks", slug="test-blocks", description="Fixture category")
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@pytest.fixture
def product_factory(db: Session, category: Category):
    """Build products with an explicit stock level."""

    def _make(slug: str = "test-toy", price_cents: int = 1999, stock: int = 10) -> Product:
        product = Product(
            name=slug.replace("-", " ").title(),
            slug=slug,
            description="A fixture toy.",
            price_cents=price_cents,
            stock_quantity=stock,
            category_id=category.id,
            min_age_months=36,
            max_age_months=96,
            brand="Fixture Co",
            safety_notes="Small parts.",
        )
        product.images.append(
            ProductImage(url=f"/static/uploads/{slug}.svg", is_primary=True, sort_order=0)
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    return _make


@pytest.fixture
def admin_user(db: Session) -> User:
    """A seeded administrator."""
    user = User(
        username="rootadmin",
        email="rootadmin@example.com",
        full_name="Root Admin",
        hashed_password=hash_password("Admin123!"),
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def customer_user(db: Session) -> User:
    """A seeded customer."""
    user = User(
        username="shopper",
        email="shopper@example.com",
        full_name="Sam Shopper",
        hashed_password=hash_password("Customer123!"),
        role=UserRole.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(client: TestClient, username: str, password: str) -> dict:
    """Log in and return an Authorization header."""
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

"""Tests for the Reset Data cleanup script."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.models.cart import CartItem
from app.models.category import Category
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment
from app.models.product import Product
from app.models.token import RevokedToken
from app.models.user import ApprovalStatus, User, UserRole
from scripts import reset_data as rd

COUNT_KEYS = ["users", "orders", "order_items", "payments", "cart_items", "revoked_tokens"]


@pytest.fixture(autouse=True)
def _development_environment(monkeypatch):
    monkeypatch.setattr(rd.settings, "environment", "development")


def _user(db, username, approval=ApprovalStatus.APPROVED):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=hash_password("Customer123!"),
        role=UserRole.CUSTOMER,
        approval_status=approval,
    )
    db.add(user)
    db.commit()
    return user


def _order(db, number, user, status, product, quantity):
    order = Order(
        order_number=number,
        user_id=user.id if user else None,
        status=status,
        contact_email="x@example.com",
        shipping_name="X",
        shipping_line1="1 Road",
        shipping_city="Town",
        shipping_state="TX",
        shipping_postal_code="12345",
    )
    order.items.append(
        OrderItem(
            product_id=product.id,
            product_name=product.name,
            product_slug=product.slug,
            unit_price_cents=100,
            quantity=quantity,
            line_total_cents=100 * quantity,
        )
    )
    order.payments.append(Payment(amount_cents=100 * quantity))
    db.add(order)
    db.commit()
    return order


def _revoked(db, jti, user):
    db.add(
        RevokedToken(
            jti=jti, user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
    )
    db.commit()


def _count(db, model):
    return db.scalar(select(func.count()).select_from(model))


@pytest.fixture
def populated(db, admin_user, product_factory):
    """Admin plus customers, orders in every status, a guest order, carts and tokens."""
    paid_product = product_factory("paid-toy", stock=10)
    delivered_product = product_factory("delivered-toy", stock=20)
    pending_product = product_factory("pending-toy", stock=30)
    cancelled_product = product_factory("cancelled-toy", stock=40)

    shopper = _user(db, "shopper")
    pending_user = _user(db, "newbie", ApprovalStatus.PENDING)
    rejected_user = _user(db, "denied", ApprovalStatus.REJECTED)

    _order(db, "T-1", shopper, OrderStatus.PAID, paid_product, 2)
    _order(db, "T-2", shopper, OrderStatus.DELIVERED, delivered_product, 3)
    _order(db, "T-3", pending_user, OrderStatus.PENDING, pending_product, 4)
    _order(db, "T-4", rejected_user, OrderStatus.CANCELLED, cancelled_product, 5)
    _order(db, "T-GUEST", None, OrderStatus.PAID, paid_product, 1)
    _order(db, "T-ADMIN", admin_user, OrderStatus.PAID, paid_product, 1)

    db.add(CartItem(user_id=shopper.id, product_id=paid_product.id, quantity=1))
    db.add(CartItem(user_id=admin_user.id, product_id=paid_product.id, quantity=1))
    db.commit()
    _revoked(db, "jti-shopper", shopper)
    _revoked(db, "jti-admin", admin_user)
    return {
        "paid": paid_product.id,
        "delivered": delivered_product.id,
        "pending": pending_product.id,
        "cancelled": cancelled_product.id,
    }


def test_reset_removes_customer_data_and_keeps_admin_and_catalogue(db, admin_user, populated):
    products_before = db.scalar(select(func.count()).select_from(Product))
    categories_before = db.scalar(select(func.count()).select_from(Category))

    result = rd.reset_data(db)

    assert result["users"] == 3
    assert result["orders"] == 6
    assert result["order_items"] == 6
    assert result["payments"] == 6
    assert result["cart_items"] == 2
    assert result["revoked_tokens"] == 1

    users = db.scalars(select(User)).all()
    assert [u.username for u in users] == [admin_user.username]
    assert _count(db, Order) == 0
    assert _count(db, OrderItem) == 0
    assert _count(db, Payment) == 0
    assert _count(db, CartItem) == 0
    assert db.scalars(select(RevokedToken.jti)).all() == ["jti-admin"]
    assert db.scalar(select(func.count()).select_from(Product)) == products_before
    assert db.scalar(select(func.count()).select_from(Category)) == categories_before


def test_stock_restored_only_for_orders_that_consumed_it(db, populated):
    result = rd.reset_data(db)

    stock = {p.id: p.stock_quantity for p in db.scalars(select(Product))}
    # paid: 2 (shopper) + 1 (guest) + 1 (admin) = 4 back
    assert stock[populated["paid"]] == 14
    assert stock[populated["delivered"]] == 23
    assert stock[populated["pending"]] == 30
    assert stock[populated["cancelled"]] == 40
    assert result["stock_restored"] == 7


def test_shipped_order_restores_stock(db, admin_user, product_factory):
    product = product_factory("ship-toy", stock=5)
    shopper = _user(db, "shopper")
    _order(db, "T-S", shopper, OrderStatus.SHIPPED, product, 2)

    rd.reset_data(db)

    db.refresh(product)
    assert product.stock_quantity == 7


def test_preview_matches_reset_and_changes_nothing(db, populated):
    before = {key: _count(db, model) for key, model in [
        ("users", User), ("orders", Order), ("order_items", OrderItem),
        ("payments", Payment), ("cart_items", CartItem), ("revoked_tokens", RevokedToken),
    ]}

    preview = rd.preview(db)

    after = {key: _count(db, model) for key, model in [
        ("users", User), ("orders", Order), ("order_items", OrderItem),
        ("payments", Payment), ("cart_items", CartItem), ("revoked_tokens", RevokedToken),
    ]}
    assert before == after
    assert db.scalars(select(Product.stock_quantity).order_by(Product.id)).all() == [10, 20, 30, 40]

    assert rd.reset_data(db) == preview


def test_second_run_is_a_noop(db, populated):
    rd.reset_data(db)

    second = rd.reset_data(db)

    assert all(second[key] == 0 for key in COUNT_KEYS)
    assert second["stock_restored"] == 0


def test_refused_without_admin(db, customer_user):
    assert rd.has_admin(db) is False
    with pytest.raises(rd.NoAdminError):
        rd.reset_data(db)
    assert db.get(User, customer_user.id) is not None


def test_has_admin_true(db, admin_user):
    assert rd.has_admin(db) is True


def test_sqlite_path_relative_and_absolute():
    assert rd.sqlite_path("sqlite:///./app.db") == Path("./app.db")
    assert rd.sqlite_path("sqlite:///C:/data/app.db") == Path("C:/data/app.db")


def test_sqlite_path_rejects_other_databases():
    with pytest.raises(rd.ResetRefused):
        rd.sqlite_path("postgresql://u:p@host/db")
    with pytest.raises(rd.ResetRefused):
        rd.sqlite_path("sqlite://")


def test_environment_guard():
    rd.check_environment("sqlite:///./app.db", "development")
    with pytest.raises(rd.ResetRefused):
        rd.check_environment("sqlite:///./app.db", "production")
    with pytest.raises(rd.ResetRefused):
        rd.check_environment("postgresql://u:p@host/db", "development")


def test_backup_path_uses_home_and_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    path = rd.backup_path(datetime(2026, 10, 8, 9, 5, 7))

    assert path == tmp_path / "ToyBox-backups" / "app-20261008-090507.db"


def test_make_backup_copies_database(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    source = tmp_path / "src.db"
    source.write_bytes(b"data")

    target = rd.make_backup(source, datetime(2026, 10, 8, 9, 5, 7))

    assert target.read_bytes() == b"data"
    assert target.parent == tmp_path / "ToyBox-backups"


def test_main_dry_run_prints_preview_and_makes_no_backup(
    tmp_path, monkeypatch, session_factory, populated, capsys
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(rd, "SessionLocal", session_factory)

    code = rd.main([])

    out = capsys.readouterr().out
    assert code == 0
    assert "Dry run: nothing was changed. Re-run with --yes to delete." in out
    assert not (tmp_path / "ToyBox-backups").exists()


def test_main_exits_2_without_admin(tmp_path, monkeypatch, session_factory, customer_user, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(rd, "SessionLocal", session_factory)

    assert rd.main(["--yes"]) == 2
    assert not (tmp_path / "ToyBox-backups").exists()


def test_main_exits_2_outside_development(tmp_path, monkeypatch, session_factory, admin_user):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(rd, "SessionLocal", session_factory)
    monkeypatch.setattr(rd.settings, "environment", "production")

    assert rd.main(["--yes"]) == 2


def test_main_yes_backs_up_then_resets(
    tmp_path, monkeypatch, session_factory, db_path, populated, capsys
):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(rd, "SessionLocal", session_factory)
    monkeypatch.setattr(rd.settings, "database_url", f"sqlite:///{db_path.as_posix()}")

    code = rd.main(["--yes"])

    out = capsys.readouterr().out
    assert code == 0
    backups = list((tmp_path / "ToyBox-backups").glob("app-*.db"))
    assert len(backups) == 1
    assert str(backups[0]) in out
    with session_factory() as check:
        assert _count(check, Order) == 0

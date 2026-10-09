"""Reset the development database to a clean slate, keeping the admin and catalogue.

Run from backend/:
    python -m scripts.reset_data          # dry run: show what would be deleted
    python -m scripts.reset_data --yes    # back up the database, then delete

Deletes every non-admin user, all orders, order items, payments and cart items,
and the revoked tokens of the deleted users. Stock from deleted paid, shipped or
delivered orders is added back to the products. The admin account(s), products,
product images and categories are kept.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.cart import CartItem
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment
from app.models.product import Product
from app.models.token import RevokedToken
from app.models.user import User, UserRole

# Same statuses order_service treats as "stock already decremented".
STOCK_CONSUMING = (OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED)
TABLES = ("users", "orders", "order_items", "payments", "cart_items", "revoked_tokens")


class ResetRefused(Exception):
    """The reset must not run against this database or environment."""


class NoAdminError(ResetRefused):
    """No admin user exists, so a reset would lock everyone out."""


def has_admin(db: Session) -> bool:
    return db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)) > 0


def sqlite_path(url: str) -> Path:
    """Database file for a SQLite URL; relative paths resolve against the CWD."""
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite" or not parsed.database or parsed.database == ":memory:":
        raise ResetRefused("Reset Data only works on a file-based SQLite database.")
    return Path(parsed.database)


def check_environment(url: str, environment: str) -> None:
    sqlite_path(url)
    if environment != "development":
        raise ResetRefused(f"Reset Data only runs when ENVIRONMENT is 'development' (got '{environment}').")


def backup_path(now: datetime) -> Path:
    return Path.home() / "ToyBox-backups" / f"app-{now:%Y%m%d-%H%M%S}.db"


def make_backup(source: Path, now: datetime) -> Path:
    target = backup_path(now)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def table_counts(db: Session) -> dict[str, int]:
    models = (User, Order, OrderItem, Payment, CartItem, RevokedToken)
    return {name: _count(db, model) for name, model in zip(TABLES, models)}


def _customer_ids(db: Session) -> list[int]:
    return list(db.scalars(select(User.id).where(User.role != UserRole.ADMIN)))


def _stock_to_restore(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(OrderItem.product_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.in_(STOCK_CONSUMING), OrderItem.product_id.is_not(None))
        .group_by(OrderItem.product_id)
    )
    return {product_id: int(total) for product_id, total in rows}


def preview(db: Session) -> dict[str, int]:
    """Counts reset_data would delete and restore, without changing anything."""
    customer_ids = _customer_ids(db)
    revoked = 0
    if customer_ids:
        revoked = db.scalar(
            select(func.count()).select_from(RevokedToken).where(RevokedToken.user_id.in_(customer_ids))
        )
    return {
        "users": len(customer_ids),
        "orders": _count(db, Order),
        "order_items": _count(db, OrderItem),
        "payments": _count(db, Payment),
        "cart_items": _count(db, CartItem),
        "revoked_tokens": revoked,
        "stock_restored": sum(_stock_to_restore(db).values()),
    }


def reset_data(db: Session) -> dict[str, int]:
    """Delete customer data and restore stock in one transaction; returns the counts."""
    if not has_admin(db):
        raise NoAdminError("No admin user exists; refusing to reset.")
    try:
        counts = preview(db)
        customer_ids = _customer_ids(db)
        for product_id, quantity in _stock_to_restore(db).items():
            product = db.get(Product, product_id)
            if product is not None:
                product.stock_quantity += quantity
        # Children first: SQLite enforces order_items/orders -> RESTRICT on users.
        db.execute(delete(Payment))
        db.execute(delete(OrderItem))
        db.execute(delete(Order))
        db.execute(delete(CartItem))
        if customer_ids:
            db.execute(delete(RevokedToken).where(RevokedToken.user_id.in_(customer_ids)))
            db.execute(delete(User).where(User.id.in_(customer_ids)))
        db.commit()
        return counts
    except Exception:
        db.rollback()
        raise


def _print_counts(title: str, counts: dict[str, int]) -> None:
    print(title)
    for name in TABLES:
        print(f"  {name}: {counts[name]}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reset customer data, keeping the admin and catalogue.")
    parser.add_argument("--yes", action="store_true", help="actually delete (default is a dry run)")
    args = parser.parse_args(argv)

    try:
        check_environment(settings.database_url, settings.environment)
        with SessionLocal() as db:
            if not has_admin(db):
                raise NoAdminError("No admin user exists; refusing to reset.")
            if not args.yes:
                counts = preview(db)
                _print_counts("Would delete:", counts)
                print(f"  stock units to restore: {counts['stock_restored']}")
                print("Dry run: nothing was changed. Re-run with --yes to delete.")
                return 0

            backup = make_backup(sqlite_path(settings.database_url), datetime.now())
            print(f"Backup written to: {backup}")
            before = table_counts(db)
            result = reset_data(db)
            after = table_counts(db)
    except ResetRefused as error:
        print(f"Refused: {error}")
        return 2

    _print_counts("Before:", before)
    _print_counts("After:", after)
    print(f"Stock units restored: {result['stock_restored']}")
    print(
        "Note: seeded history orders may not have reduced stock originally, "
        "so some products can end above their seeded level."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

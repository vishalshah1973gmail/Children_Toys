"""Seed the database with categories, toys, users and synthetic 2026 history.

Run:
    python -m scripts.seed                # seed everything (idempotent)
    python -m scripts.seed --reset        # drop and recreate every table first
    python -m scripts.seed --no-synthetic # catalogue and two logins only

Creates:
    5 categories, 24 products with placeholder SVG images
    admin    / Admin123!    (role: admin)
    customer / Customer123! (role: customer)
    50 synthetic customers and ~200 orders across January-December 2026
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.category import Category
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.product import Product, ProductImage
from app.models.user import User, UserRole
from scripts.catalog_data import CATEGORIES, PRODUCTS
from scripts.generate_synthetic_data import DATA_DIR, generate

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_DIR = BACKEND_ROOT / settings.upload_dir / "placeholders"

SYNTHETIC_PASSWORD = "Customer123!"

CATEGORY_COLOURS = {
    "building-construction": ("#2563eb", "#dbeafe"),
    "dolls-plush": ("#db2777", "#fce7f3"),
    "games-puzzles": ("#7c3aed", "#ede9fe"),
    "outdoor-active-play": ("#059669", "#d1fae5"),
    "stem-learning": ("#ea580c", "#ffedd5"),
}


def _wrap(text: str, width: int = 22) -> List[str]:
    """Naive word wrap for the placeholder artwork."""
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:4]


def write_placeholder_images() -> None:
    """Write one SVG placeholder per product so the storefront is never blank."""
    PLACEHOLDER_DIR.mkdir(parents=True, exist_ok=True)
    for product in PRODUCTS:
        accent, background = CATEGORY_COLOURS[product["category_slug"]]
        lines = _wrap(product["name"])
        text_rows = "".join(
            f'<text x="400" y="{300 + index * 46 - (len(lines) - 1) * 23}" '
            f'text-anchor="middle" font-family="Georgia, serif" font-size="34" '
            f'fill="{accent}">{line.replace("&", "&amp;")}</text>'
            for index, line in enumerate(lines)
        )
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" '
            'viewBox="0 0 800 600" role="img">'
            f'<rect width="800" height="600" fill="{background}"/>'
            f'<circle cx="400" cy="180" r="72" fill="{accent}" opacity="0.18"/>'
            f'<circle cx="400" cy="180" r="34" fill="{accent}" opacity="0.35"/>'
            f"{text_rows}"
            f'<text x="400" y="540" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="20" fill="{accent}" opacity="0.75">{product["brand"]}</text>'
            "</svg>"
        )
        (PLACEHOLDER_DIR / f"{product['slug']}.svg").write_text(svg, encoding="utf-8")


def seed_categories(db) -> Dict[str, Category]:
    """Insert the five categories, skipping any that already exist."""
    lookup: Dict[str, Category] = {}
    for data in CATEGORIES:
        category = db.execute(
            select(Category).where(Category.slug == data["slug"])
        ).scalar_one_or_none()
        if category is None:
            category = Category(**data)
            db.add(category)
            db.flush()
        lookup[data["slug"]] = category
    return lookup


def seed_products(db, categories: Dict[str, Category]) -> Dict[str, Product]:
    """Insert the 24 toys with a placeholder image each."""
    lookup: Dict[str, Product] = {}
    for data in PRODUCTS:
        existing = db.execute(
            select(Product).where(Product.slug == data["slug"])
        ).scalar_one_or_none()
        if existing is not None:
            lookup[data["slug"]] = existing
            continue

        payload = {key: value for key, value in data.items() if key != "category_slug"}
        product = Product(**payload, category_id=categories[data["category_slug"]].id)
        product.images.append(
            ProductImage(
                url=f"/{settings.upload_dir.strip('/')}/placeholders/{data['slug']}.svg",
                alt_text=data["name"],
                sort_order=0,
                is_primary=True,
            )
        )
        db.add(product)
        db.flush()
        lookup[data["slug"]] = product
    return lookup


def seed_core_users(db) -> None:
    """Create the two documented logins."""
    accounts = [
        ("admin", "admin@example.com", "Admin Account", "Admin123!", UserRole.ADMIN),
        ("customer", "customer@example.com", "Casey Customer", "Customer123!", UserRole.CUSTOMER),
    ]
    for username, email, full_name, password, role in accounts:
        existing = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        if existing is not None:
            continue
        db.add(
            User(
                username=username,
                email=email,
                full_name=full_name,
                hashed_password=hash_password(password),
                role=role,
            )
        )
    db.flush()


def _read_csv(path: Path) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _parse(value: str) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def seed_synthetic(db, products: Dict[str, Product]) -> None:
    """Load the generated 2026 customers, orders, items and payments."""
    if not (DATA_DIR / "orders.csv").exists():
        print("No synthetic CSVs found; generating them first...")
        generate()

    customers = _read_csv(DATA_DIR / "customers.csv")
    orders = _read_csv(DATA_DIR / "orders.csv")
    items = _read_csv(DATA_DIR / "order_items.csv")
    payments = _read_csv(DATA_DIR / "payments.csv")

    if db.execute(select(Order).limit(1)).scalar_one_or_none() is not None:
        print("Orders already present; skipping synthetic history.")
        return

    shared_hash = hash_password(SYNTHETIC_PASSWORD)
    users_by_username: Dict[str, User] = {}
    for row in customers:
        existing = db.execute(
            select(User).where(User.username == row["username"])
        ).scalar_one_or_none()
        if existing is None:
            existing = User(
                username=row["username"],
                email=row["email"],
                full_name=row["full_name"],
                hashed_password=shared_hash,
                role=UserRole.CUSTOMER,
            )
            db.add(existing)
            db.flush()
        users_by_username[row["username"]] = existing

    customers_by_id = {row["customer_id"]: row for row in customers}
    items_by_order: Dict[str, List[dict]] = {}
    for row in items:
        items_by_order.setdefault(row["order_number"], []).append(row)
    payments_by_order = {row["order_number"]: row for row in payments}

    for row in orders:
        customer = customers_by_id[row["customer_id"]]
        user = users_by_username[row["customer_username"]]
        order = Order(
            order_number=row["order_number"],
            user_id=user.id,
            status=OrderStatus(row["status"]),
            subtotal_cents=int(row["subtotal_cents"]),
            shipping_cents=int(row["shipping_cents"]),
            tax_cents=int(row["tax_cents"]),
            total_cents=int(row["total_cents"]),
            currency=row["currency"],
            contact_email=customer["email"],
            shipping_name=customer["full_name"],
            shipping_line1=customer["address_line1"],
            shipping_city=row["shipping_city"],
            shipping_state=row["shipping_state"],
            shipping_postal_code=row["shipping_postal_code"],
            shipping_country="US",
            placed_at=_parse(row["placed_at"]),
            paid_at=_parse(row["paid_at"]),
            shipped_at=_parse(row["shipped_at"]),
            delivered_at=_parse(row["delivered_at"]),
        )

        for line in items_by_order.get(row["order_number"], []):
            product = products[line["product_slug"]]
            order.items.append(
                OrderItem(
                    product_id=product.id,
                    product_name=line["product_name"],
                    product_slug=line["product_slug"],
                    image_url=product.primary_image_url,
                    unit_price_cents=int(line["unit_price_cents"]),
                    quantity=int(line["quantity"]),
                    line_total_cents=int(line["line_total_cents"]),
                )
            )

        payment_row = payments_by_order.get(row["order_number"])
        if payment_row is not None:
            order.payments.append(
                Payment(
                    provider=payment_row["provider"],
                    stripe_payment_intent_id=payment_row["stripe_payment_intent_id"],
                    amount_cents=int(payment_row["amount_cents"]),
                    currency=payment_row["currency"],
                    status=PaymentStatus(payment_row["status"]),
                )
            )

        db.add(order)

    db.flush()
    print(f"Loaded {len(customers)} synthetic customers and {len(orders)} 2026 orders.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the ToyBox database.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    parser.add_argument("--no-synthetic", action="store_true", help="Skip the 2026 history")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate the CSVs first")
    args = parser.parse_args()

    if args.reset:
        print("Dropping and recreating every table...")
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    if args.regenerate:
        generate()

    write_placeholder_images()
    print(f"Placeholder images written to {PLACEHOLDER_DIR}")

    with SessionLocal() as db:
        categories = seed_categories(db)
        products = seed_products(db, categories)
        seed_core_users(db)
        print(f"Seeded {len(categories)} categories and {len(products)} products.")
        if not args.no_synthetic:
            seed_synthetic(db, products)
        db.commit()

    print("\nSeed complete. Sign in with:")
    print("  admin    / Admin123!")
    print("  customer / Customer123!")
    print(f"  any synthetic customer / {SYNTHETIC_PASSWORD}")


if __name__ == "__main__":
    main()

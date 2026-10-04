"""Export the active product catalogue as a markdown file for the chatbot knowledge base.

Usage (from backend/):  python -m scripts.export_kb_products [--base-url URL] [--out PATH]
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.product import Product

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "docs" / "chatbot-kb" / "products.md"


def _price(cents: int) -> str:
    dollars, remainder = divmod(cents, 100)
    return f"${dollars}.{remainder:02d}"


def _age(months: int) -> str:
    # Mirrors formatAgeMonths in frontend/src/lib/format.ts so the bot quotes what the site shows.
    if months < 24:
        return f"{months} mo"
    return f"{months // 12} yr"


def _age_range(product: Product) -> str:
    return f"{_age(product.min_age_months)} – {_age(product.max_age_months)}"


def render_products_markdown(products: list[Product], as_of: str, base_url: str) -> str:
    """Render active products, one self-contained section each."""
    active = [product for product in products if product.is_active]
    lines = [
        "# ToyBox Product Catalogue",
        "",
        "Topic: Products for sale, prices, stock and age ranges.",
        "Source: ToyBox database export",
        "",
        f"Snapshot as of {as_of}. Prices and stock change over time; "
        "check the product page for the current price and availability.",
        "",
    ]
    if not active:
        lines.append("No products are currently listed.")
        return "\n".join(lines) + "\n"

    for product in sorted(active, key=lambda item: (item.category.name, item.name)):
        stock = "In stock" if product.stock_quantity > 0 else "Out of stock"
        lines += [
            f"## {product.name}",
            "",
            f"- Category: {product.category.name}",
            f"- Brand: {product.brand}",
            f"- Price: {_price(product.price_cents)}",
            f"- Availability: {stock}",
            f"- Recommended age: {_age_range(product)}",
            f"- Page: {base_url.rstrip('/')}/product/{product.slug}",
        ]
        if product.safety_notes:
            lines.append(f"- Safety notes: {product.safety_notes}")
        lines += ["", f"{product.name} — {product.description}".strip(), ""]
    return "\n".join(lines)


def main() -> None:
    from app.db.session import SessionLocal

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:5173")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    with SessionLocal() as session:
        products = list(
            session.scalars(
                select(Product).options(selectinload(Product.category)).where(Product.is_active)
            )
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        render_products_markdown(products, date.today().isoformat(), args.base_url),
        encoding="utf-8",
    )
    print(f"Wrote {len(products)} products to {args.out}")


if __name__ == "__main__":
    main()

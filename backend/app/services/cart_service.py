"""Cart reads and mutations. Prices always come from the database."""

from __future__ import annotations

from typing import List

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import api_error, not_found
from app.models.cart import CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartItemRead, CartRead
from app.services.pricing import totals_for


def load_cart_items(db: Session, user: User) -> List[CartItem]:
    """Fetch the user's cart lines with products eagerly loaded."""
    statement = (
        select(CartItem)
        .where(CartItem.user_id == user.id)
        .options(selectinload(CartItem.product).selectinload(Product.images))
        .order_by(CartItem.id)
    )
    return list(db.execute(statement).scalars().all())


def build_cart_response(db: Session, user: User) -> CartRead:
    """Serialise the cart, pricing every line from the product table."""
    items = load_cart_items(db, user)
    lines: List[CartItemRead] = []
    subtotal = 0

    for item in items:
        product = item.product
        line_total = product.price_cents * item.quantity
        subtotal += line_total
        lines.append(
            CartItemRead(
                id=item.id,
                product_id=product.id,
                name=product.name,
                slug=product.slug,
                image_url=product.primary_image_url,
                unit_price_cents=product.price_cents,
                quantity=item.quantity,
                line_total_cents=line_total,
                stock_quantity=product.stock_quantity,
                in_stock=product.stock_quantity >= item.quantity and product.is_active,
            )
        )

    totals = totals_for(subtotal)
    return CartRead(
        items=lines,
        item_count=sum(line.quantity for line in lines),
        currency=settings.stripe_currency,
        **totals,
    )


def get_active_product(db: Session, product_id: int) -> Product:
    """Fetch a purchasable product or raise 404."""
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise not_found("Product")
    return product


def add_item(db: Session, user: User, product_id: int, quantity: int) -> CartItem:
    """Add to (or increase) a cart line, capped at available stock."""
    product = get_active_product(db, product_id)

    existing = db.execute(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == product_id
        )
    ).scalar_one_or_none()

    desired = quantity + (existing.quantity if existing else 0)
    if desired > product.stock_quantity:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "insufficient_stock",
            f"Only {product.stock_quantity} of '{product.name}' left in stock",
            field="quantity",
        )

    if existing:
        existing.quantity = desired
        db.flush()
        return existing

    item = CartItem(user_id=user.id, product_id=product_id, quantity=quantity)
    db.add(item)
    db.flush()
    return item


def update_item(db: Session, user: User, item_id: int, quantity: int) -> CartItem:
    """Set an exact quantity on an existing line."""
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    ).scalar_one_or_none()
    if item is None:
        raise not_found("Cart item")

    if quantity > item.product.stock_quantity:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "insufficient_stock",
            f"Only {item.product.stock_quantity} of '{item.product.name}' left in stock",
            field="quantity",
        )

    item.quantity = quantity
    db.flush()
    return item


def remove_item(db: Session, user: User, item_id: int) -> None:
    """Delete one cart line."""
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id)
    ).scalar_one_or_none()
    if item is None:
        raise not_found("Cart item")
    db.delete(item)
    db.flush()


def clear_cart(db: Session, user: User) -> None:
    """Empty the user's cart."""
    for item in load_cart_items(db, user):
        db.delete(item)
    db.flush()

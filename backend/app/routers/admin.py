"""Admin-only endpoints. Every route depends on get_current_admin."""

import os
import secrets
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.deps import get_current_admin
from app.core.errors import api_error, not_found
from app.core.utils import unique_slug
from app.db.session import get_db
from app.models.category import Category
from app.models.order import Order, OrderStatus
from app.models.product import Product, ProductImage
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import Message, Page
from app.schemas.order import OrderRead, OrderStatusUpdate
from app.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    StockAdjustment,
    UploadedImage,
)
from app.schemas.user import UserRead
from app.services import order_service

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)]
)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------
@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)) -> CategoryRead:
    """Create a category."""
    category = Category(
        name=payload.name,
        slug=unique_slug(db, Category, payload.slug or payload.name),
        description=payload.description,
        image_url=payload.image_url,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return CategoryRead.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)
) -> CategoryRead:
    """Edit a category."""
    category = db.get(Category, category_id)
    if category is None:
        raise not_found("Category")

    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"]:
        data["slug"] = unique_slug(db, Category, data["slug"], exclude_id=category.id)
    for key, value in data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return CategoryRead.model_validate(category)


@router.delete("/categories/{category_id}", response_model=Message)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> Message:
    """Delete a category that has no products."""
    category = db.get(Category, category_id)
    if category is None:
        raise not_found("Category")

    count = db.execute(
        select(func.count(Product.id)).where(Product.category_id == category_id)
    ).scalar_one()
    if count:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "category_not_empty",
            f"{count} product(s) still use this category",
        )

    db.delete(category)
    db.commit()
    return Message(message="Category deleted")


# --------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------
def _serialize_product(product: Product) -> ProductRead:
    payload = ProductRead.model_validate(product)
    payload.primary_image_url = product.primary_image_url
    return payload


@router.get("/products", response_model=Page[ProductRead])
def admin_list_products(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=120),
    include_inactive: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[ProductRead]:
    """Every product, including inactive ones."""
    statement = select(Product).options(
        selectinload(Product.images), selectinload(Product.category)
    )
    if not include_inactive:
        statement = statement.where(Product.is_active.is_(True))
    if q:
        statement = statement.where(func.lower(Product.name).like(f"%{q.lower()}%"))

    total = db.execute(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ).scalar_one()
    rows = (
        db.execute(
            statement.order_by(Product.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    pages = (total + page_size - 1) // page_size if total else 0
    return Page[ProductRead](
        items=[_serialize_product(product) for product in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> ProductRead:
    """Create a product with optional images."""
    if db.get(Category, payload.category_id) is None:
        raise api_error(
            status.HTTP_400_BAD_REQUEST, "invalid_category", "Category does not exist", "category_id"
        )

    data = payload.model_dump(exclude={"images", "slug"})
    product = Product(**data, slug=unique_slug(db, Product, payload.slug or payload.name))

    for index, image in enumerate(payload.images):
        product.images.append(
            ProductImage(
                url=image.url,
                alt_text=image.alt_text or product.name,
                sort_order=image.sort_order or index,
                is_primary=image.is_primary or index == 0,
            )
        )

    db.add(product)
    db.commit()
    db.refresh(product)
    return _serialize_product(product)


@router.patch("/products/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)
) -> ProductRead:
    """Edit a product; passing `images` replaces the whole image set."""
    product = db.get(Product, product_id)
    if product is None:
        raise not_found("Product")

    data = payload.model_dump(exclude_unset=True)
    images = data.pop("images", None)

    if "category_id" in data and db.get(Category, data["category_id"]) is None:
        raise api_error(
            status.HTTP_400_BAD_REQUEST, "invalid_category", "Category does not exist", "category_id"
        )
    if "slug" in data and data["slug"]:
        data["slug"] = unique_slug(db, Product, data["slug"], exclude_id=product.id)

    for key, value in data.items():
        setattr(product, key, value)

    if product.min_age_months > product.max_age_months:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "invalid_age_range",
            "min_age_months must be less than or equal to max_age_months",
            "min_age_months",
        )

    if images is not None:
        product.images.clear()
        db.flush()
        for index, image in enumerate(images):
            product.images.append(
                ProductImage(
                    url=image["url"],
                    alt_text=image.get("alt_text") or product.name,
                    sort_order=image.get("sort_order") or index,
                    is_primary=image.get("is_primary") or index == 0,
                )
            )

    db.commit()
    db.refresh(product)
    return _serialize_product(product)


@router.patch("/products/{product_id}/stock", response_model=ProductRead)
def adjust_stock(
    product_id: int, payload: StockAdjustment, db: Session = Depends(get_db)
) -> ProductRead:
    """Set stock to an absolute value or apply a delta."""
    product = db.get(Product, product_id)
    if product is None:
        raise not_found("Product")

    new_value = payload.set_to if payload.set_to is not None else product.stock_quantity + (payload.delta or 0)
    if new_value < 0:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "negative_stock",
            "Stock cannot go below zero",
            field="delta",
        )

    product.stock_quantity = new_value
    db.commit()
    db.refresh(product)
    return _serialize_product(product)


@router.delete("/products/{product_id}", response_model=Message)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> Message:
    """Delete a product, or retire it when it already appears on orders."""
    product = db.get(Product, product_id)
    if product is None:
        raise not_found("Product")

    from app.models.order import OrderItem  # local import avoids a cycle at module load

    referenced = db.execute(
        select(func.count(OrderItem.id)).where(OrderItem.product_id == product_id)
    ).scalar_one()

    if referenced:
        product.is_active = False
        product.is_featured = False
        db.commit()
        return Message(message="Product appears on past orders; deactivated instead of deleted")

    db.delete(product)
    db.commit()
    return Message(message="Product deleted")


@router.post("/uploads/images", response_model=UploadedImage, status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile = File(...)) -> UploadedImage:
    """Store a product image on local disk and return its public URL."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "unsupported_media_type",
            f"Allowed image types: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}",
            field="file",
        )

    contents = await file.read()
    if len(contents) > settings.max_upload_bytes:
        raise api_error(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "file_too_large",
            f"Images must be {settings.max_upload_bytes // 1024} KB or smaller",
            field="file",
        )

    extension = ALLOWED_IMAGE_TYPES[file.content_type]
    filename = f"{secrets.token_hex(12)}{extension}"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / filename
    with open(destination, "wb") as handle:
        handle.write(contents)

    return UploadedImage(
        url=f"/{settings.upload_dir.strip('/')}/{filename}".replace(os.sep, "/"),
        filename=filename,
        size_bytes=len(contents),
    )


# --------------------------------------------------------------------------
# Orders and users
# --------------------------------------------------------------------------
@router.get("/orders", response_model=Page[OrderRead])
def admin_list_orders(
    db: Session = Depends(get_db),
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=64, description="Order number fragment"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[OrderRead]:
    """All orders, newest first."""
    statement = select(Order).options(
        selectinload(Order.items), selectinload(Order.payments)
    )
    if order_status is not None:
        statement = statement.where(Order.status == order_status)
    if q:
        statement = statement.where(Order.order_number.like(f"%{q.upper()}%"))

    total = db.execute(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ).scalar_one()
    rows = (
        db.execute(
            statement.order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    pages = (total + page_size - 1) // page_size if total else 0
    return Page[OrderRead](
        items=[OrderRead.model_validate(order) for order in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.patch("/orders/{order_number}/status", response_model=OrderRead)
def update_order_status(
    order_number: str, payload: OrderStatusUpdate, db: Session = Depends(get_db)
) -> OrderRead:
    """Advance an order through pending -> paid -> shipped -> delivered."""
    order = order_service.get_order_by_number(db, order_number)
    if order is None:
        raise not_found("Order")

    order_service.advance_status(db, order, payload.status)
    db.commit()
    db.refresh(order)
    return OrderRead.model_validate(order)


@router.get("/users", response_model=Page[UserRead])
def admin_list_users(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[UserRead]:
    """All accounts."""
    base = select(User)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = (
        db.execute(base.order_by(User.id).offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    pages = (total + page_size - 1) // page_size if total else 0
    return Page[UserRead](
        items=[UserRead.model_validate(user) for user in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/stats", response_model=dict)
def admin_stats(db: Session = Depends(get_db)) -> dict:
    """Headline numbers for the dashboard."""
    revenue = db.execute(
        select(func.coalesce(func.sum(Order.total_cents), 0)).where(
            Order.status.in_([OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED])
        )
    ).scalar_one()
    return {
        "products": db.execute(select(func.count(Product.id))).scalar_one(),
        "active_products": db.execute(
            select(func.count(Product.id)).where(Product.is_active.is_(True))
        ).scalar_one(),
        "low_stock": db.execute(
            select(func.count(Product.id)).where(Product.stock_quantity < 5)
        ).scalar_one(),
        "categories": db.execute(select(func.count(Category.id))).scalar_one(),
        "customers": db.execute(select(func.count(User.id))).scalar_one(),
        "orders": db.execute(select(func.count(Order.id))).scalar_one(),
        "pending_orders": db.execute(
            select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING)
        ).scalar_one(),
        "revenue_cents": revenue,
    }

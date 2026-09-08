"""Public catalog endpoints: search, filter, sort, paginate."""

from typing import List, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import not_found
from app.db.session import get_db
from app.models.category import Category
from app.models.product import Product
from app.schemas.common import Page
from app.schemas.product import ProductRead

router = APIRouter(prefix="/products", tags=["catalog"])

SortOption = Literal["newest", "price_asc", "price_desc", "name_asc", "name_desc"]

_SORTS = {
    "newest": Product.created_at.desc(),
    "price_asc": Product.price_cents.asc(),
    "price_desc": Product.price_cents.desc(),
    "name_asc": Product.name.asc(),
    "name_desc": Product.name.desc(),
}


def _serialize(product: Product) -> ProductRead:
    payload = ProductRead.model_validate(product)
    payload.primary_image_url = product.primary_image_url
    return payload


@router.get("", response_model=Page[ProductRead])
def list_products(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=120, description="Keyword search"),
    category: str | None = Query(default=None, description="Category slug"),
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    age_months: int | None = Query(
        default=None, ge=0, le=240, description="Child age in months"
    ),
    min_age_months: int | None = Query(default=None, ge=0, le=240),
    max_age_months: int | None = Query(default=None, ge=0, le=240),
    brand: str | None = Query(default=None, max_length=120),
    featured: bool | None = Query(default=None),
    in_stock: bool | None = Query(default=None),
    sort: SortOption = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=60),
) -> Page[ProductRead]:
    """Paginated catalog with keyword search and filters."""
    statement = (
        select(Product)
        .join(Category, Product.category_id == Category.id)
        .where(Product.is_active.is_(True))
        .options(selectinload(Product.images), selectinload(Product.category))
    )

    if q:
        pattern = f"%{q.lower()}%"
        statement = statement.where(
            or_(
                func.lower(Product.name).like(pattern),
                func.lower(Product.description).like(pattern),
                func.lower(Product.brand).like(pattern),
            )
        )
    if category:
        statement = statement.where(Category.slug == category)
    if min_price_cents is not None:
        statement = statement.where(Product.price_cents >= min_price_cents)
    if max_price_cents is not None:
        statement = statement.where(Product.price_cents <= max_price_cents)
    if age_months is not None:
        statement = statement.where(
            Product.min_age_months <= age_months, Product.max_age_months >= age_months
        )
    if min_age_months is not None:
        statement = statement.where(Product.max_age_months >= min_age_months)
    if max_age_months is not None:
        statement = statement.where(Product.min_age_months <= max_age_months)
    if brand:
        statement = statement.where(func.lower(Product.brand) == brand.lower())
    if featured is not None:
        statement = statement.where(Product.is_featured.is_(featured))
    if in_stock:
        statement = statement.where(Product.stock_quantity > 0)

    total = db.execute(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ).scalar_one()

    rows = (
        db.execute(
            statement.order_by(_SORTS[sort], Product.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    pages = (total + page_size - 1) // page_size if total else 0
    return Page[ProductRead](
        items=[_serialize(product) for product in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/featured", response_model=List[ProductRead])
def featured_products(
    db: Session = Depends(get_db), limit: int = Query(default=8, ge=1, le=24)
) -> List[ProductRead]:
    """Toys shown on the home page."""
    rows = (
        db.execute(
            select(Product)
            .where(Product.is_active.is_(True), Product.is_featured.is_(True))
            .options(selectinload(Product.images), selectinload(Product.category))
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_serialize(product) for product in rows]


@router.get("/brands", response_model=List[str])
def list_brands(db: Session = Depends(get_db)) -> List[str]:
    """Distinct brands, for the catalog filter panel."""
    rows = db.execute(
        select(Product.brand)
        .where(Product.is_active.is_(True))
        .distinct()
        .order_by(Product.brand)
    ).scalars()
    return list(rows)


@router.get("/{slug}", response_model=ProductRead)
def get_product(slug: str, db: Session = Depends(get_db)) -> ProductRead:
    """One product by slug."""
    product = db.execute(
        select(Product)
        .where(Product.slug == slug, Product.is_active.is_(True))
        .options(selectinload(Product.images), selectinload(Product.category))
    ).scalar_one_or_none()
    if product is None:
        raise not_found("Product")
    return _serialize(product)

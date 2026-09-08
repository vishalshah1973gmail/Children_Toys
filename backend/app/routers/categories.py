"""Public category endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.session import get_db
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryRead

router = APIRouter(prefix="/categories", tags=["catalog"])


def _with_counts(db: Session, categories: List[Category]) -> List[CategoryRead]:
    """Attach an active-product count to each category."""
    counts = dict(
        db.execute(
            select(Product.category_id, func.count(Product.id))
            .where(Product.is_active.is_(True))
            .group_by(Product.category_id)
        ).all()
    )
    result = []
    for category in categories:
        payload = CategoryRead.model_validate(category)
        payload.product_count = counts.get(category.id, 0)
        result.append(payload)
    return result


@router.get("", response_model=List[CategoryRead])
def list_categories(db: Session = Depends(get_db)) -> List[CategoryRead]:
    """All categories, alphabetically."""
    categories = list(
        db.execute(select(Category).order_by(Category.name)).scalars().all()
    )
    return _with_counts(db, categories)


@router.get("/{slug}", response_model=CategoryRead)
def get_category(slug: str, db: Session = Depends(get_db)) -> CategoryRead:
    """One category by slug."""
    category = db.execute(
        select(Category).where(Category.slug == slug)
    ).scalar_one_or_none()
    if category is None:
        raise not_found("Category")
    return _with_counts(db, [category])[0]

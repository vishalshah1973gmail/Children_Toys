"""Order history for the signed-in user."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.core.errors import api_error, not_found
from app.db.session import get_db
from app.models.order import Order
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.order import OrderRead

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=Page[OrderRead])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> Page[OrderRead]:
    """Most recent orders first."""
    base = select(Order).where(Order.user_id == current_user.id)
    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    rows = (
        db.execute(
            base.options(selectinload(Order.items), selectinload(Order.payments))
            .order_by(Order.created_at.desc(), Order.id.desc())
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


@router.get("/{order_number}", response_model=OrderRead)
def get_my_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderRead:
    """One order, owned by the caller (admins may read any order)."""
    order = db.execute(
        select(Order)
        .where(Order.order_number == order_number)
        .options(selectinload(Order.items), selectinload(Order.payments))
    ).scalar_one_or_none()
    if order is None:
        raise not_found("Order")
    if order.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise api_error(
            status.HTTP_403_FORBIDDEN, "forbidden", "This order belongs to another account"
        )
    return OrderRead.model_validate(order)

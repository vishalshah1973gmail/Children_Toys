"""Cart endpoints. Every price is recomputed from the database."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartMergeRequest, CartRead
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartRead)
def read_cart(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> CartRead:
    """The signed-in user's cart with server-computed totals."""
    return cart_service.build_cart_response(db, current_user)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartRead:
    """Add a product to the cart."""
    cart_service.add_item(db, current_user, payload.product_id, payload.quantity)
    db.commit()
    return cart_service.build_cart_response(db, current_user)


@router.patch("/items/{item_id}", response_model=CartRead)
def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartRead:
    """Set the quantity of a cart line."""
    cart_service.update_item(db, current_user, item_id, payload.quantity)
    db.commit()
    return cart_service.build_cart_response(db, current_user)


@router.delete("/items/{item_id}", response_model=CartRead)
def delete_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartRead:
    """Remove one line from the cart."""
    cart_service.remove_item(db, current_user, item_id)
    db.commit()
    return cart_service.build_cart_response(db, current_user)


@router.delete("", response_model=CartRead)
def empty_cart(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> CartRead:
    """Remove everything from the cart."""
    cart_service.clear_cart(db, current_user)
    db.commit()
    return cart_service.build_cart_response(db, current_user)


@router.post("/merge", response_model=CartRead)
def merge_cart(
    payload: CartMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CartRead:
    """Fold a guest cart into the server cart after signing in.

    Lines that no longer fit available stock are skipped rather than failing
    the whole merge.
    """
    for item in payload.items:
        try:
            cart_service.add_item(db, current_user, item.product_id, item.quantity)
        except Exception:  # noqa: BLE001 - skip unavailable lines, keep the rest
            db.rollback()
            continue
    db.commit()
    return cart_service.build_cart_response(db, current_user)

# File: src/cashpilot/api/routes/line_items.py
"""Line item CRUD endpoints for transfers and expenses."""

from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_own_session
from cashpilot.api.utils import format_time_business, get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.core.errors import NotFoundError, ValidationError
from cashpilot.core.line_items import sync_session_totals
from cashpilot.core.logging import get_logger
from cashpilot.models import CashSession, User
from cashpilot.models.expense_item import ExpenseItem
from cashpilot.models.transfer_item import TransferItem
from cashpilot.utils.datetime import now_utc

logger = get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["line-items"])

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["format_time_business"] = format_time_business


# ─────── TRANSFER ITEMS ────────


@router.post("/{session_id}/transfer-items", response_class=HTMLResponse)
async def create_transfer_item(
    request: Request,
    session_id: str,
    description: str = Form(...),
    amount: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    db: AsyncSession = Depends(get_db),
):
    """Add a bank transfer item to session."""
    # Business logic: validate description length
    description = description.strip()
    if not description:
        raise ValidationError("Description is required")
    if len(description) > 100:
        raise ValidationError("Description must be 100 characters or less")

    # Business logic: parse and validate amount (es-PY currency format)
    try:
        amount_clean = amount.replace(",", "").replace(".", "")
        if not amount_clean or amount_clean.strip() == "":
            raise ValidationError("Invalid amount format")
        amount_decimal = Decimal(amount_clean)
    except (ValueError, TypeError, InvalidOperation):
        raise ValidationError("Invalid amount format")

    # Business logic: minimum amount
    if amount_decimal < 100:
        raise ValidationError("Minimum amount is Gs 100")

    # Business logic: validate UUID format
    try:
        session_uuid = UUID(session_id)
    except (ValueError, TypeError):
        raise ValidationError("Invalid session_id format")

    # Create item
    item = TransferItem(
        session_id=session_uuid,
        description=description.strip(),
        amount=amount_decimal,
    )
    db.add(item)
    await db.flush()

    # Recalculate totals
    await sync_session_totals(session, db)

    # Update session audit
    session.last_modified_at = now_utc()
    session.last_modified_by = current_user.display_name
    db.add(session)

    await db.commit()
    await db.refresh(session, ["transfer_items", "expense_items"])

    logger.info(
        "transfer_item.created",
        session_id=session_id,
        item_id=str(item.id),
        amount=str(amount_decimal),
    )

    # Return updated table partial
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        request,
        "partials/transfer_items_table.html",
        {
            "session": session,
            "editable": True,
            "locale": locale,
            "_": _,
        },
    )


@router.delete("/{session_id}/transfer-items/{item_id}", response_class=HTMLResponse)
async def delete_transfer_item(
    request: Request,
    session_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a transfer item."""
    item = await db.get(TransferItem, UUID(item_id))

    if not item or item.session_id != UUID(session_id):
        raise NotFoundError("TransferItem", item_id)

    # Soft delete
    item.is_deleted = True
    db.add(item)
    await db.flush()

    # Recalculate totals
    await sync_session_totals(session, db)

    # Update session audit
    session.last_modified_at = now_utc()
    session.last_modified_by = current_user.display_name
    db.add(session)

    await db.commit()
    await db.refresh(session, ["transfer_items", "expense_items"])

    logger.info(
        "transfer_item.deleted",
        session_id=session_id,
        item_id=item_id,
    )

    # Return updated table partial
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        request,
        "partials/transfer_items_table.html",
        {
            "session": session,
            "editable": True,
            "locale": locale,
            "_": _,
        },
    )


# ─────── EXPENSE ITEMS ────────


@router.post("/{session_id}/expense-items", response_class=HTMLResponse)
async def create_expense_item(
    request: Request,
    session_id: str,
    description: str = Form(...),
    amount: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    db: AsyncSession = Depends(get_db),
):
    """Add an expense item to session."""
    # Business logic: validate description length
    description = description.strip()
    if not description:
        raise ValidationError("Description is required")
    if len(description) > 100:
        raise ValidationError("Description must be 100 characters or less")

    # Business logic: parse and validate amount (es-PY currency format)
    try:
        amount_clean = amount.replace(",", "").replace(".", "")
        if not amount_clean or amount_clean.strip() == "":
            raise ValidationError("Invalid amount format")
        amount_decimal = Decimal(amount_clean)
    except (ValueError, TypeError, InvalidOperation):
        raise ValidationError("Invalid amount format")

    # Business logic: minimum amount
    if amount_decimal < 100:
        raise ValidationError("Minimum amount is Gs 100")

    # Business logic: validate UUID format
    try:
        session_uuid = UUID(session_id)
    except (ValueError, TypeError):
        raise ValidationError("Invalid session_id format")

    # Create item
    item = ExpenseItem(
        session_id=session_uuid,
        description=description.strip(),
        amount=amount_decimal,
    )
    db.add(item)
    await db.flush()

    # Recalculate totals
    await sync_session_totals(session, db)

    # Update session audit
    session.last_modified_at = now_utc()
    session.last_modified_by = current_user.display_name
    db.add(session)

    await db.commit()
    await db.refresh(session, ["transfer_items", "expense_items"])

    logger.info(
        "expense_item.created",
        session_id=session_id,
        item_id=str(item.id),
        amount=str(amount_decimal),
    )

    # Return updated table partial
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        request,
        "partials/expense_items_table.html",
        {
            "session": session,
            "editable": True,
            "locale": locale,
            "_": _,
        },
    )


@router.delete("/{session_id}/expense-items/{item_id}", response_class=HTMLResponse)
async def delete_expense_item(
    request: Request,
    session_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    session: CashSession = Depends(require_own_session),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete an expense item."""
    item = await db.get(ExpenseItem, UUID(item_id))

    if not item or item.session_id != UUID(session_id):
        raise NotFoundError("ExpenseItem", item_id)

    # Soft delete
    item.is_deleted = True
    db.add(item)
    await db.flush()

    # Recalculate totals
    await sync_session_totals(session, db)

    # Update session audit
    session.last_modified_at = now_utc()
    session.last_modified_by = current_user.display_name
    db.add(session)

    await db.commit()
    await db.refresh(session, ["transfer_items", "expense_items"])

    logger.info(
        "expense_item.deleted",
        session_id=session_id,
        item_id=item_id,
    )

    # Return updated table partial
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        request,
        "partials/expense_items_table.html",
        {
            "session": session,
            "editable": True,
            "locale": locale,
            "_": _,
        },
    )

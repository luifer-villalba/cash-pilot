# File: src/cashpilot/api/routes/businesses.py
"""Business management routes (HTML endpoints)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import (
    get_assigned_businesses,
    get_locale,
    get_translation_function,
    templates,
)
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import Business
from cashpilot.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/businesses", tags=["businesses-frontend"])


@router.get("", response_class=HTMLResponse)
async def list_businesses(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List businesses with management options (AC-01, AC-02).

    Admin sees all active businesses.
    Cashier sees only assigned businesses.
    """
    locale = get_locale(request)
    _ = get_translation_function(locale)

    # Filter businesses by user role (AC-01, AC-02)
    businesses = await get_assigned_businesses(current_user, db)

    return templates.TemplateResponse(
        request,
        "businesses/list.html",
        {
            "businesses": businesses,
            "current_user": current_user,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def create_business_form(
    request: Request,
    current_user: User = Depends(require_admin),
):
    """Form to create new business. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        request,
        "businesses/create.html",
        {
            "current_user": current_user,
            "locale": locale,
            "_": _,
        },
    )


@router.post("", response_class=HTMLResponse)
async def create_business_post(
    request: Request,
    name: str = Form(...),
    address: str | None = Form(None),
    phone: str | None = Form(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Handle business creation form submission. Admin only."""
    business = Business(
        name=name.strip(),
        address=address.strip() if address else None,
        phone=phone.strip() if phone else None,
    )
    db.add(business)
    await db.commit()
    await db.refresh(business)
    logger.info(
        "business.created_html",
        business_id=str(business.id),
        business_name=business.name,
        created_by=str(current_user.id),
    )

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)


@router.get("/{business_id}/edit", response_class=HTMLResponse)
async def edit_business_form(
    request: Request,
    business_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Form to edit business. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        business_uuid = UUID(business_id)
    except (ValueError, TypeError):
        return RedirectResponse(url="/businesses", status_code=302)

    stmt = (
        select(Business).options(selectinload(Business.users)).where(Business.id == business_uuid)
    )
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    return templates.TemplateResponse(
        request,
        "businesses/edit.html",
        {
            "business": business,
            "current_user": current_user,
            "locale": locale,
            "_": _,
        },
    )


@router.put("/{business_id}", response_class=HTMLResponse)
@router.post("/{business_id}", response_class=HTMLResponse)
async def update_business_put(
    request: Request,
    business_id: str,
    name: str | None = Form(None),
    address: str | None = Form(None),
    phone: str | None = Form(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Handle business update via form. Admin only."""
    try:
        business_uuid = UUID(business_id)
    except (ValueError, TypeError):
        return RedirectResponse(url="/businesses", status_code=302)

    stmt = select(Business).where(Business.id == business_uuid)
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    if name:
        business.name = name.strip()
    if address is not None:
        business.address = address.strip() if address else None
    if phone is not None:
        business.phone = phone.strip() if phone else None

    db.add(business)
    await db.commit()
    await db.refresh(business)
    logger.info(
        "business.updated_html",
        business_id=str(business.id),
        updated_by=str(current_user.id),
    )

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)

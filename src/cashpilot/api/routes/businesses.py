"""Business management routes (HTML endpoints)."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.auth import get_current_user
from cashpilot.api.auth_helpers import require_admin
from cashpilot.api.utils import get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.models import Business
from cashpilot.models.user import User

logger = get_logger(__name__)

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/businesses", tags=["businesses-frontend"])


@router.get("", response_class=HTMLResponse)
async def list_businesses(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all businesses with management options."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(Business).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = result.scalars().all()

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
        cashiers=[],
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
    """Form to edit business and manage cashiers. Admin only."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(Business).where(Business.id == UUID(business_id))
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
    stmt = select(Business).where(Business.id == UUID(business_id))
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

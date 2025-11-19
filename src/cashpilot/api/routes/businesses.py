# File: src/cashpilot/api/routes/businesses.py
"""Business management routes (HTML endpoints)."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.api.frontend import get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.models import Business

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/businesses", tags=["businesses-frontend"])


@router.get("", response_class=HTMLResponse)
async def list_businesses(
    request: Request,
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
            "locale": locale,
            "_": _,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def create_business_form(request: Request):
    """Form to create new business."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    return templates.TemplateResponse(
        request,
        "businesses/create.html",
        {
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
    db: AsyncSession = Depends(get_db),
):
    """Handle business creation form submission."""
    business = Business(
        name=name.strip(),
        address=address.strip() if address else None,
        phone=phone.strip() if phone else None,
        cashiers=[],
    )
    db.add(business)
    await db.commit()
    await db.refresh(business)

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)


@router.get("/{business_id}/edit", response_class=HTMLResponse)
async def edit_business_form(
    request: Request,
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Form to edit business and manage cashiers."""
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
            "locale": locale,
            "_": _,
        },
    )


@router.post("/{business_id}", response_class=HTMLResponse)
async def update_business_post(
    request: Request,
    business_id: str,
    name: str = Form(...),
    address: str | None = Form(None),
    phone: str | None = Form(None),
    is_active: bool = Form(True),
    db: AsyncSession = Depends(get_db),
):
    """Handle business update form submission."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    business.name = name.strip()
    business.address = address.strip() if address else None
    business.phone = phone.strip() if phone else None
    business.is_active = is_active

    db.add(business)
    await db.commit()

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)


@router.post("/{business_id}/cashiers/add", response_class=HTMLResponse)
async def add_cashier_form(
    request: Request,
    business_id: str,
    cashier_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle adding cashier via form."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    cashier_clean = cashier_name.strip()
    if cashier_clean and cashier_clean not in business.cashiers:
        business.cashiers.append(cashier_clean)
        db.add(business)
        await db.commit()

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)


@router.post("/{business_id}/cashiers/remove", response_class=HTMLResponse)
async def remove_cashier_form(
    request: Request,
    business_id: str,
    cashier_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle removing cashier via form."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    if cashier_name in business.cashiers:
        business.cashiers.remove(cashier_name)
        db.add(business)
        await db.commit()

    return RedirectResponse(url=f"/businesses/{business.id}/edit", status_code=302)


@router.delete("/{business_id}", response_class=HTMLResponse)
async def delete_business(
    request: Request,
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete business (sets is_active=False)."""
    stmt = select(Business).where(Business.id == UUID(business_id))
    result = await db.execute(stmt)
    business = result.scalar_one_or_none()

    if not business:
        return RedirectResponse(url="/businesses", status_code=302)

    business.is_active = False
    db.add(business)
    await db.commit()

    return RedirectResponse(url="/businesses", status_code=302)

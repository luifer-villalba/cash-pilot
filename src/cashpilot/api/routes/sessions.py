"""Session management routes (HTML endpoints)."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from cashpilot.api.auth import get_current_user
from cashpilot.api.utils import (
    format_currency_py,
    get_locale,
    get_translation_function,
    parse_currency,
)
from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession
from cashpilot.models.cash_session_audit_log import CashSessionAuditLog
from cashpilot.models.user import User

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Register filter
templates.env.filters["format_currency_py"] = format_currency_py

router = APIRouter(prefix="/sessions", tags=["sessions-frontend"])


@router.get("/create", response_class=HTMLResponse)
async def create_session_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Form to create new cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(Business).where(Business.is_active).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = list(result.scalars().all())

    return templates.TemplateResponse(
        request,
        "sessions/create_session.html",
        {
            "current_user": current_user,
            "businesses": businesses,
            "locale": locale,
            "_": _,
        },
    )


@router.post("", response_class=HTMLResponse)
async def create_session_post(
    request: Request,
    current_user: User = Depends(get_current_user),
    business_id: str = Form(...),
    cashier_name: str = Form(...),
    initial_cash: str = Form(...),
    session_date: str | None = Form(None),
    opened_time: str | None = Form(None),
    allow_overlap: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    """Handle session creation form submission."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    try:
        initial_cash_val = parse_currency(initial_cash)
        if not initial_cash_val:
            raise ValueError("Initial cash required")
        session_date_val = (
            datetime.fromisoformat(session_date).date() if session_date else date_type.today()
        )
        opened_time_val = (
            datetime.strptime(opened_time, "%H:%M").time() if opened_time else datetime.now().time()
        )

        session = CashSession(
            business_id=UUID(business_id),
            cashier_name=cashier_name,
            initial_cash=initial_cash_val,
            session_date=session_date_val,
            opened_time=opened_time_val,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return RedirectResponse(url=f"/sessions/{session.id}", status_code=302)

    except Exception as e:
        stmt = select(Business).where(Business.is_active).order_by(Business.name)
        result = await db.execute(stmt)
        businesses = list(result.scalars().all())

        return templates.TemplateResponse(
            request,
            "sessions/create_session.html",
            {
                "current_user": current_user,
                "businesses": businesses,
                "error": str(e),
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )


@router.get("/{session_id}", response_class=HTMLResponse)
async def session_detail(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Display single session details."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .where(CashSession.id == UUID(session_id))
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return RedirectResponse(url="/", status_code=302)

    # Safe calculations (all values default to 0 if None)
    final_cash = session.final_cash or Decimal("0")
    envelope = session.envelope_amount or Decimal("0")
    bank = session.bank_transfer_total or Decimal("0")
    expenses = session.expenses or Decimal("0")

    net_cash_movement = final_cash - session.initial_cash + envelope + bank
    net_earnings = net_cash_movement - expenses
    cash_profit = (final_cash - session.initial_cash + envelope) - expenses

    return templates.TemplateResponse(
        request,
        "sessions/session_detail.html",
        {
            "current_user": current_user,
            "session": session,
            "net_cash_movement": net_cash_movement,
            "net_earnings": net_earnings,
            "cash_profit": cash_profit,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/{session_id}/edit", response_class=HTMLResponse)
async def edit_session_form(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Form to close/edit cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return RedirectResponse(url="/", status_code=302)

    return templates.TemplateResponse(
        request,
        "sessions/close_session.html",
        {
            "current_user": current_user,
            "session": session,
            "locale": locale,
            "_": _,
        },
    )


@router.get("/{session_id}/edit-open", response_class=HTMLResponse)
async def edit_open_session_form(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Form to edit an OPEN cash session."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return RedirectResponse(url="/", status_code=302)

    if session.status != "OPEN":
        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

    return templates.TemplateResponse(
        request,
        "sessions/edit_open_session.html",
        {
            "current_user": current_user,
            "session": session,
            "locale": locale,
            "_": _,
        },
    )


async def _update_open_session_fields(
    session: CashSession,
    cashier_name: str | None,
    initial_cash: str | None,
    opened_time: str | None,
    expenses: str | None,
) -> tuple[list[str], dict, dict]:
    """Update open session fields and track changes."""
    changed_fields = []
    old_values = {}
    new_values = {}

    # Cashier name
    if cashier_name and cashier_name.strip() != session.cashier_name:
        old_values["cashier_name"] = session.cashier_name
        new_values["cashier_name"] = cashier_name.strip()
        session.cashier_name = cashier_name.strip()
        changed_fields.append("cashier_name")

    # Initial cash
    if initial_cash:
        initial_cash_val = parse_currency(initial_cash)
        if initial_cash_val != session.initial_cash:
            old_values["initial_cash"] = str(session.initial_cash)
            new_values["initial_cash"] = str(initial_cash_val)
            session.initial_cash = initial_cash_val
            changed_fields.append("initial_cash")

    # Opened time
    if opened_time:
        opened_time_val = datetime.strptime(opened_time, "%H:%M").time()
        if opened_time_val != session.opened_time:
            old_values["opened_time"] = session.opened_time.isoformat()
            new_values["opened_time"] = opened_time_val.isoformat()
            session.opened_time = opened_time_val
            changed_fields.append("opened_time")

    # Expenses (ADD THIS)
    if expenses is not None:
        expenses_val = parse_currency(expenses) if expenses else Decimal("0")
        if expenses_val != (session.expenses or Decimal("0")):
            old_values["expenses"] = str(session.expenses or "0")
            new_values["expenses"] = str(expenses_val)
            session.expenses = expenses_val
            changed_fields.append("expenses")

    return changed_fields, old_values, new_values


@router.post("/{session_id}/edit-open", response_class=HTMLResponse)
async def edit_open_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    cashier_name: str | None = Form(None),
    initial_cash: str | None = Form(None),
    opened_time: str | None = Form(None),
    expenses: str | None = Form(None),
    reason: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle edit open session form submission."""
    try:
        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return RedirectResponse(url="/", status_code=302)

        if session.status != "OPEN":
            return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

        # Update fields
        changed_fields, old_values, new_values = await _update_open_session_fields(
            session, cashier_name, initial_cash, opened_time, expenses
        )

        # Set audit tracking
        session.last_modified_at = datetime.now()
        session.last_modified_by = "system"

        db.add(session)
        await db.commit()

        # Create audit log if changes
        if changed_fields:
            audit_log = CashSessionAuditLog(
                session_id=session.id,
                action="edit",
                changed_fields=changed_fields,
                old_values=old_values,
                new_values=new_values,
                changed_by="system",
                reason=reason,
            )
            db.add(audit_log)
            await db.commit()

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)

    except ValueError as e:
        locale = get_locale(request)
        _ = get_translation_function(locale)

        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        return templates.TemplateResponse(
            request,
            "sessions/edit_open_session.html",
            {
                "current_user": current_user,
                "session": session,
                "error": f"Invalid input: {str(e)}",
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )


@router.post("/{session_id}", response_class=HTMLResponse)
async def close_session_post(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_user),
    final_cash: str = Form(...),
    envelope_amount: str = Form(...),
    credit_card_total: str = Form(...),
    debit_card_total: str = Form(...),
    bank_transfer_total: str = Form(...),
    expenses: str = Form("0"),
    closed_time: str = Form(...),
    closing_ticket: str | None = Form(None),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle session close form submission."""
    try:
        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return RedirectResponse(url="/", status_code=302)

        session.final_cash = parse_currency(final_cash)
        session.envelope_amount = parse_currency(envelope_amount) or Decimal("0")
        session.credit_card_total = parse_currency(credit_card_total) or Decimal("0")
        session.debit_card_total = parse_currency(debit_card_total) or Decimal("0")
        session.bank_transfer_total = parse_currency(bank_transfer_total) or Decimal("0")
        session.expenses = parse_currency(expenses) or Decimal("0")
        session.closed_time = datetime.strptime(closed_time, "%H:%M").time()
        session.closing_ticket = closing_ticket
        session.notes = notes
        session.status = "CLOSED"

        db.add(session)
        await db.commit()

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=302)
    except Exception as e:
        # Re-render form with error
        locale = get_locale(request)
        _ = get_translation_function(locale)

        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        return templates.TemplateResponse(
            request,
            "sessions/close_session.html",
            {
                "current_user": current_user,
                "session": session,
                "error": str(e),
                "locale": locale,
                "_": _,
            },
            status_code=400,
        )

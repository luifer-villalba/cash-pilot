"""Frontend routes for HTML templates."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession

# Configure templates
templates = Jinja2Templates(directory="src/cashpilot/templates")

router = APIRouter(tags=["frontend"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request, skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    """Dashboard homepage with paginated session list."""
    # Get paginated sessions (most recent first)
    stmt_sessions = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .order_by(CashSession.opened_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt_sessions)
    sessions = result.scalars().unique().all()

    # Total session count (for pagination)
    stmt_total = select(func.count(CashSession.id))
    result = await db.execute(stmt_total)
    total_sessions = result.scalar() or 0

    # Active sessions count
    stmt_active = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .where(CashSession.status == "OPEN")
        .limit(10)
    )
    result = await db.execute(stmt_active)
    active_sessions_count = len(result.scalars().all())

    # Active businesses count
    stmt_businesses = select(func.count(Business.id)).where(Business.is_active is True)
    result = await db.execute(stmt_businesses)
    businesses_count = result.scalar() or 0

    # Today's total revenue (closed sessions only)
    today = date.today()
    stmt_revenue = select(
        func.sum(
            (CashSession.final_cash + CashSession.envelope_amount - CashSession.initial_cash)
            + CashSession.credit_card_total
            + CashSession.debit_card_total
            + CashSession.bank_transfer_total
        )
    ).where(
        and_(
            CashSession.status == "CLOSED",
            CashSession.final_cash.isnot(None),  # Only sum closed sessions with final_cash
            func.date(CashSession.closed_at) == today,
        )
    )
    result = await db.execute(stmt_revenue)
    total_revenue = result.scalar() or Decimal("0.00")

    # Discrepancies count (closed sessions from today with has_conflict=true)
    stmt_discrepancies = select(func.count(CashSession.id)).where(
        and_(
            CashSession.status == "CLOSED",
            CashSession.has_conflict is True,
            func.date(CashSession.closed_at) == today,
        )
    )
    result = await db.execute(stmt_discrepancies)
    discrepancies_count = result.scalar() or 0

    # Pagination info
    total_pages = (total_sessions + limit - 1) // limit
    current_page = (skip // limit) + 1

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "sessions": sessions,
            "active_sessions_count": active_sessions_count,
            "businesses_count": businesses_count,
            "total_revenue": total_revenue,
            "discrepancies_count": discrepancies_count,
            "skip": skip,
            "limit": limit,
            "total_sessions": total_sessions,
            "current_page": current_page,
            "total_pages": total_pages,
        },
    )


@router.get("/sessions/create", response_class=HTMLResponse)
async def create_session_form(request: Request, db: AsyncSession = Depends(get_db)):
    """Form to create new cash session."""
    stmt = select(Business).where(Business.is_active is True).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = list(result.scalars().all())

    return templates.TemplateResponse(
        "create_session.html",
        {
            "request": request,
            "businesses": businesses,
        },
    )


@router.post("/sessions", response_class=HTMLResponse)
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle session creation form submission."""
    form_data = await request.form()

    try:
        session_obj = CashSession(
            business_id=UUID(form_data["business_id"]),
            cashier_name=form_data["cashier_name"],
            initial_cash=Decimal(form_data["initial_cash"]),
            opened_at=(
                datetime.fromisoformat(form_data["opened_at"])
                if form_data.get("opened_at")
                else datetime.now()
            ),
        )
        db.add(session_obj)
        await db.commit()
        await db.refresh(session_obj)

        return RedirectResponse(url=f"/sessions/{session_obj.id}", status_code=303)
    except Exception as e:
        # Reload businesses for error case
        stmt = select(Business).where(Business.is_active is True).order_by(Business.name)
        result = await db.execute(stmt)
        businesses = list(result.scalars().all())

        return templates.TemplateResponse(
            "create_session.html",
            {
                "request": request,
                "error": str(e),
                "businesses": businesses,
            },
        )


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
async def view_session(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """View single session details."""
    stmt = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .where(CashSession.id == UUID(session_id))
    )
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    return templates.TemplateResponse(
        "session_detail.html",
        {
            "request": request,
            "session": session_obj,
        },
    )


@router.get("/sessions/{session_id}/edit", response_class=HTMLResponse)
async def edit_session_form(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Form to edit/close cash session."""
    stmt = (
        select(CashSession)
        .options(joinedload(CashSession.business))
        .where(CashSession.id == UUID(session_id))
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return templates.TemplateResponse(
            "404.html",
            {
                "request": request,
                "message": "Session not found",
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        "edit_session.html",
        {
            "request": request,
            "session": session,
        },
    )


@router.post("/sessions/{session_id}", response_class=HTMLResponse)
async def close_session(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle session close form submission."""
    form_data = await request.form()

    try:
        stmt = (
            select(CashSession)
            .options(joinedload(CashSession.business))
            .where(CashSession.id == UUID(session_id))
        )
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        if not session_obj:
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

        # Update session
        session_obj.status = "CLOSED"
        session_obj.final_cash = Decimal(form_data["final_cash"])
        session_obj.envelope_amount = Decimal(form_data["envelope_amount"])
        session_obj.credit_card_total = Decimal(form_data.get("credit_card_total", 0))
        session_obj.debit_card_total = Decimal(form_data.get("debit_card_total", 0))
        session_obj.bank_transfer_total = Decimal(form_data.get("bank_transfer_total", 0))
        session_obj.expenses = Decimal(form_data.get("expenses", 0))
        session_obj.closing_ticket = form_data.get("closing_ticket")
        session_obj.notes = form_data.get("notes")
        session_obj.closed_at = datetime.now()

        db.add(session_obj)
        await db.commit()

        return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
    except Exception as e:
        # Reload session for error case
        stmt = (
            select(CashSession)
            .options(joinedload(CashSession.business))
            .where(CashSession.id == UUID(session_id))
        )
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        return templates.TemplateResponse(
            "edit_session.html",
            {
                "request": request,
                "session": session_obj,
                "error": str(e),
            },
        )

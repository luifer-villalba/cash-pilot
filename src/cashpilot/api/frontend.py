"""Frontend routes for HTML templates."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from fastapi.responses import RedirectResponse

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession

# Configure templates
templates = Jinja2Templates(directory="src/cashpilot/templates")

router = APIRouter(tags=["frontend"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Dashboard homepage with session list."""
    from sqlalchemy.orm import joinedload

    # Get active sessions with business eager loaded
    stmt_active = select(CashSession).options(joinedload(CashSession.business)).where(
        CashSession.status == "OPEN").limit(10)
    result = await db.execute(stmt_active)
    sessions = result.scalars().all()

    # Get stats
    stmt_count_active = select(CashSession).where(CashSession.status == "OPEN")
    result = await db.execute(stmt_count_active)
    active_sessions_count = len(result.scalars().all())

    stmt_count_business = select(Business).where(Business.is_active == True)
    result = await db.execute(stmt_count_business)
    businesses_count = len(result.scalars().all())

    return templates.TemplateResponse("index.html", {
        "request": request,
        "sessions": sessions,
        "active_sessions_count": active_sessions_count,
        "businesses_count": businesses_count,
        "total_revenue": "2,400,000",
        "discrepancies_count": 0,
    })


@router.get("/sessions/create", response_class=HTMLResponse)
async def create_session_form(request: Request, db: AsyncSession = Depends(get_db)):
    """Form to create new cash session."""
    stmt = select(Business).where(Business.is_active == True).order_by(Business.name)
    result = await db.execute(stmt)
    businesses = list(result.scalars().all())

    print(f"DEBUG: {len(businesses)} businesses found")  # Add this

    return templates.TemplateResponse("create_session.html", {
        "request": request,
        "businesses": businesses,
    })


@router.get("/sessions/{session_id}/edit", response_class=HTMLResponse)
async def edit_session_form(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Form to edit/close cash session."""

    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
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


# Add to src/cashpilot/api/frontend.py

@router.post("/sessions", response_class=HTMLResponse)
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle session creation form submission."""
    form_data = await request.form()

    try:
        session_obj = CashSession(
            business_id=UUID(form_data["business_id"]),
            cashier_name=form_data["cashier_name"],
            initial_cash=Decimal(form_data["initial_cash"]),
            opened_at=datetime.fromisoformat(form_data["opened_at"]) if form_data.get("opened_at") else datetime.now(),
        )
        db.add(session_obj)
        await db.commit()
        await db.refresh(session_obj)

        return RedirectResponse(url=f"/sessions/{session_obj.id}", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("create_session.html", {
            "request": request,
            "error": str(e),
            "businesses": await db.execute(select(Business).where(Business.is_active == True))
        })


@router.put("/sessions/{session_id}", response_class=HTMLResponse)
async def close_session(
        request: Request,
        session_id: str,
        db: AsyncSession = Depends(get_db),
):
    """Handle session close form submission."""

    form_data = await request.form()

    try:
        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        if not session_obj:
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

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
        stmt = select(CashSession).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        return templates.TemplateResponse("edit_session.html", {
            "request": request,
            "session": session_obj,
            "error": str(e),
        })


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
async def view_session(
        request: Request,
        session_id: str,
        db: AsyncSession = Depends(get_db),
):
    """View single session details."""
    from uuid import UUID
    from sqlalchemy.orm import joinedload

    stmt = select(CashSession).options(joinedload(CashSession.business)).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    return templates.TemplateResponse("session_detail.html", {
        "request": request,
        "session": session_obj,
    })


@router.post("/sessions/{session_id}", response_class=HTMLResponse)
async def close_session(
        request: Request,
        session_id: str,
        db: AsyncSession = Depends(get_db),
):
    """Handle session close form submission."""
    from uuid import UUID
    from decimal import Decimal
    from datetime import datetime
    from sqlalchemy.orm import joinedload

    form_data = await request.form()

    try:
        stmt = select(CashSession).options(joinedload(CashSession.business)).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        if not session_obj:
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

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
        stmt = select(CashSession).options(joinedload(CashSession.business)).where(CashSession.id == UUID(session_id))
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        return templates.TemplateResponse("edit_session.html", {
            "request": request,
            "session": session_obj,
            "error": str(e),
        })

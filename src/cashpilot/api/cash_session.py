"""CashSession API endpoints for shift management."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cashpilot.core.db import get_db
from cashpilot.models import Business, CashSession, CashSessionCreate, CashSessionRead, CashSessionUpdate
from cashpilot.models.enums import SessionStatus

router = APIRouter(prefix="/cash-sessions", tags=["cash-sessions"])


@router.get("", response_model=list[CashSessionRead])
async def list_shifts(
        business_id: str | None = None,
        skip: int = 0,
        limit: int = 50,
        db: AsyncSession = Depends(get_db)
):
    """List cash sessions with optional filtering."""
    # Build query
    stmt = select(CashSession)

    if business_id:
        stmt = stmt.where(CashSession.business_id == UUID(business_id))

    stmt = stmt.offset(skip).limit(limit).order_by(CashSession.opened_at.desc())

    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("", response_model=CashSessionRead, status_code=status.HTTP_201_CREATED)
async def open_shift(session: CashSessionCreate, db: AsyncSession = Depends(get_db)):
    """Open a new cash session (shift)."""
    # Verify business exists
    business = await db.execute(
        select(Business).where(Business.id == session.business_id)
    )
    if not business.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Business not found")

    # Check no open session for this business
    open_session = await db.execute(
        select(CashSession).where(
            (CashSession.business_id == session.business_id) &
            (CashSession.status == "OPEN")
        )
    )
    if open_session.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Session already open for this business")

    session_obj = CashSession(**session.model_dump())
    db.add(session_obj)
    await db.flush()
    await db.refresh(session_obj)
    return session_obj


@router.get("/{session_id}", response_model=CashSessionRead)
async def get_shift(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get cash session details."""
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        raise HTTPException(status_code=404, detail="Cash session not found")

    return session_obj


@router.put("/{session_id}", response_model=CashSessionRead)
async def close_shift(
    session_id: str, session: CashSessionUpdate, db: AsyncSession = Depends(get_db)
):
    """Close a cash session (shift)."""
    stmt = select(CashSession).where(CashSession.id == UUID(session_id))
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        raise HTTPException(status_code=404, detail="Cash session not found")

    if session_obj.status != SessionStatus.OPEN:
        raise HTTPException(status_code=400, detail="Session is not open")

    # Set closed_at and status
    session_obj.closed_at = datetime.now()
    session_obj.status = "CLOSED"

    # Apply updates
    update_data = session.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(session_obj, key, value)

    db.add(session_obj)
    await db.flush()
    await db.refresh(session_obj)
    return session_obj

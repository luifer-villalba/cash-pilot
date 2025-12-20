# File: src/cashpilot/api/routes/settings.py
"""User settings endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from cashpilot.api.auth import get_current_user
from cashpilot.api.utils import get_locale, get_translation_function
from cashpilot.core.db import get_db
from cashpilot.core.logging import get_logger
from cashpilot.core.security import hash_password, verify_password
from cashpilot.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

TEMPLATES_DIR = Path("/app/templates")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Add this route before the POST endpoint:
@router.get("/", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Render settings page."""
    locale = get_locale(request)
    _ = get_translation_function(locale)

    error = request.query_params.get("error")
    success = request.query_params.get("success")

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "current_user": current_user,
            "_": _,
            "error": error,
            "success": success,
        },
    )


@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(..., min_length=1),
    new_password: str = Form(..., min_length=8),
    confirm_password: str = Form(..., min_length=8),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for authenticated user."""
    # Validate current password
    if not verify_password(current_password, current_user.hashed_password):
        logger.warning(
            "settings.password_change_failed",
            user_id=str(current_user.id),
            reason="invalid_current_password",
        )
        return RedirectResponse(url="/settings?error=invalid_current_password", status_code=302)

    # Validate new password matches confirmation
    if new_password != confirm_password:
        logger.warning(
            "settings.password_change_failed",
            user_id=str(current_user.id),
            reason="password_mismatch",
        )
        return RedirectResponse(url="/settings?error=password_mismatch", status_code=302)

    # Update password
    current_user.hashed_password = hash_password(new_password)
    await db.commit()

    logger.info(
        "password.changed",
        user_id=str(current_user.id),
        email=current_user.email,
    )

    return RedirectResponse(url="/settings?success=password_changed", status_code=302)

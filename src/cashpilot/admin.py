"""SQLAdmin configuration for CashPilot."""

from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine


class CashPilotAdmin(Admin):
    """Main admin application for CashPilot."""

    def __init__(self, app: FastAPI, engine: AsyncEngine):
        super().__init__(app=app, engine=engine, authentication_backend=None)
        self.title = "CashPilot Admin"
        self.favicon_url = "/static/favicon.ico"


def setup_admin(app: FastAPI, engine) -> Admin:
    """
    Initialize SQLAdmin with CashPilot models.

    Call this in main.py after creating the app.
    """
    admin = CashPilotAdmin(app=app, engine=engine)

    return admin

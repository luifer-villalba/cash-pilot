from fastapi import FastAPI
from cashpilot.api.health import router as health_router

app = FastAPI(title="CashPilot API", version="0.1.0")
app.include_router(health_router, prefix="/health", tags=["health"])
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Literal

from backend.app.auth import router as auth_router

app = FastAPI(title="ARTH API", version="0.11.0")
app.include_router(auth_router)
from backend.app.dashboard import router as dashboard_router
app.include_router(dashboard_router)
from backend.app.ledger import router as ledger_router
app.include_router(ledger_router)
from backend.app.payments import router as payment_router
app.include_router(payment_router)
from backend.app.transactions import router as transaction_router
app.include_router(transaction_router)
from backend.app.services import router as services_router
app.include_router(services_router)
from backend.app.analytics import router as analytics_router
app.include_router(analytics_router)
from backend.app.security import security_middleware
app.middleware('http')(security_middleware)

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from backend.app.auth import engine

@app.get("/ready")
def ready():
    try:
        with engine().connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(text("SELECT id FROM users WHERE 1=0"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable or migration required.")
    return {"status": "ready", "mode": "demo"}

class Health(BaseModel):
    status: Literal["ok"] = "ok"
    mode: Literal["demo"] = "demo"

@app.get("/health", response_model=Health)
def health():
    return Health()

@app.get("/api/v1/demo/dashboard")
def dashboard():
    return {"mode": "demo", "currency": "INR", "balance_minor": 850000,
            "payments_enabled": False}

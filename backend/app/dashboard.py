"""Authenticated synthetic dashboard; no real financial data."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.auth import active_session, get_db, LoginSession, User

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("")
def overview(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    user = db.get(User, session.user_id)
    return {
        "mode": "demo",
        "display_name": user.display_name,
        "currency": "INR",
        "balance_minor": 850000,
        "sample_balance": True,
        "payments_enabled": False,
        "recent_transactions": [],
        "accounts": [],
        "notifications": [],
        "sample_cashflow_minor": [120000, -30000, 98000, -44000, 24000, -62000, 117000, -61000, -70000, 24000, -5000, 125000, -20000, 103000, -47000],
    }

"""Authenticated demo dashboard; balances come from the simulated ledger."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.auth import active_session, get_db, LoginSession, User

from backend.app.ledger import owned_accounts, serialize_account

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("")
def overview(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    user = db.get(User, session.user_id)
    accounts = owned_accounts(db, session.user_id)
    return {
        "mode": "demo",
        "display_name": user.display_name,
        "currency": "INR",
        "balance_minor": sum(a.balance_minor for a in accounts),
        "sample_balance": False,
        "payments_enabled": False,
        "recent_transactions": [],
        "accounts": [serialize_account(a) for a in accounts],
        "notifications": [],
        "sample_cashflow_minor": [120000, -30000, 98000, -44000, 24000, -62000, 117000, -61000, -70000, 24000, -5000, 125000, -20000, 103000, -47000],
    }

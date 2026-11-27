"""Authenticated demo dashboard; balances come from the simulated ledger."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.auth import active_session, get_db, LoginSession, User

from backend.app.ledger import owned_accounts, serialize_account

from backend.app.transactions import history
from backend.app.analytics import summary_for, utc_now

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("")
def overview(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    user = db.get(User, session.user_id)
    accounts = owned_accounts(db, session.user_id)
    insights = summary_for(db, session.user_id, utc_now().strftime('%Y-%m'))
    return {
        "mode": "demo",
        "display_name": user.display_name,
        "currency": "INR",
        "balance_minor": sum(a.balance_minor for a in accounts),
        "sample_balance": False,
        "payments_enabled": False,  # real payments are never enabled
        "demo_payments_enabled": bool(accounts),
        "recent_transactions": history(db, session.user_id, limit=5)["items"],
        "accounts": [serialize_account(a) for a in accounts],
        "notifications": [],
        "cashflow_minor": insights["daily_net_minor"],
        "cashflow_month": insights["month"],
        "sample_cashflow_minor": insights["daily_net_minor"],  # compatibility alias
    }

"""Owner-scoped, read-only history of committed demo ledger entries."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, aliased

from backend.app.auth import LoginSession, active_session, get_db, fail
from backend.app.ledger import Account, Journal
from backend.app.payments import Payment

router = APIRouter(prefix="/api/v1/transactions", tags=["demo transactions"])
Kind = Literal["all", "opening", "internal", "sent", "received", "service", "reward"]

def visible_query(owner):
    source = aliased(Account)
    target = aliased(Account)
    return (select(Journal, Payment, source, target)
            .join(source, Journal.debit_account_id == source.id)
            .join(target, Journal.credit_account_id == target.id)
            .outerjoin(Payment, Payment.journal_id == Journal.id)
            .where(or_(source.owner_id == owner, target.owner_id == owner))), source, target

def render(row, owner):
    journal, payment, source, target = row
    if payment:
        kind = "sent" if payment.sender_id == owner else "received"
        change = -journal.amount_minor if kind == "sent" else journal.amount_minor
    elif journal.idempotency_key.startswith("svc:"):
        kind, change = "service", -journal.amount_minor
    elif journal.idempotency_key.startswith("reward:"):
        kind, change = "reward", journal.amount_minor
    elif journal.kind == "opening":
        kind, change = "opening", journal.amount_minor
    else:
        kind, change = "internal", 0
    return {
        "id": journal.id, "payment_reference": payment.id if payment else None,
        "kind": kind, "status": "completed", "currency": "INR",
        "amount_minor": journal.amount_minor, "balance_change_minor": change,
        "created_at": journal.created_at, "simulated": True,
        "source": source.kind if source.owner_id == owner and source.kind != "funding" else
                  ("demo reward funding" if kind == "reward" else "demo funding" if kind == "opening" else "another demo account"),
        "destination": "demo service clearing" if kind == "service" else target.kind if target.owner_id == owner else "another demo account",
    }

def history(db, owner, kind="all", limit=20, offset=0, since=None, until=None):
    query, source, target = visible_query(owner)
    filters = {
        "opening": and_(Payment.id.is_(None), Journal.kind == "opening"),
        "internal": and_(Payment.id.is_(None), Journal.kind == "internal",
                         ~Journal.idempotency_key.startswith("svc:"), ~Journal.idempotency_key.startswith("reward:")),
        "service": Journal.idempotency_key.startswith("svc:"),
        "reward": Journal.idempotency_key.startswith("reward:"),
        "sent": Payment.sender_id == owner,
        "received": Payment.recipient_id == owner,
    }
    if kind != "all":
        query = query.where(filters[kind])
    if since is not None:
        query = query.where(Journal.created_at >= since)
    if until is not None:
        query = query.where(Journal.created_at <= until)
    rows = db.execute(query.order_by(Journal.created_at.desc(), Journal.id.desc())
                      .offset(offset).limit(limit+1)).all()
    return {"mode": "demo", "items": [render(row, owner) for row in rows[:limit]],
            "next_offset": offset + limit if len(rows) > limit else None}

@router.get("")
def list_transactions(kind: Kind = "all", limit: int = Query(20, ge=1, le=100),
                      offset: int = Query(0, ge=0, le=100000),
                      since: int | None = Query(None, ge=0), until: int | None = Query(None, ge=0),
                      session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    if since is not None and until is not None and since > until:
        fail(400, "Invalid date range.")
    return history(db, session.user_id, kind, limit, offset, since, until)

class Lookup(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=96)

@router.post("/payment-lookup")
def lookup(data: Lookup, session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    query, _, _ = visible_query(session.user_id)
    row = db.execute(query.where(Payment.sender_id == session.user_id,
        Journal.idempotency_key == "pay:" + data.idempotency_key)).one_or_none()
    if row is None:
        # Absence is NOT evidence that a request still in flight failed.
        return {"status": "unknown", "simulated": True, "transaction": None}
    return {"status": "completed", "simulated": True, "transaction": render(row, session.user_id)}

@router.get("/{transaction_id}")
def detail(transaction_id: str, session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    query, _, _ = visible_query(session.user_id)
    row = db.execute(query.where(Journal.id == transaction_id)).one_or_none()
    if row is None:
        fail(404, "Demo transaction not found.")
    return render(row, session.user_id)

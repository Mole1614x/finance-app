"""Fictional utility catalog, ledger-backed purchases and deterministic demo cashback."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint, select, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.app.auth import Base, LoginSession, active_session, get_db, fail, now
from backend.app.ledger import Account, Journal, lock_owner, owned_accounts, post_pair

router = APIRouter(prefix="/api/v1/services", tags=["demo services"])
CATALOG = {
    "mobile-199": ("Mobile recharge", "Demo Mobile", 19900, "recharge"),
    "mobile-399": ("Mobile recharge", "Demo Mobile", 39900, "recharge"),
    "electricity": ("Electricity", "Demo Electricity", 125000, "bill"),
    "water": ("Water", "Demo Water", 35000, "bill"),
    "gas": ("Gas", "Demo Gas", 85000, "bill"),
    "internet": ("Internet", "Demo Internet", 69900, "bill"),
}

class ServiceOrder(Base):
    __tablename__ = "demo_service_orders"
    __table_args__ = (UniqueConstraint("owner_id", "request_key"),
                      UniqueConstraint("owner_id", "sku", "bill_cycle"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    sku: Mapped[str] = mapped_column(String(32))
    request_key: Mapped[str] = mapped_column(String(96))
    bill_cycle: Mapped[str | None] = mapped_column(String(7), nullable=True)
    journal_id: Mapped[str] = mapped_column(ForeignKey("ledger_journal.id"), unique=True)
    reward_journal_id: Mapped[str] = mapped_column(ForeignKey("ledger_journal.id"), unique=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    cashback_minor: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger)

class Purchase(BaseModel):
    sku: str = Field(min_length=1, max_length=32)
    bill_cycle: str | None = Field(default=None, pattern=r"^[0-9]{4}-[0-9]{2}$")

def cycle_now():
    return datetime.now(timezone.utc).strftime("%Y-%m")

def cashback(amount):
    return min(amount * 2 // 100, 2000)

def item(sku):
    category, provider, amount, kind = CATALOG[sku]
    return {"sku": sku, "category": category, "provider": provider,
            "amount_minor": amount, "kind": kind, "cashback_minor": cashback(amount)}

def serialize(order):
    return {**item(order.sku), "id": order.id, "bill_cycle": order.bill_cycle,
            "amount_minor": order.amount_minor, "cashback_minor": order.cashback_minor,
            "transaction_id": order.journal_id, "reward_transaction_id": order.reward_journal_id,
            "created_at": order.created_at, "status": "completed", "simulated": True}

@router.get("/catalog")
def catalog(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    cycle = cycle_now()
    paid = set(db.scalars(select(ServiceOrder.sku).where(
        ServiceOrder.owner_id == session.user_id, ServiceOrder.bill_cycle == cycle)).all())
    products = []
    for sku in CATALOG:
        product = item(sku)
        bill = product["kind"] == "bill"
        products.append({**product, "bill_cycle": cycle if bill else None,
                         "paid": sku in paid if bill else False,
                         "due_date": cycle + "-28" if bill else None})
    return {"simulated": True, "currency": "INR", "items": products}

@router.post("/purchase")
def purchase(data: Purchase, idempotency_key: str = Header(min_length=8, max_length=96),
             session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    owner = session.user_id
    lock_owner(db, owner)
    prior = db.scalar(select(ServiceOrder).where(ServiceOrder.owner_id == owner,
                                                ServiceOrder.request_key == idempotency_key))
    if prior:
        if (prior.sku, prior.bill_cycle) != (data.sku, data.bill_cycle):
            fail(409, "Idempotency key already used with different parameters.")
        result = serialize(prior)
        db.commit()
        return result
    if data.sku not in CATALOG:
        fail(404, "Fictional service not found.")
    product = item(data.sku)
    if product["kind"] == "bill":
        if data.bill_cycle != cycle_now():
            fail(409, "Refresh the current demo bill before paying.")
        paid = db.scalar(select(ServiceOrder).where(ServiceOrder.owner_id == owner,
            ServiceOrder.sku == data.sku, ServiceOrder.bill_cycle == data.bill_cycle))
        if paid:
            fail(409, "This demo bill has already been paid.")
    elif data.bill_cycle is not None:
        fail(400, "Recharge has no bill cycle.")
    accounts = {a.kind: a for a in owned_accounts(db, owner, include_funding=True)}
    if not {"checking", "funding"} <= accounts.keys():
        fail(409, "Initialize demo accounts first.")
    amount, reward = product["amount_minor"], product["cashback_minor"]
    charge = post_pair(db, owner, accounts["checking"], accounts["funding"],
                       amount, "internal", "svc:" + idempotency_key)
    bonus = post_pair(db, owner, accounts["funding"], accounts["checking"],
                      reward, "internal", "reward:" + idempotency_key)
    order = ServiceOrder(id=str(uuid4()), owner_id=owner, sku=data.sku,
        request_key=idempotency_key, bill_cycle=data.bill_cycle, journal_id=charge.id,
        reward_journal_id=bonus.id, amount_minor=amount, cashback_minor=reward, created_at=now())
    db.add(order)
    db.flush()
    result = serialize(order)
    db.commit()
    return result

@router.get("/orders")
def orders(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
           session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    rows = db.scalars(select(ServiceOrder).where(ServiceOrder.owner_id == session.user_id)
        .order_by(ServiceOrder.created_at.desc(), ServiceOrder.id.desc()).offset(offset).limit(limit+1)).all()
    return {"items": [serialize(row) for row in rows[:limit]],
            "next_offset": offset+limit if len(rows) > limit else None, "simulated": True}

@router.get("/rewards")
def rewards(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    total = db.scalar(select(func.coalesce(func.sum(ServiceOrder.cashback_minor), 0))
                      .where(ServiceOrder.owner_id == session.user_id))
    return {"earned_minor": total, "currency": "INR", "simulated": True,
            "credited_to": "checking", "offer": "2% demo cashback, capped at INR 20 per order"}

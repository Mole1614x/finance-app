"""INR-only simulated accounts and paired journal postings. No real money."""
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, UniqueConstraint, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column
from backend.app.auth import Base, User, LoginSession, active_session, get_db, fail, now

router = APIRouter(prefix="/api/v1/accounts", tags=["demo accounts"])
STARTING_MINOR = 850000
MAX_AMOUNT = 100000000

class Account(Base):
    __tablename__ = "ledger_accounts"
    __table_args__ = (
        UniqueConstraint("owner_id", "kind"),
        CheckConstraint("kind IN ('checking','savings','funding')"),
        CheckConstraint("kind = 'funding' OR balance_minor >= 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    balance_minor: Mapped[int] = mapped_column(BigInteger, default=0)

class Journal(Base):
    """Each row represents two equal and opposite postings in paise."""
    __tablename__ = "ledger_journal"
    __table_args__ = (
        UniqueConstraint("owner_id", "idempotency_key"),
        CheckConstraint("amount_minor > 0"),
        CheckConstraint("debit_account_id <> credit_account_id"),
        CheckConstraint("kind IN ('opening','internal')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    debit_account_id: Mapped[str] = mapped_column(ForeignKey("ledger_accounts.id"))
    credit_account_id: Mapped[str] = mapped_column(ForeignKey("ledger_accounts.id"))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(12))
    idempotency_key: Mapped[str] = mapped_column(String(104))
    created_at: Mapped[int] = mapped_column(BigInteger)

class Move(BaseModel):
    source: Literal["checking", "savings"]
    destination: Literal["checking", "savings"]
    amount_minor: int = Field(strict=True, gt=0, le=MAX_AMOUNT)

def lock_owner(db, owner):
    # Write lock serializes mutations for one owner before reading ledger state.
    db.execute(update(User).where(User.id == owner).values(id=User.id))

def owned_accounts(db, owner, include_funding=False):
    query = select(Account).where(Account.owner_id == owner)
    if not include_funding:
        query = query.where(Account.kind != "funding")
    return db.scalars(query.order_by(Account.kind)).all()

def serialize_account(account):
    return {"id": account.id, "kind": account.kind,
            "currency": "INR", "balance_minor": account.balance_minor, "simulated": True}

def serialize_journal(row):
    return {"id": row.id, "source_account_id": row.debit_account_id,
            "destination_account_id": row.credit_account_id, "amount_minor": row.amount_minor,
            "currency": "INR", "kind": row.kind, "created_at": row.created_at,
            "status": "completed", "simulated": True}

def post_pair(db, owner, source, destination, amount, kind, key):
    # Caller holds owner lock and commits balance updates and journal atomically.
    if source.owner_id != owner or destination.owner_id != owner or source.id == destination.id or amount <= 0:
        fail(400, "Invalid ledger posting.")
    if source.kind != "funding" and source.balance_minor < amount:
        fail(409, "Insufficient demo funds.")
    source.balance_minor -= amount
    destination.balance_minor += amount
    row = Journal(id=str(uuid4()), owner_id=owner, debit_account_id=source.id,
                  credit_account_id=destination.id, amount_minor=amount, kind=kind,
                  idempotency_key=key, created_at=now())
    db.add(row)
    db.flush()
    return row

@router.get("")
def list_accounts(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    return {"mode": "demo", "accounts": [serialize_account(a) for a in owned_accounts(db, session.user_id)]}

@router.post("/initialize")
def initialize(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    owner = session.user_id
    lock_owner(db, owner)
    existing = owned_accounts(db, owner, include_funding=True)
    if not existing:
        accounts = {kind: Account(id=str(uuid4()), owner_id=owner, kind=kind, balance_minor=0)
                    for kind in ("checking", "savings", "funding")}
        db.add_all(accounts.values())
        db.flush()
        post_pair(db, owner, accounts["funding"], accounts["checking"],
                  STARTING_MINOR, "opening", "opening")
    response = {"mode": "demo", "accounts": [serialize_account(a) for a in owned_accounts(db, owner)]}
    db.commit()
    return response

@router.post("/move")
def move(data: Move, idempotency_key: str = Header(min_length=8, max_length=96),
         session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    owner = session.user_id
    if data.source == data.destination:
        fail(400, "Choose different accounts.")
    lock_owner(db, owner)
    accounts = {a.kind: a for a in owned_accounts(db, owner)}
    if data.source not in accounts or data.destination not in accounts:
        fail(409, "Initialize demo accounts first.")
    source, destination = accounts[data.source], accounts[data.destination]
    key = "move:" + idempotency_key
    existing = db.scalar(select(Journal).where(Journal.owner_id == owner, Journal.idempotency_key == key))
    if existing:
        if (existing.debit_account_id, existing.credit_account_id, existing.amount_minor) != (source.id, destination.id, data.amount_minor):
            fail(409, "Idempotency key already used with different parameters.")
        response = serialize_journal(existing)
        db.commit()
        return response
    row = post_pair(db, owner, source, destination, data.amount_minor, "internal", key)
    response = serialize_journal(row)
    db.commit()
    return response

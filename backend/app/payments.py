"""Peer payments for the ARTH demo network only; never creates UPI instructions."""
import re
from uuid import uuid4

import qrcode
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from backend.app.auth import Base, LoginSession, active_session, get_db, fail
from backend.app.ledger import Account, Journal, MAX_AMOUNT, lock_owner, post_pair

router = APIRouter(prefix="/api/v1/payments", tags=["demo payments"])
PREFIX = "arth-demo:"
ID_PATTERN = re.compile(r"arth-demo:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

class Payment(Base):
    __tablename__ = "demo_payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    journal_id: Mapped[str] = mapped_column(ForeignKey("ledger_journal.id"), unique=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

class Recipient(BaseModel):
    payment_id: str = Field(min_length=46, max_length=46)

class Send(Recipient):
    amount_minor: int = Field(strict=True, gt=0, le=MAX_AMOUNT)

def account_for(db, owner):
    return db.scalar(select(Account).where(Account.owner_id == owner, Account.kind == "checking"))

def recipient_account(db, value):
    if not ID_PATTERN.fullmatch(value):
        fail(400, "Only ARTH demo payment identifiers are supported.")
    account = db.get(Account, value[len(PREFIX):])
    if not account or account.kind != "checking":
        fail(404, "Demo recipient not found.")
    return account

def receipt(payment, journal):
    return {"id": payment.id, "status": "completed", "simulated": True,
            "currency": "INR", "amount_minor": journal.amount_minor,
            "recipient_payment_id": PREFIX + journal.credit_account_id,
            "created_at": journal.created_at}

@router.get("/receive")
def receive(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    account = account_for(db, session.user_id)
    if not account:
        fail(409, "Initialize demo accounts first.")
    identifier = PREFIX + account.id
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(identifier)
    qr.make(fit=True)
    return {"payment_id": identifier, "qr_matrix": qr.get_matrix(), "simulated": True}

@router.post("/resolve")
def resolve(data: Recipient, session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    account = recipient_account(db, data.payment_id)
    if account.owner_id == session.user_id:
        fail(400, "Cannot pay your own identifier.")
    # No real identity or private profile information is exposed.
    return {"payment_id": data.payment_id, "simulated": True}

@router.post("/send")
def send(data: Send, idempotency_key: str = Header(min_length=8, max_length=96),
         session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    sender = session.user_id
    target = recipient_account(db, data.payment_id)
    recipient = target.owner_id
    if sender == recipient:
        fail(400, "Cannot pay your own identifier.")
    # All mutations use the same per-owner locks. Acquire in sorted order
    # to avoid deadlock for simultaneous opposite-direction payments.
    for owner in sorted((sender, recipient)):
        lock_owner(db, owner)
    db.expire_all()
    source = account_for(db, sender)
    target = recipient_account(db, data.payment_id)
    if not source:
        fail(409, "Initialize demo accounts first.")
    key = "pay:" + idempotency_key
    existing = db.scalar(select(Journal).where(Journal.owner_id == sender, Journal.idempotency_key == key))
    if existing:
        if (existing.debit_account_id, existing.credit_account_id, existing.amount_minor) != (source.id, target.id, data.amount_minor):
            fail(409, "Idempotency key already used with different parameters.")
        payment = db.scalar(select(Payment).where(Payment.journal_id == existing.id))
        result = receipt(payment, existing)
        db.commit()
        return result
    journal = post_pair(db, sender, source, target, data.amount_minor, "internal", key, peer=True)
    payment = Payment(id=str(uuid4()), journal_id=journal.id, sender_id=sender, recipient_id=recipient)
    db.add(payment)
    db.flush()
    result = receipt(payment, journal)
    db.commit()
    return result

@router.get("/{payment_id}")
def status(payment_id: str, session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if not payment or session.user_id not in (payment.sender_id, payment.recipient_id):
        fail(404, "Demo payment not found.")
    return receipt(payment, db.get(Journal, payment.journal_id))

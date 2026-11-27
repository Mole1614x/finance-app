"""Frozen schema baseline at PR 10; never imports mutable application models."""
from alembic import op
from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

revision = "0001_demo_baseline"
down_revision = None
branch_labels = None
depends_on = None

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str] = mapped_column(String(80), default="Demo user")

class Challenge(Base):
    __tablename__ = "auth_challenges"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires: Mapped[int] = mapped_column(Integer)
    code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)

class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires: Mapped[int] = mapped_column(Integer)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

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

class Payment(Base):
    __tablename__ = "demo_payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    journal_id: Mapped[str] = mapped_column(ForeignKey("ledger_journal.id"), unique=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

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

class Budget(Base):
    __tablename__ = "demo_monthly_budgets"
    __table_args__ = (CheckConstraint("limit_minor > 0"),)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    limit_minor: Mapped[int] = mapped_column(BigInteger)

class SavingsGoal(Base):
    __tablename__ = "demo_savings_goals"
    __table_args__ = (CheckConstraint("target_minor > 0"),)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    title: Mapped[str] = mapped_column(String(60))
    target_minor: Mapped[int] = mapped_column(BigInteger)

def upgrade():
    Base.metadata.create_all(op.get_bind(), checkfirst=False)

def downgrade():
    Base.metadata.drop_all(op.get_bind(), checkfirst=False)

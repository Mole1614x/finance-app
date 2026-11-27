"""Owner-scoped demo financial insights and opt-in aggregate explanations."""
from calendar import monthrange
from collections import defaultdict
from datetime import datetime, timezone
from statistics import median
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.app.auth import Base, LoginSession, active_session, get_db, fail
from backend.app.ledger import Journal, lock_owner, owned_accounts
from backend.app.transactions import visible_query, render
from backend.app.services import ServiceOrder, CATALOG
from backend.app.ai_assistant import explain
from backend.app.anomaly_model import review as ml_review

router = APIRouter(prefix="/api/v1/analytics", tags=["demo financial insights"])
MAX_TARGET = 10000000000

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

class BudgetInput(BaseModel):
    month: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}$")
    limit_minor: int = Field(strict=True, gt=0, le=MAX_TARGET)

class GoalInput(BaseModel):
    title: str = Field(min_length=1, max_length=60)
    target_minor: int = Field(strict=True, gt=0, le=MAX_TARGET)

def utc_now():
    return datetime.now(timezone.utc)

def month_bounds(month):
    try:
        if len(month) != 7 or month[4] != "-":
            raise ValueError()
        year, number = map(int, month.split("-"))
        if not 2000 <= year <= 2099:
            raise ValueError()
        start = datetime(year, number, 1, tzinfo=timezone.utc)
        days = monthrange(year, number)[1]
        return int(start.timestamp()), int(start.timestamp()) + days*86400, days
    except (TypeError, ValueError):
        fail(400, "Use a valid month in YYYY-MM format (2000–2099).")

def category_for(row, service_categories):
    if row["kind"] == "service":
        return service_categories.get(row["id"], "Other services")
    if row["kind"] == "sent":
        return "Peer payments"
    return None

def anomaly_flags(expenses):
    """Robust historical-size heuristic; not a trained fraud model."""
    if len(expenses) < 5:
        return []
    flags = []
    prior = []
    for item in expenses:
        amount = item["amount_minor"]
        if len(prior) >= 4:
            baseline = median(prior[-30:])
            if amount >= 100000 and amount >= 3*baseline:
                flags.append({"transaction_id": item["id"], "amount_minor": amount,
                              "reason": "At least three times the median of preceding expenses",
                              "method": "rule-based", "fraud_confirmed": False})
        prior.append(amount)
    return flags[-10:]

def summary_for(db, owner, month, *, current=None, include_ml=False):
    current = current or utc_now()
    start, end, days = month_bounds(month)
    current_month = current.strftime("%Y-%m")
    if month > current_month:
        fail(400, "Future month has no spending history.")
    service_categories = {}
    for order in db.scalars(select(ServiceOrder).where(ServiceOrder.owner_id == owner,
            ServiceOrder.created_at >= start, ServiceOrder.created_at < end)):
        service_categories[order.journal_id] = CATALOG.get(order.sku, ("Other services",))[0]
    query, _, _ = visible_query(owner)
    result = db.execute(query.where(Journal.created_at >= start, Journal.created_at < end)
                        .order_by(Journal.created_at, Journal.id).execution_options(yield_per=500))
    categories = defaultdict(int)
    income = spending = opening = cashback = 0
    daily = [0]*days
    expenses = []
    for raw in result:
        row = render(raw, owner)
        kind, change = row["kind"], row["balance_change_minor"]
        index = (row["created_at"] - start)//86400
        daily[index] += change
        if kind == "opening":
            opening += change
        elif kind == "reward":
            cashback += change
        elif kind == "received":
            income += change
        elif change < 0:
            spending -= change
            categories[category_for(row, service_categories) or "Other"] -= change
            expenses.append(row)
    budget = db.get(Budget, (owner, month))
    limit = budget.limit_minor if budget else None
    # Use complete UTC days for a current-month forecast, excluding partial today.
    elapsed = current.day - 1 if month == current_month else days
    forecast = None
    if month == current_month and elapsed >= 7:
        completed_spend = sum(r["amount_minor"] for r in expenses
                              if r["created_at"] < start + elapsed*86400)
        forecast = max(spending, completed_spend*days//elapsed)
    return {"mode": "demo", "month": month, "currency": "INR",
            "received_minor": income, "spent_minor": spending, "cashback_minor": cashback,
            "opening_funds_minor": opening, "net_change_minor": income+cashback+opening-spending,
            "categories": [{"category": k, "amount_minor": v} for k, v in sorted(categories.items())],
            "daily_net_minor": daily, "budget_limit_minor": limit,
            "budget_remaining_minor": limit-spending if limit is not None else None,
            "forecast_spending_minor": forecast, "forecast_method": "linear daily spending extrapolation",
            "anomalies": anomaly_flags(expenses),
            **({"ml_review": ml_review(expenses)} if include_ml else {})}

@router.get("/summary")
def summary(month: str | None = Query(None, max_length=7),
            session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    return summary_for(db, session.user_id, month or utc_now().strftime("%Y-%m"))

@router.get("/risk")
def risk_review(month: str | None = Query(None, max_length=7),
                session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    info = summary_for(db, session.user_id, month or utc_now().strftime("%Y-%m"), include_ml=True)
    return {"mode": "demo", "month": info["month"], "currency": "INR",
            "rule_flags": info["anomalies"], **info["ml_review"]}

@router.put("/budget")
def set_budget(data: BudgetInput, session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    month_bounds(data.month)
    owner = session.user_id
    lock_owner(db, owner)
    row = db.get(Budget, (owner, data.month))
    if row:
        row.limit_minor = data.limit_minor
    else:
        db.add(Budget(owner_id=owner, month=data.month, limit_minor=data.limit_minor))
    db.commit()
    return {"month": data.month, "limit_minor": data.limit_minor, "simulated": True}

def goal_for(db, owner):
    goal = db.get(SavingsGoal, owner)
    saved = next((a.balance_minor for a in owned_accounts(db, owner) if a.kind == "savings"), 0)
    return {"simulated": True, "title": goal.title if goal else None,
            "target_minor": goal.target_minor if goal else None, "saved_minor": saved,
            "remaining_minor": max(0, goal.target_minor-saved) if goal else None,
            "achieved": bool(goal and saved >= goal.target_minor)}

@router.get("/goal")
def get_goal(session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    return goal_for(db, session.user_id)

@router.put("/goal")
def set_goal(data: GoalInput, session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    title = data.title.strip()
    if not title:
        fail(400, "Goal title cannot be blank.")
    owner = session.user_id
    lock_owner(db, owner)
    row = db.get(SavingsGoal, owner)
    if row:
        row.title, row.target_minor = title, data.target_minor
    else:
        db.add(SavingsGoal(owner_id=owner, title=title, target_minor=data.target_minor))
    db.commit()
    return goal_for(db, owner)

class AssistantInput(BaseModel):
    topic: Literal["spending", "budget", "savings", "risk"]
    allow_external_ai: bool = Field(default=False, strict=True)

@router.post("/assistant")
def assistant(data: AssistantInput, session: LoginSession = Depends(active_session), db: Session = Depends(get_db)):
    owner = session.user_id
    info = summary_for(db, owner, utc_now().strftime("%Y-%m"), include_ml=data.topic == "risk")
    if data.topic == "spending":
        answer = {"spent_minor": info["spent_minor"], "categories": info["categories"]}
    elif data.topic == "budget":
        answer = {"limit_minor": info["budget_limit_minor"], "remaining_minor": info["budget_remaining_minor"]}
    elif data.topic == "savings":
        answer = goal_for(db, owner)
    else:
        answer = {"flags": info["anomalies"], "ml_review": info["ml_review"],
                  "note": "Rule-based and ML review flags are not proof of fraud."}
    # Release the read transaction before any bounded external call.
    db.rollback()
    generated = explain(data.topic, answer, data.allow_external_ai)
    return {"mode": "demo", "topic": data.topic, "answer": answer, **generated}

"""Native financial insights based on committed demo ledger transactions."""
from datetime import datetime, timezone
from uuid import uuid4
from kivy.uix.switch import Switch
from kivy.metrics import dp
try:
    from .onboarding_ui import label, field, button
    from .dashboard_data import inr
    from .payment_data import parse_amount
except ImportError:
    from onboarding_ui import label, field, button
    from dashboard_data import inr
    from payment_data import parse_amount

def money(value):
    return inr(value) if value is not None else "Not set / unavailable"

def install_analytics_screens(manager, make, nav, go, run):
    screen, outer, body = make("analytics", "Financial insights")
    body.add_widget(label("Simulated transactions only. Month boundaries use UTC.", 60))
    month = field("Month YYYY-MM")
    month.text = datetime.now(timezone.utc).strftime("%Y-%m")
    body.add_widget(month)
    report = label("", 220)
    categories = label("", 220)
    status = label("", 60)
    for widget in (report, categories, status):
        body.add_widget(widget)
    budget = field("Monthly spending budget in INR")
    body.add_widget(budget)

    def show(data):
        report.text = "\n".join([
            "Received: " + money(data["received_minor"]),
            "Spent: " + money(data["spent_minor"]),
            "Cashback: " + money(data["cashback_minor"]),
            "Opening funds: " + money(data["opening_funds_minor"]),
            "Budget: " + money(data["budget_limit_minor"]),
            "Budget remaining: " + money(data["budget_remaining_minor"]),
            "Estimated month spending: " + money(data["forecast_spending_minor"]),
        ])
        categories.text = "\n".join(r["category"] + ": " + money(r["amount_minor"]) for r in data["categories"]) or "No expenses."
    def load():
        value = month.text.strip()
        report.text = categories.text = ""
        run(lambda: manager.auth_client.insights(value), show, status)
    def save_budget():
        try:
            amount = parse_amount(budget.text)
        except ValueError as exc:
            status.text = str(exc)
            return
        value = month.text.strip()
        def saved(_):
            budget.text = ""
            load()
        run(lambda: manager.auth_client.set_budget(value, amount), saved, status)
    body.add_widget(button("Save budget", save_budget))
    body.add_widget(button("Refresh / select month", load, True))
    body.add_widget(button("Savings goal", lambda: go("savings"), True))
    body.add_widget(button("Financial assistant", lambda: go("assistant"), True))
    body.add_widget(button("Home", lambda: go("home"), True))
    screen.bind(on_pre_enter=lambda *_: load())
    nav(outer)

    savings, outer, body = make("savings", "Savings goal")
    body.add_widget(label("One demo goal tracks your existing savings account balance. It does not reserve funds.", 100))
    goal_report = label("", 120)
    title = field("Goal name")
    target = field("Target in INR")
    transfer = field("Move INR from checking to savings")
    goal_status = label("", 72)
    for widget in (goal_report, title, target, transfer, goal_status):
        body.add_widget(widget)
    pending = {}
    def show_goal(data):
        goal_report.text = (data["title"] or "No goal yet") + "\nSaved: " + money(data["saved_minor"]) + "\nTarget: " + money(data["target_minor"]) + "\nRemaining: " + money(data["remaining_minor"])
    def load_goal():
        goal_report.text = ""
        run(manager.auth_client.goal, show_goal, goal_status)
    def save_goal():
        try:
            value = parse_amount(target.text)
        except ValueError as exc:
            goal_status.text = str(exc)
            return
        name = title.text
        run(lambda: manager.auth_client.set_goal(name, value), show_goal, goal_status)
    def move_savings():
        try:
            amount = parse_amount(transfer.text)
        except ValueError as exc:
            goal_status.text = str(exc)
            return
        token = manager.auth_client.access
        if pending.get("token") != token:
            pending.clear()
        if pending and pending["amount"] != amount:
            goal_status.text = "Resolve the earlier transfer using its original amount first."
            return
        if not pending:
            pending.update(token=token, amount=amount, key=str(uuid4()))
        key = pending["key"]
        def done(_):
            pending.clear()
            transfer.text = ""
            load_goal()
        run(lambda: manager.auth_client.move("checking", "savings", amount, key), done, goal_status)
    body.add_widget(button("Save goal", save_goal))
    body.add_widget(button("Confirm / retry demo savings transfer", move_savings))
    body.add_widget(label("Retry an uncertain transfer with the same amount and session. Restart recovery is not supported.", 80))
    body.add_widget(button("Refresh", load_goal, True))
    body.add_widget(button("Home", lambda: go("home"), True))
    savings.bind(on_pre_enter=lambda *_: load_goal())
    nav(outer)

    assistant, outer, body = make("assistant", "Financial assistant")
    body.add_widget(label("Local assistant by default. Optional Gemini explanations send fictional aggregate amounts and fixed categories only to Google. No real data or financial advice.", 120))
    body.add_widget(label("Allow Gemini for this screen (optional)", 48))
    consent = Switch(active=False, size_hint_y=None, height=dp(48))
    body.add_widget(consent)
    answer = label("", 240)
    error = label("", 60)
    body.add_widget(answer)
    body.add_widget(error)
    def ask(topic):
        allow_external = consent.active
        answer.text = ""
        def show_answer(data):
            info = data["answer"]
            if topic == "spending":
                answer.text = "Spent this month: " + money(info["spent_minor"]) + "\n" + "\n".join(x["category"] + ": " + money(x["amount_minor"]) for x in info["categories"])
            elif topic == "budget":
                answer.text = "Budget: " + money(info["limit_minor"]) + "\nRemaining: " + money(info["remaining_minor"])
            elif topic == "savings":
                answer.text = "Saved: " + money(info["saved_minor"]) + "\nTarget: " + money(info["target_minor"])
            else:
                answer.text = info["note"] + "\n" + ("\n".join(money(x["amount_minor"]) + " — review suggested" for x in info["flags"]) or "No flags from the current heuristic.")
            if data.get("engine") == "gemini":
                answer.text += "\n\nGemini explanation (may be inaccurate):\n" + data["explanation"]
            elif allow_external:
                answer.text += "\n\nGemini unavailable; local facts shown."
        run(lambda: manager.auth_client.assistant(topic, allow_external), show_answer, error)
    for topic, name in (("spending", "Spending summary"), ("budget", "Budget status"), ("savings", "Savings progress"), ("risk", "Unusual spending")):
        body.add_widget(button(name, lambda topic=topic: ask(topic)))
    body.add_widget(button("Back home", lambda: go("home"), True))
    def reset_assistant(*_):
        answer.text = error.text = ""
        consent.active = False
    assistant.bind(on_leave=reset_assistant)
    nav(outer)

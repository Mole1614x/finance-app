"""Authenticated transaction history, filters and receipt view."""
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.core.clipboard import Clipboard
try:
    from .onboarding_ui import label, button
    from .transaction_data import row_label, receipt_text
except ImportError:
    from onboarding_ui import label, button
    from transaction_data import row_label, receipt_text

def install_transaction_screens(manager, make, nav, go, run):
    screen, outer, body = make("transactions", "Transaction history")
    body.add_widget(label("Completed demo transactions only. No real money.", 56))
    names = {"All": "all", "Opening funds": "opening", "Internal transfers": "internal",
             "Money sent": "sent", "Money received": "received", "Bills / recharge": "service", "Cashback": "reward"}
    selector = Spinner(text="All", values=list(names), size_hint_y=None, height=dp(48))
    body.add_widget(selector)
    items = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
    items.bind(minimum_height=items.setter("height"))
    body.add_widget(items)
    status = label("", 60)
    body.add_widget(status)
    state = {"next": None}
    detail, detail_outer, detail_body = make("transaction_receipt", "Demo receipt")
    detail_label = label("", 300)
    detail_body.add_widget(detail_label)
    copied = label("", 40)
    detail_body.add_widget(copied)
    def copy_receipt():
        if detail_label.text:
            Clipboard.copy(detail_label.text)
            copied.text = "Demo receipt copied."
    detail_body.add_widget(button("Copy receipt", copy_receipt))
    detail_body.add_widget(button("Back to history", lambda: go("transactions"), True))
    nav(detail_outer)

    def show_detail(reference):
        def ready(data):
            detail_label.text = receipt_text(data)
            copied.text = ""
            go("transaction_receipt")
        run(lambda: manager.auth_client.transaction(reference), ready, status)

    def load(offset=0):
        kind = names[selector.text]
        def render(data):
            if selector.text != next(k for k, v in names.items() if v == kind):
                return
            if offset == 0:
                items.clear_widgets()
            for row in data["items"]:
                items.add_widget(label(row_label(row), 58))
                items.add_widget(button("View receipt", lambda ref=row["id"]: show_detail(ref), True))
            state["next"] = data["next_offset"]
            more.disabled = state["next"] is None
            if not data["items"] and offset == 0:
                status.text = "No transactions found."
        if offset == 0:
            items.clear_widgets()
            state["next"] = None
            more.disabled = True
        run(lambda: manager.auth_client.transactions(kind, offset), render, status)

    def next_page():
        if state["next"] is not None:
            load(state["next"])

    more = button("Load more", next_page, True)
    more.disabled = True
    body.add_widget(more)
    body.add_widget(button("Refresh / apply filter", lambda: load(), True))
    body.add_widget(button("Back to home", lambda: go("home"), True))
    nav(outer)
    screen.bind(on_pre_enter=lambda *_: load())
    screen.bind(on_leave=lambda *_: items.clear_widgets())
    detail.bind(on_leave=lambda *_: setattr(detail_label, "text", ""))

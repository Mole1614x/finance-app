"""Fictional service catalog, explicit confirmation, cashback and orders."""
from copy import copy
from uuid import uuid4
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
try:
    from .onboarding_ui import label, button
    from .dashboard_data import inr
except ImportError:
    from onboarding_ui import label, button
    from dashboard_data import inr

def install_service_screens(manager, make, nav, go, run):
    screen, outer, body = make("services", "Bills and recharge")
    body.add_widget(label("Fictional providers only. No real bills, phone numbers or customer IDs.", 80))
    catalog_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
    catalog_box.bind(minimum_height=catalog_box.setter("height"))
    body.add_widget(catalog_box)
    status = label("", 72)
    body.add_widget(status)
    draft = {}

    _, confirm_outer, confirm_body = make("service_confirm", "Confirm demo purchase")
    summary = label("", 140)
    message = label("", 100)
    confirm_body.add_widget(summary)
    confirm_body.add_widget(message)

    def prepare(product):
        token = manager.auth_client.access
        if draft.get("attempted") and draft.get("token") == token:
            status.text = "Resolve the previous purchase using its existing reference."
            go("service_confirm")
            return
        draft.clear()
        draft.update(product=product, key=str(uuid4()), token=token, attempted=False)
        summary.text = product["provider"] + "\n" + inr(product["amount_minor"]) + "\nDemo cashback: " + inr(product["cashback_minor"])
        message.text = "Confirm simulated purchase."
        go("service_confirm")

    def execute():
        if not draft or draft.get("token") != manager.auth_client.access:
            message.text = "Session changed. Return to the catalog."
            return
        client = copy(manager.auth_client)
        product, key = draft["product"], draft["key"]
        draft["attempted"] = True
        def complete(data):
            draft.clear()
            summary.text = "Completed: " + inr(data["amount_minor"]) + "\nCashback: " + inr(data["cashback_minor"])
            message.text = "Demo order reference: " + data["id"]
        run(lambda: client.purchase_service(product["sku"], product["bill_cycle"], key), complete, message)

    def back():
        if draft.get("attempted") and draft.get("token") == manager.auth_client.access:
            message.text = "Retry using the same reference. Only discard after a definite rejection."
            return
        draft.clear()
        go("services")

    def discard():
        draft.clear()
        go("services")

    confirm_body.add_widget(button("Confirm / retry same purchase", execute))
    confirm_body.add_widget(button("Back to services", back, True))
    confirm_body.add_widget(label("A network error may mean the purchase completed. Do not discard an uncertain reference.", 80))
    confirm_body.add_widget(button("Discard reference", discard, True))

    def show(data):
        catalog_box.clear_widgets()
        for product in data["items"]:
            text = product["category"] + " | " + inr(product["amount_minor"])
            if product["kind"] == "bill":
                text += " | " + ("Paid" if product["paid"] else "Due " + product["due_date"])
            catalog_box.add_widget(label(text, 62))
            if not product["paid"]:
                catalog_box.add_widget(button("Review " + product["provider"], lambda p=product: prepare(p), True))
    def load():
        catalog_box.clear_widgets()
        run(manager.auth_client.service_catalog, show, status)
    screen.bind(on_pre_enter=lambda *_: load())
    screen.bind(on_leave=lambda *_: catalog_box.clear_widgets())
    body.add_widget(button("Refresh bills", load, True))
    body.add_widget(button("Service orders", lambda: go("service_orders"), True))
    body.add_widget(button("Rewards", lambda: go("promotions"), True))
    body.add_widget(button("Home", lambda: go("home"), True))
    nav(outer)

    orders, outer, body = make("service_orders", "Service order history")
    orders_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
    orders_box.bind(minimum_height=orders_box.setter("height"))
    body.add_widget(orders_box)
    order_status = label("", 60)
    body.add_widget(order_status)
    def show_orders(data):
        orders_box.clear_widgets()
        for item in data["items"]:
            orders_box.add_widget(label(item["provider"] + "\n" + inr(item["amount_minor"]) + " | Completed\nCashback " + inr(item["cashback_minor"]), 90))
        if not data["items"]:
            order_status.text = "No demo purchases yet."
    def load_orders():
        orders_box.clear_widgets()
        run(manager.auth_client.service_orders, show_orders, order_status)
    orders.bind(on_pre_enter=lambda *_: load_orders())
    orders.bind(on_leave=lambda *_: orders_box.clear_widgets())
    body.add_widget(button("Refresh", load_orders, True))
    body.add_widget(button("Back", lambda: go("services"), True))
    nav(outer)

    rewards, outer, body = make("promotions", "Rewards and offers")
    earned = label("", 80, "H5")
    offer = label("", 100)
    reward_status = label("", 60)
    for widget in (earned, offer, reward_status):
        body.add_widget(widget)
    def show_rewards(data):
        earned.text = "Lifetime demo cashback: " + inr(data["earned_minor"])
        offer.text = data["offer"] + "\nCredited to checking; no separate redeemable balance."
    def load_rewards():
        earned.text = offer.text = ""
        run(manager.auth_client.rewards, show_rewards, reward_status)
    rewards.bind(on_pre_enter=lambda *_: load_rewards())
    body.add_widget(button("Refresh", load_rewards, True))
    body.add_widget(button("Back home", lambda: go("home"), True))
    nav(outer)

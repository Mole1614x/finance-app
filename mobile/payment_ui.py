"""Payment screens using existing native UI primitives; no live payment rails."""
from copy import copy
from uuid import uuid4
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.core.clipboard import Clipboard
try:
    from .onboarding_ui import label, button, field
    from .dashboard_data import inr
    from .payment_data import parse_amount, parse_identifier
except ImportError:
    from onboarding_ui import label, button, field
    from dashboard_data import inr
    from payment_data import parse_amount, parse_identifier

class QRDisplay(Widget):
    def __init__(self, **kwargs):
        super().__init__(size_hint_y=None, height=dp(240), **kwargs)
        self.matrix = []
        self.bind(pos=self.draw, size=self.draw)

    def show(self, matrix):
        self.matrix = matrix
        self.draw()

    def draw(self, *_):
        self.canvas.clear()
        if not self.matrix:
            return
        n = len(self.matrix)
        step = int(min(self.width, self.height) / n)
        if not step:
            return
        side = n * step
        x, y = round(self.center_x-side/2), round(self.center_y-side/2)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=(x, y), size=(side, side))
            Color(0, 0, 0, 1)
            for row, values in enumerate(self.matrix):
                for col, dark in enumerate(values):
                    if dark:
                        Rectangle(pos=(x+col*step, y+(n-1-row)*step), size=(step, step))

def install_payment_screens(manager, make, nav, go, run):
    send, outer, body = make("send", "Send demo money")
    body.add_widget(label("ARTH demo network only. No real funds.", 56))
    recipient = field("ARTH demo payment identifier")
    amount = field("Amount in INR")
    send_status = label("", 64)
    for item in (recipient, amount, send_status):
        body.add_widget(item)

    draft = {}
    confirmation, confirm_outer, confirm_body = make("payment_confirm", "Confirm payment")
    summary = label("", 112)
    confirm_status = label("", 84)
    confirm_body.add_widget(summary)
    confirm_body.add_widget(confirm_status)
    success, success_outer, success_body = make("payment_success", "Payment successful")
    success_copy = label("", 128)
    success_body.add_widget(success_copy)
    success_body.add_widget(button("Return home", lambda: go("home")))
    nav(success_outer)

    def prepare():
        if draft.get("attempted") and draft.get("token") == manager.auth_client.access:
            send_status.text = "Previous payment outcome is unresolved. Retry the same confirmation first."
            go("payment_confirm")
            return
        try:
            ident, minor = parse_identifier(recipient.text), parse_amount(amount.text)
        except ValueError as exc:
            send_status.text = str(exc)
            return
        client = copy(manager.auth_client)
        def ready(data):
            draft.clear()
            draft.update(identifier=data["payment_id"], amount=minor,
                         key=str(uuid4()), token=client.access, attempted=False)
            summary.text = inr(minor) + "\nTo " + data["payment_id"]
            confirm_status.text = "Confirm simulated transfer."
            go("payment_confirm")
        run(lambda: client.resolve_payment(ident), ready, send_status)

    def execute():
        if not draft or draft.get("token") != manager.auth_client.access:
            confirm_status.text = "Session changed. Start a new payment."
            return
        client = copy(manager.auth_client)
        ident, minor, key = draft["identifier"], draft["amount"], draft["key"]
        draft["attempted"] = True
        def completed(data):
            success_copy.text = inr(data["amount_minor"]) + "\nSimulated transfer completed.\nReference: " + data["id"]
            draft.clear()
            recipient.text = amount.text = ""
            go("payment_success")
        run(lambda: client.send_payment(ident, minor, key), completed, confirm_status)

    def check_status():
        if not draft.get("attempted") or draft.get("token") != manager.auth_client.access:
            confirm_status.text = "No attempted payment in this session."
            return
        client = copy(manager.auth_client)
        key = draft["key"]
        def checked(data):
            if data["status"] == "completed":
                transaction = data["transaction"]
                success_copy.text = inr(transaction["amount_minor"]) + "\nSimulated transfer completed.\nReference: " + transaction["payment_reference"]
                draft.clear()
                recipient.text = amount.text = ""
                go("payment_success")
            else:
                confirm_status.text = "Outcome unknown. Retry only with the same reference."
        run(lambda: client.lookup_payment(key), checked, confirm_status)

    def back():
        if draft.get("attempted") and draft.get("token") == manager.auth_client.access:
            confirm_status.text = "Retry with the same reference to resolve the payment. For a definite rejection, discard it."
            return
        draft.clear()
        go("send")

    def discard():
        # Explicitly warned: unknown outcomes may already have succeeded.
        draft.clear()
        go("send")

    body.add_widget(button("Review transfer", prepare))
    body.add_widget(button("Back", lambda: go("home"), True))
    nav(outer)
    confirm_body.add_widget(button("Confirm / retry same payment", execute))
    confirm_body.add_widget(button("Check payment status", check_status, True))
    confirm_body.add_widget(button("Back", back, True))
    confirm_body.add_widget(label("Only discard after a definite rejection. A network error may mean the transfer already completed.", 80))
    confirm_body.add_widget(button("Discard reference", discard, True))

    receive, outer, body = make("receive", "Receive demo money")
    qr = QRDisplay()
    identifier = label("", 90)
    receive_status = label("", 60)
    body.add_widget(qr)
    body.add_widget(identifier)
    body.add_widget(receive_status)
    def show(data):
        qr.show(data["qr_matrix"])
        identifier.text = data["payment_id"]
    def load():
        qr.show([])
        identifier.text = ""
        run(manager.auth_client.receive_payment, show, receive_status)
    receive.bind(on_pre_enter=lambda *_: load())
    def copy_identifier():
        if identifier.text.startswith("arth-demo:"):
            Clipboard.copy(identifier.text)
            receive_status.text = "Demo identifier copied."
    body.add_widget(button("Copy payment identifier", copy_identifier, True))
    body.add_widget(button("Refresh QR", load, True))
    receive.bind(on_leave=lambda *_: (qr.show([]), setattr(identifier, "text", "")))
    body.add_widget(button("Back", lambda: go("home"), True))
    nav(outer)

    scan, outer, body = make("scan", "Pay from QR")
    body.add_widget(label("Paste the decoded text from an ARTH demo QR. Live camera scanning is not implemented.", 100))
    payload = field("Decoded QR text")
    scan_status = label("", 60)
    body.add_widget(payload)
    body.add_widget(scan_status)
    def use_payload():
        try:
            recipient.text = parse_identifier(payload.text)
            payload.text = ""
            go("send")
        except ValueError as exc:
            scan_status.text = str(exc)
    body.add_widget(button("Use QR identifier", use_payload))
    body.add_widget(button("Back", lambda: go("home"), True))
    nav(outer)

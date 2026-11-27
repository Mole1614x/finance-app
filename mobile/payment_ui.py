"""Payment screens using existing native UI primitives; no live payment rails."""
from copy import copy
from sqlite3 import Error as SQLiteError
from kivymd.app import MDApp
from uuid import uuid4
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.core.clipboard import Clipboard
try:
    from .onboarding_ui import label, button, field
    from .dashboard_data import inr
    from .payment_data import parse_amount, parse_identifier
    from .pending_payment import PendingStore
    from .camera_ui import DemoScanner
except ImportError:
    from onboarding_ui import label, button, field
    from dashboard_data import inr
    from payment_data import parse_amount, parse_identifier
    from pending_payment import PendingStore
    from camera_ui import DemoScanner

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

    def store():
        return PendingStore(MDApp.get_running_app().user_data_dir)

    def storage_error():
        return "Cannot access private recovery storage. No new transfer was submitted."

    def load_pending(client):
        owner = client.profile()["id"]
        return owner, store().get(client.base, owner)

    def open_pending(owner, record, token):
        draft.clear()
        draft.update(identifier=record["recipient"], amount=record["amount_minor"],
                     key=record["request_key"], owner=owner, token=token, attempted=True)
        summary.text = inr(draft["amount"]) + "\nTo " + draft["identifier"]
        confirm_status.text = "Recovered reference. Check status, retry the same payment, or cancel safely."
        go("payment_confirm")

    def restore():
        if manager.dashboard_busy:
            return
        draft.clear()
        client = copy(manager.auth_client)
        def operation():
            try:
                return load_pending(client)
            except (OSError, SQLiteError, ValueError):
                raise ValueError(storage_error()) from None
        def ready(value):
            owner, record = value
            if record:
                open_pending(owner, record, client.access)
        run(operation, ready, send_status)

    def prepare():
        if manager.dashboard_busy:
            return
        try:
            ident, minor = parse_identifier(recipient.text), parse_amount(amount.text)
        except ValueError as exc:
            send_status.text = str(exc)
            return
        client = copy(manager.auth_client)
        def operation():
            try:
                owner, record = load_pending(client)
            except (OSError, SQLiteError, ValueError):
                raise ValueError(storage_error()) from None
            if record:
                return owner, record, None
            return owner, None, client.resolve_payment(ident)
        def ready(value):
            owner, record, data = value
            if record:
                open_pending(owner, record, client.access)
                return
            draft.clear()
            draft.update(identifier=data["payment_id"], amount=minor, owner=owner,
                         key=str(uuid4()), token=client.access, attempted=False)
            summary.text = inr(minor) + "\nTo " + data["payment_id"]
            confirm_status.text = "Confirm simulated transfer."
            go("payment_confirm")
        run(operation, ready, send_status)

    def valid():
        return bool(draft and draft.get("token") == manager.auth_client.access and not manager.dashboard_busy)

    def clear_known(client, saved):
        try:
            store().clear(client.base, saved["owner"], saved["key"])
            return True
        except (OSError, SQLiteError, ValueError):
            return False

    def completed(data, cleared):
        success_copy.text = inr(data["amount_minor"]) + "\nSimulated transfer completed.\nReference: " + data["id"]
        if not cleared:
            success_copy.text += "\nLocal reference retained; check status again before another payment."
        draft.clear()
        recipient.text = amount.text = ""
        go("payment_success")

    def execute():
        if not valid():
            return
        client = copy(manager.auth_client)
        saved = dict(draft)
        def operation():
            try:
                # Commit the original key locally before any network mutation.
                store().reserve(client.base, saved["owner"], saved["key"], saved["identifier"], saved["amount"])
            except (OSError, SQLiteError, ValueError):
                raise ValueError(storage_error()) from None
            data = client.send_payment(saved["identifier"], saved["amount"], saved["key"])
            return data, clear_known(client, saved)
        draft["attempted"] = True
        run(operation, lambda result: completed(*result), confirm_status)

    def recover(cancel=False):
        if not valid() or not draft.get("attempted"):
            confirm_status.text = "No attempted payment to recover."
            return
        client = copy(manager.auth_client)
        saved = dict(draft)
        def operation():
            result = (client.cancel_payment if cancel else client.recover_payment)(saved["key"])
            if result["status"] == "completed":
                receipt = result["receipt"]
                if receipt["amount_minor"] != saved["amount"] or receipt["recipient_payment_id"] != saved["identifier"]:
                    raise ValueError("Reference mismatch. Local record retained.")
            cleared = clear_known(client, saved) if result["status"] in ("completed", "cancelled") else False
            return result, cleared
        def checked(value):
            result, cleared = value
            if result["status"] == "completed":
                completed(result["receipt"], cleared)
            elif result["status"] == "cancelled":
                if cleared:
                    draft.clear()
                    recipient.text = amount.text = ""
                    go("send")
                    send_status.text = "Payment reference cancelled. No funds moved."
                else:
                    confirm_status.text = "Cancelled on server; local cleanup failed. Check status again."
            else:
                confirm_status.text = "Outcome unknown. Retry the same reference or cancel it on the server."
        run(operation, checked, confirm_status)

    def back():
        if manager.dashboard_busy:
            return
        draft.clear()
        go("send")

    send.bind(on_pre_enter=lambda *_: restore())
    body.add_widget(button("Recover pending payment", restore, True))
    body.add_widget(button("Review transfer", prepare))
    body.add_widget(button("Back", lambda: go("home"), True))
    nav(outer)
    confirm_body.add_widget(button("Confirm / retry same payment", execute))
    confirm_body.add_widget(button("Check payment status", recover, True))
    confirm_body.add_widget(button("Back", back, True))
    confirm_body.add_widget(label("Cancellation prevents a future send with this key; an already committed payment cannot be reversed.", 80))
    confirm_body.add_widget(button("Cancel pending reference", lambda: recover(True), True))

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
    body.add_widget(label("Scan an ARTH demo QR locally or paste its decoded text. Camera access is optional.", 100))
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
    def scanned(value):
        payload.text = value
        scan_status.text = "ARTH identifier detected. Choose Use QR identifier to continue."
    scanner = DemoScanner(scanned, lambda message: setattr(scan_status, "text", message))
    manager.stop_demo_camera = scanner.stop
    body.add_widget(scanner)
    body.add_widget(button("Start camera", scanner.start))
    body.add_widget(button("Stop camera", scanner.stop, True))
    scan.bind(on_pre_leave=lambda *_: scanner.stop())
    body.add_widget(button("Use QR identifier", use_payload))
    body.add_widget(button("Back", lambda: go("home"), True))
    nav(outer)

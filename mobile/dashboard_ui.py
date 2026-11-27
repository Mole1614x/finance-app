"""Native dashboard and navigation; original artwork pending asset access."""
from threading import Thread
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDFlatButton
try:
    from . import theme
    from .dashboard_data import inr, chart_fractions
    from .onboarding_ui import label, panel, button, field
    from .api import APIError
except ImportError:
    import theme
    from dashboard_data import inr, chart_fractions
    from onboarding_ui import label, panel, button, field
    from api import APIError


class CashflowChart(Widget):
    def __init__(self, **kwargs):
        super().__init__(size_hint_y=None, height=dp(160), **kwargs)
        self.values = []
        self.bind(pos=self.draw, size=self.draw)

    def update_values(self, values):
        self.values = chart_fractions(values)
        self.draw()

    def draw(self, *_):
        self.canvas.clear()
        if not self.values:
            return
        mid = self.center_y
        gap = self.width / len(self.values)
        bar = min(dp(9), gap * .65)
        with self.canvas:
            Color(.86, .88, .92, 1)
            Line(points=[self.x, mid, self.right, mid], width=1)
            for i, value in enumerate(self.values):
                if not value:
                    continue
                height = abs(value) * (self.height / 2 - dp(7))
                Color(*get_color_from_hex(theme.PRIMARY if value > 0 else "#F04444"))
                RoundedRectangle(pos=(self.x + gap*(i+.5)-bar/2, mid if value > 0 else mid-height),
                                 size=(bar, height), radius=[dp(3)])


def install_dashboard(manager: ScreenManager, sign_out):
    busy = False
    manager.dashboard_busy = False
    current_name = label("ARTH", 56, "H5", theme.WHITE)
    menu_name = label("Demo user", 56, "H5")
    balance = label("Loading balance...", 52, "H5", "#087943")
    status = label("", 48)
    chart = CashflowChart()
    profile_name = field("Display name")
    profile_status = label("", 48)

    def go(name):
        if busy:
            return
        if manager.auth_client.access:
            manager.current = name
        else:
            manager.current = "welcome"

    def run(action, done, message):
        nonlocal busy
        if busy:
            return
        busy = True
        manager.dashboard_busy = True
        token = manager.auth_client.access
        message.text = "Loading..."
        def finish(value, error):
            nonlocal busy
            busy = False
            manager.dashboard_busy = False
            if token != manager.auth_client.access:
                return
            message.text = error or ""
            if not error:
                done(value)
        def task():
            try:
                value = action()
                Clock.schedule_once(lambda _: finish(value, None), 0)
            except (APIError, ValueError, KeyError) as exc:
                problem = str(exc)
                Clock.schedule_once(lambda _: finish(None, problem), 0)
        Thread(target=task, daemon=True).start()

    def make(name, title=None):
        screen = Screen(name=name)
        outer = BoxLayout(orientation="vertical")
        scroll, body = panel()
        outer.add_widget(scroll)
        screen.add_widget(outer)
        manager.add_widget(screen)
        if title:
            body.add_widget(label(title, 56, "H4"))
        return screen, outer, body

    def nav(outer):
        row = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(2))
        for name, title in (("home", "Home"), ("notifications", "Alerts"), ("profile", "Profile")):
            b = button(title, lambda target=name: go(target), True)
            row.add_widget(b)
        outer.add_widget(row)

    def update_home(data):
        name = data["display_name"]
        current_name.text = "Welcome, " + name
        menu_name.text = name
        balance.text = inr(data["balance_minor"])
        chart.update_values(data["cashflow_minor"])
        recent.text = "\n".join(row_label(r) for r in data["recent_transactions"][:3]) or "No recent transactions."

    home, outer, body = make("home")
    header = MDCard(orientation="vertical", size_hint_y=None, height=dp(176),
                    radius=[dp(30)], padding=dp(12), md_bg_color=get_color_from_hex(theme.PRIMARY))
    header.add_widget(button("Menu", lambda: go("menu"), True))
    header.add_widget(current_name)
    header.add_widget(label("ARTH | DEMO", 28, "Caption", theme.WHITE))
    body.add_widget(header)
    card = MDCard(orientation="vertical", size_hint_y=None, height=dp(325),
                  radius=[dp(theme.BALANCE_RADIUS)], padding=dp(18), elevation=2)
    card.add_widget(label("Your total demo balance", 32))
    card.add_widget(balance)
    card.add_widget(chart)
    card.add_widget(label("Current month net demo cashflow (UTC)", 32, "Caption"))
    body.add_widget(card)
    body.add_widget(button("Check your bank accounts", lambda: go("accounts")))
    body.add_widget(label("Quick actions", 36, "H6"))
    actions = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
    actions.bind(minimum_height=actions.setter("height"))
    for name, title in (("scan", "Scan & Pay"), ("send", "Send money"), ("receive", "Receive money"), ("transactions", "Transaction history")):
        actions.add_widget(button(title, lambda target=name: go(target), True))
    body.add_widget(actions)
    body.add_widget(button("Bills and recharge", lambda: go("services")))
    body.add_widget(button("Rewards and offers", lambda: go("promotions"), True))
    body.add_widget(button("Financial insights", lambda: go("analytics")))
    recent = label("", 190)
    body.add_widget(label("Recent transactions", 38, "H6"))
    body.add_widget(recent)
    body.add_widget(status)
    body.add_widget(button("Refresh", lambda: load(), True))
    nav(outer)
    def load():
        balance.text = "Loading balance..."
        recent.text = ""
        chart.update_values([])
        run(manager.auth_client.dashboard, update_home, status)
    home.bind(on_pre_enter=lambda *_: load())
    home.bind(on_leave=lambda *_: setattr(recent, "text", ""))

    menu, _, body = make("menu", "ARTH")
    body.add_widget(menu_name)
    for name, title in (("home", "Home"), ("payments", "Payments"), ("transactions", "Transactions"),
                        ("accounts", "Bank accounts / My Cards"), ("promotions", "Promotions"),
                        ("savings", "Savings"), ("analytics", "Financial insights"), ("settings", "Settings"), ("profile", "Profile")):
        body.add_widget(button(title, lambda target=name: go(target), True))
    body.add_widget(button("Sign out", sign_out))

    profile, outer, body = make("profile", "Profile")
    body.add_widget(profile_name)
    body.add_widget(profile_status)
    def profile_loaded(data):
        profile_name.text = data["display_name"]
    profile.bind(on_pre_enter=lambda *_: run(manager.auth_client.profile, profile_loaded, profile_status))
    profile.bind(on_leave=lambda *_: setattr(profile_name, "text", ""))
    def save():
        value = profile_name.text
        run(lambda: manager.auth_client.update_profile(value),
            lambda data: setattr(profile_status, "text", "Profile saved."), profile_status)
    body.add_widget(button("Save", save))
    body.add_widget(button("Sign out", sign_out, True))
    nav(outer)

    accounts_screen, outer, body = make("accounts", "Demo bank accounts")
    body.add_widget(label("Simulated accounts only. No real bank linking.", 72))
    account_summary = label("", 100)
    account_status = label("", 48)
    body.add_widget(account_summary)
    body.add_widget(account_status)
    def show_accounts(data):
        accounts = data["accounts"]
        account_summary.text = "\n".join(a["kind"].title() + ": " + inr(a["balance_minor"]) for a in accounts) or "No demo accounts. Initialize to receive simulated funds."
    def load_accounts():
        account_summary.text = ""
        run(manager.auth_client.accounts, show_accounts, account_status)
    accounts_screen.bind(on_pre_enter=lambda *_: load_accounts())
    body.add_widget(button("Initialize demo accounts", lambda: run(manager.auth_client.initialize_accounts, show_accounts, account_status)))
    body.add_widget(button("Refresh", load_accounts, True))
    body.add_widget(button("Back to home", lambda: go("home"), True))
    nav(outer)

    try:
        from .payment_ui import install_payment_screens
    except ImportError:
        from payment_ui import install_payment_screens
    install_payment_screens(manager, make, nav, go, run)

    try:
        from .transaction_ui import install_transaction_screens
        from .transaction_data import row_label
    except ImportError:
        from transaction_ui import install_transaction_screens
        from transaction_data import row_label
    install_transaction_screens(manager, make, nav, go, run)

    try:
        from .service_ui import install_service_screens
    except ImportError:
        from service_ui import install_service_screens
    install_service_screens(manager, make, nav, go, run)

    try:
        from .analytics_ui import install_analytics_screens
    except ImportError:
        from analytics_ui import install_analytics_screens
    install_analytics_screens(manager, make, nav, go, run)

    descriptions = {
        "payments": ("Payments", "Select a simulated payment option. No real funds."),
        "notifications": ("Notifications", "No notifications yet."),
        "settings": ("Settings", "Demo mode only. No real banking or payment credentials should be entered."),
    }
    for name, (title, copy) in descriptions.items():
        _, outer, body = make(name, title)
        body.add_widget(label(copy, 110))
        if name == "payments":
            for target, action in (("scan", "Scan & Pay"), ("send", "Send money"), ("receive", "Receive money"), ("services", "Bills and recharge")):
                body.add_widget(button(action, lambda target=target: go(target)))
        body.add_widget(button("Back to home", lambda: go("home"), True))
        nav(outer)

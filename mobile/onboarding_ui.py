"""Provisional native onboarding, pending original Figma asset integration."""
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
try:
    from . import theme, onboarding as demo
except ImportError:  # Buildozer entry point
    import theme
    import onboarding as demo


def label(text, height=48, size="Body1", color=theme.TEXT):
    return MDLabel(text=text, font_style=size, size_hint_y=None, height=dp(height),
                   theme_text_color="Custom", text_color=get_color_from_hex(color),
                   halign="center")


def panel():
    root = BoxLayout(orientation="vertical", padding=dp(30), spacing=dp(16),
                     size_hint_y=None)
    root.bind(minimum_height=root.setter("height"))
    scroll = ScrollView(do_scroll_x=False)
    scroll.add_widget(root)
    return scroll, root


def button(text, callback, flat=False):
    cls = MDFlatButton if flat else MDRaisedButton
    b = cls(text=text, pos_hint={"center_x": .5})
    if not flat:
        b.md_bg_color = get_color_from_hex(theme.SECONDARY)
    b.bind(on_release=lambda *_: callback())
    return b


def field(hint, password=False, numeric=False):
    return MDTextField(hint_text=hint, password=password, multiline=False,
                       input_filter="int" if numeric else None,
                       size_hint_y=None, height=dp(64))


class Header(BoxLayout):
    def __init__(self, height=250, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None,
                         height=dp(height), padding=dp(20), **kwargs)
        with self.canvas.before:
            Color(*get_color_from_hex(theme.PRIMARY))
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(36)])
        self.bind(pos=self.sync, size=self.sync)
        self.add_widget(label("ARTH", 66, "H3", theme.WHITE))
        self.add_widget(label("Welcome Back", 72, "H5", theme.WHITE))
        self.add_widget(Widget())

    def sync(self, *_):
        self.bg.pos, self.bg.size = self.pos, self.size


def install_onboarding(manager):
    def go(name):
        manager.current = name

    def make(name):
        screen = Screen(name=name)
        scroll, body = panel()
        screen.add_widget(scroll)
        manager.add_widget(screen)
        return body

    splash = make("splash")
    splash.add_widget(Widget(size_hint_y=None, height=dp(260)))
    splash.add_widget(label("ARTH", 80, "H2", theme.PRIMARY))
    splash.add_widget(label("Pay. Manage. Prosper."))
    splash.add_widget(button("Continue", lambda: go("welcome")))

    welcome = make("welcome")
    welcome.add_widget(Header(390))
    welcome.add_widget(button("Sign in", lambda: go("signin")))
    welcome.add_widget(button("Sign up", lambda: go("signup"), True))
    welcome.add_widget(label("Demo only. Do not enter real credentials.", 60))

    for name, title in (("signin", "Sign in"), ("signup", "Sign up")):
        body = make(name)
        body.add_widget(Header())
        body.add_widget(label(title, 52, "H4"))
        body.add_widget(label("Use demo@example.com / demo-only", 48))
        email, password = field("Email address"), field("Password", True)
        body.add_widget(email)
        body.add_widget(password)
        error = label("", 60)
        body.add_widget(error)
        def submit(e=email, p=password, msg=error):
            accepted = demo.demo_credentials(e.text, p.text)
            p.text = ""
            if accepted:
                e.text = ""
                msg.text = ""
                go("phone")
            else:
                msg.text = "Use the provided demo credentials only."
        body.add_widget(button(title, submit))
        body.add_widget(button("Back", lambda: go("welcome"), True))

    phone = make("phone")
    phone.add_widget(Widget(size_hint_y=None, height=dp(220)))
    phone.add_widget(label("OTP Verification", 50, "H5"))
    phone.add_widget(label("Demo verification only. No SMS is sent.", 64))
    number = field("+91 demo number", numeric=True)
    phone.add_widget(number)
    phone.add_widget(label("Use 9000000000"))
    phone_error = label("", 48)
    phone.add_widget(phone_error)
    def request_code():
        if demo.demo_phone(number.text):
            number.text = ""
            phone_error.text = ""
            go("otp")
        else:
            phone_error.text = "Use the provided demo number."
    phone.add_widget(button("Get OTP", request_code))
    phone.add_widget(button("Back", lambda: go("welcome"), True))

    otp = make("otp")
    otp.add_widget(Widget(size_hint_y=None, height=dp(220)))
    otp.add_widget(label("OTP Verification", 50, "H5"))
    otp.add_widget(label("Demo code: 7358"))
    code = field("Enter four-digit demo code", numeric=True)
    otp.add_widget(code)
    otp_error = label("", 48)
    otp.add_widget(otp_error)
    def verify():
        accepted = demo.demo_code(code.text)
        code.text = ""
        if accepted:
            otp_error.text = ""
            go("home")
        else:
            otp_error.text = "Incorrect demo code."
    otp.add_widget(button("Verify", verify))
    otp.add_widget(button("Resend demo code", lambda: setattr(otp_error, "text", "Demo code: 7358"), True))
    otp.add_widget(button("Back", lambda: go("phone"), True))
    manager.current = "splash"
    Clock.schedule_once(lambda _: go("welcome") if manager.current == "splash" else None, 1.5)

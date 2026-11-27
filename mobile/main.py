"""Provisional ARTH mobile shell; never processes real payments."""
from threading import Thread
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.core.window import Window
from kivymd.app import MDApp
try:
    from .onboarding_ui import install_onboarding
except ImportError:
    from onboarding_ui import install_onboarding

KV = """
ScreenManager:
    Screen:
        name: 'home'
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(24)
            spacing: dp(20)
            MDLabel:
                text: 'Good morning'
                font_style: 'H5'
                size_hint_y: None
                height: dp(64)
            MDCard:
                orientation: 'vertical'
                padding: dp(24)
                radius: [dp(44)]
                elevation: 2
                size_hint_y: None
                height: dp(230)
                MDLabel:
                    text: 'Your total demo balance'
                MDLabel:
                    text: 'INR 8,500.00'
                    font_style: 'H4'
                    theme_text_color: 'Custom'
                    text_color: .125, .788, .408, 1
                MDLabel:
                    text: 'Sample data only'
            MDRaisedButton:
                text: 'Payment features (preview)'
                pos_hint: {'center_x': .5}
                on_release: root.current = 'payments'
            Widget:
            MDFlatButton:
                text: 'Sign out'
                on_release: app.sign_out()
    Screen:
        name: 'payments'
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(24)
            spacing: dp(16)
            MDLabel:
                text: 'Payments'
                font_style: 'H4'
            MDLabel:
                text: 'Transfers, QR scanning and payment history are planned. No real or simulated transfer is executed by this screen.'
                halign: 'center'
            MDFlatButton:
                text: 'Return to home'
                on_release: root.current = 'home'
"""

class ArthApp(MDApp):
    def sign_out(self):
        client = self.root.auth_client
        def revoke():
            try:
                client.logout()
            except Exception:
                pass  # Local tokens are discarded even when offline.
        Thread(target=revoke, daemon=True).start()
        self.root.current = 'welcome'

    def build(self):
        self.title = "ARTH"
        self.theme_cls.primary_palette = "Blue"
        Window.clearcolor = (1, 1, 1, 1)
        manager = Builder.load_string(KV)
        install_onboarding(manager)
        return manager

if __name__ == "__main__":
    ArthApp().run()

"""ARTH mobile application — development demo only."""
from threading import Thread
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
try:
    from .onboarding_ui import install_onboarding
    from .dashboard_ui import install_dashboard
except ImportError:
    from onboarding_ui import install_onboarding
    from dashboard_ui import install_dashboard

class ArthApp(MDApp):
    def sign_out(self):
        client = self.root.auth_client
        # Snapshot the old session so a later login cannot be cleared by logout.
        from copy import copy
        old = copy(client)
        client.access = client.refresh = client.challenge = None
        def revoke():
            try:
                old.logout()
            except Exception:
                pass
        Thread(target=revoke, daemon=True).start()
        self.root.current = "welcome"

    def build(self):
        self.title = "ARTH"
        self.theme_cls.primary_palette = "Blue"
        Window.clearcolor = (1, 1, 1, 1)
        manager = ScreenManager()
        install_dashboard(manager, self.sign_out)
        install_onboarding(manager)
        return manager

if __name__ == "__main__":
    ArthApp().run()

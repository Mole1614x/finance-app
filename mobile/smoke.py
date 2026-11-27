"""Desktop graphical smoke test; run under a display server (Xvfb in CI)."""
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from mobile.main import ArthApp
from mobile.ui_components import ActionButton

def run():
    app = ArthApp()
    errors = []
    def inspect(_):
        try:
            manager = app.root
            manager.transition = NoTransition()
            required = {"splash", "welcome", "signin", "signup", "phone", "otp",
                        "home", "menu", "accounts", "send", "receive", "scan",
                        "transactions", "transaction_receipt", "services",
                        "promotions", "analytics", "savings", "assistant"}
            assert required <= set(manager.screen_names)
            manager.current = "welcome"
            signin = next(w for w in manager.current_screen.walk()
                          if isinstance(w, ActionButton) and w.text == "Sign in")
            signin.dispatch("on_release")
            assert manager.current == "signin"
            Clock.schedule_once(check_layout, .3)
        except Exception as exc:
            errors.append(exc)
            app.stop()

    def check_layout(_):
        try:
            assert app.root.current == "signin"
            buttons = [w for w in app.root.current_screen.walk() if isinstance(w, ActionButton)]
            assert buttons and all(w.width > 0 and w.height >= 48 for w in buttons)
            next(w for w in buttons if w.text == "Back").dispatch("on_release")
            assert app.root.current == "welcome"
        except Exception as exc:
            errors.append(exc)
        finally:
            app.stop()
    Window.size = (375,812)
    Clock.schedule_once(inspect, .4)
    app.run()
    if errors:
        raise errors[0]
    print("ARTH desktop UI smoke passed")

if __name__ == "__main__":
    run()

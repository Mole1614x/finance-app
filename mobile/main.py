"""Provisional ARTH mobile shell; never processes real payments."""
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.core.window import Window
from kivymd.app import MDApp

KV = """
ScreenManager:
    Screen:
        name: 'welcome'
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(30)
            spacing: dp(22)
            canvas.before:
                Color:
                    rgba: 0.078, 0.075, 1, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Widget:
            MDLabel:
                text: 'ARTH'
                font_style: 'H2'
                theme_text_color: 'Custom'
                text_color: 1, 1, 1, 1
                halign: 'center'
            MDLabel:
                text: 'Pay. Manage. Prosper.'
                theme_text_color: 'Custom'
                text_color: 1, 1, 1, 1
                halign: 'center'
            Widget:
            MDRaisedButton:
                text: 'Explore demo'
                pos_hint: {'center_x': .5}
                on_release: root.current = 'home'
            MDLabel:
                text: 'Demo only • No real money'
                halign: 'center'
                theme_text_color: 'Custom'
                text_color: 1, 1, 1, 1
                size_hint_y: None
                height: dp(36)
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
                text: 'Back'
                on_release: root.current = 'welcome'
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
    def build(self):
        self.title = "ARTH"
        self.theme_cls.primary_palette = "Blue"
        Window.clearcolor = (1, 1, 1, 1)
        return Builder.load_string(KV)

if __name__ == "__main__":
    ArthApp().run()

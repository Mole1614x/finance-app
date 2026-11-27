"""Shared native controls; layout refinement independent of missing artwork."""
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
try:
    from . import theme
except ImportError:
    import theme

def label(text, height=48, size="Body1", color=theme.TEXT):
    widget = MDLabel(text=text, font_style=size, size_hint_y=None,
                     height=dp(height), theme_text_color="Custom",
                     text_color=get_color_from_hex(color), halign="center",
                     markup=False)
    def wrap(*_):
        widget.text_size = (max(dp(1), widget.width), None)
    def fit(*_):
        widget.height = max(dp(height), widget.texture_size[1]+dp(8))
    widget.bind(width=wrap, texture_size=fit)
    wrap()
    fit()
    return widget

def panel():
    content = BoxLayout(orientation="vertical", padding=dp(theme.PADDING),
                        spacing=dp(theme.GAP), size_hint=(None,None))
    content.bind(minimum_height=content.setter("height"))
    # Horizontal centering with a readable maximum width on desktop/tablet.
    wrapper = BoxLayout(orientation="horizontal", size_hint_y=None)
    from kivy.uix.widget import Widget
    wrapper.add_widget(Widget())
    wrapper.add_widget(content)
    wrapper.add_widget(Widget())
    content.bind(height=wrapper.setter("height"))
    wrapper.bind(width=lambda w, value: setattr(content, "width", min(value, dp(theme.MAX_CONTENT))))
    scroll = ScrollView(do_scroll_x=False)
    scroll.add_widget(wrapper)
    return scroll, content

class ArthActionButton(Button):
    def __init__(self, text, callback, flat=False, **kwargs):
        super().__init__(text=text, size_hint_y=None, height=dp(theme.MIN_TOUCH),
                         background_normal="", background_down="", background_disabled_normal="",
                         background_color=(0,0,0,0), halign="center", valign="middle",
                         font_size=sp(15), **kwargs)
        self.flat = flat
        with self.canvas.before:
            self.tint = Color(1,1,1,1)
            self.shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(theme.BUTTON_RADIUS)])
        self.bind(pos=self.sync, size=self.sync, state=self.sync, disabled=self.sync,
                  texture_size=self.fit)
        self.bind(on_release=lambda *_: callback())
        self.sync()

    def fit(self, *_):
        self.height = max(dp(theme.MIN_TOUCH), self.texture_size[1]+dp(16))

    def sync(self, *_):
        self.shape.pos, self.shape.size = self.pos, self.size
        self.text_size = (max(dp(1), self.width-dp(20)), None)
        background = theme.SURFACE if self.flat else theme.SECONDARY
        foreground = theme.PRIMARY if self.flat else theme.WHITE
        if self.disabled:
            background, foreground = theme.BORDER, theme.SECONDARY_TEXT
        elif self.state == "down":
            background = theme.BORDER if self.flat else theme.PRIMARY
        self.tint.rgba = get_color_from_hex(background)
        self.color = get_color_from_hex(foreground)

def button(text, callback, flat=False):
    return ArthActionButton(text, callback, flat)

def field(hint, password=False, numeric=False):
    return MDTextField(hint_text=hint, password=password, multiline=False,
                       input_filter="int" if numeric else None,
                       size_hint_y=None, height=dp(64), mode="rectangle")

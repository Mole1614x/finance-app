"""Explicit local camera preview; no frame upload or automatic payment."""
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.camera import Camera
try:
    from .qr_decode import decode_rgba
except ImportError:
    from qr_decode import decode_rgba

class DemoScanner(BoxLayout):
    def __init__(self, found, report, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(240), **kwargs)
        self.found, self.report = found, report
        self.camera = self.event = None
        self.request_generation = 0

    def start(self):
        self.stop()
        generation = self.request_generation
        if platform == "android":
            try:
                from android.permissions import request_permissions, Permission
                def allowed(_, grants):
                    Clock.schedule_once(lambda dt: self._permission_result(generation, all(grants)),0)
                request_permissions([Permission.CAMERA], allowed)
            except Exception:
                self.report("Camera permission unavailable. Paste a decoded identifier.")
        else:
            self._permission_result(generation, True)

    def _permission_result(self, generation, granted):
        if generation != self.request_generation:
            return
        if not granted:
            self.report("Camera permission denied. Paste a decoded identifier.")
            return
        try:
            import cv2
            self.camera = Camera(index=0, resolution=(640,480), play=True)
            self.add_widget(self.camera)
            self.event = Clock.schedule_interval(self.scan, .7)
            self.report("Point the camera at an ARTH demo QR code.")
        except Exception:
            self.stop()
            self.report("Camera or decoder unavailable. Paste a decoded identifier.")

    def scan(self, _):
        try:
            texture = self.camera.texture if self.camera else None
            if texture is None:
                return
            identifier = decode_rgba(texture.pixels, *texture.size)
            if identifier:
                self.stop()
                self.found(identifier)
                return False
        except ValueError:
            self.report("Only ARTH demo QR identifiers are accepted.")
        except Exception:
            self.stop()
            self.report("Camera decoding unavailable. Paste a decoded identifier.")
            return False

    def stop(self):
        self.request_generation += 1
        if self.event:
            self.event.cancel()
            self.event = None
        if self.camera:
            camera, self.camera = self.camera, None
            camera.play = False
            if camera.parent is self:
                self.remove_widget(camera)

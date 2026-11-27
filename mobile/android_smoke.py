"""ADB-opt-in diagnostic, no credentials or ledger writes."""
import json
from threading import Thread
from urllib.request import urlopen

def check(manager):
    required = {"welcome", "signin", "home", "send", "scan", "payment_confirm",
                "risk_review", "transactions", "assistant"}
    try:
        assert required <= set(manager.screen_names)
        assert manager.current in {"splash", "welcome"}
        print("ARTH_ANDROID_UI_OK", flush=True)
    except Exception:
        print("ARTH_ANDROID_UI_FAILED", flush=True)
        raise

    def native_checks():
        try:
            import qrcode
            import numpy as np
            try:
                from .qr_decode import decode_image
            except ImportError:
                from qr_decode import decode_image
            value = "arth-demo:00000000-0000-0000-0000-000000000000"
            qr = qrcode.QRCode(box_size=8, border=4)
            qr.add_data(value)
            qr.make(fit=True)
            image = np.kron(255*(1-np.asarray(qr.get_matrix(), dtype=np.uint8)),
                            np.ones((8,8), dtype=np.uint8))
            assert decode_image(image) == value
            print("ARTH_ANDROID_QR_OK", flush=True)
            with urlopen(manager.auth_client.base + "/health", timeout=5) as response:
                assert json.load(response) == {"status":"ok","mode":"demo"}
            print("ARTH_ANDROID_BACKEND_OK", flush=True)
        except Exception:
            import traceback
            traceback.print_exc()
            print("ARTH_ANDROID_NATIVE_FAILED", flush=True)
    Thread(target=native_checks, daemon=True).start()

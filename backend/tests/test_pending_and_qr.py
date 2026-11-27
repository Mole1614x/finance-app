import pytest
from uuid import uuid4
from mobile.pending_payment import PendingStore
from mobile.qr_decode import decode_image, decode_rgba
import numpy as np
import qrcode

IDENT = "arth-demo:00000000-0000-0000-0000-000000000000"

def test_persist_restart_scope_and_no_overwrite(tmp_path):
    store = PendingStore(tmp_path)
    key = str(uuid4())
    store.reserve("backend-a","owner-a",key,IDENT,50001)
    restarted = PendingStore(tmp_path)
    assert restarted.get("backend-a","owner-a") == {"request_key":key,"recipient":IDENT,"amount_minor":50001}
    assert restarted.get("backend-b","owner-a") is None
    assert restarted.get("backend-a","owner-b") is None
    restarted.reserve("backend-a","owner-a",key,IDENT,50001)
    with pytest.raises(ValueError):
        restarted.reserve("backend-a","owner-a",str(uuid4()),IDENT,50001)
    restarted.clear("backend-a","owner-a",str(uuid4()))
    assert restarted.get("backend-a","owner-a")
    restarted.clear("backend-a","owner-a",key)
    assert PendingStore(tmp_path).get("backend-a","owner-a") is None

def qr_image(text):
    qr = qrcode.QRCode(box_size=8,border=4)
    qr.add_data(text)
    qr.make(fit=True)
    return np.kron(255*(1-np.asarray(qr.get_matrix(),dtype=np.uint8)), np.ones((8,8),dtype=np.uint8))

def test_qr_decoder_accepts_only_arth():
    image = qr_image(IDENT)
    assert decode_image(image) == IDENT
    rgba = np.repeat(image[:,:,None],4,axis=2)
    assert decode_rgba(rgba.tobytes(), image.shape[1], image.shape[0]) == IDENT
    with pytest.raises(ValueError):
        decode_image(qr_image("upi://pay?pa=demo@example.com"))
    assert decode_image(np.full((200,200),255,dtype=np.uint8)) is None

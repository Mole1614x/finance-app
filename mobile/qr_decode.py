"""Local QR decoding. Imports native decoder only when requested."""
try:
    from .payment_data import parse_identifier
except ImportError:
    from payment_data import parse_identifier

def decode_image(image):
    import cv2
    import numpy as np
    frame = np.asarray(image)
    if frame.ndim not in (2,3) or frame.size == 0:
        raise ValueError("Invalid camera image")
    detector = cv2.QRCodeDetector()
    # Kivy camera textures may be vertically flipped.
    for candidate in (frame, np.ascontiguousarray(frame[::-1])):
        text, _, _ = detector.detectAndDecode(candidate)
        if text:
            return parse_identifier(text)
    return None

def decode_rgba(pixels, width, height):
    import numpy as np
    if width <= 0 or height <= 0 or width*height > 4000000:
        raise ValueError("Unsupported camera frame dimensions")
    image = np.frombuffer(pixels, dtype=np.uint8).reshape(height,width,4)
    return decode_image(image[:,:,:3].copy())

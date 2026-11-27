"""Pure display helpers shared by dashboard screens and tests."""
def inr(minor):
    if isinstance(minor, bool) or not isinstance(minor, int):
        raise ValueError("Amounts must use integer minor units")
    sign = "-" if minor < 0 else ""
    whole, paise = divmod(abs(minor), 100)
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        parts = []
        while head:
            parts.insert(0, head[-2:])
            head = head[:-2]
        digits = ",".join(parts + [tail])
    return f"{sign}INR {digits}.{paise:02d}"

def chart_fractions(values):
    scale = max((abs(v) for v in values), default=0) or 1
    return [v / scale for v in values]

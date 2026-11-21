"""Formatting helpers so numbers and dates look identical in every language."""
import datetime as dt

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def inr(n) -> str:
    """Rupees with Indian digit grouping: 1840 -> ₹1,840 ; 123456 -> ₹1,23,456."""
    n = int(round(n))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return "%s₹%s" % (sign, s)


def fmt_date(d) -> str:
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10])
    if isinstance(d, dt.datetime):
        d = d.date()
    return "%d %s %d" % (d.day, MONTHS[d.month - 1], d.year)


def fmt_dt(d: dt.datetime) -> str:
    return "%s, %s" % (fmt_date(d), d.strftime("%H:%M"))


def fmt_hours(h: float) -> str:
    """51.0 -> '51 h', 11.983 -> '11 h 59 m'."""
    neg = h < 0
    h = abs(h)
    total_min = int(h * 60 + 1e-6)
    hh, mm = divmod(total_min, 60)
    out = "%d h" % hh if mm == 0 else "%d h %d m" % (hh, mm)
    return ("-" + out) if neg else out

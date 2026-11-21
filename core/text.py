"""Formatting helpers so numbers and dates look identical in every language."""
import datetime as dt

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def inr(paise) -> str:
    """Money is kept in paise. Shows rupees with Indian digit grouping: 306250 -> ₹3,062.50 ; 229200 -> ₹2,292 ; 12345600 -> ₹1,23,456."""
    paise = int(round(paise))
    sign = "-" if paise < 0 else ""
    rupees, pr = divmod(abs(paise), 100)
    s = str(rupees)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return "%s₹%s%s" % (sign, s, (".%02d" % pr) if pr else "")


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

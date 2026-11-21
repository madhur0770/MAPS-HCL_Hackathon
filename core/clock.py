"""Time helpers. Everything is Indian Standard Time (IST).

`as_of` is the "what time is it for this question" value. It defaults to now, but tests and
judges can pass any time (time travel). DEMO_NOW pins the clock for the whole service.
"""
import datetime as dt
import os

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def parse_dt(s: str) -> dt.datetime:
    """Parse an ISO date or datetime. No timezone means IST."""
    s = s.strip().replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=IST)
    return d.astimezone(IST)


def parse_d(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def real_now() -> dt.datetime:
    fixed = os.getenv("DEMO_NOW")
    if fixed:
        return parse_dt(fixed)
    return dt.datetime.now(IST)


def resolve_as_of(as_of) -> dt.datetime:
    if as_of is None or as_of == "":
        return real_now()
    if isinstance(as_of, dt.datetime):
        return as_of if as_of.tzinfo else as_of.replace(tzinfo=IST)
    return parse_dt(str(as_of))


def iso(d: dt.datetime) -> str:
    return d.astimezone(IST).isoformat(timespec="seconds")

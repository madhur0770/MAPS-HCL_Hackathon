"""Deadlines: when can the passenger still cancel / change boarding station. All measured as the rules say."""
import datetime as dt
from tools import settings as st
from tools.timetable import departure_dt, stops_of


def origin_departure(db, booking):
    first = stops_of(db, booking["train_no"])[0]["station_code"]
    return departure_dt(db, booking["train_no"], booking["journey_date"], first)


def boarding_change_deadline(db, booking, as_of):
    """RUL-010 3.2 + CIR-004: the change must be ACCEPTED MORE than 6 hours before scheduled ORIGIN departure; exactly 6 h is too late."""
    h = st.get_int(db, "boarding_change.cutoff_hours_before_origin", as_of, 6)
    return origin_departure(db, booking) - dt.timedelta(hours=h), h, ("RUL-010", "3.2")


def refund_bands(db, booking, as_of):
    """The cut-off moments (48h, 12h, 4h before departure from the boarding station) as concrete times (RUL-003 3.4)."""
    dep = departure_dt(db, booking["train_no"], booking["journey_date"], booking["from_code"])
    g = lambda n, d: st.get_int(db, n, as_of, d)  # noqa: E731
    return {"departure": dep, "a_until": dep - dt.timedelta(hours=g("cancellation.band_b.upper_hours_inclusive", 48)),
            "b_until": dep - dt.timedelta(hours=g("cancellation.band_c.upper_hours_inclusive", 12)),
            "c_until": dep - dt.timedelta(hours=g("cancellation.band_d.upper_hours_inclusive", 4)),
            "pct_b": g("cancellation.band_b.deduction_percent", 25), "pct_c": g("cancellation.band_c.deduction_percent", 50),
            "pct_d": g("cancellation.band_d.deduction_percent", 75)}

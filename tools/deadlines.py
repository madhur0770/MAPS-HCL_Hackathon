"""Deadlines: when can the passenger still cancel / change boarding station."""
import datetime as dt
from tools import settings as st
from tools.timetable import departure_dt


def boarding_change_deadline(db, booking, as_of):
    h = st.get_int(db, "boarding_change_cutoff_hours", as_of, 24)
    dep = departure_dt(db, booking["train_no"], booking["journey_date"], booking["from_code"])
    return dep - dt.timedelta(hours=h), h, st.source(db, "boarding_change_cutoff_hours", as_of)


def refund_bands(db, booking, as_of):
    """The three cut-off moments (48h, 12h, 4h before departure) as concrete times."""
    dep = departure_dt(db, booking["train_no"], booking["journey_date"], booking["from_code"])
    f, m, n = (st.get_int(db, k, as_of, d) for k, d in (("refund_free_hours", 48), ("refund_mid_hours", 12), ("refund_none_hours", 4)))
    return {"departure": dep, "flat_until": dep - dt.timedelta(hours=f), "mid_until": dep - dt.timedelta(hours=m),
            "none_after": dep - dt.timedelta(hours=n)}

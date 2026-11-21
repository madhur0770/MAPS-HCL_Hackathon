"""Pass a case to a human desk with a short summary. The assistant never promises the outcome."""
import uuid

from core import clock
from assistant import guardrails

DESKS = {"dispute": "Refund Desk", "missed_train": "Refund Desk", "concession": "Concession Desk",
         "human": "Booking Desk", "other": "Booking Desk", "gave_up": "Booking Desk", "not_found": "Booking Desk"}


def pick_desk(text: str, reason: str) -> str:
    import re
    if re.search(r"(disab|handicap|divyang|press|defence|defense|army|veteran|concession|proof|certificate)", text, re.I):
        return "Concession Desk"
    if re.search(r"(refund|missed|miss|chhoot|चूक|छूट|charged|dispute|complain|शिकायत|shikayat)", text, re.I):
        return "Refund Desk"
    return DESKS.get(reason, "Booking Desk")


def create(db, passenger_id, booking_id, reason, user_text, facts, as_of, trace_id):
    """facts: list of short strings the desk should know (already free of full phone/ID numbers)."""
    hid = "HND-" + uuid.uuid4().hex[:8].upper()
    desk = pick_desk(user_text, reason)
    summary = "Passenger %s%s asks: \"%s\". " % (passenger_id, (" about booking " + booking_id) if booking_id else "",
                                                guardrails.mask(user_text)[:300])
    if facts:
        summary += "Facts checked by the assistant: " + " ".join(facts)
    summary += " The assistant made no promise about the outcome."
    db.execute("INSERT INTO handoffs VALUES(?,?,?,?,?,?,?,?,?)",
               (hid, passenger_id, booking_id or "", desk, reason, summary, "open", clock.iso(as_of), trace_id))
    db.commit()
    return {"handoff_id": hid, "desk": desk, "summary": summary}

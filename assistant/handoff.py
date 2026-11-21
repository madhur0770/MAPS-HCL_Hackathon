"""Pass a case to a human desk with a short summary. The assistant never promises the outcome."""
import uuid

from core import clock
from assistant import guardrails

DESKS = {"dispute": "Refund Desk", "missed_train": "Refund Desk", "concession": "Concession Desk",
         "human": "Booking Desk", "other": "Booking Desk", "gave_up": "Booking Desk", "not_found": "Booking Desk"}


import os
import re

SAFETY = re.compile(r"(stole|stolen|theft|robbed|robbery|pickpocket|चोरी|chori|harass|molest|eve.?teas|threat|attack|assault|unsafe|emergency|medical emergency|heart attack|faint|unconscious|\bbomb\b|suspicious (bag|package)|unattended (bag|luggage)|fire\b|stalk|following me|छेड़|धमकी|आपातकाल|ख़तरा|khatre|chhed|dhamki|bachao|help me)", re.I)
PRIVACY = re.compile(r"(my (details|data|phone|aadhaar|id|otp|password) (was|were|got|has been) (leaked|stolen|exposed|shared|hacked)|leaked|someone (logged|accessed|opened) (in )?my|hacked|unauthori[sz]ed|identity (theft|exposure)|data breach|privacy complaint|डेटा लीक)", re.I)
ACTIVE = re.compile(r"(train (is )?(leaving|departing)|at the station|boarding now|already (at|on)|in the train|on board|aaj (ki|ka)|today'?s train|missed my train|miss(ed)? the train|train chhoot|ट्रेन छूट)", re.I)

# RUL-012 section 3.5 acknowledgement targets. Read from the settings table first so a circular can change them.
TARGET_DEFAULTS = {"safety": ("15 minutes", 15), "privacy": ("1 hour", 60), "active_travel": ("2 hours", 120),
                   "refund_dispute": ("1 business day", 1440), "other": ("2 business days", 2880)}
DESK_FOR = {"safety": "Safety Desk", "privacy": "Privacy and Security Desk", "active_travel": "Booking Desk",
            "refund_dispute": "Refund Desk", "other": "Service Desk"}


def emergency_channel() -> str:
    return os.getenv("EMERGENCY_CHANNEL", "Ujjwal Rail Emergency Line 1800-000-0112 (fictional demo number)")


def classify(text: str, reason: str = "other") -> str:
    """RUL-012 category. Safety first, then privacy, then active travel, then refund dispute, then other."""
    if SAFETY.search(text):
        return "safety"
    if PRIVACY.search(text):
        return "privacy"
    if ACTIVE.search(text):
        return "active_travel"
    if re.search(r"concession|disab|divyang|veteran|defen[cs]e|press pass|senior citizen", text, re.I):
        return "other"
    if reason == "missed_train" or re.search(r"(refund|money|charged|dispute|deduct|double|duplicate|wrong status|missing booking|पैसे|रिफंड|paisa|paise)", text, re.I):
        return "refund_dispute"
    return "other"


def target_for(db, category: str, as_of=None):
    try:
        from tools import settings as cfg
        v = cfg.get_int(db, "complaints.ack_target_minutes_" + category, as_of, 0) if as_of else 0
    except Exception:
        v = 0
    label, mins = TARGET_DEFAULTS[category]
    if v:
        mins = v
        label = "%d minutes" % v
    return label, mins


def pick_desk(text: str, reason: str) -> str:
    if re.search(r"(disab|handicap|divyang|press|defence|defense|army|veteran|concession|proof|certificate)", text, re.I):
        return "Concession Desk"
    if re.search(r"(refund|missed|miss|chhoot|चूक|छूट|charged|dispute)", text, re.I):
        return "Refund Desk"
    return DESKS.get(reason, "Booking Desk")


def create(db, passenger_id, booking_id, reason, user_text, facts, as_of, trace_id):
    """facts: list of short strings the desk should know (already free of full phone/ID numbers)."""
    hid = "HND-" + uuid.uuid4().hex[:8].upper()
    cat = classify(user_text, reason)
    label, mins = target_for(db, cat, as_of)
    desk = pick_desk(user_text, reason) if cat in ("other", "refund_dispute") and re.search(r"concession|disab|divyang|veteran|defen[cs]e|press", user_text, re.I) else DESK_FOR[cat]
    summary = "Passenger %s%s asks: \"%s\". " % (passenger_id, (" about booking " + booking_id) if booking_id else "",
                                                guardrails.mask(user_text)[:300])
    if facts:
        summary += "Facts checked by the assistant: " + " ".join(facts)
    summary += " Category: %s. Acknowledgement target: %s." % (cat, label)
    if cat == "safety":
        summary += " Emergency channel given to the passenger: %s." % emergency_channel()
    summary += " The assistant made no promise about the outcome."
    db.execute("INSERT INTO handoffs VALUES(?,?,?,?,?,?,?,?,?)",
               (hid, passenger_id, booking_id or "", desk, reason, summary, "open", clock.iso(as_of), trace_id))
    db.commit()
    return {"handoff_id": hid, "desk": desk, "summary": summary, "category": cat, "ack_target": label, "ack_minutes": mins,
            "emergency_channel": emergency_channel() if cat == "safety" else None}

"""Spelling repair for the words this assistant depends on. Only words close to a known domain word are changed
(difflib ratio >= 0.8, 4+ letters), station names, codes with digits and Devanagari are never touched, so a traveller's
name or a place is not 'corrected'. Station typos are repaired separately in tools/timetable.py."""
import difflib
import re

VOCAB = ["refund", "cancel", "cancellation", "status", "ticket", "tickets", "train", "trains", "booking", "bookings", "tatkal", "luggage", "baggage",
         "boarding", "station", "available", "availability", "seats", "confirm", "confirmed", "waitlist", "tomorrow", "platform", "passenger", "passengers",
         "charge", "charges", "supplement", "complaint", "complain", "refunded", "departure", "arrival", "journey", "travel", "reservation", "schedule",
         "timetable", "sleeper", "premium", "executive", "concession", "discount", "senior", "child", "children", "identity", "proof", "document", "documents",
         "allowed", "carry", "please", "morning", "evening", "afternoon", "night", "friday", "saturday", "sunday", "monday", "tuesday", "wednesday", "thursday"]
ABBR = {"pls": "please", "plz": "please", "u": "you", "wht": "what", "wat": "what", "whn": "when", "hlp": "help", "wnat": "want", "wanna": "want",
        "tmrw": "tomorrow", "tmr": "tomorrow", "frm": "from", "abt": "about", "bkg": "bkg", "cnf": "cnf", "tkt": "ticket", "tkts": "tickets", "reqd": "required"}
_V = set(VOCAB)
# real English words that sit close to a domain word: never "corrected"
SAFE = set("""change changed changes changing chance channel charged charging cancels cancelled cancelling traveller travellers travelled traveler travelers booked books bookings
trained strain stations refunds refunded refunding statue stated states seated sleep sleeping sleepers carries carrier carried married documented discounts concessions
senior seniors children's confirms confirming confirmation platforms platter schedules scheduled arrive arrived arrives arriving depart departs departed reserve reserved
passes passing proofs allowed allow allows morning mornings evenings nights nightly tonight right light flight flights licence license identify identified tickets'""".split())


def fix(text: str, protected=()):
    prot = {p.lower() for p in protected}
    out = []
    for tok in re.split(r"(\W+)", text):
        low = tok.lower()
        if not tok or not re.fullmatch(r"[A-Za-z]+", tok) or low in prot:
            out.append(tok)
            continue
        if low in ABBR:
            out.append(ABBR[low])
            continue
        if len(low) < 5 or low in _V or low in SAFE:
            out.append(tok)
            continue
        m = difflib.get_close_matches(low, VOCAB, n=1, cutoff=0.8)
        out.append(m[0] if m else tok)
    return "".join(out)

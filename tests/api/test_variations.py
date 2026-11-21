"""Many phrasings of the 12 question types in the brief (typos, missing words, Hinglish). Each row: (messages, substring that must be in the LAST reply,
answer_type or None, substrings that must NOT appear). Run for passenger P001 on the demo clock 21 Nov 2026 10:00."""
import pytest
from fastapi.testclient import TestClient
from core import db as dbm, seed
from app.main import make_app

OOS = "I can only help with Ujjwal Rail travel"
ROWS = [
    # find a train
    ("Trains from Arunoday to Chetakgarh on 5 Dec after 6 pm", "UJ1018", "answer", ["UJ1006 Vindhya"]),
    ("train from arunday to chetakgrh tomorow", "22 Nov 2026", "answer", []),
    ("trains arunoday to chetakgarh friday", "27 Nov 2026", "answer", []),
    ("chetakgarh se arunoday kal ki train", "ko Chetakgarh se Arunoday", "answer", []),
    ("trians from arunoday to chetakgarh 25/11", "UJ1006", "answer", []),
    ("trains from arunoday to chetakgarh tomorrow morning", "UJ1006", "answer", []),
    # seats and fares
    ("Is there a 3AC seat on UJ1006 this Friday, and how much is it", "₹2,312.50", "answer", ["Please tell me"]),
    ("seat availability UJ1006 AC3 25 nov", "AC3 36 available", "answer", []),
    ("fare for sleeper UJ1024 23 nov", "SL", "answer", ["station called"]),
    ("UJ1006 25 nov", "UJ1006", "answer", []),
    ("is there a seat on 12123 this friday", "could not find train 12123", "clarification", []),
    # my booking
    ("What's the status of my ticket for tomorrow?", "BKG0025", "answer", ["Which booking"]),
    ("staus bkg0001", "Booking BKG0001", "answer", []),
    ("mera ticket confirm hai kya", "BKG0025", "clarification", []),
    ("bkg-0001 status", "Booking BKG0001", "answer", []),
    # refund
    ("If I cancel my 2AC ticket now, how much will I get back?", "₹2,802", "answer", ["FAQ"]),
    ("refnd for BKG0001", "₹2,802", "answer", []),
    ("Kal ki train cancel karni hai, kitna paisa wapas milega?", "₹2,234", "answer", []),
    ("what refund for UJ1006 ticket", "₹2,802", "answer", []),
    ("refund?", "Which booking", "clarification", []),
    # rules
    ("Can I carry my pet dog?", "RUL-008", "answer", []),
    ("Which ID proof is accepted?", "RUL-006 3.2", "answer", []),
    ("konsa ID chalega", "RUL-006", "answer", []),
    ("tatkal booking timing", "RUL-005 3.2", "answer", []),
    ("how long does refund take", "FAQ-017", "answer", []),
    ("what is 2+2", OOS, "not_found", []),
    # rule changed
    ("Is the Tatkal charge for AC2 still 400", "₹450", "answer", []),
    ("tatkal charge sleeper", "₹180", "answer", []),
    ("is cancellation charge for AC2 still 240", "₹260", "answer", []),
    ("tatkal ka charge kitna hai AC2", "₹450", "answer", []),
    # make a change
    ("Cancel my ticket for tomorrow", "BKG0025", "confirm_needed", []),
    ("cancle BKG0001", "Preview", "confirm_needed", []),
    ("cancel all my bookings", "one booking at a time", "clarification", []),
    ("Change my boarding station to Anandpur North", "Which booking", "clarification", ["later stop"]),
    ("change boarding of BKG0001 to Kaveripuram", "Preview", "confirm_needed", []),
    ("i want to change something", "boarding station", "refusal", []),
    ("book UJ1006 AC2 25 nov for Neha 31", "Preview", "confirm_needed", ["station called"]),
    # needs a person
    ("My train was cancelled 10 days ago and I still haven't got my money. I want to complain", "Refund Desk", "handed_to_human", []),
    ("I want to complain", "Service Desk", "handed_to_human", []),
    ("talk to customer care", "Service Desk", "handed_to_human", []),
    ("someone stole my bag in the train", "Safety Desk", "handed_to_human", []),
    # mixed language
    ("BKG0001 रद्द करने पर कितना रिफंड मिलेगा", "₹2,802", "answer", []),
    ("mujhe pet le jaana hai kya rule hai", "RUL-008", "answer", []),
    # too vague
    ("I need a ticket to Delhi", "Delhi", "clarification", ["not sure I understood"]),
    ("i need a ticket delhi", "Delhi", "clarification", ["not sure I understood"]),
    ("ticket to delhi 25 nov", "Delhi", "clarification", ["Booking opens"]),
    ("from delhi to pune", "Delhi", "clarification", []),
    ("I need a ticket", "travelling from", "clarification", []),
    ("chetakgarh", "start your journey", "clarification", []),
    # not covered
    ("Book me a hotel near New Delhi station", OOS, "not_found", []),
    ("hotel near arunoday", OOS, "not_found", ["start your journey"]),
    ("book a flight to mumbai", OOS, "not_found", []),
    ("tell me a joke", OOS, "not_found", []),
    # someone else's booking
    ("What's the status of booking UR-48213? It's my friend's", "can't find UR-48213", "not_found", []),
    ("refund for BKG0003", "can't find BKG0003", "not_found", []),
    ("show bookings of P002", "own account", "refusal", []),
]


@pytest.fixture(scope="module")
def client():
    import os
    os.environ["DEMO_NOW"] = "2026-11-21T10:00:00+05:30"
    d = dbm.connect(":memory:")
    seed.seed(d)
    return TestClient(make_app(d))


@pytest.mark.parametrize("msg,must,atype,mustnot", ROWS, ids=[r[0][:40] for r in ROWS])
def test_variation(client, msg, must, atype, mustnot):
    r = client.post("/chat", json={"session_id": "v%d" % (abs(hash(msg)) % 10**9), "message": msg}, headers={"X-Passenger-Id": "P001"}).json()
    assert must in r["answer"], r["answer"]
    if atype:
        assert r["answer_type"] == atype, (r["answer_type"], r["answer"])
    for bad in mustnot:
        assert bad not in r["answer"], r["answer"]


def test_class_not_on_train_and_name_and_age(client_factory=None):
    """3AC asked on a train without it: say so, keep the booking going, accept 'Madhur and 24'."""
    import os
    from fastapi.testclient import TestClient
    from core import db as dbm, seed
    from app.main import make_app
    d = dbm.connect(":memory:"); seed.seed(d); c = TestClient(make_app(d))
    def say(m):
        return c.post("/chat", json={"session_id": "77", "message": m}, headers={"X-Passenger-Id": "P001"}).json()
    r = say("is there 3AC from chet to arunoday on 30-11-2026")
    assert "has AC3" in r["answer"] and "AC2" in r["answer"]
    assert "traveller" in say("book one 3AC ticket in this train")["answer"]
    assert "does not have AC3" in say("Madhur and 24")["answer"]
    r = say("AC2")
    assert r["answer_type"] == "confirm_needed" and "Madhur (24)" in r["answer"]
